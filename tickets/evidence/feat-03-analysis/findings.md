# LayoutBench 0.3 qualitative observations

Published analysis date: 2026-09-17. These observations describe nine complete model configurations answering the same 292 questions once each. Four Claude configurations stopped at 221 questions because the provider account exhausted its credits; they remain in the source availability record and raw ledger, outside every comparison below.

The authoritative source is `results/runs/0.3.0/qualitative-20260917/final_results.json`, SHA-256 `5a3178a03a80aea435c63301908d577fd8dfb0541e5610f53bceab5361141b6e`. The analysis independently reparses the checkpoint's raw responses using each question's shuffled semantic options, then verifies the selected roster and all 2,628 comparison raw answers, validity flags, correctness flags and scores against the sealed source. Detailed denominators, model contrasts and task responses are in [diagnostics.json](diagnostics.json); complete tables are in [observations.md](observations.md).

## Equal spacing was a recurring source of errors

Equal grid gutters were identified correctly in **20/36 responses**, compared with **65/72** on unequal gutters. All 16 errors on equal gutters chose the option saying the vertical distance between rows was larger. Gemini 3.1 Pro Preview and Gemini 3.8 Flash each made that choice on all four equal-gutter images. GPT-6 Astra and GPT-5.6 Sol answered all 12 grid-gutter questions correctly.

Equal horizontal and vertical insets showed a similar descriptive pattern: **17/36** correct, compared with **70/72** for unequal insets. Of the 19 errors on equal insets, 14 said the vertical inset was larger and five said the horizontal inset was larger. Astra and Sol answered all 12 inset questions correctly.

Exact cases: `layoutbench-gridgaps-010` (`gridcols-3-light-1.png`) was **4/9** correct; Terra, Gemini Pro, Gemini Flash and both Muse versions answered vertical. `layoutbench-padcompare-012` (`padcompare-equal-dark-1.png`) was **3/9** correct; Terra and Muse 1.3 answered horizontal, while Gemini Pro, Gemini Flash, Flash-Lite and Muse 1.2 answered vertical. Both images were visually inspected. Evidence: `families.gridgaps.semantic_confusion`, `families.padcompare.semantic_confusion`, their `by_model` entries, and the corresponding `examples` entries.

## Right-aligned text was sometimes called centered

Right alignment was identified correctly in **18/36 responses**. It was called centered in **13/36**, left-aligned in 3/36 and justified in 2/36. On `layoutbench-textalign-012` (`textalign-right-dark-1.png`), only **Astra and Gemini Flash** were correct: Sol, Terra, Luna, Gemini Pro and both Muse versions chose center; Flash-Lite chose left. Astra and Gemini Flash also answered all **16/16 text-justification questions** correctly.

This exact image was visually inspected: its text lines share a right edge. These observations identify the semantic answers that were confused; the single responses do not establish why the models made those choices. Evidence: `families.textalign.semantic_confusion.right`, `families.textalign.by_model`, and `examples.textalign`.

## The outlined hierarchy scenes reached a ceiling

Each model saw **24 images with two independently asked questions**: the arrangement of the outer sections and the flow inside Field notes. Every model answered both correctly on every image: **216/216 model-image pairs**, with **zero outer-correct/inner-wrong, inner-correct/outer-wrong, or both-wrong pairs**.

All nine models also answered all **24 nested final-row alignment questions** correctly (**216/216 responses**). Per model, that includes 12/12 with sections arranged horizontally, 12/12 vertically, 12/12 with Field notes first, 12/12 second, and 8/8 each for left, center and right alignment. The vertical-parent, second-section, left-aligned case is explicitly present: `layoutbench-nestedwrap-006` (`h-22.png`, visually inspected) and `layoutbench-nestedwrap-008` (`h-24.png`) each received **9/9** correct answers.

These are clear outlined synthetic scenes. The ceiling does not establish general hierarchical understanding. Flat and nested families use separate stimuli, so their family totals cannot estimate a causal effect of nesting. Thirteen of the twenty families reached an all-model ceiling in this cohort. Evidence: `hierarchy_pairs`, `nestedwrap` and `ceiling_families_all_models`; exact task definitions and raw responses remain in the sealed source and manifest.

## Reproduce and validate

Run from the LayoutBench repository root:

```sh
python3 tickets/evidence/feat-03-analysis/layoutbench-final-analysis.py --output-dir tickets/evidence/feat-03-analysis
python3 tickets/evidence/feat-03-analysis/test_analysis.py
```

The first command reads SQLite in read-only mode, requires a terminal campaign and a matching sealed comparison, and generates `diagnostics.json` and `observations.md`. `LAYOUTBENCH_ROOT` and `LAYOUTBENCH_RUN` optionally override the repository and source-run locations. The second command exercises five controls: malformed responses and duplicate keys, the active-campaign guard, a changed sealed roster, a changed sealed raw answer, and exclusion of partial providers from every comparison while retaining their availability records.

All counts describe this finite designed corpus. Model answers, repeated wording, themes and related layouts are correlated; these denominators are not independent human judgments or repeated model trials. No confidence intervals, causal mechanisms or estimates of performance on arbitrary interfaces are inferred. The displayed exact examples were selected for low observed accuracy, except the hierarchy example chosen to illustrate the requested vertical-parent/second-section case.
