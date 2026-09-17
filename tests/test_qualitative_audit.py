"""Publication diagnostics must reject invented scores and missing model rows."""

from collections import Counter
import hashlib
import json
from pathlib import Path

import pytest

from scripts.audit_qualitative import audit, parse

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def report_file(tmp_path):
    manifest_path = "dataset/layoutbench-v0.3/manifest.json"
    tasks = json.loads((ROOT / manifest_path).read_text())
    counts = Counter(t["family"] for t in tasks)
    families = {}
    for family, count in counts.items():
        chosen = [t for t in tasks if t["family"] == family]
        labels = "ABCDEF"[:len(chosen[0]["design"]["options"])]
        truth_counts = Counter(t["groundTruth"]["choice"] for t in chosen)
        families[family] = dict(count=count, valid_count=count, invalid_count=0, correct_count=count,
                               accuracy=1.0, validity_rate=1.0, group_count=len({t["groupId"] for t in chosen}),
                               chance_accuracy=1 / len(labels), mean_api_response_cost_usd=0.0,
                               confusion={label: {label: truth_counts[label]} if truth_counts[label] else {} for label in labels})
    model = dict(model_id="fixture", model_config=dict(input_per_m=1, output_per_m=1), families=families)
    results = [dict(model_id="fixture", included_in_comparison=True, result=dict(
        task_id=t["taskId"], family=t["family"], group_id=t["groupId"], ground_truth=t["groundTruth"],
        prompt_sha256=hashlib.sha256(t["prompt"].encode()).hexdigest(), raw_prediction=json.dumps(t["groundTruth"]),
        prediction=t["groundTruth"], valid=True, correct=True, score=100, error_kind=None,
        err=None, key_errors=None, tight_score=None, within_bands=None,
        input_tokens=0, output_tokens=0, unmetered_attempts=0,
    )) for t in tasks]
    report = dict(version="fixture", dataset_manifest=manifest_path, expected_task_count=len(tasks),
                  comparison=dict(task_ids=[t["taskId"] for t in tasks], model_ids=["fixture"], count=len(tasks), scope="full"),
                  models=[model], results=results)
    path = tmp_path / "fixture.json"
    path.write_text(json.dumps(report))
    return path


def test_independent_audit_reconstructs_perfect_fixture_and_paired_hierarchy(report_file):
    result = audit(report_file)
    assert result["response_count"] == 292
    assert result["hierarchy_pairs"]["fixture"] == dict(both=24, outer_only=0, inner_only=0, neither=0)
    assert result["models"]["fixture"]["nestedwrap"]["count"] == 24


@pytest.mark.parametrize("mutation", ["grade", "metric", "raw", "roster", "family", "cohort"])
def test_independent_audit_rejects_tampering(report_file, mutation):
    report = json.loads(report_file.read_text())
    if mutation == "grade":
        report["results"][0]["result"]["correct"] = False
    elif mutation == "metric":
        report["models"][0]["families"]["nestedwrap"]["accuracy"] = .5
    elif mutation == "raw":
        report["results"][0]["result"]["raw_prediction"] = '{"choice":"A","choice":"B"}'
    elif mutation == "roster":
        report["models"] = []
    elif mutation == "family":
        del report["models"][0]["families"]["direction"]
    else:
        report["comparison"]["task_ids"].pop()
    report_file.write_text(json.dumps(report))
    with pytest.raises(AssertionError):
        audit(report_file)


def test_audit_parser_rejects_unknown_letters_and_extra_keys():
    assert parse('{"choice":" c "}', "ABC") == {"choice": "C"}
    for raw in ('{"choice":"D"}', '{"choice":"A","extra":1}', '{"choice":true}', 'A'):
        assert parse(raw, "ABC") is None
