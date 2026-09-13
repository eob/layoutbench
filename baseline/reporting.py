"""Shared scorecard integrity checks for report consumers."""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone

from baseline.evaluator import GRADING_VERSION, cohort_fingerprint, evaluation_protocol_fingerprint

from baseline.protocol import FAMILIES, NUMERIC_FAMILIES, NUMERIC_SCORING
from baseline.statistics import metrics


def scorecard_tasks(card: dict, *, dataset_fingerprint: str | None = None, complete: bool = False) -> list[dict]:
    """Reject incomplete provenance and malformed rows before computing metrics."""
    tasks = card.get("tasks")
    if not isinstance(tasks, list) or any(not isinstance(task, dict) for task in tasks):
        raise ValueError("Malformed task rows")
    ids = [task.get("task_id") for task in tasks]
    if (any(not isinstance(task_id, str) or not task_id for task_id in ids)
            or len(set(ids)) != len(ids)
            or type(card.get("total_tasks")) is not int or card["total_tasks"] != len(tasks)
            or type(card.get("expected_task_count")) is not int
            or card["expected_task_count"] <= 0 or len(tasks) > card["expected_task_count"]):
        raise ValueError("Inconsistent task coverage")
    if (str(card.get("grading_version")) != GRADING_VERSION
            or card.get("evaluation_protocol") != evaluation_protocol_fingerprint()
            or not isinstance(card.get("dataset_fingerprint"), str)
            or dataset_fingerprint is not None and card.get("dataset_fingerprint") != dataset_fingerprint
            or card.get("cohort_sha256") != cohort_fingerprint(ids)
            or not isinstance(card.get("mock"), bool)):
        raise ValueError("Incompatible dataset, protocol, or mock provenance")
    if card.get("status") not in ("complete", "partial") or (
            card["status"] == "complete" and len(tasks) != card["expected_task_count"]):
        raise ValueError("Inconsistent completion status")
    if complete and (card["status"] != "complete" or not tasks or card["mock"]):
        raise ValueError("Only complete live runs are eligible")
    for task in tasks:
        if task.get("family") not in FAMILIES or type(task.get("valid")) is not bool:
            raise ValueError("Malformed family or validity flag")
        if task.get("error_kind") not in (None, "invalid_response") or task.get("error") and task.get("error_kind") != "invalid_response":
            raise ValueError("Infrastructure failures are not completed measurements")
        if not finite_nonnegative(task.get("score")) or task["score"] > 100:
            raise ValueError("Invalid observation score")
        if task["family"] in NUMERIC_FAMILIES:
            if not finite_nonnegative(task.get("tight_score")) or task["tight_score"] > 100:
                raise ValueError("Invalid tight observation score")
            bands = task.get("within_bands")
            if task["valid"]:
                if (not isinstance(bands, dict) or set(bands) != {str(band) for band in NUMERIC_SCORING["exact_bands"]}
                        or not all(type(hit) is bool for hit in bands.values())):
                    raise ValueError("Malformed band flags")
            elif bands is not None:
                raise ValueError("Malformed band flags")
            if task["valid"] and not finite_nonnegative(task.get("err")):
                raise ValueError("Invalid observation error")
            if not task["valid"] and (task.get("err") is not None or task.get("key_errors") is not None):
                raise ValueError("Invalid rows carry no error detail")
        elif (task.get("tight_score") is not None or task.get("within_bands") is not None
                or task.get("err") is not None or task.get("key_errors") is not None):
            raise ValueError("Choice tasks carry no numeric metrics")
    try:
        recomputed = metrics(tasks)
    except KeyError as error:
        raise ValueError(f"Task rows are missing grade fields: {error}") from error
    if card.get("families") != recomputed:
        raise ValueError("Stored family metrics disagree with task rows")
    return tasks


def finite_nonnegative(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def _ledger_time(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Missing ledger timestamp")
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("Malformed ledger timestamp") from error
    if timestamp.tzinfo is None:
        raise ValueError("Ledger timestamp requires a timezone")
    return timestamp.astimezone(timezone.utc)


def _code_identity(record: dict) -> tuple:
    if "runner_git_commit" not in record or "runner_git_dirty" not in record:
        raise ValueError("Missing runner Git provenance")
    commit, dirty = record["runner_git_commit"], record["runner_git_dirty"]
    if commit is None and dirty is None:
        return None, None
    if not isinstance(commit, str) or re.fullmatch("[0-9a-f]{40}", commit) is None or type(dirty) is not bool:
        raise ValueError("Invalid runner Git provenance")
    return commit, dirty


def validate_task_result(task: dict, item: dict, model: dict) -> None:
    """Replay every saved answer against its frozen family and decoded target."""
    import hashlib
    from baseline.evaluator import grade_prediction
    from baseline.protocol import parse_prediction
    targets = dict(task_id=item["taskId"], family=item["family"], group_id=item["groupId"],
                   ground_truth=item["groundTruth"], model_name=model["model"], provider=model["provider"],
                   prompt_sha256=hashlib.sha256(item["prompt"].encode()).hexdigest())
    if any(type(task.get(key)) is not type(value) or task.get(key) != value for key, value in targets.items()):
        raise ValueError("Task targets or model identity disagree with the frozen dataset")
    if not isinstance(task.get("raw_prediction"), str):
        raise ValueError("Task has no raw prediction")
    try:
        parsed = parse_prediction(task["raw_prediction"], item["family"])
    except ValueError:
        parsed = None
    invalid = task.get("error_kind") == "invalid_response"
    if task.get("error_kind") not in (None, "invalid_response") or task.get("error") and not invalid:
        raise ValueError("Infrastructure failures are not completed observations")
    if parsed is not None and invalid:
        raise ValueError("Parseable answer was mislabeled invalid_response")
    if parsed is None and not invalid:
        raise ValueError("Malformed raw prediction was not graded invalid")
    flags = grade_prediction(item["family"], parsed, item["groundTruth"])
    if any(key not in task or type(task.get(key)) is not type(value) or task[key] != value for key, value in flags.items()):
        raise ValueError("Task grades disagree with raw prediction replay")
    if task.get("prediction") != (parsed or {}):
        raise ValueError("Stored prediction disagrees with raw prediction")
    for name in ("latency_sec", "cost_usd"):
        if task.get(name) is not None and not finite_nonnegative(task[name]):
            raise ValueError(f"Invalid observation {name}")
    for name in ("input_tokens", "output_tokens", "request_attempts", "unmetered_attempts"):
        value = task.get(name)
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError(f"Invalid observation {name}")
    _ledger_time(task.get("recorded_at"))
