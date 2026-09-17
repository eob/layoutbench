# LayoutBench final descriptive analysis

Descriptive fixed-corpus counts. One response per model and question; related stimuli are correlated. No causal mechanism, population estimate, or confidence interval is inferred.

9 complete configurations, 292 questions each. 4 partial configurations are excluded from this comparison and preserved in availability. Manifest SHA-256: `832a69216d693a8b722441c3f4dfda94666775dfb685454048d2a398ff7897fa`.

Source checkpoint commit: `cb46d35ccc1f411b2aa23376adfd37b4c3baa8cb`. Sealed final_results.json SHA-256: `5a3178a03a80aea435c63301908d577fd8dfb0541e5610f53bceab5361141b6e`. The selected roster and all comparison raw answers, validity flags, scores and correctness flags were checked against that sealed artifact.

## Reproduction

Run `python3 tickets/evidence/feat-03-analysis/layoutbench-final-analysis.py --output-dir tickets/evidence/feat-03-analysis`. The script reads one SQLite snapshot without writes, reparses each raw response using that task’s shuffled options, and verifies valid/correct/score against the stored row. The final-only guard requires terminal model states, then includes only configurations with all 292 questions. Partial configurations remain in availability and in the source raw ledger, outside every pooled metric, example denominator and hierarchy count. Run this command from the repository root. LAYOUTBENCH_ROOT and LAYOUTBENCH_RUN optionally override the repository and run paths; the source run and manifest digest are recorded in diagnostics.json. The separately sealed source and independent publication audit remain authoritative.

## Shared-image parent/child questions

Each of the 24 images has two independently asked questions: the top-level arrangement and the flow inside Field notes. This compares answers on the same image. The scenes use clear outlined section boundaries; a ceiling here does not establish general hierarchical understanding. Flat-versus-nested families use separate stimuli and cannot establish a causal effect of nesting.

| Model | Both correct | Outer only | Inner only | Neither | Pair denominator |
| --- | ---: | ---: | ---: | ---: | ---: |
| GPT-6 Astra | 24 | 0 | 0 | 0 | 24 |
| GPT-5.6 Sol | 24 | 0 | 0 | 0 | 24 |
| GPT-5.6 Terra | 24 | 0 | 0 | 0 | 24 |
| GPT-5.6 Luna | 24 | 0 | 0 | 0 | 24 |
| Gemini 3.1 Pro Preview | 24 | 0 | 0 | 0 | 24 |
| Gemini 3.8 Flash | 24 | 0 | 0 | 0 | 24 |
| Gemini 3.5 Flash-Lite | 24 | 0 | 0 | 0 | 24 |
| Muse Spark 1.3 | 24 | 0 | 0 | 0 | 24 |
| Muse Spark 1.2 | 24 | 0 | 0 | 0 | 24 |

## Nested final-row alignment

Columns below retain their own denominators; theme and copy/position variants are designed cases, not independent replications.

| Model | All | Parent row | Parent column | First position | Second position | Left truth | Center truth | Right truth |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| GPT-6 Astra | 24/24 | 12/12 | 12/12 | 12/12 | 12/12 | 8/8 | 8/8 | 8/8 |
| GPT-5.6 Sol | 24/24 | 12/12 | 12/12 | 12/12 | 12/12 | 8/8 | 8/8 | 8/8 |
| GPT-5.6 Terra | 24/24 | 12/12 | 12/12 | 12/12 | 12/12 | 8/8 | 8/8 | 8/8 |
| GPT-5.6 Luna | 24/24 | 12/12 | 12/12 | 12/12 | 12/12 | 8/8 | 8/8 | 8/8 |
| Gemini 3.1 Pro Preview | 24/24 | 12/12 | 12/12 | 12/12 | 12/12 | 8/8 | 8/8 | 8/8 |
| Gemini 3.8 Flash | 24/24 | 12/12 | 12/12 | 12/12 | 12/12 | 8/8 | 8/8 | 8/8 |
| Gemini 3.5 Flash-Lite | 24/24 | 12/12 | 12/12 | 12/12 | 12/12 | 8/8 | 8/8 | 8/8 |
| Muse Spark 1.3 | 24/24 | 12/12 | 12/12 | 12/12 | 12/12 | 8/8 | 8/8 | 8/8 |
| Muse Spark 1.2 | 24/24 | 12/12 | 12/12 | 12/12 | 12/12 | 8/8 | 8/8 | 8/8 |

