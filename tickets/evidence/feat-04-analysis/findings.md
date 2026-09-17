# LayoutBench 0.3: thirteen-model qualitative observations

Analysis date: 2026-09-17. All thirteen configurations completed the same 292 questions, yielding 3,796 scored responses. None was invalid. The source is `results/runs/full-roster/0.3.0/qualitative-20260917/final_results.json`, committed at `811dbd016689132a51ec1ffe80de7225751af095`, SHA-256 `e5686b10f3040e44eed007cbf860a5170d9e0e97edd6b7aa222bac37d2f94938`.

The analysis independently decodes each raw answer using its task's shuffled semantic options, verifies all answers and scoring fields against the seal, and checks all 260 model-family cells. Complete evidence is in [diagnostics.json](diagnostics.json), [observations.md](observations.md), [all model-family results](model-family-results.csv) and [Claude family results](claude-family-results.md). There is no combined benchmark score.

## Flow recognition and final-row alignment separated on the same image

Each model received two independently asked flow questions on the same 24 hierarchy images: one about the outer sections and one about the children inside Field notes. Every model answered both correctly on every image: **312/312 model-image pairs**, with zero outer-correct/inner-wrong, inner-correct/outer-wrong or both-wrong pairs.

Nested final-row alignment was **305/312 correct**. Twelve configurations scored **24/24**; Claude Haiku 4.5 scored **17/24**. Haiku recognized all eight centered final rows, seven of eight left-aligned rows and two of eight right-aligned rows. Of its six errors on right alignment, five chose center and one chose left. Its remaining error called a left-aligned row centered.

The selected nested example makes this distinction concrete. On `h-23.png`, Haiku correctly answered **column** for `layoutbench-topflow-023` and **wrapped** for `layoutbench-nestedflow-023`, but answered **center** instead of **left** for `layoutbench-nestedwrap-007`. The other twelve configurations answered all three questions correctly. The image was visually inspected: the shorter row touches the left inner boundary. Another inspected case, `layoutbench-nestedwrap-024` (`h-40.png`), has a right-aligned final row in the second vertically stacked section; Haiku called it centered.

Haiku's nested alignment counts were 9/12 with horizontally arranged parent sections and 8/12 with vertically arranged sections; 7/12 with Field notes first and 10/12 with it second. Those position variants also change sample words, so they do not isolate position causally. The vertical-parent, second-section, left-aligned case is explicitly covered: `layoutbench-nestedwrap-006` (`h-22.png`) and `layoutbench-nestedwrap-008` (`h-24.png`) each received **13/13** correct answers.

These are clear outlined synthetic scenes. The flow ceiling does not establish general hierarchical understanding. Flat and nested families use separate stimuli and cannot estimate a causal effect of nesting. Evidence: `hierarchy_pairs`, `nestedwrap`, `examples.nestedwrap`, and the named tasks in the sealed source.

## Equal spacing attracted more errors than unequal spacing

Equal grid gutters were identified correctly in **30/52 responses**, compared with **89/104** for unequal gutters. Twenty responses to equal gutters said the vertical distance between rows was larger; two said the horizontal distance between columns was larger. Gemini 3.1 Pro Preview and Gemini 3.8 Flash each chose vertical on all four equal-gutter images; Claude Fable 5.1 did so on three of four. GPT-6 Astra and GPT-5.6 Sol answered all twelve grid-gutter questions correctly.

Equal horizontal and vertical insets were **25/52 correct**, compared with **95/104** for unequal insets. Of the 27 errors on equal insets, twenty chose vertical and seven horizontal. Astra, Sol and Claude Opus 5 answered all twelve inset questions correctly. The other Claude inset scores were Fable **9/12**, Sonnet **11/12** and Haiku **1/12**.

Exact cases: `layoutbench-gridgaps-012` (`gridcols-3-dark-1.png`, visually inspected) was **6/13** correct. Fable, Sonnet, Gemini Pro, Gemini Flash and Flash-Lite chose vertical; Opus and Haiku chose horizontal. `layoutbench-padcompare-012` (`padcompare-equal-dark-1.png`) was **4/13** correct: Opus, Astra, Sol and Luna answered equal. Evidence: `families.gridgaps.semantic_confusion`, `families.padcompare.semantic_confusion`, their model entries and the corresponding `examples` entries.

## Right-aligned text was sometimes called centered

Right-aligned paragraphs were identified correctly in **28/52 responses**. They were called centered in **15/52**, justified in 6/52 and left-aligned in 3/52. Claude Fable 5.1, Claude Opus 5, GPT-6 Astra and Gemini 3.8 Flash each answered all **16/16** text-justification questions correctly. Claude Sonnet 5 scored **14/16**, with both errors calling right-aligned text centered. Claude Haiku 4.5 scored **4/16** and chose justified on every text-justification question.

The selected example, `layoutbench-textalign-012` (`textalign-right-dark-1.png`), was **4/13** correct: Fable, Opus, Astra and Gemini Flash chose right. Sonnet, Sol, Terra, Luna, Gemini Pro and both Muse versions chose center; Haiku chose justified; Flash-Lite chose left. Its visible text lines share a right edge. Evidence: `families.textalign.semantic_confusion`, `families.textalign.by_model`, `examples.textalign`, and Haiku's sixteen raw responses in the sealed source.

Nine of the twenty families reached an all-model ceiling. These counts identify observed semantic confusions and controlled tasks that distinguish configurations; they do not establish why a model made a choice.

## Reproduce and interpret

Run from the repository root:

```sh
LAYOUTBENCH_RUN=results/runs/full-roster/0.3.0/qualitative-20260917 python3 tickets/evidence/feat-04-analysis/run-analysis.py --output-dir tickets/evidence/feat-04-analysis
python3 tickets/evidence/feat-04-analysis/test_analysis.py
```

The wrapper uses the unchanged raw-answer analyzer filed with the earlier cohort, requires all thirteen configurations to be complete and the selected roster to match the new seal, and derives valid/invalid/correct counts independently for every model-family cell. It writes the machine-readable diagnostics, full observations, CSV and Claude table. The tests reject the earlier nine-model cohort without writing output, and verify complete generation and the published example/denominator structure. The original evidence and sealed run remain preserved.

These are descriptive counts from one response per configuration and question. Related questions, words, themes and layouts are correlated; there are no repeated model trials or human-agreement measurements. No confidence intervals, causal mechanisms or estimates of performance on arbitrary interfaces are inferred. Examples are selected for lowest accuracy within their family, with task ID breaking ties, except the additional hierarchy cases chosen to make the question scopes concrete.
