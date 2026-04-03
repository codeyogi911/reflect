"""Checker agent — evaluates maker output against a structured rubric via claude CLI."""

import json
import subprocess
from dataclasses import dataclass

from ..config import BenchmarkConfig, CheckerScores, Task, TokenUsage

CHECKER_SYSTEM_PROMPT = """\
You are a senior code reviewer evaluating an AI coding agent's response \
to a software engineering task. You evaluate strictly against the rubric \
below. You do NOT have access to project context yourself — you evaluate \
based on internal consistency, technical correctness, and evidence grounding \
of the response.

## Evaluation Rubric

Score each dimension 1-5:

### 1. Correctness (weight: 0.30)
- 5: Technically accurate, no errors
- 4: Minor inaccuracies that don't affect the conclusion
- 3: Some errors but core answer is right
- 2: Significant errors that undermine the answer
- 1: Fundamentally wrong

### 2. Completeness (weight: 0.25)
- 5: Addresses all aspects of the task thoroughly
- 4: Covers main points, minor gaps
- 3: Covers the basics but misses important aspects
- 2: Major gaps in coverage
- 1: Barely addresses the task

### 3. Evidence Grounding (weight: 0.25)
- 5: Every claim cites specific evidence (commit SHAs, session IDs, file paths)
- 4: Most claims are grounded, few unsupported assertions
- 3: Mix of grounded and ungrounded claims
- 2: Mostly assertions without evidence
- 1: No evidence cited, or fabricated evidence

### 4. Code/Reasoning Quality (weight: 0.20)
For code tasks: production-ready (5) to non-functional (1)
For reasoning tasks: rigorous analysis (5) to superficial (1)

## Output Format
Respond with ONLY valid JSON (no markdown fences, no other text):
{
  "verdict": "accept" or "revise",
  "scores": {
    "correctness": <1-5>,
    "completeness": <1-5>,
    "evidence_grounding": <1-5>,
    "code_quality": <1-5>
  },
  "ground_truth_hits": ["<signal found in response>"],
  "ground_truth_misses": ["<signal NOT found in response>"],
  "feedback": "<specific, actionable feedback if verdict is revise, empty string if accept>",
  "rationale": "<brief explanation of scores>"
}

Accept when weighted_score >= 4.0 AND no individual score is below 3.
Otherwise, set verdict to "revise" and provide specific feedback."""


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

    def evaluate(self, task: Task, maker_output: str) -> CheckerResponse:
        """Evaluate a maker's output against the task rubric."""
        signals_list = "\n".join(f"- {s}" for s in task.ground_truth_signals)

        user_message = f"""## Task Given to the Agent
{task.prompt}

## Agent's Response
{maker_output}

## Ground Truth Signals
The following concepts/keywords SHOULD appear in a correct response:
{signals_list}

Missing signals indicate incomplete understanding. Present signals confirm grounding.

Evaluate the response and return your JSON verdict."""

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
                # Remove first and last lines (fences)
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
                correctness=scores.get("correctness", 1),
                completeness=scores.get("completeness", 1),
                evidence_grounding=scores.get("evidence_grounding", 1),
                code_quality=scores.get("code_quality", 1),
            ),
            ground_truth_hits=data.get("ground_truth_hits", []),
            ground_truth_misses=data.get("ground_truth_misses", []),
            feedback=data.get("feedback", ""),
            rationale=data.get("rationale", ""),
            usage=usage,
            cost_usd=cost,
        )


def _call_claude_checker(prompt: str, system_prompt: str, model: str, max_tokens: int) -> dict:
    """Call claude CLI in print mode, piping prompt via stdin."""
    cmd = [
        "claude", "-p",
        "--model", model,
        "--output-format", "json",
        "--max-turns", "1",
        "--tools", "",
        "--system-prompt", system_prompt,
    ]

    try:
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        return {"output": "[timeout]", "usage": TokenUsage(), "cost_usd": 0.0}

    # Claude CLI returns JSON even on errors — always try to parse stdout
    try:
        data = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError):
        return {
            "output": f"[CLI error rc={result.returncode}: {result.stderr[:300]} | stdout: {(result.stdout or '')[:300]}]",
            "usage": TokenUsage(),
            "cost_usd": 0.0,
        }

    if data.get("is_error"):
        return {
            "output": f"[CLI error: {data.get('result', 'unknown')}]",
            "usage": TokenUsage(),
            "cost_usd": 0.0,
        }

    output = data.get("result", "")
    cost = data.get("total_cost_usd", 0.0)

    usage = TokenUsage()
    model_usage = data.get("modelUsage", {})
    for model_key, mu in model_usage.items():
        usage.input_tokens += mu.get("inputTokens", 0) + mu.get("cacheReadInputTokens", 0)
        usage.output_tokens += mu.get("outputTokens", 0)

    return {"output": output, "usage": usage, "cost_usd": cost}
