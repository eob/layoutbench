import pytest

from baseline.validate_dataset import (
    adjacent_pairs,
    derive_alignment,
    expected_prompt,
    nearest_neighbors,
    paragraph_last_indexes,
    require_valid_dataset,
)


def test_frozen_corpus_passes():
    tasks = require_valid_dataset()
    assert len(tasks) == 208


def test_nearest_neighbors():
    assert nearest_neighbors(16, [0, 4, 8, 12, 16, 24, 32]) == [12, 8, 24]
    assert nearest_neighbors(8, [8, 16, 24, 32, 48]) == [16, 24, 32]


def test_adjacent_pairs_groups_grid_rows():
    items = [
        {"id": "0", "x": 0, "y": 10, "width": 50, "height": 40},
        {"id": "1", "x": 60, "y": 0, "width": 50, "height": 60},
        {"id": "2", "x": 0, "y": 100, "width": 50, "height": 40},
        {"id": "3", "x": 60, "y": 100, "width": 50, "height": 40},
    ]
    pairs = adjacent_pairs(items, "grid-2col")
    assert [[a["id"], b["id"]] for a, b in pairs] == [["0", "1"], ["2", "3"]]


def line(x, y, width, height=10.0):
    return {"x": x, "y": y, "width": width, "height": height}


def test_paragraph_last_detection():
    lines = [line(0, 0, 100), line(0, 12, 100), line(0, 40, 60)]
    assert paragraph_last_indexes(lines) == {1, 2}


def test_derive_alignment_all_modes():
    left = [line(10, 0, 90), line(10, 12, 70), line(10, 24, 80)]
    assert derive_alignment(left) == "left"
    right = [line(30, 0, 70), line(10, 12, 90), line(20, 24, 80)]
    assert derive_alignment(right) == "right"
    center = [line(10, 0, 80), line(0, 12, 100), line(20, 24, 60)]
    assert derive_alignment(center) == "center"
    justified = [line(10, 0, 90), line(10, 12, 90), line(10, 24, 90), line(10, 52, 50)]
    assert derive_alignment(justified) == "justify"
    with pytest.raises(ValueError):
        derive_alignment([line(0, 0, 50)])


def test_expected_prompt_templates():
    prompt = expected_prompt("gap", ["8px", "12px", "16px", "24px"])
    assert "A: 8px" in prompt and "D: 24px" in prompt and "{options}" not in prompt
    assert "{options}" not in expected_prompt("flow", None)
