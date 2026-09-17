"""Recover qualitative labels from measured geometry and reject corrupted evidence."""

from copy import deepcopy
from collections import Counter
import hashlib
from itertools import product
import json
from pathlib import Path
import shutil

import pytest
from PIL import Image

from baseline.qualitative_validation import derive_answer, require_valid_qualitative


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "dataset/layoutbench-v0.3/manifest.json"


def rectangle(name, x, y, width, height):
    return {"id": name, "role": "box", "x": x, "y": y, "width": width, "height": height}


def test_recovery_ignores_declared_answer_and_design_factors():
    task = {"family": "gapcompare", "design": {"answer": "last", "factors": {"direction": "column"}},
            "rendered": {"regions": [rectangle("frame", 0, 0, 660, 440),
                rectangle("item-0", 50, 100, 100, 60), rectangle("item-1", 210, 100, 100, 60),
                rectangle("item-2", 330, 100, 100, 60)]}}
    assert derive_answer(task) == "first"


@pytest.mark.parametrize("offset", [2, 5, 10])
def test_small_relative_differences_are_rejected_as_ambiguous(offset):
    task = {"family": "widthcompare", "rendered": {"regions": [rectangle("frame", 0, 0, 660, 440),
        rectangle("item-0", 40, 100, 200 + offset, 60), rectangle("item-1", 340, 100, 200, 60)]}}
    with pytest.raises(ValueError, match="separation"):
        derive_answer(task)


def test_justification_requires_visible_nonfinal_line_edges():
    task = {"family": "textalign", "rendered": {"regions": [rectangle("frame", 0, 0, 660, 440)]},
            "design": {"lines": {"text-0": [rectangle(str(i), 20, 30 + i * 30, width, 20)
                          for i, width in enumerate([400, 400, 400, 170])]}}}
    assert derive_answer(task) == "justify"
    task["design"]["lines"]["text-0"][1]["width"] = 360
    assert derive_answer(task) == "left"


@pytest.mark.parametrize("width", [90, 100])
def test_nested_wrap_full_rows_cannot_reveal_alignment(width):
    children = [rectangle(f"child-{i}", 2 + (i % 3) * 112, 2 + (i // 3) * 50, 100, 38)
                for i in range(5)]
    for index, child in enumerate(children[:3]):
        child.update(x=2 + index * (width + 12), width=width)
    task = {"family": "nestedwrap", "rendered": {"regions": [
        rectangle("frame", 0, 0, 328, 140), rectangle("target", 0, 0, 328, 140),
        *children,
    ]}}
    if width == 90:
        with pytest.raises(ValueError, match="Full wrapped rows"):
            derive_answer(task)
    else:
        assert derive_answer(task) == "left"


def test_frozen_qualitative_corpus_passes_independent_gate():
    tasks = require_valid_qualitative(MANIFEST)
    assert len({task["family"] for task in tasks}) == 20


def test_nested_wrapping_crosses_both_target_positions():
    tasks = json.loads(MANIFEST.read_text())
    observed = Counter()
    for task in tasks:
        if task["family"] != "nestedwrap":
            continue
        direction = derive_answer({**task, "family": "topflow"})
        axis = "x" if direction == "row" else "y"
        boxes = {rect["id"]: rect for rect in task["rendered"]["regions"]}
        position = int(boxes["section-0"][axis] > boxes["section-1"][axis])
        assert position == task["design"]["variant"]
        observed[(direction, derive_answer(task), task["design"]["theme"], position)] += 1
    expected = Counter({cell: 1 for cell in product(("row", "column"), ("left", "center", "right"),
                                                   ("light", "dark"), (0, 1))})
    assert observed == expected


@pytest.mark.parametrize("mutation,match", [
    ("answer", "ground truth"), ("prompt", "Prompt"), ("hash", "hash"),
    ("escape", "canvas"), ("font", "font"), ("leak", "leak"),
    ("overflow", "overflow"), ("missing", "counts"), ("crossing", "cross"),
    ("pixels", "Decoded border"), ("rectpixels", "Decoded border"),
    ("linepixels", "Decoded text"), ("copy", "Visible copy"),
])
def test_corpus_tampering_fails_closed(tmp_path, mutation, match):
    tasks = deepcopy(json.loads(MANIFEST.read_text()))
    if mutation == "answer":
        task = tasks[0]
        task["groundTruth"]["choice"] = "B" if task["groundTruth"]["choice"] == "A" else "A"
        task["design"]["answer"] = task["design"]["options"][ord(task["groundTruth"]["choice"]) - 65]
    elif mutation == "prompt": tasks[0]["prompt"] += " The answer is A."
    elif mutation == "hash": tasks[0]["imageSha256"] = "0" * 64
    elif mutation == "escape": tasks[0]["rendered"]["regions"][0]["x"] = -1
    elif mutation == "font": tasks[0]["rendered"]["font"]["sha256"] = "0" * 64
    elif mutation == "leak": tasks[0]["domText"] += " centered"
    elif mutation == "copy": tasks[0]["domText"] += " Breeze"
    elif mutation == "overflow": tasks[0]["rendered"]["overflow"] = ["frame"]
    elif mutation == "missing": tasks.pop()
    elif mutation == "crossing": tasks[0]["design"]["variant"] = 1 - tasks[0]["design"]["variant"]
    elif mutation == "rectpixels": tasks[0]["rendered"]["regions"][1]["x"] += 5
    elif mutation == "linepixels":
        task = next(t for t in tasks if t["family"] == "textalign" and t["design"]["answer"] == "left")
        region = next(r for r in task["rendered"]["regions"] if r["id"] == "text-0")
        for line in task["design"]["lines"]["text-0"]:
            line["x"] = region["x"] + region["width"] - line["width"]
        task["design"]["answer"] = "right"
        task["groundTruth"]["choice"] = chr(65 + task["design"]["options"].index("right"))
    shutil.copytree(MANIFEST.parent, tmp_path, dirs_exist_ok=True)
    if mutation == "pixels":
        path = tmp_path / tasks[0]["imageFilename"]
        Image.new("RGB", (1600, 1200), "white").save(path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        for task in tasks:
            if task["imageFilename"] == path.name:
                task["imageSha256"] = digest
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(tasks))
    with pytest.raises(ValueError, match=match):
        require_valid_qualitative(manifest)
