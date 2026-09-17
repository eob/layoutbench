import json
from pathlib import Path

import pytest

from baseline.protocol import choice_labels, grade_prediction, parse_prediction

ROOT = Path(__file__).resolve().parents[1]


def test_nested_questions_are_scored_as_atomic_choices():
    for family in ("topflow", "nestedflow", "nestedwrap"):
        parsed = parse_prediction('{"choice":"B"}', family)
        assert grade_prediction(family, parsed, {"choice": "B"})["correct"]
    assert choice_labels("topflow") == ["A", "B"]
    assert choice_labels("nestedflow") == ["A", "B", "C"]
    with pytest.raises(ValueError):
        parse_prediction('{"choice":"C"}', "topflow")


def test_qualitative_catalog_covers_requested_constructs():
    catalog = json.loads((ROOT / "config/qualitative.json").read_text())
    assert set(catalog) == {
        "direction", "distribution", "crossalign", "textalign", "textcolumns",
        "gridcols", "gridrows", "gridgaps", "gridtracks", "gridspan",
        "wrapcount", "wrapalign", "gapcompare", "padcompare", "blockalign",
        "widthcompare", "groupgap", "topflow", "nestedflow", "nestedwrap",
    }
    for family, spec in catalog.items():
        assert len(choice_labels(family)) == len(spec["options"])
        assert len(set(spec["options"].values())) == len(spec["options"])
        assert "pixel" not in spec["question"].lower()


def test_answer_slots_do_not_follow_the_visible_theme_and_copy_rotation():
    catalog = json.loads((ROOT / "config/qualitative.json").read_text())
    tasks = json.loads((ROOT / "dataset/layoutbench-v0.3/manifest.json").read_text())
    matches = 0
    for task in tasks:
        keys = list(catalog[task["family"]]["options"])
        design = task["design"]
        leaked_slot = (keys.index(design["answer"]) + (design["theme"] == "dark") + design["variant"]) % len(keys)
        matches += ord(task["groundTruth"]["choice"]) - 65 == leaked_slot
    # That construction made the truth obey a known semantic-position rule on
    # every trial. Independent slots must break the rule across this corpus.
    assert matches / len(tasks) < .5
