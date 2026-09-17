"""Independent geometry and decoded-image gate for the qualitative release."""

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re

from PIL import Image, ImageChops


ROOT = Path(__file__).resolve().parents[1]
FONT_HASH = "abdc775b21b1bc470d50c97e790d276f2054b7504e56e5bd3e64f48d68582322"
TOL = 1.1


def require(condition, message):
    if not condition:
        raise ValueError(message)


def close(a, b):
    return abs(a - b) <= TOL


def equal(values):
    return max(values) - min(values) <= TOL


def compare(a, b, larger, smaller):
    if close(a, b):
        return "equal"
    require(abs(a - b) >= 24, "Insufficient qualitative separation")
    return larger if a > b else smaller


def bands(rectangles, axis):
    groups = []
    for rectangle in sorted(rectangles, key=lambda r: r[axis]):
        if not groups or not close(rectangle[axis], groups[-1][0][axis]):
            groups.append([])
        groups[-1].append(rectangle)
    return groups


def flow(rectangles):
    require(len(rectangles) >= 2, "Too few boxes to identify flow")
    candidates = []
    for direction, axis, size in (("row", "x", "width"), ("column", "y", "height")):
        ordered = sorted(rectangles, key=lambda r: r[axis])
        if all(b[axis] - a[axis] - a[size] >= 8 for a, b in zip(ordered, ordered[1:])):
            candidates.append(direction)
    require(len(candidates) == 1, "Ambiguous immediate flow")
    return candidates[0]


def spaces(rectangles, frame, direction):
    axis, size = ("x", "width") if direction == "row" else ("y", "height")
    ordered = sorted(rectangles, key=lambda r: r[axis])
    gaps = [b[axis] - a[axis] - a[size] for a, b in zip(ordered, ordered[1:])]
    return (ordered[0][axis] - frame[axis] - 2,
            frame[axis] + frame[size] - 2 - ordered[-1][axis] - ordered[-1][size], gaps)


def placement(rectangles, frame):
    left, right, _ = spaces(rectangles, frame, "row")
    require(min(left, right) >= -TOL, "Horizontal overflow")
    if close(left, 0) and right >= 24:
        return "left"
    if close(right, 0) and left >= 24:
        return "right"
    require(close(left, right) and left >= 12, "Ambiguous horizontal placement")
    return "center"


def wrapped_rows(rectangles):
    rows = bands(rectangles, "y")
    require(len(rows) >= 2 and len(rows[-1]) < len(rows[0]), "No incomplete final row")
    require(all(len(row) == len(rows[0]) for row in rows[:-1]), "Irregular full rows")
    return rows


