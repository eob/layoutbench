"""Frozen LayoutBench dataset gate: every validity property, no trust."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = ROOT / "dataset" / "layoutbench-v0.1"
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
    "gap": ["A", "B", "C", "D"],
    "pad": ["A", "B", "C", "D"],
    "columns": ["A", "B", "C"],
    "textjustify": ["A", "B", "C", "D"],
    "headerpad": ["A", "B", "C"],
    "regionpad": ["A", "B", "C", "D"],
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
    letters = ["A", "B", "C", "D", "E"]
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
            check_token_options(family, members)


def nearest_neighbors(truth: int, tokens: list[int]) -> list[int]:
    return sorted([t for t in tokens if t != truth], key=lambda t: abs(t - truth))[:3]


def check_token_options(family: str, members: list[dict]) -> None:
    tokens = TOKEN_SETS[family]
    key = {"gap": "gap_px", "pad": "padding_px", "regionpad": "pad_px",
           "tablepad": "cell_pad_px"}[family]
    for task in members:
        options = task["design"].get("options")
        if not options or len(options) != 4 or len(set(options)) != 4:
            raise ValueError(f"Bad options: {task['taskId']}")
        values = []
        for option in options:
            match = re.fullmatch(r"(\d+)px", option)
            if not match or int(match.group(1)) not in tokens:
                raise ValueError(f"Option outside token set {task['taskId']}: {option}")
            values.append(int(match.group(1)))
        truth_px = task["design"][key]
        if truth_px not in values:
            raise ValueError(f"Truth missing from options: {task['taskId']}")
        if sorted(values) != sorted([truth_px, *nearest_neighbors(truth_px, tokens)]):
            raise ValueError(f"Distractors not nearest neighbors: {task['taskId']}")
        letters = ["A", "B", "C", "D"]
        if task["groundTruth"]["choice"] != letters[values.index(truth_px)]:
            raise ValueError(f"Choice letter mislabels truth: {task['taskId']}")


def check_crossing(tasks: list[dict]) -> None:
    by_family: dict[str, list[dict]] = {}
    for task in tasks:
        by_family.setdefault(task["family"], []).append(task)

    def crossed(family: str, key_fn, levels: set) -> None:
        seen: dict[str, set] = {}
        for task in by_family[family]:
            seen.setdefault(task["groundTruth"]["choice"], set()).add(key_fn(task))
        for answer, values in seen.items():
            if values != levels:
                raise ValueError(f"Uncrossed {family} {answer}: {sorted(values)}")

    themes = {"light", "dark"}
    for family in ("flow", "distribute", "align"):
        crossed(family, lambda t: t["design"]["theme"], themes)
    crossed("flow", lambda t: t["design"]["content_variant"], {"uniform", "variable"})
    for family in ("distribute", "align"):
        crossed(family, lambda t: t["design"]["direction"], {"row", "column"})
    for family in ("gap", "pad"):
        crossed(family, lambda t: t["design"]["theme"], themes)
        crossed(family, lambda t: t["design"]["direction"], {"row", "column"})
    for family in ("columns", "textjustify"):
        crossed(family, lambda t: t["design"]["theme"], themes)
    crossed("columns", lambda t: t["design"]["text_align"], {"left", "justify"})
    crossed("textjustify", lambda t: t["design"]["column_count"], {1, 2})
    crossed("headerpad", lambda t: t["design"]["theme"], themes)
    crossed("regionpad", lambda t: t["design"]["theme"], themes)
    crossed("regionpad", lambda t: t["design"]["bordered"], {True, False})
    crossed("tablepad", lambda t: (t["design"]["rows"], t["design"]["cols"]),
            {(2, 2), (2, 3), (3, 3)})


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
        elif design["archetype"] == "header":
            for key in ("above", "below"):
                if abs(decoded.get(key, -1) - design[f"{key}_px"]) > 0.6:
                    raise ValueError(f"Decoded {key} differs: {task['taskId']}")
            above, below = design["above_px"], design["below_px"]
            want = "A" if above > below else "B" if below > above else "C"
            if task["family"] == "headerpad" and task["groundTruth"]["choice"] != want:
                raise ValueError(f"Header comparison mislabeled: {task['taskId']}")
        elif design["archetype"] == "region":
            sides = [decoded.get(side, -1) for side in ("pad_top", "pad_left", "pad_bottom", "pad_right")]
            if any(abs(side - design["pad_px"]) > 0.6 for side in sides):
                raise ValueError(f"Region pad not uniform: {task['taskId']} {sides}")
        elif design["archetype"] == "table":
            for key in ("cell_pad_top", "cell_pad_left"):
                if abs(decoded.get(key, -1) - design["cell_pad_px"]) > 0.6:
                    raise ValueError(f"Decoded {key} differs: {task['taskId']}")
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
            if px(image, stage["x"] + 20, stage["y"] + 20) != palette["card"]:
                raise ValueError(f"Padding corner not background: {task['taskId']}")
        elif design["archetype"] == "header":
            above = regions[("above-spacer", "above")]
            below = regions[("below-spacer", "below")]
            for rect in (above, below):
                if px(image, rect["x"] + rect["width"] / 2, rect["y"] + rect["height"] / 2) != palette["card"]:
                    raise ValueError(f"Header spacer not background: {task['taskId']}")
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
                edges = [
                    (card["x"], card["y"] + card["height"] / 2),
                    (card["x"] + card["width"] - 1, card["y"] + card["height"] / 2),
                    (card["x"] + card["width"] / 2, card["y"]),
                    (card["x"] + card["width"] / 2, card["y"] + card["height"] - 1),
                ]
                for x, y in edges:
                    if px(image, x, y) != palette["border"]:
                        raise ValueError(f"Card border pixel missing: {task['taskId']}")
        elif design["archetype"] == "table":
            cell = regions[("cell", "0-0")]
            if px(image, cell["x"], cell["y"] + cell["height"] / 2) != palette["border"]:
                raise ValueError(f"Cell border pixel missing: {task['taskId']}")
            if px(image, cell["x"] + 3, cell["y"] + 3) != palette["tint"]:
                raise ValueError(f"Cell interior not tinted: {task['taskId']}")
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

