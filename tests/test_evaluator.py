from baseline.evaluator import BaselineEvaluator, TaskEvaluationResult, LayoutBenchScorecard
from baseline.providers import LayoutPrediction


def test_layout_prediction_schema():
    valid = {
        "direction": "row",
        "justify_content": "start",
        "align_items": "center",
        "gap": "16px",
        "padding": "24px",
    }
    pred = LayoutPrediction.model_validate(valid)
    assert pred.direction == "row"
    assert pred.justify_content == "start"
    assert pred.align_items == "center"
    assert pred.gap == "16px"
    assert pred.padding == "24px"


def test_evaluator_scoring():
    evaluator = BaselineEvaluator(mock=True)
    item = {
        "taskId": "test-1",
        "imagePath": "test.png",
        "groundTruth": {
            "direction": "row",
            "justify_content": "start",
            "align_items": "center",
            "gap": "16px",
            "padding": "24px",
            "theme": "light",
        },
    }
    result = evaluator._eval_single_task(item, "prompt")
    assert result.all_correct is True
    assert result.direction_correct is True
    assert result.justify_content_correct is True
    assert result.align_items_correct is True
    assert result.gap_correct is True
    assert result.padding_correct is True

    scorecard = evaluator.score_results([result], expected_task_count=1)
    assert scorecard.overall_exact_match == 100.0
    assert scorecard.direction_accuracy == 100.0
    assert scorecard.justify_content_accuracy == 100.0
    assert scorecard.align_items_accuracy == 100.0
    assert scorecard.gap_accuracy == 100.0
    assert scorecard.padding_accuracy == 100.0
    assert scorecard.total_tasks == 1