## Semantic confusion candidates

Each denominator counts all responses with that semantic truth in that family. Named-model fractions count this particular wrong prediction, not total error rate. These are descriptive confusions, not inferred mechanisms.

- Grid gutter comparison: truth **equal** was answered **vertical** in **16/36** responses. GPT-5.6 Terra: 1/4; Gemini 3.1 Pro Preview: 4/4; Gemini 3.8 Flash: 4/4; Gemini 3.5 Flash-Lite: 2/4; Muse Spark 1.3: 2/4; Muse Spark 1.2: 3/4.

- Horizontal versus vertical inset: truth **equal** was answered **vertical** in **14/36** responses. GPT-5.6 Luna: 1/4; Gemini 3.1 Pro Preview: 3/4; Gemini 3.8 Flash: 3/4; Gemini 3.5 Flash-Lite: 3/4; Muse Spark 1.3: 2/4; Muse Spark 1.2: 2/4.

- Text justification: truth **right** was answered **center** in **13/36** responses. GPT-5.6 Sol: 2/4; GPT-5.6 Terra: 3/4; GPT-5.6 Luna: 2/4; Gemini 3.1 Pro Preview: 1/4; Muse Spark 1.3: 2/4; Muse Spark 1.2: 3/4.

- Spacing within and between groups: truth **equal** was answered **between** in **8/36** responses. GPT-5.6 Luna: 3/4; Gemini 3.5 Flash-Lite: 4/4; Muse Spark 1.2: 1/4.

- Text justification: truth **justify** was answered **left** in **6/36** responses. GPT-5.6 Terra: 1/4; GPT-5.6 Luna: 1/4; Gemini 3.1 Pro Preview: 2/4; Gemini 3.5 Flash-Lite: 2/4.

- Column span: truth **1** was answered **2** in **5/36** responses. GPT-5.6 Luna: 1/4; Gemini 3.5 Flash-Lite: 4/4.

- Column span: truth **2** was answered **3** in **5/36** responses. GPT-5.6 Luna: 3/4; Gemini 3.5 Flash-Lite: 2/4.

- Horizontal versus vertical inset: truth **equal** was answered **horizontal** in **5/36** responses. GPT-5.6 Terra: 1/4; Gemini 3.5 Flash-Lite: 1/4; Muse Spark 1.3: 1/4; Muse Spark 1.2: 2/4.

- Text justification: truth **left** was answered **justify** in **5/36** responses. GPT-5.6 Terra: 1/4; Gemini 3.5 Flash-Lite: 2/4; Muse Spark 1.3: 2/4.

- Grid gutter comparison: truth **vertical** was answered **horizontal** in **4/36** responses. GPT-5.6 Luna: 1/4; Gemini 3.5 Flash-Lite: 3/4.

## Complete-family ceilings

Immediate flow, Cross-axis alignment, Text columns, Grid columns, Grid rows, Grid track proportions, Wrapped row count, Incomplete row alignment, Text block placement, Relative panel width, Top-level hierarchy, Nested section flow, Nested incomplete row alignment

## Lowest-accuracy example per family

Selection uses the same rule as the website: fewest correct answers, then task ID. These are deliberately selected examples.

### Immediate flow: layoutbench-direction-001

Image: `direction-row-light-0.png`. Correct answer: **row**. Correct responses: **9/9**.

Every configuration answered this example correctly.

### Main-axis distribution: layoutbench-distribution-004

Image: `distribution-start-dark-1.png`. Correct answer: **start**. Correct responses: **8/9**.

Gemini 3.5 Flash-Lite → center

### Cross-axis alignment: layoutbench-crossalign-001

Image: `crossalign-start-light-0.png`. Correct answer: **start**. Correct responses: **9/9**.

Every configuration answered this example correctly.

