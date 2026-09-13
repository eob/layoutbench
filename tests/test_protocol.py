import pytest

from baseline.protocol import (
    NUMERIC_SCORING,
    choice_labels,
    get_prompt,
    grade_prediction,
    parse_prediction,
)


def test_choice_labels_per_family():
    assert choice_labels("flow") == ["A", "B", "C", "D"]
    assert choice_labels("distribute") == ["A", "B", "C", "D", "E"]
    assert choice_labels("gap") == ["A", "B", "C", "D", "E", "F", "G"]
    assert choice_labels("pad") == ["A", "B", "C", "D", "E"]
    assert choice_labels("regionpad") == ["A", "B", "C", "D", "E"]
    assert choice_labels("columns") == ["A", "B", "C"]
    assert choice_labels("headerpad") == ["A", "B", "C"]
    with pytest.raises(ValueError):
        choice_labels("gapnum")


def test_parse_choice_normalizes_case_and_whitespace():
    assert parse_prediction('{"choice": "c"}', "flow") == {"choice": "C"}
    assert parse_prediction('  {"choice":"B"}  ', "gap") == {"choice": "B"}
    assert parse_prediction('{"choice": "g"}', "gap") == {"choice": "G"}


def test_parse_rejects_bad_shapes():
    for raw, family in [
        ('{"choice": "F"}', "flow"),
        ('{"choice": "H"}', "gap"),
        ('{"choice": "F"}', "pad"),
        ('{"choice": "D"}', "columns"),
        ('{"choice": "E"}', "flow"),
        ('{"choice": "A", "extra": 1}', "flow"),
        ('{"choice": 1}', "flow"),
        ('{"choice": "A", "choice": "B"}', "flow"),
        ('{"gap_px": 12, "gap_px": 13}', "gapnum"),
        ('{"gap_px": 12.0}', "gapnum"),
        ('{"gap_px": -1}', "gapnum"),
        ('{"gap_px": 801}', "gapnum"),
        ('{"above_px": 8}', "headerpx"),
        ('{"above_px": 8, "below_px": 8, "extra": 0}', "headerpx"),
        ('{"pad_px": True}', "regionpx"),
        ('not json', "flow"),
        ('{"choice": "A"} trailing', "flow"),
    ]:
        try:
            parse_prediction(raw, family)
        except ValueError:
            continue
        raise AssertionError(f"accepted {raw} / {family}")


def test_parse_numeric_exact_keys():
    assert parse_prediction('{"gap_px": 0}', "gapnum") == {"gap_px": 0}
    assert parse_prediction('{"above_px": 48, "below_px": 8}', "headerpx") == {"above_px": 48, "below_px": 8}


def test_grade_choice():
    assert grade_prediction("flow", {"choice": "A"}, {"choice": "A"}) == {
        "valid": True, "correct": True, "score": 100, "tight_score": None,
        "err": None, "key_errors": None, "within_bands": None,
    }
    wrong = grade_prediction("flow", {"choice": "B"}, {"choice": "A"})
    assert (wrong["valid"], wrong["correct"], wrong["score"]) == (True, False, 0)
    invalid = grade_prediction("flow", None, {"choice": "A"})
    assert (invalid["valid"], invalid["correct"], invalid["score"]) == (False, False, 0)


def test_grade_numeric_exact_and_off():
    exact = grade_prediction("gapnum", {"gap_px": 16}, {"gap_px": 16})
    assert exact["valid"] and exact["score"] == 100 and exact["tight_score"] == 100
    assert exact["err"] == 0 and exact["key_errors"] == {"gap_px": 0}
    assert exact["within_bands"] == {"1": True, "2": True, "4": True, "8": True}
    off = grade_prediction("gapnum", {"gap_px": 20}, {"gap_px": 16})
    assert off["score"] == 100 * (1 - 4 / 16) and off["tight_score"] == 0
    assert off["within_bands"] == {"1": False, "2": False, "4": True, "8": True}
    invalid = grade_prediction("gapnum", None, {"gap_px": 16})
    assert (invalid["valid"], invalid["score"], invalid["tight_score"]) == (False, 0, 0)
    assert invalid["err"] is None and invalid["within_bands"] is None


def test_grade_headerpx_bands_require_both_sides():
    split = grade_prediction("headerpx", {"above_px": 24, "below_px": 16}, {"above_px": 24, "below_px": 8})
    assert split["err"] == 4.0
    assert split["within_bands"]["8"] is True
    assert split["within_bands"]["4"] is False
    assert split["key_errors"] == {"above_px": 0, "below_px": 8}


def test_numeric_scoring_block_shape():
    assert NUMERIC_SCORING["score_ceiling"] == 16
    assert NUMERIC_SCORING["tight_ceiling"] == 4
    assert NUMERIC_SCORING["exact_bands"] == [1, 2, 4, 8]


def test_prompts_cover_all_families():
    for family in ("flow", "distribute", "align", "columns", "textjustify", "headerpad"):
        prompt = get_prompt(family)
        assert "{options}" not in prompt and '"choice"' in prompt
    assert "gap_px" in get_prompt("gapnum")
    assert "above_px" in get_prompt("headerpx") and "below_px" in get_prompt("headerpx")
    assert "pad_px" in get_prompt("regionpx")
    assert get_prompt("gap", ["0px", "4px", "8px", "12px", "16px", "24px", "32px"]).splitlines()[-2:] == [
        "G: 32px",
        'Return only a JSON object with one key, "choice", whose value is the selected option letter.',
    ]
