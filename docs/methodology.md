# LayoutBench 0.3.0 methodology

## Intended inference

LayoutBench asks whether an image-input model can identify visible spatial relationships. Its 292 questions cover 20 families using 250 unique rendered images. The target is an atomic observation with a definite geometric answer, rather than aesthetic preference, hidden CSS provenance or an absolute pixel estimate. These observations may be ingredients of design understanding; this experiment does not test downstream transfer.

Human inter-rater agreement is unmeasured. The corpus deliberately uses visible group boundaries and coarse separations to make low-variance judgments plausible. Automated geometric agreement does not substitute for a human study. Scores are descriptive results on a small fixed synthetic corpus, not population estimates or a statistically established model ranking.

## Stimuli and questions

Every image is an 800×600 CSS-pixel browser canvas saved as a 1600×1200 sRGB PNG. The bundled DejaVu Sans font is hash-pinned, loaded before rendering, and checked through Chromium's actual platform-font records. Text-bearing cards use neutral nature/travel copy. The light/dark themes use the same geometry and high-contrast outlines. No answer strings or measurement guides are printed on the images.

The catalog in `config/qualitative.json` defines the question and complete semantic answer set for each family. Each question requests exactly one JSON letter. Questions name visible boundaries: inset comparisons measure to the tinted rectangle, and distribution measures to the inside of the outlined frame. Around-spacing uses outer gaps exactly half the inner gaps; evenly-spaced arrangements use equal gaps; edge-to-edge arrangements touch the inner frame. These are visible patterns, not claims about which CSS rule generated them.

The 17 single-level families cross every semantic answer with light/dark theme and two content variants. For distribution, cross-axis alignment and neighboring gaps, variants also cover horizontal and vertical sequences. Grid-column questions vary the row count; grid-row questions vary the column count. Text block placement crosses block position with left/right internal text alignment. These are controlled nuisance bundles, not a fully factorial test of all possible content, type, scale, viewport and layout combinations.

The hierarchy bank crosses parent row/column, child row/column/wrapped, theme and two content/target-position variants: 24 images support 24 parent and 24 child questions. Field notes appears first in one variant and second in the other. Five cards are retained across all child-flow answers, so item count cannot reveal the flow. Wrapped scenes have a complete row of three and an incomplete row of two. Twenty-four nested-row-alignment questions cross left/center/right placement with parent orientation, theme and both target positions; eight share images with the parent/child questions.

Repeated pixel-identical images across families are deduplicated by SHA-256 and retain one image filename and group ID. Distinct images related by theme or content also are not independent random samples. No independent-sample confidence intervals are reported.

## Answer construction and controls

Semantic answers have equal counts within each family. Answer-letter slots are drawn from an independently shuffled balanced multiset; distractors are independently shuffled into the remaining slots. This avoids deriving the truth slot from the answer, its numeric ordering, theme or content variant. Models receive only a question and PNG, without source code, geometry, task IDs, paths or metadata. The full option set appears in every question of that family.

The independent qualitative validator reconstructs the answer from bounding rectangles and rendered text-line edges without trusting the generator's semantic answer. It checks counts, crossing, prompt reconstruction, balanced letters, containment, clipping, actual font usage, image dimensions and hashes, and decoded pixels on measured borders. The canonical renderer and the independent validator must agree before the runner accepts the release. Deliberate answer, geometry, option, pixel, font and corpus tampering are regression cases.

Text justification requires multiple nonfinal lines. Cross-axis alignment uses unequal card sizes except when all cards fill that axis. Relative spacing uses clear differences (for example 60 versus 20 for neighboring gaps); equality is exact by construction. There are no near-threshold bins. Grid spans are measured against a visible guide row. Hierarchy asks about bounded immediate regions, avoiding an ambiguous reading-order inference from an ungrouped grid.

## Evaluation and publication

The shared catalog contains 13 enabled model configurations: four Claude, four GPT, three Gemini and two Muse. Exact API IDs, endpoint, output caps and recorded pricing are pinned in each invocation. An API model listing confirms visibility, not credits or inference availability. Account failures block only their provider/endpoint/key scope; OpenAI and Meta use separate accounts despite sharing a transport adapter.

Each valid letter is scored by exact equality. Invalid structured responses are retained as final incorrect observations. Infrastructure failures are preserved in the attempt ledger and availability report, excluded from accuracy denominators, and never presented as model mistakes. Full-cohort publication requires every compared model to answer every question; unavailable models are disclosed separately.

Uniform-guess chance is 1 divided by the family option count, ranging from 1/6 to 1/2. Family accuracy includes invalid answers. API response costs use recorded tokens and the recorded catalog rates on exactly the scored cohort; campaign accounting also retains infrastructure attempts and any unmetered reserves. No aggregate across unlike families is reported.

Before paid calls, the dataset and protocol are committed and their fingerprints frozen in the release descriptor. Finalization reconciles SQLite, raw attempts, scorecards, configurations, timestamps, costs and committed bytes; it reparses raw answers and recomputes grades. A separate publication audit independently replays raw predictions and computes semantic confusion tables and paired parent/child correctness. Neither finalization nor the audit makes provider calls.
