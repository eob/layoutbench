# plan-01: Balanced LayoutBench perception design

- **Status:** In Progress
- **Date:** 2026-09-13
- **Assignee:** Edward Benson
- **Branch:** `rebuild-01-balanced`
- **Scope:** Rebuild LayoutBench as a balanced abstract + document layout
  perception pilot: dataset, frozen validators, baseline machinery,
  first paid run, critique.

## Purpose and suite boundary

The design quartet measures recognition of observable visual properties:
FontBench covers typography; BorderBench covers strokes, corners, and
shadows; ColorBench covers color; LayoutBench covers spatial
arrangement. LayoutBench should ask whether a model can see columns,
alignment, justification, and spacing in a rendered image: how items
flow, how text is justified, how many columns exist, and how much space
surrounds headers, regions, and table cells.

Aesthetics, semantic intent, responsive behavior, and advice about what
a designer should choose are outside this scope. So are CSS vocabulary
quizzes: prompts use visual language ("how much space", "which side")
and ground truth is decoded from rendered pixels, never trusted from
stylesheets. Like its siblings, this pilot does not establish
perceptual thresholds or human calibration; it reports descriptive
accuracy on frozen questions through each model's image-input pipeline.

## Inspected baseline

Read-only source inspection on 2026-09-13:

| Repository | Commit | Relevant evidence |
| --- | --- | --- |
| LayoutBench | `779db8e` | `src/specimens.ts:14`, `src/render.ts:14`, `baseline/evaluator.py:80` |
| ColorBench | `653183f` | `tickets/plan-02-harder-tasks.md`, `baseline/protocol.py`, `baseline/finalize.py`, `baseline/validate_dataset.py` |
| BorderBench | main | `docs/methodology.md`, `baseline/validate_dataset.py`, `releases/` |

LayoutBench already has a 100-image prototype and TypeScript/Python
scaffolding. It cannot be scored as a perception benchmark:

- `src/render.ts:247-249` prints the specimen title and tag into every
  image, and `src/specimens.ts` builds those strings from the answers
  (`Row Gap: 16px`, `Spacing scale test: 16px (16px)`, `Main-axis
  distribution: space-between`). A model that reads text scores 100%
  without perceiving layout. This is the same flaw class ColorBench's
  plan-01 found in its own prototype.
- One prompt asks for five attributes at once (`render.ts:259`), so no
  family has a clean chance baseline or independent denominator.
- The manifest stores absolute `imagePath`, has no frozen release, no
  dataset fingerprint, no pixel verification, and no decoded ground
  truth: CSS values are trusted, never measured.
- Sweeps are uncontrolled: justify is tested mostly in row mode,
  padding at one gap, gap at one padding; nothing is crossed against
  theme, count, or content variant, so correlates are uncontrolled.

Preserve this prototype as history; do not carry its images or scores
into the rebuild. Rebuild on the repaired ColorBench/BorderBench
machinery: frozen releases with fingerprints, strict answer parsing,
pixel-decoded ground truth, suite-style finalization, and one scored
question per task.

## Corpus design (13 families, 208 tasks, 150 images)

One scored question per task. Option letters refer to values named in
prompt text; no answer text appears in any pixel. All families render
on one frozen canvas: 800x600 CSS px at 2x DPR with a pinned body font
(see Construction). Choice families use exact-letter scoring with
declared chance baselines; numeric families share images with a
sibling choice family (as ColorBench numeric families share targets)
and score absolute px error. The 8 intersecting `columns`/`textjustify`
cells (counts {1,2} x aligns {left,justify} x themes) also share one
render each, since the stimulus is identical and only the question
differs; remaining cells render alone.

### Abstract side (5 families, 84 tasks)

| Family | Question | Answers | Chance | Tasks |
| --- | --- | --- | --- | --- |
| `flow` | In which direction do the items flow? | A row (left-to-right), B column (top-to-bottom), C 2-column grid, D 3-column grid | 25% | 16: 4 dirs x 2 themes x 2 content variants |
| `distribute` | How are items spread along the main axis? | A packed at start, B centered, C packed at end, D spread edge-to-edge, E spread with half-space at edges | 20% | 20: 5 options x 2 flow dirs x 2 themes |
| `align` | How are items aligned across the axis? | A top/left, B centered, C bottom/right, D stretched to fill | 25% | 16: 4 options x 2 flow dirs x 2 themes; variable-size items only |
| `gap` | How much space is between neighboring items? | 4 lettered px values sampled per task (truth + 3 distractors, adjacent-biased) from {0,4,8,12,16,24,32} | 25% | 16: each token >= 2, row/col balanced |
| `pad` | How much space is between the container edge and the items? | 4 lettered px values sampled per task from {8,16,24,32,48} | 25% | 16: each token >= 3, row/col x theme balanced |

