import json
from pathlib import Path

import pytest

from scripts.audit_results import ROOT, audit, check_geometry


ARCHIVE = Path(__file__).resolve().parents[1] / 'results/runs/0.1.0/pilot-20260913'


def test_independent_audit_replays_archived_raw_predictions():
    summary = audit(ARCHIVE / 'final_results.json')
    assert summary['response_count'] == 2288
    assert len(summary['models']) == 11


@pytest.mark.parametrize('mutation', ['row_grade', 'family_metric'])
def test_independent_audit_rejects_result_tampering(tmp_path, mutation):
    report = json.loads((ARCHIVE / 'final_results.json').read_text())
    if mutation == 'row_grade':
        report['results'][0]['result']['score'] = 0
    else:
        report['models'][0]['families']['flow']['accuracy'] = 0
    path = tmp_path / 'final_results.json'
    path.write_text(json.dumps(report))
    with pytest.raises(AssertionError):
        audit(path)


def test_geometry_audit_does_not_trust_saved_decoded_spacing():
    tasks = json.loads((ROOT / 'dataset/layoutbench-v0.2/manifest.json').read_text())
    task = next(row for row in tasks if row['family'] == 'gapnum')
    task['groundTruth']['gap_px'] += 4
    task['design']['decoded']['gap'] += 4
    with pytest.raises(AssertionError):
        check_geometry({task['taskId']: task})
