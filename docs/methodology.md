# LayoutBench V0.2.0 methodology

## Intended inference

LayoutBench asks whether a model can see spatial arrangement in a
rendered image: flow direction, axis distribution and alignment,
column counts, text justification, and the spacing around headers,
regions, and table cells. It reports descriptive accuracy on 208
frozen questions through each model's image-input pipeline. The pilot
does not establish perceptual thresholds, does not calibrate against
human agreement (not measured), and pools nothing across families.

## Quantization and reference frame

Every stimulus renders in headless Chromium on a frozen 800x600 CSS
px canvas at deviceScaleFactor 2 (1600x1200 PNG, sRGB). A vendored
DejaVu Sans body font (`src/assets`, SHA-256 pinned, asserted loaded
before every screenshot) fixes text metrics. Abstract cards and
document pages share one centered 640x440 card; region-bare tasks
center a tinted block on the bare canvas instead.

Spacing ground truth is decoded from rendered geometry, never trusted
from stylesheets: Playwright bounding rects for containers, items,
spacers, text line boxes, and table cells are recorded per task, and a
frozen validator re-derives every swept value within sub-pixel
tolerance: gap, padding, above/below, all-cell table padding, column
count, text alignment from line-box edges, and — from item boxes —
flow direction, main-axis distribution, and cross-axis alignment. It
then anchors the boxes to paint: content-band midpoints must be
background, points just inside each content edge must be item ink, gap
midlines must be background, and borders/tint must sample correctly.
Numeric truth is the rounded decode, not the stylesheet value.

Box-to-box is the operational definition of spacing. Header and body
blocks are tinted so the measured edges are visible; prompts explicitly
name those edges. Container padding asks for the smallest item-to-border
distance, and table padding asks for the left text inset. Absolute px
estimates test proportional judgment (providers rescale inputs), so
numeric prompts state the 800x600 design canvas; scores normalize
error against a 16px ceiling (4px tight).

## Experimental design

Thirteen families, 208 tasks, 150 images. Ten choice families use
exact-letter scoring against 3-7 lettered options (chance 14.3-33.3%
depending on family). Token-choice tasks offer the full token set on
every trial — the option set is identical across tasks, so it cannot
leak the truth; truth slots are balanced, and all remaining options are independently
shuffled using a task seed. Version 0.1 used sorted distractors, which
leaked the truth through option order; that version is superseded. Three numeric families share
images with choice siblings and score absolute px error; the 8
intersecting columns/justification cells share one render each and are
disclosed as correlated observations.

Every swept token value occurs with both themes and each level of its
structural nuisances (flow direction, bordered vs bare canvas, table
size), verified on token value rather than answer letter. This is
marginal coverage, not a complete factorial: sparse token families
have only two to four observations per value, leaving interactions
confounded. Fixed-option families use the stated full crossings. Fixed-option families cross answers
against nuisances; flow item counts have identical distributions across directions, so
count alone provides no advantage over chance. Abstract fixed values are disjoint
across families (gap tasks pad 40, pad tasks gap 20) so no two
families can render identical stimuli. No answer-adjacent word,
digit, or px value appears in any pixel; a frozen word list enforces
this on rendered DOM text. Grid tasks stretch items across each column so horizontal box gaps equal
the gutter; vertical placement also depends on the row tracks and item heights. `justify_content`/`align_items`
are not swept for grids. Prompts use visual language and are frozen
per family.

Fairness limitation: the finest token step is 4 CSS px (8 device px
before model-side rescaling), with no human-agreement calibration in
this pilot. Per-token-pair accuracy in the pilot report shows which
discriminations models actually resolve; steps that prove
unresolvable would be widened or dropped in a revision.

## Validation and evidence

`baseline/validate_dataset.py` is the frozen dataset gate: task
identity and corpus census, PNG dimensions/hash uniqueness, canvas and
font pins, neutral-text grep, prompt-template replay, choice-label
balance, full-set options with truth-slot checks, token-value crossing
tables, decoded spacing plus direction/distribution/alignment
derivation, choice letters checked against decoded constructs,
line-rect alignment derivation, exact numeric truth, share-pair and
group discipline, and pixel probes. The release gate additionally
checks Git provenance, manifest bytes, artifact census, fingerprints,
and protocol identity. Paid work is refused if any of these differ.

## Scoring and publication

Choice accuracy includes invalid responses in the denominator;
confusion tables record predicted-vs-truth labels with invalids kept.
Numeric means include invalids as zero; error quantiles and band hit
rates describe valid rows. No combined score exists. Finalization
reconciles the SQLite ledger, attempt export, scorecards, invocation
chronology, and committed bytes, then reparses every raw answer and
recomputes all metrics; see `releases/FINALIZATION.md`.
