# LayoutBench

LayoutBench tests whether vision-language models can answer atomic questions about the visible arrangement of text and interface regions. It covers flow, alignment, grid geometry, wrapping, relative spacing and nested layout hierarchy.

**Version 0.3.0: 292 qualitative questions, 20 families, 250 unique images.** Every image contains sample text. Answers describe visible geometry; they do not require identifying CSS implementation, estimating pixels, or judging aesthetic quality.

## Question bank

| Family | Atomic question | Questions |
| --- | --- | ---: |
| Immediate flow | Are the cards in one row or one column? | 8 |
| Main-axis distribution | Packed at an edge, centered, edge-to-edge, half-size outer spaces, or equal spaces? | 24 |
| Cross-axis alignment | Start, center, end, or fill the cross axis? | 16 |
| Text justification | Left, centered, right, or both-edge justification? | 16 |
| Text columns | How many side-by-side text columns? | 12 |
| Grid columns | How many columns in the card grid? | 12 |
| Grid rows | How many rows in the card grid? | 12 |
| Grid gutter comparison | Are horizontal or vertical gutters larger, or equal? | 12 |
| Grid track proportions | Equal tracks, wider left track, or wider right track? | 12 |
| Column span | How many visible column positions does a card span? | 12 |
| Wrapped row count | How many rows does the repeated sequence occupy? | 12 |
| Incomplete row alignment | Does the shorter final row sit left, center, or right? | 12 |
| Neighboring gap comparison | Which of two successive gaps is larger, or are they equal? | 12 |
| Horizontal versus vertical inset | Which inset around the centered content rectangle is larger? | 12 |
| Text block placement | Where is the whole block, independently of its text alignment? | 12 |
| Relative panel width | Which panel is wider, or are they equal? | 12 |
| Spacing within and between groups | Which gap is larger, or are they equal? | 12 |
| Top-level hierarchy | Are the outlined page sections horizontal-first or vertical-first? | 24 |
| Nested section flow | Is Field notes a row, column, or wrapped sequence? | 24 |
| Nested incomplete row alignment | Where does the shorter row sit inside its own nested frame? | 24 |

Exact question wording and complete answer sets live in [config/qualitative.json](config/qualitative.json). Text alignment and block placement are separate questions. Parent and child flow are independently crossed; Field notes can be the first or second section. The same image can support multiple atomic questions, linked through a shared group ID.

## Run

```sh
bun install
bunx playwright install chromium
python3 -m venv .venv
.venv/bin/pip install -e .
bun run validate
bun test src
.venv/bin/python -m pytest tests

# The combined catalog includes 13 configurations across four API accounts.
.venv/bin/python -m baseline.runner --release 0.3.0 --config config/models.all.json --run-id qualitative-20260917 --concurrency 6 --budget-usd 100
```

API credentials are read from environment variables named in the model catalog. Requests contain only the image and question, without the manifest, HTML, CSS, task IDs, filenames, or answer keys. Model/account failures are recorded separately from incorrect answers.

To reproduce the images, render into a separate candidate directory and validate
it explicitly. Rendering refuses registered release inputs and archived dataset
paths, including parent directories and symlink aliases.

```sh
bun run render
.venv/bin/python -m baseline.validate_dataset --manifest dataset/candidate-rendered/manifest.json
```

## Evidence and interpretation

The renderer pins an 800×600 CSS canvas, 2× image resolution, a bundled font and actual browser font usage. A separate validator derives answers from measured visible geometry, checks image hashes and border pixels, verifies text line edges, and rejects clipping, ambiguous arrangements and mislabeled answers. Option sets are complete; answer slots are balanced and randomized independently of semantic answers.

Choice accuracy includes invalid responses as incorrect. Scores and API response costs are reported separately for each family on a frozen shared cohort. There is no overall benchmark score. Images, correlated questions, model settings, raw responses, attempts and source commits remain traceable through the release and finalization records.

Human agreement has not been measured. Clear boundaries, coarse differences and qualitative answer sets are design controls, not evidence of agreement. Success here measures these rendered tasks; transfer to high-level design understanding remains a hypothesis.

[Methodology](docs/methodology.md) · [Release format](releases/README.md) · [Finalization](releases/FINALIZATION.md) · [Review and delivery record](tickets/feat-03-qualitative-layout.md)
