"""Independent raw-answer replay and descriptive diagnostics for qualitative LayoutBench."""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def strict_object(pairs):
    if len(dict(pairs)) != len(pairs):
        raise ValueError("duplicate JSON key")
    return dict(pairs)


def parse(raw, labels):
    try:
        result = json.loads(raw, object_pairs_hook=strict_object)
        if not isinstance(result, dict) or set(result) != {"choice"} or not isinstance(result["choice"], str):
            return None
        choice = result["choice"].strip().upper()
        return {"choice": choice} if len(choice) == 1 and choice in labels else None
    except (ValueError, TypeError):
        return None


def same(actual, expected):
    if type(expected) is float:
        assert type(actual) in (float, int) and math.isclose(actual, expected, abs_tol=1e-10), (actual, expected)
    else:
        assert actual == expected, (actual, expected)


def audit(path):
    report = json.loads(Path(path).read_text())
    manifest = json.loads((ROOT / report["dataset_manifest"]).read_text())
    tasks = {t["taskId"]: t for t in manifest}
    assert len(tasks) == len(manifest) == report["expected_task_count"]
    assert all(t["design"]["kind"] == "qualitative" for t in manifest)
    cohort = set(report["comparison"]["task_ids"])
    roster = set(report["comparison"]["model_ids"])
    model_ids = [model["model_id"] for model in report["models"]]
    assert len(model_ids) == len(set(model_ids)) and roster <= set(model_ids)
    assert len(cohort) == report["comparison"]["count"] and cohort <= tasks.keys()
    if report["comparison"]["scope"] == "full":
        assert cohort == tasks.keys()
    rows = defaultdict(list)
    seen = set()
    for observation in report["results"]:
        row = observation["result"]
        model, task_id = observation["model_id"], row["task_id"]
        assert model in model_ids
        assert (model, task_id) not in seen
        seen.add((model, task_id))
        task = tasks[task_id]
        assert row["family"] == task["family"] and row["group_id"] == task["groupId"]
        assert row["ground_truth"] == task["groundTruth"]
        assert row["prompt_sha256"] == hashlib.sha256(task["prompt"].encode()).hexdigest()
        options = task["design"]["options"]
        labels = "ABCDEF"[:len(options)]
        answer = parse(row["raw_prediction"], labels)
        correct = answer is not None and answer == task["groundTruth"]
        same(row["prediction"], answer or {})
        same(row["valid"], answer is not None)
        same(row["correct"], correct)
        same(row["score"], 100 if correct else 0)
        same(row["error_kind"], None if answer else "invalid_response")
        for key in ("err", "key_errors", "tight_score", "within_bands"):
            same(row[key], None)
        included = model in roster and task_id in cohort
        same(observation["included_in_comparison"], included)
        if included:
            rows[model].append(row)
    summary = {"version": report["version"], "response_count": len(seen), "comparison_count": len(cohort), "models": {}, "hierarchy_pairs": {}}
    for model in report["models"]:
        model_id = model["model_id"]
        selected = rows[model_id]
        if model_id in roster:
            assert {r["task_id"] for r in selected} == cohort
        config = model["model_config"]
        families = {}
        assert set(model["families"]) == {t["family"] for t in manifest}
        for family, stored in model["families"].items():
            subset = [r for r in selected if r["family"] == family]
            n = len(subset)
            valid = sum(r["valid"] for r in subset)
            correct = sum(r["correct"] for r in subset)
            same(stored["count"], n)
            same(stored["valid_count"], valid)
            same(stored["invalid_count"], n - valid)
            same(stored["correct_count"], correct)
            same(stored["accuracy"], correct / n if n else None)
            same(stored["validity_rate"], valid / n if n else None)
            same(stored["group_count"], len({r["group_id"] for r in subset}))
            option_count = len(next(t for t in manifest if t["family"] == family)["design"]["options"])
            same(stored["chance_accuracy"], 1 / option_count)
            label_confusion = {label: dict(Counter(r["prediction"]["choice"] if r["valid"] else "invalid" for r in subset if r["ground_truth"]["choice"] == label)) for label in "ABCDEF"[:option_count]}
            same(stored["confusion"], label_confusion)
            costs = [(r["input_tokens"] * config["input_per_m"] + r["output_tokens"] * config["output_per_m"]) / 1e6 for r in subset if r["input_tokens"] is not None and r["output_tokens"] is not None and not r.get("cost_estimated") and r.get("unmetered_attempts") == 0]
            same(stored["mean_api_response_cost_usd"], sum(costs) / n if n and len(costs) == n else None)
            semantic = defaultdict(Counter)
            for row in subset:
                task = tasks[row["task_id"]]
                options = task["design"]["options"]
                truth = options[ord(task["groundTruth"]["choice"]) - 65]
                predicted = options[ord(row["prediction"]["choice"]) - 65] if row["valid"] else "invalid"
                semantic[truth][predicted] += 1
            families[family] = {"correct": correct, "count": n, "accuracy": correct / n if n else None, "semantic_confusion": {k: dict(v) for k, v in semantic.items()}}
        summary["models"][model_id] = families
        paired = defaultdict(dict)
        for row in selected:
            if row["family"] in ("topflow", "nestedflow"):
                paired[row["group_id"]][row["family"]] = row["correct"]
        pair_counts = Counter()
        for answers in paired.values():
            if set(answers) == {"topflow", "nestedflow"}:
                outer, inner = answers["topflow"], answers["nestedflow"]
                pair_counts["both" if outer and inner else "outer_only" if outer else "inner_only" if inner else "neither"] += 1
        summary["hierarchy_pairs"][model_id] = {key: pair_counts[key] for key in ("both", "outer_only", "inner_only", "neither")}
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    summary = audit(args.report)
    content = json.dumps(summary, indent=2) + "\n"
    if args.output:
        args.output.write_text(content)
    print(f"Independently audited {summary['response_count']} raw responses on {summary['comparison_count']} questions.")