### Document side (5 families, 74 tasks)

| Family | Question | Answers | Chance | Tasks |
| --- | --- | --- | --- | --- |
| `columns` | How many columns of text are there? | A one, B two, C three | 33.3% | 12: 3 counts x 2 text-justifications x 2 themes |
| `textjustify` | How is the body text aligned? | A left, B centered, C right, D justified on both edges | 25% | 16: 4 options x 2 column-counts x 2 themes |
| `headerpad` | Which space is larger: above the header or below it? | A above, B below, C equal | 33.3% | 18: 3 answers x 3 magnitudes x 2 themes; above/below drawn from {8,16,24,32,48} |
| `regionpad` | How much padding surrounds the content region? | 4 lettered px values sampled per task from {8,16,24,32,48} | 25% | 16: each token >= 3, bordered-card vs bare-canvas crossed |
| `tablepad` | How much space is between the cell text and the cell borders? | 4 lettered px values sampled per task from {4,8,12,16} | 25% | 12: 4 tokens x 3 table sizes (2x2, 2x3, 3x3), theme balanced |

### Numeric side (3 families, 50 tasks, images shared)

| Family | Question | Answer schema | Scoring | Tasks |
| --- | --- | --- | --- | --- |
| `gapnum` | Estimate the gap between items in CSS px (integer). | `{"gap_px": int}` | err vs decoded px | 16: shares `gap` images |
| `headerpx` | Estimate the space above and below the header in CSS px. | `{"above_px": int, "below_px": int}` | mean err of both keys | 18: shares `headerpad` images |
| `regionpx` | Estimate the padding around the content region in CSS px. | `{"pad_px": int}` | err vs decoded px | 16: shares `regionpad` images |

Numeric score: `100 * (1 - min(err / 16, 1))`; tight score with
ceiling 4; `within_bands` flags for {1, 2, 4, 8} px on the scored err
(`headerpx`: max of the two key errors, so a flag means both sides are
within the band). Invalid answers score 0 and carry null bands.

## Construction and shortcut controls

- **One frozen canvas.** Every family renders 800x600 CSS px at
  deviceScaleFactor 2 in headless Chromium. The abstract card is
  centered at fixed geometry; document pages are centered at fixed
  geometry. Validators enforce exact PNG dimensions.
- **Pinned font.** Text-heavy families pin a vendored TrueType body
  font loaded via `@font-face`; the renderer asserts
  `document.fonts.check`, records the font SHA-256 in every task, and
  the validator rejects anything else. System font stacks would make
  wrapping, justification, and cell metrics platform-dependent.
- **Neutral pixels.** No titles, tags, captions, or value strings in
  any image. Body copy comes from a fixed neutral word list; a frozen
  validator greps rendered DOM text for forbidden tokens (px values,
  `space-between`, `justify`, `stretch`, `padding`, `gap`, `column`,
  `left`, `right`, `center`, `justified`) and fails the dataset if any
  appear. Option letters never appear in pixels; options are values in
  prompt text.
- **Decoded ground truth.** At render time Playwright measures
  `getBoundingClientRect` for the container, every item, header, body,
  region, and table cells, in CSS px. The manifest stores these rects
  plus derived spacing (gap = distance between adjacent item boxes;
  padding = container content-box inset to outer items; header
  above/below = header box to container top / body box top). Truth for
  numeric families is the decoded value, rounded to int.
- **Pixel verification.** The validator samples pixels along gap
  midlines and padding bands and requires stage/canvas background;
  requires item interiors to differ from background; requires bordered
  cards to show border pixels on all four sides and bare-canvas tasks
  to show none; requires decoded spacing to match intended tokens
  within 0.6 px (sub-pixel rounding) and numeric truth to equal the
  rounded decode exactly.
- **Crossing.** Every swept value is crossed against its nuisance
  axes: theme (light/dark), flow direction or column count, item/table
  size, content variant, and border-vs-edge for `regionpad`. The
  validator enforces the crossing table in the Corpus section (each
  answer x each nuisance level present) so no family can be solved
  from a correlated cue.
