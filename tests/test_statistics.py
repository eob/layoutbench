import pytest

from baseline.statistics import family_metrics, metrics, quantile


def choice_row(choice="A", truth="A", valid=True):
    return {
        "family": "flow",
        "valid": valid,
        "correct": (choice == truth) if valid else False,
        "ground_truth": {"choice": truth},
        "prediction": {"choice": choice} if valid else {},
    }


def numeric_row(err=0.0, valid=True, bands=None, truth=0):
    return {
        "family": "gapnum",
        "valid": valid,
        "score": 100 * (1 - min(err / 16, 1)) if valid else 0,
        "tight_score": 100 * (1 - min(err / 4, 1)) if valid else 0,
        "err": err if valid else None,
        "key_errors": {"gap_px": err} if valid else None,
        "within_bands": bands if valid else None,
        "ground_truth": {"gap_px": truth},
    }


def test_quantile_edges():
    assert quantile([], 0.5) is None
    assert quantile([4.0], 0.5) == 4.0
    assert quantile([0.0, 10.0], 0.5) == 5.0


def test_choice_metrics_with_confusion():
    rows = [choice_row("A", "A"), choice_row("B", "A"), choice_row("C", "C", valid=False)]
    value = family_metrics(rows, "flow")
    assert value["kind"] == "choice" and value["count"] == 3
    assert (value["valid_count"], value["invalid_count"], value["validity_rate"]) == (2, 1, pytest.approx(2 / 3))
    assert (value["correct_count"], value["accuracy"], value["chance_accuracy"]) == (1, pytest.approx(1 / 3), 0.25)
    assert value["confusion"] == {"A": {"A": 1, "B": 1}, "B": {}, "C": {"invalid": 1}, "D": {}}


def test_numeric_metrics_include_invalids_in_means():
    rows = [
        numeric_row(0.0, True, {"1": True, "2": True, "4": True, "8": True}),
        numeric_row(8.0, True, {"1": False, "2": False, "4": False, "8": True}),
        numeric_row(valid=False),
    ]
    value = family_metrics(rows, "gapnum")
    assert value["kind"] == "numeric" and value["count"] == 3
    assert value["mean_score"] == pytest.approx((100 + 50 + 0) / 3)
    assert value["mean_tight_score"] == pytest.approx((100 + 0 + 0) / 3)
    assert value["mean_err"] == pytest.approx(4.0)
    assert value["median_err"] == pytest.approx(4.0)
    assert value["band_hit_rate"] == {"1": 0.5, "2": 0.5, "4": 0.5, "8": 1.0}
    assert value["mean_key_errors"] == {"gap_px": pytest.approx(4.0)}
    assert value["key_known_count"] == {"gap_px": 2}


def test_metrics_rejects_unknown_family():
    with pytest.raises(ValueError):
        family_metrics([], "nope")


def test_metrics_covers_all_families():
    assert set(metrics([])) == {
        "flow", "distribute", "align", "gap", "pad", "columns", "textjustify",
        "headerpad", "regionpad", "tablepad", "gapnum", "headerpx", "regionpx",
    }
