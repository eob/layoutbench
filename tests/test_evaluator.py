from baseline.evaluator import BaselineEvaluator, TaskEvaluationResult
from baseline.protocol import grade_prediction


def mock_item(family="flow", ground_truth=None):
    return {
        "taskId": "test-1",
        "family": family,
        "groupId": "test-1",
        "imagePath": "test.png",
        "groundTruth": ground_truth or {"choice": "A"},
        "prompt": "prompt",
    }


def test_mock_choice_task_is_graded():
    evaluator = BaselineEvaluator(mock=True)
    result = evaluator._eval_single_task(mock_item(), "prompt")
    assert isinstance(result, TaskEvaluationResult)
    assert result.valid is True and result.correct is True and result.score == 100
    assert result.prediction == {"choice": "A"}
    assert result.latency_sec is not None and result.latency_sec >= 0


def test_mock_numeric_task_is_graded():
    evaluator = BaselineEvaluator(mock=True)
    item = mock_item("gapnum", {"gap_px": 20})
    result = evaluator._eval_single_task(item, "prompt")
    assert result.valid is True and result.err == 4.0
    assert result.score == 100 * (1 - 4 / 16)
    assert result.within_bands == {"1": False, "2": False, "4": True, "8": True}


def test_score_results_reports_per_family_metrics():
    evaluator = BaselineEvaluator(mock=True)
    results = [
        evaluator._eval_single_task(mock_item(), "prompt"),
        evaluator._eval_single_task(mock_item("gapnum", {"gap_px": 20}), "prompt"),
    ]
    scorecard = evaluator.score_results(results, expected_task_count=2)
    assert scorecard.total_tasks == 2
    assert scorecard.families["flow"]["accuracy"] == 1.0
    assert scorecard.families["gapnum"]["mean_err"] == 4.0
    assert scorecard.grading_version == "1"
    assert scorecard.status == "complete"


def test_grade_replay_matches_protocol():
    flags = grade_prediction("headerpad", {"choice": "C"}, {"choice": "C"})
    assert flags["correct"] is True and flags["score"] == 100
