"""Benchmark configuration and data models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class BenchmarkConfig:
    target_repo: str
    v3_reflect_dir: str
    maker_model: str = "claude-sonnet-4-6"
    checker_model: str = "claude-sonnet-4-6"
    max_rounds: int = 5
    temperature: float = 0.0
    seed: int = 42
    max_maker_tokens: int = 4096
    max_checker_tokens: int = 2048
    tasks_file: str = ""
    run_id: str = ""
    dry_run: bool = False

    def __post_init__(self):
        if not self.run_id:
            self.run_id = datetime.now().strftime("%Y-%m-%d_%H%M")

    def to_dict(self):
        return {
            "target_repo": self.target_repo,
            "v3_reflect_dir": self.v3_reflect_dir,
            "maker_model": self.maker_model,
            "checker_model": self.checker_model,
            "max_rounds": self.max_rounds,
            "temperature": self.temperature,
            "seed": self.seed,
            "max_maker_tokens": self.max_maker_tokens,
            "max_checker_tokens": self.max_checker_tokens,
            "tasks_file": self.tasks_file,
            "run_id": self.run_id,
        }


@dataclass
class Task:
    id: str
    type: str  # why_query, code_modification, debugging, architectural_reasoning
    title: str
    prompt: str
    ground_truth_signals: list[str]
    difficulty: str = "medium"
    relevant_files: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total(self):
        return self.input_tokens + self.output_tokens


@dataclass
class CheckerScores:
    correctness: int = 0
    completeness: int = 0
    evidence_grounding: int = 0
    code_quality: int = 0

    @property
    def weighted_score(self) -> float:
        return (
            self.correctness * 0.30
            + self.completeness * 0.25
            + self.evidence_grounding * 0.25
            + self.code_quality * 0.20
        )

    def to_dict(self):
        return {
            "correctness": self.correctness,
            "completeness": self.completeness,
            "evidence_grounding": self.evidence_grounding,
            "code_quality": self.code_quality,
            "weighted_score": round(self.weighted_score, 2),
        }


@dataclass
class Round:
    round_num: int
    maker_output: str
    checker_verdict: str  # "accept" or "revise"
    checker_scores: CheckerScores
    checker_feedback: str
    checker_rationale: str
    ground_truth_hits: list[str]
    ground_truth_misses: list[str]
    maker_usage: TokenUsage
    checker_usage: TokenUsage

    maker_cost_usd: float = 0.0
    checker_cost_usd: float = 0.0

    @property
    def cost_usd(self) -> float:
        """Actual cost reported by claude CLI."""
        return self.maker_cost_usd + self.checker_cost_usd

    def to_dict(self):
        return {
            "round_num": self.round_num,
            "maker_output": self.maker_output,
            "checker_verdict": self.checker_verdict,
            "checker_scores": self.checker_scores.to_dict(),
            "checker_feedback": self.checker_feedback,
            "checker_rationale": self.checker_rationale,
            "ground_truth_hits": self.ground_truth_hits,
            "ground_truth_misses": self.ground_truth_misses,
            "maker_tokens": {"input": self.maker_usage.input_tokens, "output": self.maker_usage.output_tokens},
            "checker_tokens": {"input": self.checker_usage.input_tokens, "output": self.checker_usage.output_tokens},
            "cost_usd": round(self.cost_usd, 4),
        }


@dataclass
class TaskResult:
    task_id: str
    version: str  # "v3" or "v4"
    rounds: list[Round]
    context_size_chars: int

    @property
    def converged(self) -> bool:
        return bool(self.rounds) and self.rounds[-1].checker_verdict == "accept"

    @property
    def num_rounds(self) -> int:
        return len(self.rounds)

    @property
    def final_score(self) -> Optional[CheckerScores]:
        return self.rounds[-1].checker_scores if self.rounds else None

    @property
    def total_cost(self) -> float:
        return sum(r.cost_usd for r in self.rounds)

    @property
    def ground_truth_coverage(self) -> float:
        if not self.rounds:
            return 0.0
        last = self.rounds[-1]
        total = len(last.ground_truth_hits) + len(last.ground_truth_misses)
        return len(last.ground_truth_hits) / total if total else 0.0

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "version": self.version,
            "converged": self.converged,
            "num_rounds": self.num_rounds,
            "final_scores": self.final_score.to_dict() if self.final_score else None,
            "ground_truth_coverage": round(self.ground_truth_coverage, 2),
            "total_cost_usd": round(self.total_cost, 4),
            "context_size_chars": self.context_size_chars,
            "rounds": [r.to_dict() for r in self.rounds],
        }