def derive_answer(task):
    """Read visible relationships only; declared answer/factors are never inputs."""
    boxes = {r["id"]: r for r in task["rendered"]["regions"]}
    family = task["family"]
    frame = boxes["frame"]
    items = [r for name, r in boxes.items() if name.startswith("item-")]
    if family == "direction":
        return flow(items)
    if family == "distribution":
        left, right, gaps = spaces(items, frame, flow(items))
        require(len(items) == 3 and equal(gaps) and min(gaps) >= 8, "Irregular distribution")
        gap = gaps[0]
        require(min(left, right) >= -TOL, "Distribution overflow")
        if close(left, 0) and close(right, 0):
            return "between"
        if close(left, 0) and right >= gap * 3:
            return "start"
        if close(right, 0) and left >= gap * 3:
            return "end"
        require(close(left, right), "Unequal outer distribution spaces")
        if close(gap, left * 2) and left >= 12:
            return "around"
        if close(gap, left) and left >= 12:
            return "evenly"
        require(left >= gap * 3, "Ambiguous packed-center distribution")
        return "center"
    if family == "crossalign":
        axis, size = ("y", "height") if flow(items) == "row" else ("x", "width")
        lo, hi = frame[axis] + 2, frame[axis] + frame[size] - 2
        if all(close(r[axis], lo) and close(r[axis] + r[size], hi) for r in items):
            return "stretch"
        require(max(r[size] for r in items) - min(r[size] for r in items) >= 30,
                "Alignment requires visibly unequal box sizes")
        matches = []
        for answer, condition in (
            ("start", all(close(r[axis], lo) for r in items)),
            ("end", all(close(r[axis] + r[size], hi) for r in items)),
            ("center", all(close(r[axis] + r[size] / 2, (lo + hi) / 2) for r in items)),
        ):
            if condition:
                matches.append(answer)
        require(len(matches) == 1, "Ambiguous cross-axis alignment")
        return matches[0]
    if family == "textalign":
        lines = task["design"]["lines"]["text-0"]
        require(len(lines) >= 4, "Too few lines to judge text alignment")
        lefts = [r["x"] for r in lines]
        rights = [r["x"] + r["width"] for r in lines]
        mids = [(a + b) / 2 for a, b in zip(lefts, rights)]
        if equal(lefts[:-1]) and equal(rights[:-1]):
            require(lines[-1]["width"] <= lines[0]["width"] - 12, "No visible short final line")
            return "justify"
        require(max(r["width"] for r in lines) - min(r["width"] for r in lines) >= 24,
                "Text line lengths lack separation")
        matches = [name for name, values in (("left", lefts), ("right", rights), ("center", mids)) if equal(values)]
        require(len(matches) == 1, "Ambiguous text line alignment")
        return matches[0]
    if family == "textcolumns":
        columns = [r for name, r in boxes.items() if name.startswith("text-")]
        require(equal([r["y"] for r in columns]), "Text columns do not share a top edge")
        require(len(bands(columns, "x")) == len(columns), "Text columns overlap")
        return str(len(columns))
    if family in {"gridcols", "gridrows", "gridgaps", "gridtracks"}:
        rows, columns = bands(items, "y"), bands(items, "x")
        require(len(rows) >= 2 and len(columns) >= 2 and len(items) == len(rows) * len(columns), "Incomplete grid")
        require(all(len(row) == len(columns) for row in rows) and all(len(col) == len(rows) for col in columns), "Irregular grid")
        if family == "gridcols":
            return str(len(columns))
        if family == "gridrows":
            return str(len(rows))
        gx = [gap for row in rows for gap in spaces(row, frame, "row")[2]]
        gy = [gap for column in columns for gap in spaces(column, frame, "column")[2]]
        require(equal(gx) and equal(gy) and min(gx + gy) >= 12, "Irregular grid gutters")
        if family == "gridgaps":
            return compare(gx[0], gy[0], "horizontal", "vertical")
        widths = [column[0]["width"] for column in columns]
        require(len(widths) == 3 and all(equal([r["width"] for r in col]) for col in columns), "Irregular column widths")
        if equal(widths):
            return "equal"
        if close(widths[1], widths[2]) and widths[0] >= widths[1] * 1.7:
            return "left"
        require(close(widths[0], widths[1]) and widths[2] >= widths[1] * 1.7, "Insufficient track separation")
        return "right"
    if family == "gridspan":
        guides = sorted([r for name, r in boxes.items() if name.startswith("guide-")], key=lambda r: r["x"])
        span = boxes["span"]
        require(len(guides) == 3 and equal([r["width"] for r in guides]) and equal([r["y"] for r in guides]), "Invalid span guides")
        require(close(span["x"], guides[0]["x"]) and span["y"] + span["height"] + 12 <= guides[0]["y"], "Misplaced span")
        matches = [str(i + 1) for i, guide in enumerate(guides) if close(span["x"] + span["width"], guide["x"] + guide["width"])]
        require(len(matches) == 1, "Span endpoint does not match a column")
        return matches[0]
    if family == "wrapcount":
        rows = bands(items, "y")
        require(len(items) == 6 and all(len(row) == len(rows[0]) for row in rows), "Irregular wrapped rows")
        return str(len(rows))
    if family == "wrapalign":
        return placement(wrapped_rows(items)[-1], frame)
    if family == "gapcompare":
        _, _, gaps = spaces(items, frame, flow(items))
        require(len(gaps) == 2 and min(gaps) >= 12, "Missing neighboring gaps")
        return compare(gaps[0], gaps[1], "first", "last")
    if family == "padcompare":
        inset = boxes["inset"]
        left, right, _ = spaces([inset], frame, "row")
        top, bottom, _ = spaces([inset], frame, "column")
        require(close(left, right) and close(top, bottom) and min(left, top) >= 12, "Inset is not centered")
        return compare(left, top, "horizontal", "vertical")
    if family == "blockalign":
        return placement([boxes["block"]], frame)
    if family == "widthcompare":
        ordered = sorted(items, key=lambda r: r["x"])
        require(len(ordered) == 2, "Panel pair missing")
        return compare(ordered[0]["width"], ordered[1]["width"], "first", "last")
    if family == "groupgap":
        ordered = sorted(items, key=lambda r: r["x"])
        gaps = spaces(ordered, frame, "row")[2]
        require(len(gaps) == 3 and close(gaps[0], gaps[2]) and min(gaps) >= 12, "Irregular within-group gaps")
        return compare(gaps[1], gaps[0], "between", "within")
    if family == "topflow":
        return flow([boxes["section-0"], boxes["section-1"]])
    if family in {"nestedflow", "nestedwrap"}:
        children = [r for name, r in boxes.items() if name.startswith("child-")]
        if family == "nestedwrap":
            rows = wrapped_rows(children)
            for row in rows[:-1]:
                left, right, _ = spaces(row, boxes["target"], "row")
                require(close(left, 0) and close(right, 0), "Full wrapped rows must fill both inner edges")
            return placement(rows[-1], boxes["target"])
        rows = bands(children, "y")
        if 1 < len(rows) < len(children):
            wrapped_rows(children)
            return "wrapped"
        return flow(children)
    raise ValueError(f"Unknown qualitative family: {family}")


