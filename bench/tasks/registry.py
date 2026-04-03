"""Task registry — loads and validates benchmark task definitions."""

import json
from pathlib import Path

from ..config import Task


def load_tasks(tasks_file: str) -> list[Task]:
    """Load tasks from a JSON file."""
    path = Path(tasks_file)
    if not path.exists():
        raise FileNotFoundError(f"Tasks file not found: {tasks_file}")

    with open(path) as f:
        data = json.load(f)

    tasks = []
    for t in data["tasks"]:
        _validate_task(t)
        tasks.append(Task(
            id=t["id"],
            type=t["type"],
            title=t["title"],
            prompt=t["prompt"],
            ground_truth_signals=t["ground_truth_signals"],
            difficulty=t.get("difficulty", "medium"),
            relevant_files=t.get("relevant_files", []),
            tags=t.get("tags", []),
        ))
    return tasks


def _validate_task(t: dict):
    required = ["id", "type", "title", "prompt", "ground_truth_signals"]
    missing = [k for k in required if k not in t]
    if missing:
        raise ValueError(f"Task {t.get('id', '???')} missing fields: {missing}")

    valid_types = {"why_query", "code_modification", "debugging", "architectural_reasoning", "bug_fix"}
    if t["type"] not in valid_types:
        raise ValueError(f"Task {t['id']} has invalid type '{t['type']}'. Must be one of: {valid_types}")

    if not t["ground_truth_signals"]:
        raise ValueError(f"Task {t['id']} must have at least one ground_truth_signal")
