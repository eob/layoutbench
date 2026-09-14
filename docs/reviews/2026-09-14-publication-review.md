# LayoutBench publication review — 2026-09-14

Review started from `62a557c` (sealed 0.1.0 pilot). This is an adversarial source, corpus, and evidence review, not human perception calibration. The original 0.1.0 dataset and sealed run remain byte-for-byte historical artifacts.

## Findings that required a new experiment

**Critical: sorted distractors revealed token-choice answers without images.** `tokenOptions` sorted every incorrect token then inserted the correct one. Removing each option and checking whether the remainder is sorted exposes the inserted answer. Full option sets and balanced letters did not prevent this. A deterministic first-candidate attacker scored 13/16 gap (81.25%; nominal chance 14.29%), 12/16 padding (75%; chance 20%), 11/16 region padding (68.75%; chance 20%), and 10/12 table padding (83.33%; chance 25%). It uniquely recovered 10, 9, 8, and 5 answers respectively. The v0.1 token-choice results do not establish visual perception.

The fix keeps balanced truth slots and shuffles all distractors with an independent task seed. A regression enumerates 256 seeds at one fixed truth slot and requires all 24 possible four-distractor orders. Red evidence:

```text
error: expect(received).toBe(expected)
Expected: 24
Received: 1
(fail) LayoutBench builders > randomizes distractors independently of the truth slot
```

**High: header metrics measured invisible line-box boundaries.** The screenshot had glyphs on a uniform card, while truth measured header/body element boxes. The glyph ink does not reveal those box edges, particularly for numeric questions. Version 0.2 tints the header and body blocks and names the visible block edges explicitly in both prompts. The frozen pixel gate now checks both top and bottom edges. Red evidence:

```text
FAILED tests/test_validate_dataset.py::test_header_spacing_has_visible_box_edges
assert (255, 255, 255) == (214, 224, 235)
```

**Moderate: item count was a partial flow shortcut.** Counts 3, 4, 6 had different answer distributions; a count-only majority lookup reached 6/16 (37.5%) versus 25% chance. Every flow direction now has exactly two four-item and two six-item examples. Variable-width six-item rows fit within the card. Both the builder regression and frozen validator enforce identical distributions. Red evidence:

```text
(fail) LayoutBench builders > balances item counts across flow answers
Expected: ["A", "B", "C", "D"]
Received: ["A", "B", "C"]
```

**Prompt precision:** distribution's previous "half-size spaces" was not literally true after fixed CSS gap and card padding. It now describes smaller equal outside spaces. Container padding explicitly asks the smallest item-to-inner-border distance; table padding asks for the left text inset. Header prompts identify actual tinted block edges.

**Protocol provenance:** provider request construction and response schemas were not in the protocol digest. `providers.py` is now fingerprinted. A change to image detail, request payload, schema, or provider-side parsing therefore requires a new protocol release.

**Documentation:** corrected the missing 14.3% gap chance baseline, obsolete $15/$25 campaign estimate (the archived campaign actually spent $27.87 with a $50 cap), and overstatement of nuisance crossing. Sparse token families cover every marginal level but do not provide complete factorial coverage.

## Validation plan and gates

Base commit: `62a557c`.

| Gate | Result |
| --- | --- |
| Original TypeScript builder suite | 7 passed, 623 assertions |
| Original Python suite | 70 passed |
| Original dataset validation | 208 tasks / 150 images |
| Original release validation | Passed exact committed artifacts/protocol |
| Original seal replay | Passed all 2,288 source responses and ledger reconciliation |
| New targeted regressions | All three failed before repair for the stated cause |
| Revised builder, Python, static checks | 9 TS tests / 884 assertions; 71 Python tests; `bunx tsc --noEmit` and `git diff --check` pass |
| Revised render repeat / image inspection | All 153 artifact hashes identical across repeat render; header blocks and six-item variable row inspected |
| Full 0.2.0 campaign and independent recomputation | Pending |

## Decisions and limitations

Version 0.2.0 changes prompts and some images, so archived predictions cannot be rescored as the revised experiment. All 11 configurations receive all 208 questions again, with a $50 cumulative budget cap. Version 0.1 remains inspectable using its compatible checkout at `62a557c` and is explicitly superseded.

