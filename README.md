# LayoutBench

**LayoutBench** is a vision-language benchmark evaluating multimodal AI models on UI spatial geometry, layout flow direction, alignment, justification, gap spacing, and padding in software screenshots.

It forms the third foundational benchmark in Ted Benson's design perception suite:
1. [FontBench](https://github.com/eob/fontbench): Typography (family, category, weight, kerning, line-height)
2. [BorderBench](https://github.com/eob/borderbench): Surfaces & Edges (stroke width, style, sides, corner radius curvature, elevation/shadow)
3. **LayoutBench**: Spatial Geometry & Flow (direction, justify-content, align-items, gap tokens, padding tokens)

---

## Dimensions Evaluated

LayoutBench evaluates models across a standardized 480×300 CSS px card container rendered on high-resolution Retina canvases (2× DPR, 560×380 px) across 5 core spatial dimensions:

1. **Layout Flow Direction** (`direction`):
   - `row`: Horizontal flexbox flow
   - `column`: Vertical flexbox stack
   - `grid-2col`: Two-column CSS grid matrix
   - `grid-3col`: Three-column CSS grid matrix

2. **Main-Axis Justification** (`justify_content`):
   - `start`: Packed to leading edge
   - `center`: Centered along main axis
   - `end`: Packed to trailing edge
   - `space-between`: Distributed edge-to-edge
   - `space-around`: Distributed with half-space at edges

3. **Cross-Axis Alignment** (`align_items`):
   - `start`: Aligned to cross-axis origin (top in row, left in column)
   - `center`: Centered along cross axis
   - `end`: Aligned to cross-axis end (bottom in row, right in column)
   - `stretch`: Stretched to fill full cross-axis dimension

4. **Gap Spacing Tokens** (`gap`):
   - `0px`, `4px`, `8px`, `12px`, `16px`, `24px`, `32px`

5. **Container Inset Padding Tokens** (`padding`):
   - `8px`, `16px`, `24px`, `32px`

6. **Content Proportions & Themes**:
   - `uniform` vs `variable` child item heights/widths (isolating cross-axis stretch vs center vs start)
   - `light` vs `dark` themes

---

## Dataset Breakdown (100 Tasks)

The benchmark comprises exactly 100 systematic tasks covering:
- **Direction Sweeps**: Row vs Column vs Grid-2col vs Grid-3col
- **Main-Axis Justification**: Start, Center, End, Space-Between, Space-Around across Row & Column
- **Cross-Axis Alignment**: Start, Center, End, Stretch with variable height/width items
- **Gap Spacing Grids**: Fine-grained metric sweeps from 0px (flush segmented controls) to 32px
- **Container Inset Padding**: 8px through 32px
- **UI Archetypes**: Segmented controls, navbar action bars, modal button rows, metric stat decks, form stacks, and settings lists.

---

## Quick Start

### 1. Installation

```bash
bun install
python3 -m venv .venv
.venv/bin/pip install -e .
```

### 2. Render Benchmark Dataset

Renders all 100 high-DPI screenshots with Playwright Chromium and generates `dataset/layoutbench-1/manifest.json`:

```bash
bun run render
```

### 3. Run Benchmark Baseline

```bash
# Run quick mock test
bun run benchmark:mock

# Run real evaluation against frontier vision models
.venv/bin/python baseline/runner.py --models gemini-3.1-pro-preview gemini-3.8-flash claude-sonnet-5 gpt-5.6-sol
```

### 4. Export Structured Summary

```bash
bun run export
```

---

## Manifest Task Format

Each task in `dataset/layoutbench-1/manifest.json` provides:
```json
{
  "taskId": "layoutbench-001",
  "imagePath": "/path/to/dataset/rendered/layoutbench-001.png",
  "imageFilename": "layoutbench-001.png",
  "groundTruth": {
    "direction": "row",
    "justify_content": "start",
    "align_items": "center",
    "gap": "12px",
    "gap_px": 12,
    "padding": "16px",
    "padding_px": 16,
    "item_count": 3,
    "content_variant": "uniform",
    "theme": "light"
  },
  "prompt": "Analyze the container layout in this UI screenshot..."
}
```

---

## Testing

```bash
# Test specimen generation and token integrity
bun test

# Test evaluator scoring and SQLite state store
.venv/bin/pytest tests
```

---

## License

MIT © Edward Benson
