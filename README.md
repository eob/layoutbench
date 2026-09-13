# LayoutBench

**LayoutBench** is a vision-language benchmark evaluating multimodal AI models on spatial arrangement in rendered UI: flow direction, axis distribution and alignment, text columns and justification, and spacing around headers, regions, and table cells.

It forms the third foundational benchmark in Ted Benson's design perception suite:
1. [FontBench](https://github.com/eob/fontbench): Typography (family, category, weight, kerning, line-height)
2. [BorderBench](https://github.com/eob/borderbench): Surfaces & Edges (stroke width, style, sides, corner radius curvature, elevation/shadow)
3. **LayoutBench**: Spatial Geometry & Flow (direction, distribution, alignment, columns, justification, spacing)
4. [ColorBench](https://github.com/eob/colorbench): Color (matching, lightness, chroma, hue, binding, gradients, reconstruction)

---

## Question bank (208 tasks, 13 families, 150 images)

Every stimulus renders on a frozen 800x600 CSS px canvas at 2x DPR with a pinned body font. One scored question per task; no answer text appears in any pixel.

**Abstract side** (neutral cards, no text in pixels):

1. **Flow** (`flow`, 16): row, column, 2-col grid, or 3-col grid.
2. **Distribution** (`distribute`, 20): packed at start, centered, packed at end, edge-to-edge, or half-space at edges; rows and columns.
3. **Alignment** (`align`, 16): cross-axis start, center, end, or stretch; variable-size items.
4. **Gap tokens** (`gap`, 16): spacing between items from {0, 4, 8, 12, 16, 24, 32}px, nearest-neighbor distractors.
5. **Container padding** (`pad`, 16): edge-to-item spacing from {8, 16, 24, 32, 48}px.

**Document side** (fixed neutral copy, pinned font):

6. **Columns** (`columns`, 12): one, two, or three text columns.
7. **Text justification** (`textjustify`, 16): left, centered, right, or both-edges alignment.
8. **Header padding** (`headerpad`, 18): more space above the header, below it, or equal.
9. **Region padding** (`regionpad`, 16): padding around a content region from {8, 16, 24, 32, 48}px, bordered-card vs bare-canvas crossed.
10. **Table padding** (`tablepad`, 12): cell text-to-border spacing from {4, 8, 12, 16}px.

**Numeric side** (px estimates on shared images):

11. **Gap estimate** (`gapnum`, 16), **header estimate** (`headerpx`, 18, above + below), **region estimate** (`regionpx`, 16).

Every swept value is crossed against theme plus structural nuisances; spacing truth is decoded from rendered geometry. See [docs/methodology.md](docs/methodology.md).

---

## Quick Start

### 1. Installation

```bash
bun install
python3 -m venv .venv
.venv/bin/pip install -e .
```

### 2. Render the dataset

Renders 150 high-DPI screenshots with Playwright Chromium and generates `dataset/layoutbench-v0.1/manifest.json` with decoded rects:

```bash
bun run render
bun run validate
```

### 3. Run the baseline

```bash
# Quick mock test (no API calls)
bun run benchmark:mock

# Frozen release run against configured models
.venv/bin/python -m baseline.runner --release 0.1.0 --run-id pilot-20260913 --max-tasks 208 --concurrency 6 --budget-usd 25
```

### 4. Seal a run

```bash
.venv/bin/python -m baseline.finalize --run-dir results/runs/0.1.0/pilot-20260913 --scope full
.venv/bin/python -m baseline.finalize --run-dir results/runs/0.1.0/pilot-20260913 --verify
```

See [releases/README.md](releases/README.md) and [releases/FINALIZATION.md](releases/FINALIZATION.md).

---

## Manifest task format

Each task in `dataset/layoutbench-v0.1/manifest.json` provides:

```json
{
  "taskId": "layoutbench-gap-01",
  "family": "gap",
  "groupId": "gap-01",
  "imageFilename": "gap-01.png",
  "imageSha256": "…",
  "groundTruth": { "choice": "B" },
  "prompt": "Look at the card in this image. …",
  "design": { "kind": "abstract", "direction": "row", "gap_px": 16, "decoded": { "gap": 16.0 } },
  "domText": "",
  "rendered": { "width": 800, "height": 600, "dpr": 2, "colorSpace": "srgb", "font": { "path": "fonts/DejaVuSans.ttf", "sha256": "…" }, "regions": [ … ] }
}
```

---

## Testing

```bash
# Builder, crossing, and determinism tests
bun test

# Protocol, grading, statistics, dataset gate, and state store tests
.venv/bin/pytest tests
```