def require_valid_qualitative(manifest_path):
    manifest_path = Path(manifest_path)
    tasks = json.loads(manifest_path.read_text())
    catalog = json.loads((ROOT / "config/qualitative.json").read_text())
    expected = {family: len(spec["options"]) * 4 for family, spec in catalog.items()}
    expected.update(topflow=24, nestedflow=24, nestedwrap=24)
    require(isinstance(tasks, list) and Counter(t["family"] for t in tasks) == expected, "Qualitative corpus counts differ")
    font_path = manifest_path.parent / "fonts/DejaVuSans.ttf"
    require(font_path.is_file() and not font_path.is_symlink() and hashlib.sha256(font_path.read_bytes()).hexdigest() == FONT_HASH, "Bundled font differs")
    ids, images, hashes, groups = set(), {}, {}, {}
    census, hierarchies, copy_groups = Counter(), Counter(), {}
    forbidden = {"left", "right", "center", "centered", "justify", "justified", "row", "rows", "column", "columns", "grid", "stretch", "between", "evenly", "horizontal", "vertical", "padding", "gap", "gaps", "equal", "wider", "larger", "smaller"}
    for task in tasks:
        task_id, family, design, rendered = (task[k] for k in ("taskId", "family", "design", "rendered"))
        require(task_id not in ids and re.fullmatch(rf"layoutbench-{family}-\d{{3}}", task_id), "Invalid or duplicate task identity")
        ids.add(task_id)
        require(design["kind"] == "qualitative" and design["theme"] in {"light", "dark"} and type(design["variant"]) is int and design["variant"] in {0, 1}, "Invalid qualitative design")
        require((rendered["width"], rendered["height"], rendered["dpr"], rendered["colorSpace"]) == (800, 600, 2, "srgb"), "Canvas dimensions differ")
        require(rendered["font"]["path"] == "fonts/DejaVuSans.ttf" and rendered["font"]["sha256"] == FONT_HASH, "Rendered font differs")
        used_fonts = rendered["font"].get("used")
        require(isinstance(used_fonts, list) and used_fonts and all(font.get("isCustomFont") is True and font.get("familyName") == "DejaVu Sans" and font.get("glyphCount", 0) > 0 for font in used_fonts), "Actual font use differs from bundled font")
        require(rendered.get("overflow") == [], "Missing or nonempty overflow evidence")
        words = set(re.findall(r"[a-z]+", task["domText"].lower()))
        require(not words & forbidden and not re.search(r"\d", task["domText"]), "Answer leakage in DOM text")
        if family not in {"textcolumns", "gridcols", "gridrows"}:
            copy_groups.setdefault((family, design["theme"], design["variant"]), set()).add(task["domText"])
        options = design["options"]
        require(len(options) == len(catalog[family]["options"]) and set(options) == set(catalog[family]["options"]), "Invalid option permutation")
        prompt = catalog[family]["question"] + "\n" + "\n".join(f"{chr(65+i)}: {catalog[family]['options'][key]}" for i, key in enumerate(options)) + '\nReturn only a JSON object with one key, "choice", whose value is the selected option letter.'
        require(task["prompt"] == prompt, "Prompt differs from canonical catalog")
        boxes = rendered["regions"]
        require(isinstance(boxes, list) and len({r["id"] for r in boxes}) == len(boxes), "Duplicate rectangle IDs")
        for rect in boxes + [line for lines in design["lines"].values() for line in lines]:
            require(all(type(rect[k]) in {int, float} and math.isfinite(rect[k]) for k in ("x", "y", "width", "height")), "Nonfinite rectangle")
            require(rect["x"] >= 0 and rect["y"] >= 0 and rect["width"] > 0 and rect["height"] > 0 and rect["x"] + rect["width"] <= 800 + TOL and rect["y"] + rect["height"] <= 600 + TOL, "Rectangle escapes canvas")
        by_id = {r["id"]: r for r in boxes}
        frame = by_id["frame"]
        for rect in boxes:
            parent = by_id["target"] if rect["id"].startswith("child-") else by_id["section-0"] if rect["id"] == "target" else frame
            require(rect["x"] >= parent["x"] - TOL and rect["y"] >= parent["y"] - TOL and rect["x"] + rect["width"] <= parent["x"] + parent["width"] + TOL and rect["y"] + rect["height"] <= parent["y"] + parent["height"] + TOL, "Box overflows its visible parent")
        for name, lines in design["lines"].items():
            parent = by_id[name]
            require(len(lines) >= 2, "Insufficient multiline text evidence")
            for line in lines:
                require(line["x"] >= parent["x"] - TOL and line["y"] >= parent["y"] - TOL and line["x"] + line["width"] <= parent["x"] + parent["width"] + TOL and line["y"] + line["height"] <= parent["y"] + parent["height"] + TOL, "Text line overflow")
        answer = derive_answer(task)
        truth = task["groundTruth"]
        require(set(truth) == {"choice"} and truth["choice"] in [chr(65 + i) for i in range(len(options))] and options[ord(truth["choice"]) - 65] == answer, "Geometry disagrees with ground truth")
        require(design["answer"] == answer, "Geometry disagrees with declared answer")
        census[(family, answer, design["theme"], design["variant"])] += 1
        if family == "topflow":
            nested = derive_answer({**task, "family": "nestedflow"})
            hierarchies[(answer, nested, design["theme"], design["variant"])] += 1
        elif family == "nestedwrap":
            parent_flow = derive_answer({**task, "family": "topflow"})
            hierarchies[("wrap", parent_flow, answer, design["theme"], design["variant"])] += 1
        name = task["imageFilename"]
        require(isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9_.-]+\.png", name), "Unsafe image filename")
        path = manifest_path.parent / name
        require(path.is_file() and not path.is_symlink(), "Missing image or image symlink")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        require(digest == task["imageSha256"], "Image hash differs")
        require(digest not in hashes or hashes[digest] == name, "Duplicate images must share their image identity")
        hashes[digest] = name
        require(task["groupId"] not in groups or groups[task["groupId"]] == name, "Image group contains different images")
        groups[task["groupId"]] = name
        identity = (task["groupId"], rendered, design["lines"], task["domText"], design["theme"], design["variant"])
        if name in images:
            require(images[name][0] == identity, "Shared image has inconsistent render evidence")
            images[name][1].append(family)
            continue
        images[name] = (identity, [family])
        with Image.open(path) as source:
            require(source.format == "PNG" and source.size == (1600, 1200), "PNG dimensions differ")
            image = source.convert("RGB")
        border = (154, 171, 194) if design["theme"] == "dark" else (82, 103, 127)
        for rect in boxes:
            if rect["id"].startswith(("text-", "group-")):
                continue
            x, y, w, h = (rect[k] for k in ("x", "y", "width", "height"))
            samples = [(x + w * f, y + .5) for f in (.25, .5, .75)] + [(x + w * f, y + h - .5) for f in (.25, .5, .75)]
            samples += [(x + .5, y + h * f) for f in (.25, .5, .75)] + [(x + w - .5, y + h * f) for f in (.25, .5, .75)]
            matches = sum(max(abs(a - b) for a, b in zip(image.getpixel((int(px * 2), int(py * 2))), border)) <= 35 for px, py in samples)
            require(matches >= 9, f"Decoded border disagrees with rectangle {rect['id']}")
        ink = (241, 245, 249) if design["theme"] == "dark" else (23, 32, 51)
        for name, lines in design["lines"].items():
            region = by_id[name]
            for line in lines:
                x0, x1 = math.floor(region["x"] * 2), math.ceil((region["x"] + region["width"]) * 2)
                y0, y1 = math.floor(line["y"] * 2), math.ceil((line["y"] + line["height"]) * 2)
                crop = image.crop((x0, y0, x1, y1))
                red, green, blue = ImageChops.difference(crop, Image.new("RGB", crop.size, ink)).split()
                mask = ImageChops.lighter(ImageChops.lighter(red, green), blue).point(lambda value: 255 if value <= 30 else 0)
                bounds = mask.getbbox()
                require(bounds is not None, "Decoded text line has no ink")
                # Glyph side bearings differ from browser advance widths by a few pixels.
                require(abs((x0 + bounds[0]) / 2 - line["x"]) <= 3
                        and abs((x0 + bounds[2]) / 2 - line["x"] - line["width"]) <= 3,
                        "Decoded text edges disagree with measured line")
    for family, spec in catalog.items():
        for answer in spec["options"]:
            repeats = 3 if family == "topflow" else 2 if family in {"nestedflow", "nestedwrap"} else 1
            for theme in ("light", "dark"):
                for variant in (0, 1):
                    require(census[(family, answer, theme, variant)] == repeats, "Answer/theme/content crossing differs")
        letters = Counter(t["groundTruth"]["choice"] for t in tasks if t["family"] == family)
        require(len(letters) == len(spec["options"]) and max(letters.values()) - min(letters.values()) <= 1, "Answer letters are unbalanced")
    require(len(hierarchies) == 48 and set(hierarchies.values()) == {1}, "Parent/child hierarchy crossing differs")
    require(all(len(variants) == 1 for variants in copy_groups.values()), "Visible copy changes with the answer")
    for _, families in images.values():
        if len(families) > 1:
            require(len(families) == len(set(families)), "Repeated same-family question on a shared image")
    return tasks