- **Distractor discipline.** Token-choice distractors are the nearest
  neighbors of the truth in the token set (e.g. truth 16 ->
  {8,12,24,32} choose 3), with option-letter positions balanced per
  family. No task may have a unique pixel checksum that identifies its
  answer across the corpus (validator checks: identical (family,
  answer) pairs must still differ in at least one nuisance pixel
  region... more precisely, no two tasks share an identical PNG).

## Scoring and experimental units

- Choice families: exact letter match, invalid in the denominator,
  per-family accuracy only. No combined score anywhere.
- Numeric families: mean score / tight score over all rows (invalid =
  0), error quantiles over valid rows, band hit rates, all per family.
- Shared images (`gap`/`gapnum`, `headerpad`/`headerpx`,
  `regionpad`/`regionpx`) are correlated observations; report notes
  this. Families never pool across each other.
- Chance baselines are declared per family (20% / 25% / 33.3%);
  numeric families report an always-guess-16 constant baseline instead
  of chance.

## Repository structure and reuse

Mirror ColorBench's repaired machinery, minus color math:

- `src/types.ts`, `src/abstract.ts` (abstract specimens),
  `src/document.ts` (document specimens), `src/render.ts` (frozen
  Chromium renderer + rect decoder). All dataset checks live in
  `baseline/validate_dataset.py` (single frozen gate: pixels,
  crossing, neutral text, decode, sharing); no separate TS validator.
- `baseline/protocol.py` (family answer contracts, strict parsing),
  `baseline/prompts.json` (frozen per-family prompts),
  `baseline/evaluator.py` (grading), `baseline/statistics.py`
  (family metrics), `baseline/reporting.py`, `baseline/releases.py`,
  `baseline/finalize.py` (seal + `--verify`), `baseline/validate_dataset.py`.
- Keep and adapt `baseline/providers.py`, `baseline/runner.py`,
  `baseline/run_state.py`, `baseline/model_config.py`,
  `baseline/export_structured.py`.
- `releases/0.1.0.json` + `README.md` + `FINALIZATION.md`;
  `dataset/layoutbench-v0.1/` with manifest + PNGs;
  `fonts/` vendored body font; `results/` for runs; `docs/methodology.md`.
- Bun tests for specimen construction/crossing; pytest for parsing,
  grading, statistics, release validation, frozen corpora.

## Explicit non-goals

- Website publication (follows the pilot, as with siblings).
- Human agreement calibration.
- Responsive/multi-viewport behavior, RTL layouts, animation.
- GitHub publication of this repo (no remote exists yet; decide with
  owner before pushing).
- Carrying any prototype image, score, or manifest field forward.

## Implementation sequence

1. Branch `rebuild-01-balanced`; Red: run new frozen validators
   against the prototype corpus and record verbatim failures.
2. Types + abstract specimens/renderer (neutral chrome, rect decoder).
3. Document specimens/renderer (columns, text, header, region, table).
4. Validators (pixels, crossing, neutral text, dimensions, font).
5. Baseline machinery (protocol through finalize).
6. Generate + freeze release 0.1.0.
7. Adversarial review with fixes; record in this plan.
8. Mock campaign + full gates; paid pilot (requires spend
   authorization); analysis + critique.

## Red evidence

Probe `/tmp/layoutbench_red_probe.py` against prototype commit
`779db8e` (2026-09-13), asserting the validity properties the rebuild
must satisfy. Verbatim output (exit 1):

```text
FAIL no-answer-text-in-pixels -- title/tag printed in-image and built from answers, e.g. ['Gap: ${g.token}', 'scale test: ${g.token}']
FAIL portable-manifest-paths -- 100/100 absolute, e.g. ['/mnt/disks/data/layoutbench/dataset/rendered/layoutbench-001.png']
FAIL decoded-ground-truth -- 100/100 tasks without decoded rects
FAIL frozen-release -- releases/0.1.0.json missing
FAIL single-question-per-task -- 1 distinct prompt(s) ask 5 attributes at once

5 failing checks: ['no-answer-text-in-pixels', 'portable-manifest-paths', 'decoded-ground-truth', 'frozen-release', 'single-question-per-task']
```

Each failure is causal, not incidental: `render.ts:247-249` prints
answer-derived titles into pixels; the manifest stores absolute
`imagePath`; no rect decoder exists; no `releases/` exists; the single
frozen prompt requests all five attributes. The rebuild turns each
check green via `baseline/validate_dataset.py`, kept as a durable
gate.

## Adversarial review (pre-paid-run)

(To be recorded.)

## Validation gate matrix

(To be recorded.)

