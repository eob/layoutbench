"""Descriptive family metrics on a fixed cohort, without pooling unlike tasks."""

import math

from baseline.protocol import CHOICE_FAMILIES, FAMILIES, NUMERIC_KEYS, NUMERIC_SCORING, choice_labels, grade_prediction


def quantile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * probability
    lower = math.floor(index)
    fraction = index - lower
    return ordered[lower] * (1 - fraction) + ordered[min(lower + 1, len(ordered) - 1)] * fraction


def family_metrics(tasks: list[dict], family: str) -> dict:
    if family not in FAMILIES:
        raise ValueError(f"Unknown family: {family}")
    rows = [row for row in tasks if row["family"] == family]
    valid = [row for row in rows if row["valid"]]
    count = len(rows)
    value = dict(kind="choice" if family in CHOICE_FAMILIES else "numeric", count=count,
                 valid_count=len(valid), invalid_count=count - len(valid), validity_rate=len(valid) / count if count else None)
    if family in CHOICE_FAMILIES:
        correct = sum(row["correct"] is True for row in rows)
        labels = choice_labels(family)
        confusion = {label: {} for label in labels}
        for row in rows:
            cells = confusion[row["ground_truth"]["choice"]]
            predicted = row["prediction"]["choice"] if row["valid"] else "invalid"
            cells[predicted] = cells.get(predicted, 0) + 1
        value.update(correct_count=correct, accuracy=correct / count if count else None,
                     chance_accuracy=1 / len(labels), confusion=confusion)
    else:
        errors = [row["err"] for row in valid]
        keys = sorted({key for row in valid for key in (row["key_errors"] or {})})
        means, known = {}, {}
        for key in keys:
            selected = [row["key_errors"][key] for row in valid if (row["key_errors"] or {}).get(key) is not None]
            means[key] = sum(value / len(selected) for value in selected) if selected else None
            known[key] = len(selected)
        bands = [str(band) for band in NUMERIC_SCORING["exact_bands"]]
        hits = {band: sum(row["within_bands"][band] is True for row in valid) / len(valid) if valid else None
                for band in bands}
        constant = {key: 16 for key in NUMERIC_KEYS[family]}
        graded = [grade_prediction(family, constant, row["ground_truth"]) for row in rows]
        value.update(mean_score=sum(row["score"] for row in rows) / count if count else None,
                     mean_tight_score=sum(row["tight_score"] for row in rows) / count if count else None,
                     mean_err=sum(error / len(errors) for error in errors) if errors else None,
                     median_err=quantile(errors, .5), p90_err=quantile(errors, .9),
                     mean_key_errors=means, key_known_count=known, band_hit_rate=hits,
                     constant16_mean_score=sum(g["score"] for g in graded) / count if count else None,
                     constant16_mean_err=sum(g["err"] for g in graded) / count if count else None)
    return value


def metrics(tasks: list[dict]) -> dict:
    return {family: family_metrics(tasks, family) for family in FAMILIES}
