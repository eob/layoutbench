"""Frozen LayoutBench answer contracts, strict parsing, and grading."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

CHOICE_FAMILIES = ("flow", "distribute", "align", "gap", "pad", "columns",
                   "textjustify", "headerpad", "regionpad", "tablepad")
NUMERIC_FAMILIES = ("gapnum", "headerpx", "regionpx")
FAMILIES = CHOICE_FAMILIES + NUMERIC_FAMILIES

NUMERIC_KEYS = {"gapnum": ("gap_px",), "headerpx": ("above_px", "below_px"),
                "regionpx": ("pad_px",)}
NUMERIC_RANGE = (0, 800)

NUMERIC_SCORING = {
    "distance": "absolute-px-error",
    "score_ceiling": 16,
    "score_formula": "100 * (1 - min(err_px / 16, 1))",
    "tight_ceiling": 4,
    "tight_formula": "100 * (1 - min(err_px / 4, 1))",
    "exact_bands": [1, 2, 4, 8],
    "interpretation": "Engineering normalization; not a just-noticeable-difference threshold.",
}

PROMPTS_PATH = Path(__file__).with_name("prompts.json")


def choice_labels(family: str) -> list[str]:
    if family == "gap":
        return ["A", "B", "C", "D", "E", "F", "G"]
    if family in ("distribute", "pad", "regionpad"):
        return ["A", "B", "C", "D", "E"]
    if family in ("columns", "headerpad"):
        return ["A", "B", "C"]
    if family in CHOICE_FAMILIES:
        return ["A", "B", "C", "D"]
    raise ValueError(f"Not a choice family: {family}")


@lru_cache(maxsize=1)
def _prompts() -> dict:
    return json.loads(PROMPTS_PATH.read_text(encoding="utf-8"))


def get_prompt(family: str, options: list[str] | None = None) -> str:
    template = _prompts()[family]
    if "{options}" not in template:
        return template
    letters = ["A", "B", "C", "D", "E", "F", "G"]
    block = "\n".join(f"{letters[i]}: {value}" for i, value in enumerate(options or []))
    return template.replace("{options}", block)


def _no_duplicates(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str):
    raise ValueError(f"Non-finite JSON constant: {value}")


def parse_prediction(raw_text: str, family: str) -> dict:
    if family not in FAMILIES:
        raise ValueError(f"Unknown family: {family}")
    text = (raw_text or "").strip()
    if not text.startswith("{") or not text.endswith("}"):
        raise ValueError("Response must be exactly one JSON object")
    try:
        parsed = json.loads(text, object_pairs_hook=_no_duplicates, parse_constant=_reject_constant)
    except (json.JSONDecodeError, ValueError) as error:
        raise ValueError(f"Malformed prediction JSON: {error}") from error
    if not isinstance(parsed, dict):
        raise ValueError("Prediction must be a JSON object")
    if family in CHOICE_FAMILIES:
        if set(parsed) != {"choice"} or not isinstance(parsed["choice"], str):
            raise ValueError("Choice prediction must be exactly {\"choice\": <letter>}")
        label = parsed["choice"].strip().upper()
        if label not in choice_labels(family):
            raise ValueError(f"Choice {parsed['choice']!r} is not an option for {family}")
        return {"choice": label}
    keys = NUMERIC_KEYS[family]
    if set(parsed) != set(keys):
        raise ValueError(f"{family} prediction must have exactly keys {sorted(keys)}")
    cleaned = {}
    for key in keys:
        value = parsed[key]
        if type(value) is not int or isinstance(value, bool):
            raise ValueError(f"{key} must be an integer number of pixels")
        if not NUMERIC_RANGE[0] <= value <= NUMERIC_RANGE[1]:
            raise ValueError(f"{key} is outside the 0..800 canvas range")
        cleaned[key] = value
    return cleaned


def _score(err: float, ceiling: float) -> float:
    return 100 * (1 - min(err / ceiling, 1))


def grade_prediction(family: str, parsed: dict | None, ground_truth: dict) -> dict:
    if family in CHOICE_FAMILIES:
        if parsed is None:
            return {"valid": False, "correct": False, "score": 0, "tight_score": None,
                    "err": None, "key_errors": None, "within_bands": None}
        correct = parsed["choice"] == ground_truth["choice"]
        return {"valid": True, "correct": correct, "score": 100 if correct else 0,
                "tight_score": None, "err": None, "key_errors": None, "within_bands": None}
    if parsed is None:
        return {"valid": False, "correct": None, "score": 0, "tight_score": 0,
                "err": None, "key_errors": None, "within_bands": None}
    keys = NUMERIC_KEYS[family]
    errors = {key: abs(parsed[key] - ground_truth[key]) for key in keys}
    err = sum(errors.values()) / len(errors)
    band_err = max(errors.values())
    scoring = NUMERIC_SCORING
    return {"valid": True, "correct": None, "score": _score(err, scoring["score_ceiling"]),
            "tight_score": _score(err, scoring["tight_ceiling"]), "err": err,
            "key_errors": errors,
            "within_bands": {str(band): band_err <= band for band in scoring["exact_bands"]}}
