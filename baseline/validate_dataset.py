"""Frozen LayoutBench dataset gate: every validity property, no trust."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = ROOT / "dataset" / "layoutbench-v0.2"
MANIFEST_PATH = DATASET_DIR / "manifest.json"
PROMPTS_PATH = Path(__file__).with_name("prompts.json")

CANVAS = (800, 600)
DPR = 2
PNG_SIZE = (CANVAS[0] * DPR, CANVAS[1] * DPR)
FONT_PATH = "fonts/DejaVuSans.ttf"
FONT_SHA256 = "abdc775b21b1bc470d50c97e790d276f2054b7504e56e5bd3e64f48d68582322"

CHOICE_FAMILIES = ("flow", "distribute", "align", "gap", "pad", "columns",
                   "textjustify", "headerpad", "regionpad", "tablepad")
NUMERIC_FAMILIES = ("gapnum", "headerpx", "regionpx")
FAMILIES = CHOICE_FAMILIES + NUMERIC_FAMILIES

LABELS = {
    "flow": ["A", "B", "C", "D"],
    "distribute": ["A", "B", "C", "D", "E"],
    "align": ["A", "B", "C", "D"],
    "gap": ["A", "B", "C", "D", "E", "F", "G"],
    "pad": ["A", "B", "C", "D", "E"],
    "columns": ["A", "B", "C"],
    "textjustify": ["A", "B", "C", "D"],
    "headerpad": ["A", "B", "C"],
    "regionpad": ["A", "B", "C", "D", "E"],
    "tablepad": ["A", "B", "C", "D"],
}

EXPECTED_COUNTS = {
    "flow": 16, "distribute": 20, "align": 16, "gap": 16, "pad": 16,
    "columns": 12, "textjustify": 16, "headerpad": 18, "regionpad": 16,
    "tablepad": 12, "gapnum": 16, "headerpx": 18, "regionpx": 16,
}

GAP_TOKENS = [0, 4, 8, 12, 16, 24, 32]
PAD_TOKENS = [8, 16, 24, 32, 48]
TABLE_TOKENS = [4, 8, 12, 16]
TOKEN_SETS = {"gap": GAP_TOKENS, "pad": PAD_TOKENS, "regionpad": PAD_TOKENS,
              "tablepad": TABLE_TOKENS}
TOKEN_KEYS = {"gap": "gap_px", "pad": "padding_px", "regionpad": "pad_px",
              "tablepad": "cell_pad_px"}

PALETTE = {
    "light": {"canvas": (241, 245, 249), "card": (255, 255, 255),
              "border": (148, 163, 184), "tint": (214, 224, 235)},
    "dark": {"canvas": (9, 13, 22), "card": (17, 24, 39),
             "border": (75, 85, 99), "tint": (45, 58, 80)},
}

FORBIDDEN_WORDS = {
    "px", "pixel", "pixels", "space", "spaces", "between", "justify",
    "justified", "justification", "stretch", "stretched", "padding", "pad",
    "padded", "gap", "gaps", "column", "columns", "row", "rows", "left",
    "right", "center", "centered", "middle", "top", "bottom", "above",
    "below", "equal", "larger", "smaller", "bigger", "biggest", "border",
    "bordered", "edge", "edges", "container", "item", "items", "text",
    "align", "aligned", "alignment", "start", "end", "grid", "table",
    "tables", "cell", "cells", "header", "headers", "title", "one", "two",
    "three", "four", "five", "first", "second", "third", "single",
    "double", "triple", "more", "less", "most", "least", "wide", "narrow",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_manifest() -> list[dict]:
    data = json.loads(MANIFEST_PATH.read_text())
    if not isinstance(data, list) or not data:
        raise ValueError("Manifest must be a nonempty array")
    return data


def load_prompts() -> dict:
    return json.loads(PROMPTS_PATH.read_text())


def expected_prompt(family: str, options: list[str] | None) -> str:
    template = load_prompts()[family]
    if "{options}" not in template:
        return template
    letters = ["A", "B", "C", "D", "E", "F", "G"]
    block = "\n".join(f"{letters[i]}: {value}" for i, value in enumerate(options or []))
    return template.replace("{options}", block)


def check_identity(tasks: list[dict]) -> None:
    seen = set()
    for task in tasks:
        for key in ("taskId", "family", "groupId", "imageFilename", "imageSha256",
                    "groundTruth", "prompt", "design", "domText", "rendered"):
            if key not in task:
                raise ValueError(f"Task missing {key}: {task.get('taskId')}")
        if task["family"] not in FAMILIES:
            raise ValueError(f"Unknown family: {task['family']}")
        if task["taskId"] in seen:
            raise ValueError(f"Duplicate taskId: {task['taskId']}")
        seen.add(task["taskId"])
        want = f"layoutbench-{task['family']}-"
        if not task["taskId"].startswith(want) or not re.fullmatch(r"\d{2}", task["taskId"][len(want):]):
            raise ValueError(f"Bad taskId shape: {task['taskId']}")
    counts: dict[str, int] = {}
    for task in tasks:
        counts[task["family"]] = counts.get(task["family"], 0) + 1
    if counts != EXPECTED_COUNTS:
        raise ValueError(f"Corpus counts differ: {counts}")


def check_images(tasks: list[dict]) -> dict[str, Image.Image]:
    images: dict[str, Image.Image] = {}
    hashes = set()
    for task in tasks:
        name = task["imageFilename"]
        if "/" in name or "\\" in name or not name.endswith(".png"):
            raise ValueError(f"Unsafe image filename: {name}")
        path = DATASET_DIR / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Image missing or symlink: {name}")
        digest = _sha256(path)
        if digest != task["imageSha256"]:
            raise ValueError(f"Image hash differs: {name}")
        if digest in hashes and name not in images:
            raise ValueError(f"Duplicate PNG bytes: {name}")
        hashes.add(digest)
        if name not in images:
            image = Image.open(path).convert("RGB")
            if image.size != PNG_SIZE:
                raise ValueError(f"Bad PNG dimensions: {name} {image.size}")
            images[name] = image
    from collections import Counter

    multiplicities = Counter(t["imageFilename"] for t in tasks)
    if max(multiplicities.values()) > 2:
        raise ValueError("An image is shared by more than two tasks")
    return images


def check_rendered(tasks: list[dict]) -> None:
    for task in tasks:
        rendered = task["rendered"]
        if (rendered["width"], rendered["height"]) != CANVAS or rendered["dpr"] != DPR:
            raise ValueError(f"Canvas differs: {task['taskId']}")
        if rendered["colorSpace"] != "srgb":
            raise ValueError(f"Color space differs: {task['taskId']}")
        font = rendered["font"]
        if font["path"] != FONT_PATH or font["sha256"] != FONT_SHA256:
            raise ValueError(f"Font differs: {task['taskId']}")
        if not isinstance(rendered["regions"], list) or not rendered["regions"]:
            raise ValueError(f"No decoded regions: {task['taskId']}")
    if _sha256(DATASET_DIR / FONT_PATH) != FONT_SHA256:
        raise ValueError("Dataset font bytes differ")


def check_dom_text(tasks: list[dict]) -> None:
    for task in tasks:
        words = set(re.findall(r"[A-Za-z]+", task["domText"].lower()))
        leaked = words & FORBIDDEN_WORDS
        if leaked:
            raise ValueError(f"Answer-adjacent words in pixels {task['taskId']}: {sorted(leaked)}")
        if re.search(r"\d", task["domText"]):
            raise ValueError(f"Digits in pixels: {task['taskId']}")


def check_prompts(tasks: list[dict]) -> None:
    for task in tasks:
        options = task["design"].get("options")
        if task["prompt"] != expected_prompt(task["family"], options):
            raise ValueError(f"Prompt differs from frozen template: {task['taskId']}")


def check_choice_ground_truth(tasks: list[dict]) -> None:
    by_family: dict[str, list[dict]] = {}
    for task in tasks:
        by_family.setdefault(task["family"], []).append(task)
    for family in CHOICE_FAMILIES:
        members = by_family[family]
        letters = LABELS[family]
        seen: dict[str, int] = {}
        for task in members:
            truth = task["groundTruth"]
            if set(truth) != {"choice"} or truth["choice"] not in letters:
                raise ValueError(f"Bad choice truth: {task['taskId']}")
            seen[truth["choice"]] = seen.get(truth["choice"], 0) + 1
        lo, hi = min(seen.values()), max(seen.values())
        if set(seen) != set(letters) or hi - lo > 1:
            raise ValueError(f"Unbalanced truth letters {family}: {seen}")
        if family in TOKEN_SETS:
            check_full_options(family, members)


def check_full_options(family: str, members: list[dict]) -> None:
    # The set is fixed; distractor order is shuffled rather than sorted.
    tokens = TOKEN_SETS[family]
    key = TOKEN_KEYS[family]
    letters = LABELS[family]
    for task in members:
        options = task["design"].get("options")
        if not options or len(options) != len(tokens) or len(set(options)) != len(tokens):
            raise ValueError(f"Bad options: {task['taskId']}")
        values = []
        for option in options:
            match = re.fullmatch(r"(\d+)px", option)
            if not match or int(match.group(1)) not in tokens:
                raise ValueError(f"Option outside token set {task['taskId']}: {option}")
            values.append(int(match.group(1)))
        if sorted(values) != sorted(tokens):
            raise ValueError(f"Options are not the full token set: {task['taskId']}")
        truth_px = task["design"][key]
        truth_index = values.index(truth_px)
        if task["groundTruth"]["choice"] != letters[truth_index]:
            raise ValueError(f"Choice letter mislabels truth: {task['taskId']}")


def check_crossing(tasks: list[dict]) -> None:
    by_family: dict[str, list[dict]] = {}
    for task in tasks:
        by_family.setdefault(task["family"], []).append(task)

    def crossed(family: str, key_fn, levels: set) -> None:
        # Letter grouping is meaningful only where the choice letter is a
        # deterministic function of the design (verified by check_choice_maps).
        seen: dict[str, set] = {}
        for task in by_family[family]:
            seen.setdefault(task["groundTruth"]["choice"], set()).add(key_fn(task))
        for answer, values in seen.items():
            if values != levels:
                raise ValueError(f"Uncrossed {family} {answer}: {sorted(values, key=repr)}")

    def spanned(family: str, key_fn, levels: set) -> None:
        # Token families randomize the letter, so cross the TOKEN VALUE against
        # each nuisance axis: no nuisance level may predict the token.
        seen: dict[int, set] = {}
        for task in by_family[family]:
            seen.setdefault(task["design"][TOKEN_KEYS[family]], set()).add(key_fn(task))
        for token, values in seen.items():
            if values != levels:
                raise ValueError(f"Token {token} uncrossed in {family}: {sorted(values, key=repr)}")

    def distinct_letters(family: str) -> None:
        # The truth letter is the option slot: within one token value no slot
        # may repeat, so the slot carries no information about the token.
        seen: dict[int, list] = {}
        for task in by_family[family]:
            seen.setdefault(task["design"][TOKEN_KEYS[family]], []).append(task["groundTruth"]["choice"])
        for token, letters in seen.items():
            if len(set(letters)) != len(letters):
                raise ValueError(f"Repeated truth slot for token {token} in {family}: {letters}")

    themes = {"light", "dark"}
    for family in ("flow", "distribute", "align"):
        crossed(family, lambda t: t["design"]["theme"], themes)
    crossed("flow", lambda t: t["design"]["content_variant"], {"uniform", "variable"})
    for family in ("distribute", "align"):
        crossed(family, lambda t: t["design"]["direction"], {"row", "column"})
    for family in ("gap", "pad"):
        spanned(family, lambda t: t["design"]["theme"], themes)
        spanned(family, lambda t: t["design"]["direction"], {"row", "column"})
        distinct_letters(family)
    for family in ("columns", "textjustify"):
        crossed(family, lambda t: t["design"]["theme"], themes)
    crossed("columns", lambda t: t["design"]["text_align"], {"left", "justify"})
    crossed("textjustify", lambda t: t["design"]["column_count"], {1, 2})
    crossed("headerpad", lambda t: t["design"]["theme"], themes)
    spanned("regionpad", lambda t: t["design"]["theme"], themes)
    spanned("regionpad", lambda t: t["design"]["bordered"], {True, False})
    distinct_letters("regionpad")
    spanned("tablepad", lambda t: t["design"]["theme"], themes)
    spanned("tablepad", lambda t: (t["design"]["rows"], t["design"]["cols"]),
            {(2, 2), (2, 3), (3, 3)})
    crossed("tablepad", lambda t: (t["design"]["rows"], t["design"]["cols"]),
            {(2, 2), (2, 3), (3, 3)})
    check_flow_counts(by_family["flow"])


def check_flow_counts(members: list[dict]) -> None:
    from collections import Counter

    distributions = [Counter(task["design"]["item_count"] for task in members
                             if task["design"]["direction"] == direction)
                     for direction in ("row", "column", "grid-2col", "grid-3col")]
    if any(distribution != distributions[0] for distribution in distributions[1:]):
        raise ValueError("Item count distribution differs across flow directions")
    by_count: dict[int, set] = {}
    by_direction: dict[str, set] = {}
    for task in members:
        by_count.setdefault(task["design"]["item_count"], set()).add(task["design"]["direction"])
        by_direction.setdefault(task["design"]["direction"], set()).add(task["design"]["item_count"])
    for count, directions in by_count.items():
        if len(directions) < 2:
            raise ValueError(f"Item count {count} identifies one flow direction: {directions}")
    for direction, counts in by_direction.items():
        if len(counts) < 2:
            raise ValueError(f"Flow direction {direction} has one item count: {counts}")


RECT_TOL = 1.0


def _bands(items: list[dict], axis: int) -> list[list[dict]]:
    key = (lambda r: (r["y"], r["x"])) if axis == 1 else (lambda r: (r["x"], r["y"]))
    ordered = sorted(items, key=key)
    bands = [[ordered[0]]]
    for item in ordered[1:]:
        first = bands[-1][0]
        lo = item["y"] if axis == 1 else item["x"]
        size = item["height"] if axis == 1 else item["width"]
        first_lo = first["y"] if axis == 1 else first["x"]
        first_size = first["height"] if axis == 1 else first["width"]
        if lo < first_lo + first_size and first_lo < lo + size:
            bands[-1].append(item)
        else:
            bands.append([item])
    return bands


def derive_direction(items: list[dict]) -> str:
    """Recover row/column/grid from item boxes, never from the design."""
    if len(items) < 2:
        raise ValueError("Too few items to judge direction")
    rows = _bands(items, 1)
    cols = _bands(items, 0)
    if len(rows) == 1 and len(cols) == len(items):
        return "row"
    if len(cols) == 1 and len(rows) == len(items):
        return "column"
    if len(rows) > 1 and len(cols) > 1:
        if len(cols) == 2:
            return "grid-2col"
        if len(cols) == 3:
            return "grid-3col"
    raise ValueError(f"Ambiguous layout bands: {len(cols)} columns x {len(rows)} rows")


def _axis_spans(items: list[dict], stage: dict, pad: float, direction: str) -> tuple:
    if direction == "row":
        lo = min(item["x"] for item in items)
        hi = max(item["x"] + item["width"] for item in items)
        stage_lo, stage_hi = stage["x"], stage["x"] + stage["width"]
        ordered = sorted(items, key=lambda r: r["x"])
        inners = [ordered[k + 1]["x"] - (ordered[k]["x"] + ordered[k]["width"])
                  for k in range(len(ordered) - 1)]
    else:
        lo = min(item["y"] for item in items)
        hi = max(item["y"] + item["height"] for item in items)
        stage_lo, stage_hi = stage["y"], stage["y"] + stage["height"]
        ordered = sorted(items, key=lambda r: r["y"])
        inners = [ordered[k + 1]["y"] - (ordered[k]["y"] + ordered[k]["height"])
                  for k in range(len(ordered) - 1)]
    return lo - (stage_lo + pad), (stage_hi - pad) - hi, inners


def derive_justify(items: list[dict], stage: dict, pad: float, gap: float, direction: str) -> str:
    """Recover main-axis distribution from edge gaps and inner gaps.

    Note the flex `gap` participates: under space-around each edge holds half
    a free-space unit while each inner holds a full unit PLUS the fixed gap,
    so edge == (inner - gap) / 2, not inner / 2.
    """
    if direction not in ("row", "column"):
        raise ValueError(f"Justify is not swept for {direction}")
    edge_lo, edge_hi, inners = _axis_spans(items, stage, pad, direction)
    if edge_lo < -RECT_TOL or edge_hi < -RECT_TOL:
        raise ValueError(f"Content overflows padding: {edge_lo:.1f}/{edge_hi:.1f}")
    equal_inners = all(abs(gap_px - inners[0]) <= RECT_TOL for gap_px in inners)
    if edge_lo <= RECT_TOL and edge_hi <= RECT_TOL:
        if equal_inners and inners[0] > gap + RECT_TOL:
            return "space-between"
        raise ValueError("Content fills the axis without space-between gaps")
    if equal_inners:
        around_edge = (inners[0] - gap) / 2
        if abs(edge_lo - around_edge) <= RECT_TOL and abs(edge_hi - around_edge) <= RECT_TOL:
            return "space-around"
    if edge_lo <= RECT_TOL:
        return "start"
    if edge_hi <= RECT_TOL:
        return "end"
    if abs(edge_lo - edge_hi) <= RECT_TOL:
        return "center"
    raise ValueError(f"Ambiguous justify edges: {edge_lo:.1f}/{edge_hi:.1f}")


def derive_align(items: list[dict], stage: dict, pad: float, direction: str) -> str:
    """Recover cross-axis alignment from the cross-axis span."""
    if direction == "row":
        lo = min(item["y"] for item in items)
        hi = max(item["y"] + item["height"] for item in items)
        stage_lo, stage_hi = stage["y"], stage["y"] + stage["height"]
        sizes = [item["height"] for item in items]
    elif direction == "column":
        lo = min(item["x"] for item in items)
        hi = max(item["x"] + item["width"] for item in items)
        stage_lo, stage_hi = stage["x"], stage["x"] + stage["width"]
        sizes = [item["width"] for item in items]
    else:
        raise ValueError(f"Align is not swept for {direction}")
    edge_lo, edge_hi = lo - (stage_lo + pad), (stage_hi - pad) - hi
    full = (stage_hi - pad) - (stage_lo + pad)
    if all(size >= full - RECT_TOL for size in sizes) and edge_lo <= RECT_TOL and edge_hi <= RECT_TOL:
        return "stretch"
    if edge_lo < -RECT_TOL or edge_hi < -RECT_TOL:
        raise ValueError(f"Content overflows padding: {edge_lo:.1f}/{edge_hi:.1f}")
    if edge_lo <= RECT_TOL and edge_hi <= RECT_TOL:
        raise ValueError("Content fills the cross axis without stretching")
    if edge_lo <= RECT_TOL:
        return "start"
    if edge_hi <= RECT_TOL:
        return "end"
    if abs(edge_lo - edge_hi) <= RECT_TOL:
        return "center"
    raise ValueError(f"Ambiguous align edges: {edge_lo:.1f}/{edge_hi:.1f}")


def check_table_cells(task: dict) -> None:
    # Every cell, not just 0-0: top/left/bottom pads equal the token (single
    # line of text, top-aligned); the right side only needs to stay inside.
    regions = regions_by_role(task)
    cells = {rect_id: rect for (role, rect_id), rect in regions.items() if role == "cell"}
    texts = {rect_id: rect for (role, rect_id), rect in regions.items() if role == "celltext"}
    design = task["design"]
    want_rows = {(r, c) for r in range(design["rows"]) for c in range(design["cols"])}
    if {tuple(map(int, key.split("-"))) for key in cells} != want_rows:
        raise ValueError(f"Cell census differs: {task['taskId']}")
    for key, cell in cells.items():
        text = texts.get(key)
        if text is None:
            raise ValueError(f"Cell text missing: {task['taskId']} {key}")
        pads = {
            "top": text["y"] - (cell["y"] + 1),
            "left": text["x"] - (cell["x"] + 1),
            "bottom": (cell["y"] + cell["height"] - 1) - (text["y"] + text["height"]),
        }
        for side, value in pads.items():
            if abs(value - design["cell_pad_px"]) > 0.6:
                raise ValueError(f"Cell {key} {side} pad differs {task['taskId']}: {value}")
        right = (cell["x"] + cell["width"] - 1) - (text["x"] + text["width"])
        if right < -0.1:
            raise ValueError(f"Cell {key} text overflows {task['taskId']}: {right}")


FLOW_CHOICE = {"row": "A", "column": "B", "grid-2col": "C", "grid-3col": "D"}
DISTRIBUTE_CHOICE = {"start": "A", "center": "B", "end": "C",
                     "space-between": "D", "space-around": "E"}
ALIGN_CHOICE = {"start": "A", "center": "B", "end": "C", "stretch": "D"}
COLUMNS_CHOICE = {1: "A", 2: "B", 3: "C"}
TEXT_ALIGN_CHOICE = {"left": "A", "center": "B", "right": "C", "justify": "D"}


def check_choice_maps(tasks: list[dict]) -> None:
    # Every fixed-option choice letter must equal the mapping of the DECODED
    # construct, so a builder mislabel cannot hide behind balanced letters.
    for task in tasks:
        family = task["family"]
        if family not in ("flow", "distribute", "align", "columns",
                          "textjustify", "headerpad"):
            continue
        design = task["design"]
        decoded = design.get("decoded") or {}
        want = None
        if family in ("flow", "distribute", "align"):
            regions = regions_by_role(task)
            items = sorted((rect for (role, _), rect in regions.items() if role == "item"),
                           key=lambda r: int(r["id"]))
            stage = regions[("stage", "stage")]
            try:
                if family == "flow":
                    want = FLOW_CHOICE[derive_direction(items)]
                elif family == "distribute":
                    want = DISTRIBUTE_CHOICE[derive_justify(items, stage, design["padding_px"],
                                                           design["gap_px"], design["direction"])]
                else:
                    want = ALIGN_CHOICE[derive_align(items, stage, design["padding_px"],
                                                   design["direction"])]
            except (ValueError, KeyError) as error:
                raise ValueError(f"Choice undecodable {task['taskId']}: {error}") from error
        elif family == "columns":
            want = COLUMNS_CHOICE.get(decoded.get("column_count"))
        elif family == "textjustify":
            try:
                derived = {derive_alignment(lines) for lines in (design.get("lines") or {}).values()}
            except ValueError as error:
                raise ValueError(f"Choice undecodable {task['taskId']}: {error}") from error
            if len(derived) != 1:
                raise ValueError(f"Columns disagree {task['taskId']}: {sorted(derived)}")
            want = TEXT_ALIGN_CHOICE[derived.pop()]
        else:
            above, below = decoded.get("above", -1), decoded.get("below", -1)
            want = "A" if above > below else "B" if below > above else "C"
        if task["groundTruth"]["choice"] != want:
            raise ValueError(f"Choice mislabels decoded construct {task['taskId']}: want {want}")


def check_decoded(tasks: list[dict]) -> None:
    for task in tasks:
        design = task["design"]
        decoded = design.get("decoded") or {}
        if design["kind"] == "abstract":
            if design["justify_content"] in ("space-between", "space-around"):
                if decoded.get("gap", -1) < design["gap_px"] - 0.01:
                    raise ValueError(f"Decoded gap below CSS gap: {task['taskId']}")
            elif abs(decoded.get("gap", -1) - design["gap_px"]) > 0.6:
                raise ValueError(f"Decoded gap differs {task['taskId']}: {decoded.get('gap')}")
            rests_left = design["direction"] in ("row", "grid-2col", "grid-3col") and design["justify_content"] == "start"
            rests_top = design["direction"] == "column" and design["justify_content"] == "start"
            if design["direction"].startswith("grid"):
                want_cols = 2 if design["direction"] == "grid-2col" else 3
                if decoded.get("grid_columns") != want_cols:
                    raise ValueError(f"Decoded grid columns differ: {task['taskId']}")
            if rests_left and abs(decoded.get("pad_left", -1) - design["padding_px"]) > 0.6:
                raise ValueError(f"Decoded pad_left differs: {task['taskId']}")
            if rests_top and abs(decoded.get("pad_top", -1) - design["padding_px"]) > 0.6:
                raise ValueError(f"Decoded pad_top differs: {task['taskId']}")
            regions = regions_by_role(task)
            items = sorted((rect for (role, _), rect in regions.items() if role == "item"),
                           key=lambda r: int(r["id"]))
            stage = regions[("stage", "stage")]
            try:
                derived_direction = derive_direction(items)
            except ValueError as error:
                raise ValueError(f"Direction undecodable {task['taskId']}: {error}") from error
            if derived_direction != design["direction"]:
                raise ValueError(f"Direction differs {task['taskId']}: {derived_direction}")
            if not design["direction"].startswith("grid"):
                try:
                    derived_justify = derive_justify(items, stage, design["padding_px"],
                                                   design["gap_px"], design["direction"])
                    derived_align = derive_align(items, stage, design["padding_px"],
                                               design["direction"])
                except ValueError as error:
                    raise ValueError(f"Justify/align undecodable {task['taskId']}: {error}") from error
                if derived_justify != design["justify_content"]:
                    raise ValueError(f"Justify differs {task['taskId']}: {derived_justify}")
                if derived_align != design["align_items"]:
                    raise ValueError(f"Align differs {task['taskId']}: {derived_align}")
        elif design["archetype"] == "header":
            for key in ("above", "below"):
                if abs(decoded.get(key, -1) - design[f"{key}_px"]) > 0.6:
                    raise ValueError(f"Decoded {key} differs: {task['taskId']}")
        elif design["archetype"] == "region":
            sides = [decoded.get(side, -1) for side in ("pad_top", "pad_left", "pad_bottom", "pad_right")]
            if any(abs(side - design["pad_px"]) > 0.6 for side in sides):
                raise ValueError(f"Region pad not uniform: {task['taskId']} {sides}")
            roles = {(role, rect_id) for (role, rect_id) in regions_by_role(task)}
            if design["bordered"]:
                if ("card", "card") not in roles:
                    raise ValueError(f"Bordered region has no card: {task['taskId']}")
            else:
                if ("card", "card") in roles:
                    raise ValueError(f"Bare region renders a card: {task['taskId']}")
                if ("bare-wrap", "bare") not in roles:
                    raise ValueError(f"Bare region has no bare wrap: {task['taskId']}")
        elif design["archetype"] == "table":
            for key in ("cell_pad_top", "cell_pad_left"):
                if abs(decoded.get(key, -1) - design["cell_pad_px"]) > 0.6:
                    raise ValueError(f"Decoded {key} differs: {task['taskId']}")
            check_table_cells(task)
        else:
            if decoded.get("column_count") != design["column_count"]:
                raise ValueError(f"Decoded column count differs: {task['taskId']}")
            if design["column_count"] > 1 and abs(decoded.get("column_gap", -1) - 32) > 0.6:
                raise ValueError(f"Column gap differs: {task['taskId']}")
        for key, overflow in (design.get("overflow") or {}).items():
            if overflow["scroll"] > overflow["client"] + 1:
                raise ValueError(f"Text overflow {task['taskId']} {key}")


def line_edges(lines: list[dict]) -> tuple[list[float], list[float], list[float]]:
    lefts = [line["x"] for line in lines]
    rights = [line["x"] + line["width"] for line in lines]
    mids = [(left + right) / 2 for left, right in zip(lefts, rights)]
    return lefts, rights, mids


def paragraph_last_indexes(lines: list[dict]) -> set[int]:
    last = set()
    for i, line in enumerate(lines):
        nxt = lines[i + 1] if i + 1 < len(lines) else None
        if nxt is None or nxt["y"] - (line["y"] + line["height"]) > line["height"] * 0.5:
            last.add(i)
    return last


def derive_alignment(lines: list[dict]) -> str:
    if len(lines) < 3:
        raise ValueError("Too few text lines to judge alignment")
    lefts, rights, mids = line_edges(lines)
    last = paragraph_last_indexes(lines)
    body = [i for i in range(len(lines)) if i not in last]
    if len(body) < 2:
        raise ValueError("Too few body lines to judge alignment")
    spread = lambda values: max(values) - min(values)
    if spread(lefts) <= 1.0 and spread([rights[i] for i in body]) <= 1.0:
        return "justify"
    if spread(lefts) <= 1.0 and spread(rights) > 10:
        return "left"
    if spread(rights) <= 1.0 and spread(lefts) > 10:
        return "right"
    if spread(mids) <= 1.0 and spread(lefts) > 10 and spread(rights) > 10:
        return "center"
    raise ValueError(f"Ambiguous line edges: lefts={lefts} rights={rights}")


def check_alignment(tasks: list[dict]) -> None:
    for task in tasks:
        design = task["design"]
        if design.get("archetype") not in ("columns", "text"):
            continue
        for col_id, lines in (design.get("lines") or {}).items():
            try:
                derived = derive_alignment(lines)
            except ValueError as error:
                raise ValueError(f"Alignment undecodable {task['taskId']} col {col_id}: {error}") from error
            if derived != design["text_align"]:
                raise ValueError(f"Alignment differs {task['taskId']} col {col_id}: {derived}")
        if len(design.get("lines") or {}) != design["column_count"]:
            raise ValueError(f"Line-rect column census differs: {task['taskId']}")


def check_numeric_truth(tasks: list[dict]) -> None:
    for task in tasks:
        design = task["design"]
        decoded = design.get("decoded") or {}
        truth = task["groundTruth"]
        if task["family"] == "gapnum":
            if set(truth) != {"gap_px"} or truth["gap_px"] != round(decoded["gap"]):
                raise ValueError(f"Numeric truth differs: {task['taskId']}")
        elif task["family"] == "headerpx":
            if (set(truth) != {"above_px", "below_px"}
                    or truth["above_px"] != round(decoded["above"])
                    or truth["below_px"] != round(decoded["below"])):
                raise ValueError(f"Numeric truth differs: {task['taskId']}")
        elif task["family"] == "regionpx":
            if set(truth) != {"pad_px"} or truth["pad_px"] != round(decoded["pad"]):
                raise ValueError(f"Numeric truth differs: {task['taskId']}")


def check_shared_images(tasks: list[dict]) -> None:
    by_image: dict[str, list[dict]] = {}
    for task in tasks:
        by_image.setdefault(task["imageFilename"], []).append(task)
    allowed = [{"gap", "gapnum"}, {"headerpad", "headerpx"},
               {"regionpad", "regionpx"}, {"columns", "textjustify"}]
    for name, members in by_image.items():
        families = sorted(t["family"] for t in members)
        if len(members) == 1:
            if members[0]["family"] in NUMERIC_FAMILIES:
                raise ValueError(f"Orphan numeric task: {members[0]['taskId']}")
            if members[0]["groupId"] != name.removesuffix(".png"):
                raise ValueError(f"Solo image group differs: {name}")
            continue
        if len(members) != 2:
            raise ValueError(f"Image shared by {len(members)} tasks: {name}")
        first, second = members
        if set(families) not in allowed:
            raise ValueError(f"Wrong share pair: {name} {families}")
        if first["groupId"] != second["groupId"] or first["groupId"] != name.removesuffix(".png"):
            raise ValueError(f"Shared image group differs: {name}")
        for key in ("imageSha256", "domText"):
            if first[key] != second[key]:
                raise ValueError(f"Shared image {key} differs: {name}")
        if first["rendered"]["regions"] != second["rendered"]["regions"]:
            raise ValueError(f"Shared image regions differ: {name}")
        if first["design"].get("decoded") != second["design"].get("decoded"):
            raise ValueError(f"Shared image decoded differs: {name}")


def px(image: Image.Image, x: float, y: float) -> tuple[int, int, int]:
    return image.getpixel((int(x * DPR), int(y * DPR)))


def regions_by_role(task: dict) -> dict[tuple[str, str], dict]:
    return {(r["role"], r["id"]): r for r in task["rendered"]["regions"]}


def adjacent_pairs(items: list[dict], direction: str) -> list[tuple[dict, dict]]:
    if direction in ("row", "column"):
        return list(zip(items, items[1:]))
    ordered = sorted(items, key=lambda r: (r["y"], r["x"]))
    rows: list[list[dict]] = [[ordered[0]]]
    for item in ordered[1:]:
        first = rows[-1][0]
        if item["y"] < first["y"] + first["height"] and first["y"] < item["y"] + item["height"]:
            rows[-1].append(item)
        else:
            rows.append([item])
    pairs = []
    for row in rows:
        across = sorted(row, key=lambda r: r["x"])
        pairs.extend(zip(across, across[1:]))
    return pairs


def check_content_bands(task: dict, image: Image.Image, palette: dict,
                        items: list[dict], stage: dict) -> None:
    # Anchor the decoded boxes to paint: every band between the stage edge and
    # the content span is background at its midpoint, and just inside each
    # content edge is item ink. Band midpoints are provably empty: each lies
    # outside every item box on its side's axis.
    left = min(items, key=lambda r: r["x"])
    right = max(items, key=lambda r: r["x"] + r["width"])
    top = min(items, key=lambda r: r["y"])
    bottom = max(items, key=lambda r: r["y"] + r["height"])
    stage_right, stage_bottom = stage["x"] + stage["width"], stage["y"] + stage["height"]
    bands = [
        ((stage["x"] + left["x"]) / 2, left["y"] + left["height"] / 2),
        ((right["x"] + right["width"] + stage_right) / 2, right["y"] + right["height"] / 2),
        (top["x"] + top["width"] / 2, (stage["y"] + top["y"]) / 2),
        (bottom["x"] + bottom["width"] / 2, (bottom["y"] + bottom["height"] + stage_bottom) / 2),
    ]
    for x, y in bands:
        if px(image, x, y) != palette["card"]:
            raise ValueError(f"Content band not background: {task['taskId']} ({x:.1f},{y:.1f})")
    ink = [
        (left["x"] + 3, left["y"] + left["height"] / 2),
        (right["x"] + right["width"] - 3, right["y"] + right["height"] / 2),
        (top["x"] + top["width"] / 2, top["y"] + 3),
        (bottom["x"] + bottom["width"] / 2, bottom["y"] + bottom["height"] - 3),
    ]
    for x, y in ink:
        if px(image, x, y) == palette["card"]:
            raise ValueError(f"Content edge not ink: {task['taskId']} ({x:.1f},{y:.1f})")


def check_pixels(tasks: list[dict], images: dict[str, Image.Image]) -> None:
    for task in tasks:
        image = images[task["imageFilename"]]
        palette = PALETTE[task["design"]["theme"]]
        regions = regions_by_role(task)
        design = task["design"]
        if design["kind"] == "abstract":
            items = sorted(
                (r for (role, _), r in regions.items() if role == "item"),
                key=lambda r: int(r["id"]),
            )
            stage = regions[("stage", "stage")]
            for item in items:
                if px(image, item["x"] + item["width"] / 2, item["y"] + item["height"] / 2) == palette["card"]:
                    raise ValueError(f"Item interior matches background: {task['taskId']}")
            pairs = adjacent_pairs(items, design["direction"])
            if not pairs:
                raise ValueError(f"No adjacent item pairs: {task['taskId']}")
            for first, second in pairs:
                horizontal = design["direction"] != "column"
                if horizontal:
                    seam = first["x"] + first["width"]
                    other = second["x"]
                    mid_y = first["y"] + min(first["height"], second["height"]) / 2
                else:
                    seam = first["y"] + first["height"]
                    other = second["y"]
                    mid_y = None
                gap = other - seam
                if gap < 1:
                    inside = (
                        (px(image, seam - 3, first["y"] + first["height"] / 2), px(image, other + 3, second["y"] + second["height"] / 2))
                        if horizontal
                        else (
                            px(image, first["x"] + first["width"] / 2, seam - 3),
                            px(image, second["x"] + second["width"] / 2, other + 3),
                        )
                    )
                    if any(pixel == palette["card"] for pixel in inside):
                        raise ValueError(f"Flush seam shows background: {task['taskId']}")
                elif horizontal:
                    if px(image, (seam + other) / 2, mid_y) != palette["card"]:
                        raise ValueError(f"Gap midline not background: {task['taskId']}")
                else:
                    mid_x = first["x"] + min(first["width"], second["width"]) / 2
                    if px(image, mid_x, (seam + other) / 2) != palette["card"]:
                        raise ValueError(f"Gap midline not background: {task['taskId']}")
            check_content_bands(task, image, palette, items, stage)
        elif design["archetype"] == "header":
            above = regions[("above-spacer", "above")]
            below = regions[("below-spacer", "below")]
            for rect in (above, below):
                if px(image, rect["x"] + rect["width"] / 2, rect["y"] + rect["height"] / 2) != palette["card"]:
                    raise ValueError(f"Header spacer not background: {task['taskId']}")
            for role in ("header", "tbody"):
                rect = regions[(role, role)]
                for y in (rect["y"] + 1, rect["y"] + rect["height"] - 1):
                    if px(image, rect["x"] + rect["width"] - 2, y) != palette["tint"]:
                        raise ValueError(f"Header block edge not visible: {task['taskId']} {role}")
        elif design["archetype"] == "region":
            content = regions[("content", "content")]
            outside = palette["card"] if design["bordered"] else palette["canvas"]
            samples = [
                ((content["x"] + content["width"] / 2, content["y"] - design["pad_px"] / 2)),
                ((content["x"] + content["width"] / 2, content["y"] + content["height"] + design["pad_px"] / 2)),
                ((content["x"] - design["pad_px"] / 2, content["y"] + content["height"] / 2)),
                ((content["x"] + content["width"] + design["pad_px"] / 2, content["y"] + content["height"] / 2)),
            ]
            for x, y in samples:
                if px(image, x, y) != outside:
                    raise ValueError(f"Region pad band not background: {task['taskId']}")
            if px(image, content["x"] + 12, content["y"] + 12) != palette["tint"]:
                raise ValueError(f"Content block not tinted: {task['taskId']}")
            if design["bordered"]:
                card = regions[("card", "card")]
                # Border centers, not edges: for a 1px border [e, e+1], sampling
                # e+0.5 always lands a device pixel fully inside the border.
                edges = [
                    (card["x"] + 0.5, card["y"] + card["height"] / 2),
                    (card["x"] + card["width"] - 0.5, card["y"] + card["height"] / 2),
                    (card["x"] + card["width"] / 2, card["y"] + 0.5),
                    (card["x"] + card["width"] / 2, card["y"] + card["height"] - 0.5),
                ]
                for x, y in edges:
                    if px(image, x, y) != palette["border"]:
                        raise ValueError(f"Card border pixel missing: {task['taskId']}")
        elif design["archetype"] == "table":
            cells = sorted((rect for (role, _), rect in regions.items() if role == "cell"),
                           key=lambda r: r["id"])
            if not cells:
                raise ValueError(f"No table cells: {task['taskId']}")
            for cell in cells:
                if px(image, cell["x"] + 0.5, cell["y"] + cell["height"] / 2) != palette["border"]:
                    raise ValueError(f"Cell border pixel missing: {task['taskId']} {cell['id']}")
                if px(image, cell["x"] + 3, cell["y"] + 3) != palette["tint"]:
                    raise ValueError(f"Cell interior not tinted: {task['taskId']} {cell['id']}")
        else:
            tcols = sorted(
                (r for (role, _), r in regions.items() if role == "tcol"),
                key=lambda r: r["x"],
            )
            for first, second in zip(tcols, tcols[1:]):
                mid = (first["x"] + first["width"] + second["x"]) / 2
                if px(image, mid, first["y"] + 40) != palette["card"]:
                    raise ValueError(f"Column gap not background: {task['taskId']}")


def require_valid_dataset(manifest_path: str | Path | None = None) -> list[dict]:
    global DATASET_DIR, MANIFEST_PATH
    if manifest_path is not None:
        MANIFEST_PATH = Path(manifest_path)
        DATASET_DIR = MANIFEST_PATH.parent
    tasks = load_manifest()
    check_identity(tasks)
    images = check_images(tasks)
    check_rendered(tasks)
    check_dom_text(tasks)
    check_prompts(tasks)
    check_choice_ground_truth(tasks)
    check_crossing(tasks)
    check_decoded(tasks)
    check_choice_maps(tasks)
    check_alignment(tasks)
    check_numeric_truth(tasks)
    check_shared_images(tasks)
    check_pixels(tasks, images)
    print(f"LayoutBench dataset valid: {len(tasks)} tasks, {len(images)} images")
    return tasks


def main() -> None:
    require_valid_dataset()


if __name__ == "__main__":
    main()