The benchmark is a small descriptive pilot: 12–20 tasks per choice family and 16–18 per numeric family; one response per model/task; no human agreement study; no significance/rank claims or pooled score. Families use one font, one renderer, one canvas, limited copy and geometry. Providers may rescale the 1600×1200 image differently. Numeric errors use a known 800×600 CSS canvas, engineering ceilings of 16px/4px, and prompt examples that may anchor estimates. A constant-16 baseline accompanies numeric scores. The choice/numeric siblings and eight columns/justification pairs share images; their 208 questions are 150 distinct stimuli, not 208 independent observations. Full option sets remove subset clues; seeded permutation does not make the public bank resistant to memorization. Item identities/colors and some dimensions remain fixed templates. Sparse marginal crossings do not identify all interaction effects.

Invalid model outputs remain in accuracy/mean-score denominators as zero. Numeric error summaries and within-band rates use valid rows only. Header numeric error is the average of its two absolute errors; its band flag requires both edges within the band. Unknown metering makes response mean costs null; estimated conservative reserves stay separately disclosed. API runs test end-to-end provider pipelines, not isolated visual encoders.

Source repair validation also temporarily restored the old sorted distractor
and count constructions: both new tests failed with the same signatures,
then passed after restoring the repair. Typechecking uncovered existing
heterogeneous Cartesian-product typing errors; one tuple-preserving shared
helper replaces the two incorrectly homogeneous versions without changing
the generated corpus. A test invocation overlapped an intentional render
directory rebuild and failed on its temporarily absent manifest; the
ordered post-render run passed all 71 tests. No implementation change was
made for that execution-order error. A pre-publication scan of all 422
historical Git objects found none of the 14 configured secret values.

## Scope of the source and corpus audit

- Builders: traced all thirteen families, every answer mapping, option permutation, token distribution, theme/geometry level coverage, neutral copy, and sibling render reuse. The revised old remove-one-sort attacker has its true answer among candidates in 0/16 gap, 0/16 padding, 0/16 region, and 0/12 table tasks. This directly breaks the demonstrated rule; it is not proof against every possible finite-bank shortcut.
- Renderer and pixels: verified fixed canvas/DPR and font bytes, DOM overflow gates, actual PNG hashes, geometry-derived flow/distribution/alignment, line-box text justification, all table cells, visible header edges, outer region bands, gap midlines and item-ink probes. Inspected revised light header, dark variable six-item row, dark six-item grid, three-column justified document, and small-padding table. Grid boxes stretch horizontally; vertical tracks also determine spacing. The documentation now makes that distinction.
- Protocol: read strict JSON parsing, duplicate-key rejection, exact schemas, integer bounds, case normalization, invalid handling, choice grades, numeric ceilings, max-error bands for two-key headers, quantiles, confusion denominators, and constant-16 baselines. Native request paths contain image bytes and the family prompt only; they expose no manifest answer, task ID, filename, or design metadata to a model. No previous response is included in a later request.
- Runner/state: reviewed frozen gates before paid calls, deterministic task order, per-provider key scopes, explicit model catalog, request/token ceilings, conservative budget reservations, SQLite result/attempt separation, retry classification, valid-versus-infrastructure completion, checkpoint resume identity, model configuration persistence, and sealed-run refusal. Costs reflect stored catalog prices, not a provider invoice; the $50 budget is separate from score accuracy.
- Finalization: read the committed-source byte check, closed-WAL requirement, SQLite integrity and ledger reconciliation, attempt chronology, exact model/scorecard census, raw answer replay, cohort intersection/full-scope requirements, metering completeness, hash seal, immutable roster, and repeat verification. The independent audit script imports none of these scoring modules, recomputes each grade directly from raw text, and checks all family accuracy, confusion, numeric score/error/quantile/band/baseline, cost, latency, and group-count metrics. It first passed all 2,288 historical responses. Corrupting either a saved grade or an aggregate accuracy is rejected in dedicated tests.

The run records `runner_git_dirty: true`: the sole untracked file when the
2a8e9aa invocation began was generated TypeScript incremental build metadata
(`tsconfig.tsbuildinfo`). Dataset, protocol, catalog and implementation were
committed. The metadata flag is preserved honestly. The file pattern is now
ignored; the separately pinned dataset/protocol and final source evidence
remain fully verifiable.
