"""Checker agent — evaluates actual code diffs from sandbox sessions via claude CLI."""

import json
import subprocess
from dataclasses import dataclass

from ..config import BenchmarkConfig, CheckerScores, Task, TokenUsage

CHECKER_SYSTEM_PROMPT = """\
You are a senior code reviewer evaluating an AI coding agent's work on a \
software engineering task. You are given the TASK the agent was asked to do, \
the GIT DIFF of what the agent actually changed, and the agent's SESSION \
TRANSCRIPT (its reasoning and tool use).

Evaluate the ACTUAL CODE CHANGES (the diff), not just the agent's words.

## Evaluation Rubric

Score each dimension 1-5:

### 1. Correctness (weight: 0.35)
- 5: The diff correctly solves the stated problem, no bugs introduced
- 4: Solves the problem with minor issues that don't affect core functionality
- 3: Partially solves the problem, or solves it with notable issues
- 2: Attempt is on the right track but doesn't actually fix the problem
- 1: Wrong approach, broken code, or no meaningful changes

### 2. Completeness (weight: 0.25)
- 5: All aspects of the task are addressed in the diff
- 4: Main task is done, minor aspects missing
- 3: Core task done but significant aspects missing
- 2: Only partially addresses the task
- 1: Barely touches the task

### 3. Code Quality (weight: 0.25)
- 5: Production-ready code, follows project patterns, clean diff
- 4: Good code with minor style/pattern issues
- 3: Functional but messy or doesn't follow project conventions
- 2: Poor quality, hacks, or overly complex
- 1: Non-functional or harmful changes

### 4. Awareness (weight: 0.15)
- 5: Agent clearly understood project context, referenced relevant history/patterns
- 4: Shows good awareness of the codebase, uses appropriate patterns
- 3: Basic awareness, some project-specific knowledge used
- 2: Generic approach, didn't leverage project context
- 1: Showed no awareness of the project

## Output Format
Respond with ONLY valid JSON (no markdown fences, no other text):
{
  "verdict": "accept" or "revise",
  "scores": {
    "correctness": <1-5>,
    "completeness": <1-5>,
    "code_quality": <1-5>,
    "awareness": <1-5>
  },
  "ground_truth_hits": ["<signal found in the diff or transcript>"],
  "ground_truth_misses": ["<signal NOT found>"],
  "feedback": "<what would need to change for accept, empty if accept>",
  "rationale": "<1-2 sentence explanation of the key score drivers>"
}

Accept when weighted_score >= 3.5 AND correctness >= 3.
Otherwise verdict = "revise" with specific feedback."""


@dataclass
class CheckerResponse:
    verdict: str
    scores: CheckerScores
    ground_truth_hits: list[str]
    ground_truth_misses: list[str]
    feedback: str
    rationale: str
    usage: TokenUsage
    cost_usd: float = 0.0


