import pytest


def test_header_spacing_has_visible_box_edges():
    from PIL import Image
    from baseline.validate_dataset import DATASET_DIR, PALETTE, load_manifest

    for task in load_manifest():
        if task["family"] != "headerpad":
            continue
        image = Image.open(DATASET_DIR / task["imageFilename"]).convert("RGB")
        for rect in task["rendered"]["regions"]:
            if rect["role"] in ("header", "tbody"):
                point = (round((rect["x"] + rect["width"] - 2) * 2),
                         round((rect["y"] + 1) * 2))
                assert image.getpixel(point) == PALETTE[task["design"]["theme"]]["tint"]

from baseline.validate_dataset import (
    adjacent_pairs,
    derive_align,
    derive_alignment,
    derive_direction,
    derive_justify,
    expected_prompt,
    paragraph_last_indexes,
    require_valid_dataset,
)


def test_frozen_corpus_passes():
    tasks = require_valid_dataset()
    assert len(tasks) == 208


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
    prompt = expected_prompt("gap", ["0px", "4px", "8px", "12px", "16px", "24px", "32px"])
    assert "A: 0px" in prompt and "G: 32px" in prompt and "{options}" not in prompt
    assert "{options}" not in expected_prompt("flow", None)


def box(x, y, width, height, box_id="0"):
    return {"id": box_id, "x": x, "y": y, "width": width, "height": height}


def test_derive_direction_modes():
    row = [box(0, 0, 50, 40, "0"), box(60, 5, 50, 30, "1"), box(120, 0, 50, 40, "2")]
    assert derive_direction(row) == "row"
    column = [box(0, 0, 60, 40, "0"), box(5, 50, 50, 40, "1"), box(0, 100, 60, 40, "2")]
    assert derive_direction(column) == "column"
    grid = [box(0, 0, 50, 40, "0"), box(60, 0, 50, 40, "1"),
            box(0, 50, 50, 40, "2"), box(60, 50, 50, 40, "3")]
    assert derive_direction(grid) == "grid-2col"
    ragged = [box(0, 0, 50, 40, "0"), box(60, 0, 50, 40, "1"),
              box(120, 0, 50, 40, "2"), box(0, 50, 50, 40, "3")]
    assert derive_direction(ragged) == "grid-3col"
    with pytest.raises(ValueError):
        derive_direction([box(0, 0, 50, 40)])


def test_derive_justify_modes():
    stage = box(0, 0, 640, 440)
    across = lambda xs: [box(x, 100, 100, 40, str(i)) for i, x in enumerate(xs)]
    assert derive_justify(across([24, 136, 248]), stage, 24, 12, "row") == "start"
    assert derive_justify(across([292, 404, 516]), stage, 24, 12, "row") == "end"
    assert derive_justify(across([158, 270, 382]), stage, 24, 12, "row") == "center"
    assert derive_justify(across([24, 270, 516]), stage, 24, 12, "row") == "space-between"
    assert derive_justify(across([68.67, 270, 471.33]), stage, 24, 12, "row") == "space-around"
    with pytest.raises(ValueError):
        derive_justify(across([24, 136, 248]), stage, 24, 12, "grid-2col")


def test_derive_align_modes():
    stage = box(0, 0, 640, 440)
    down = lambda ys, hs: [box(100, y, 100, h, str(i)) for i, (y, h) in enumerate(zip(ys, hs))]
    assert derive_align(down([24, 24, 24], [40, 60, 50]), stage, 24, "row") == "start"
    assert derive_align(down([376, 356, 366], [40, 60, 50]), stage, 24, "row") == "end"
    assert derive_align(down([200, 190, 195], [40, 60, 50]), stage, 24, "row") == "center"
    assert derive_align(down([24, 24, 24], [392, 392, 392]), stage, 24, "row") == "stretch"
    with pytest.raises(ValueError):
        derive_align(down([24, 24, 24], [40, 60, 50]), stage, 24, "grid-3col")