### Text justification: layoutbench-textalign-012

Image: `textalign-right-dark-1.png`. Correct answer: **right**. Correct responses: **2/9**.

GPT-5.6 Sol → center; GPT-5.6 Terra → center; GPT-5.6 Luna → center; Gemini 3.1 Pro Preview → center; Gemini 3.5 Flash-Lite → left; Muse Spark 1.3 → center; Muse Spark 1.2 → center

### Text columns: layoutbench-textcolumns-001

Image: `textcolumns-1-light-0.png`. Correct answer: **1**. Correct responses: **9/9**.

Every configuration answered this example correctly.

### Grid columns: layoutbench-gridcols-001

Image: `gridcols-2-light-0.png`. Correct answer: **2**. Correct responses: **9/9**.

Every configuration answered this example correctly.

### Grid rows: layoutbench-gridrows-001

Image: `gridcols-2-light-0.png`. Correct answer: **2**. Correct responses: **9/9**.

Every configuration answered this example correctly.

### Grid gutter comparison: layoutbench-gridgaps-010

Image: `gridcols-3-light-1.png`. Correct answer: **equal**. Correct responses: **4/9**.

GPT-5.6 Terra → vertical; Gemini 3.1 Pro Preview → vertical; Gemini 3.8 Flash → vertical; Muse Spark 1.3 → vertical; Muse Spark 1.2 → vertical

### Grid track proportions: layoutbench-gridtracks-001

Image: `gridgaps-equal-light-0.png`. Correct answer: **equal**. Correct responses: **9/9**.

Every configuration answered this example correctly.

### Column span: layoutbench-gridspan-001

Image: `gridspan-1-light-0.png`. Correct answer: **1**. Correct responses: **7/9**.

GPT-5.6 Luna → 2; Gemini 3.5 Flash-Lite → 2

### Wrapped row count: layoutbench-wrapcount-001

Image: `wrapcount-1-light-0.png`. Correct answer: **1**. Correct responses: **9/9**.

Every configuration answered this example correctly.

### Incomplete row alignment: layoutbench-wrapalign-001

Image: `wrapalign-left-light-0.png`. Correct answer: **left**. Correct responses: **9/9**.

Every configuration answered this example correctly.

### Neighboring gap comparison: layoutbench-gapcompare-001

Image: `gapcompare-first-light-0.png`. Correct answer: **first**. Correct responses: **8/9**.

Gemini 3.5 Flash-Lite → equal

### Horizontal versus vertical inset: layoutbench-padcompare-012

Image: `padcompare-equal-dark-1.png`. Correct answer: **equal**. Correct responses: **3/9**.

GPT-5.6 Terra → horizontal; Gemini 3.1 Pro Preview → vertical; Gemini 3.8 Flash → vertical; Gemini 3.5 Flash-Lite → vertical; Muse Spark 1.3 → horizontal; Muse Spark 1.2 → vertical

### Text block placement: layoutbench-blockalign-001

Image: `blockalign-left-light-0.png`. Correct answer: **left**. Correct responses: **9/9**.

Every configuration answered this example correctly.

### Relative panel width: layoutbench-widthcompare-001

Image: `widthcompare-first-light-0.png`. Correct answer: **first**. Correct responses: **9/9**.

Every configuration answered this example correctly.

### Spacing within and between groups: layoutbench-groupgap-009

Image: `groupgap-equal-light-0.png`. Correct answer: **equal**. Correct responses: **6/9**.

GPT-5.6 Luna → between; Gemini 3.5 Flash-Lite → between; Muse Spark 1.2 → between

### Top-level hierarchy: layoutbench-topflow-001

Image: `h-01.png`. Correct answer: **row**. Correct responses: **9/9**.

Every configuration answered this example correctly.

### Nested section flow: layoutbench-nestedflow-001

Image: `h-01.png`. Correct answer: **row**. Correct responses: **9/9**.

Every configuration answered this example correctly.

### Nested incomplete row alignment: layoutbench-nestedwrap-001

Image: `h-09.png`. Correct answer: **left**. Correct responses: **9/9**.

Every configuration answered this example correctly.