class CheckerAgent:
    def __init__(self, config: BenchmarkConfig):
        self.config = config

    def evaluate(self, task: Task, diff: str, transcript: str) -> CheckerResponse:
        """Evaluate actual code changes from a sandbox session."""
        signals_list = "\n".join(f"- {s}" for s in task.ground_truth_signals)

        # Truncate diff/transcript — keep head + tail to avoid missing key parts
        diff_text = _smart_truncate(diff, 8000) if diff else "(no changes made)"
        transcript_text = _smart_truncate(transcript, 6000) if transcript else "(no transcript)"

        user_message = f"""## Task Given to the Agent
{task.prompt}

## Git Diff (what the agent actually changed)
```diff
{diff_text}
```

## Session Transcript (agent's reasoning, truncated)
{transcript_text}

## Ground Truth Signals
The following should appear in a correct solution:
{signals_list}

Evaluate the DIFF for correctness, completeness, and code quality.
Use the TRANSCRIPT to assess awareness — did the agent reference project history, \
past decisions, or context that informed its approach? This is where reflect's \
impact is most visible.
Return your JSON verdict."""

        result = _call_claude_checker(
            user_message, CHECKER_SYSTEM_PROMPT,
            self.config.checker_model, self.config.max_checker_tokens,
        )

        return self._parse_response(result["output"], task, result["usage"], result["cost_usd"])

    def _parse_response(
        self, raw: str, task: Task, usage: TokenUsage, cost: float,
    ) -> CheckerResponse:
        """Parse checker JSON response, with fallback for malformed output."""
        try:
            # Strip markdown fences if present
            clean = raw.strip()
            if clean.startswith("```"):
                lines = clean.split("\n")
                clean = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
                clean = clean.strip()

            data = json.loads(clean)
        except (json.JSONDecodeError, IndexError):
            return CheckerResponse(
                verdict="revise",
                scores=CheckerScores(2, 2, 2, 2),
                ground_truth_hits=[],
                ground_truth_misses=task.ground_truth_signals,
                feedback=f"Checker output was not valid JSON. Raw: {raw[:300]}",
                rationale="Parse failure",
                usage=usage,
                cost_usd=cost,
            )

        scores = data.get("scores", {})
        return CheckerResponse(
            verdict=data.get("verdict", "revise"),
            scores=CheckerScores(
                correctness=_clamp_score(scores.get("correctness", 1)),
                completeness=_clamp_score(scores.get("completeness", 1)),
                evidence_grounding=_clamp_score(scores.get("awareness", scores.get("evidence_grounding", 1))),
                code_quality=_clamp_score(scores.get("code_quality", 1)),
            ),
            ground_truth_hits=data.get("ground_truth_hits", []),
            ground_truth_misses=data.get("ground_truth_misses", []),
            feedback=data.get("feedback", ""),
            rationale=data.get("rationale", ""),
            usage=usage,
            cost_usd=cost,
        )


def _smart_truncate(text: str, max_chars: int) -> str:
    """Keep head + tail of text to avoid missing important parts."""
    if len(text) <= max_chars:
        return text
    head_size = int(max_chars * 0.6)
    tail_size = int(max_chars * 0.3)
    omitted = len(text) - head_size - tail_size
    return f"{text[:head_size]}\n\n... ({omitted:,} chars omitted) ...\n\n{text[-tail_size:]}"


def _clamp_score(val) -> int:
    """Clamp a score value to 1-5 integer range."""
    try:
        n = int(val)
    except (TypeError, ValueError):
        return 1
    return max(1, min(5, n))


def _call_claude_checker(prompt: str, system_prompt: str, model: str, max_tokens: int, retries: int = 1) -> dict:
    """Call claude CLI in print mode, piping prompt via stdin. Retries on transient errors."""
    cmd = [
        "claude", "-p",
        "--model", model,
        "--output-format", "json",
        "--max-budget-usd", "0.10",
        "--append-system-prompt", system_prompt,
    ]

    for attempt in range(1 + retries):
        try:
            result = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            if attempt < retries:
                print(f"      [checker] timeout, retrying ({attempt+1}/{retries})...")
                continue
            return {"output": "[ERROR: timeout]", "usage": TokenUsage(), "cost_usd": 0.0}

        try:
            data = json.loads(result.stdout)
        except (json.JSONDecodeError, TypeError):
            if attempt < retries:
                print(f"      [checker] JSON parse error, retrying ({attempt+1}/{retries})...")
                continue
            return {
                "output": f"[ERROR: CLI rc={result.returncode}: {result.stderr[:200]}]",
                "usage": TokenUsage(),
                "cost_usd": 0.0,
            }

        if data.get("is_error"):
            if attempt < retries:
                print(f"      [checker] CLI error, retrying ({attempt+1}/{retries})...")
                continue
            return {
                "output": f"[ERROR: {data.get('result', 'unknown')}]",
                "usage": TokenUsage(),
                "cost_usd": 0.0,
            }

        # Success
        output = data.get("result", "")
        cost = data.get("total_cost_usd", 0.0)

        usage = TokenUsage()
        model_usage = data.get("modelUsage", {})
        for model_key, mu in model_usage.items():
            usage.input_tokens += mu.get("inputTokens", 0) + mu.get("cacheReadInputTokens", 0)
            usage.output_tokens += mu.get("outputTokens", 0)

        return {"output": output, "usage": usage, "cost_usd": cost}

    return {"output": "[ERROR: all retries exhausted]", "usage": TokenUsage(), "cost_usd": 0.0}
