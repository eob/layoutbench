# feat-03-qualitative-layout: Atomic spatial perception and publication

- Status: In Review
- Branch: feat-03-qualitative-layout
- Harness: codex
- Session: 01a0ad34-d16c-7a82-b973-d59084daaf32
- Assignee: Edward Benson
- Base: 80b30a1
- PR: https://github.com/eob/layoutbench/pull/2
- Authorization: audit, expand, evaluate all configured models, publish and deploy edwardbenson-prod without further questions.

## Evidence and decisions

Current 0.2.0 has 208 tasks. Census from source: 110 ask for absolute pixel values; no nested hierarchy, wrapping, spans, track proportions or relative gap comparisons. Existing geometry/protocol freezing and raw-response replay are valuable and will be retained. The qualitative release asks about visible arrangement, never hidden CSS implementation. Preserve archived releases and results.

Sibling review: ColorBench uses controlled paired interventions to reject shortcuts; BorderBench uses visible coarse prototypes and crossed nuisances; FontBench provides the shared model roster and sealed publication conventions. Independent agents are reviewing sibling source, LayoutBench validity, and website production structure.

## Plan and acceptance gates

- [x] Freeze a qualitative question catalog covering direction, distribution, cross-axis alignment, text justification/columns, grid parameters, wrapping, relative spacing and nested layout hierarchy.
- [x] Build text-bearing stimuli with crossed themes/content variants and balanced shuffled answers; derive answers independently from rendered geometry and inspect images.
- [x] Pin missing coverage, ambiguity/overflow, answer-label integrity, nuisance crossing and parser failures with meaningful tests.
- [x] Run Python/TypeScript gates, deterministic render and mock; commit and freeze release identity before paid calls.
- [x] Execute every enabled sibling-model configuration, keep unavailable/credit failures explicit, seal and independently audit raw results.
- [ ] Publish graph, table, explanation and data-grounded task observations; activate benchmarks/tinkering links; inspect desktop/mobile.
- [ ] Merge scoped website PR to edwardbenson-prod and verify live deployment, links and published evidence.

## Durable constraints

Qualitative categories are defined by visible geometry with large separations; human agreement is a design aim, not a measured claim. Each question has one answer. Related questions/images retain group identity. Dataset, prompts, protocol, provider settings and raw attempts must be traceable. Public framing is self-contained and does not discuss earlier runs.

## Adversarial review findings

Sibling source inspected at BorderBench `70619a4`, FontBench `14b09c3a`, ColorBench `55204df`. BorderBench's coarse visible prototypes, FontBench's font/line/overflow checks, and ColorBench's matched controls informed this release. Combined roster comes byte-for-byte from ColorBench.

| Finding | Evidence | Resolution |
| --- | --- | --- |
| Exact pixel tasks do not meet qualitative brief | 110/208 tasks in source family census | Qualitative release, no pixel answers |
| Distribution options overlap | distribute-13 has outer gaps24/24 and inner gaps172/172: both old D and E descriptions apply | Explicit inner frame, mutually exclusive geometric descriptions |
| Content edge ambiguous | regionpad-01 has48px to tint,72px to text | Questions name visible tinted rectangle edge |
| Missing hierarchy and wrap coverage | No builders/families for nested flow, wrapping, spans, track proportions | 20-family catalog, independently crossed parent/child flow and both target positions |
| Count shortcut in proposed nesting | Different child counts could identify wrapped flow | Five identical-count cards for every nested-flow answer |
| Option rotation shortcut in initial draft | Formula based on semantic index+theme+variant matches280/280 truth slots | Independent balanced slot shuffle; old rule matches87/280 after fix; regression pinned |
| Model catalog rejects Muse+OpenAI | Endpoint-agnostic five-model limit rejects combined13-model catalog | Account endpoint limits, aliases normalized; red/reversion evidence under tickets/evidence |
| Finalizer blocks valid publication during outages | `ValueError: Unresolved infrastructure failures cannot be finalized; retry them first` | Complete selected cohort seals with full unavailable roster and attempt ledger preserved |

Initial coverage red evidence: `ValueError: Unknown family: topflow`; catalog test also reported `FileNotFoundError: config/qualitative.json`. Both turn green after implementation. Geometry validation tests deliberately coordinate forged answer+declared semantic labels, so passing requires independent geometry. Pixel tamper tests update the PNG hash too, proving checks do more than trust hashes.

## Implementation and verification checkpoint

Source builders produce text-bearing scenes with unchanged neutral copy across answers. Exact identical images are deduplicated and grouped; the renderer records actual Chromium font usage and rejects overflow. Independent Python geometry and decoded-pixel gates cover every current question. Browser hierarchy tests cover all scenes, target positions, constant child count and3+2 wrapping.

At checkpoint a32035f plus working changes, the Python suite passed103 tests and the TypeScript suite passed13 tests/1908 assertions. A second render matched all245 artifacts byte-for-byte before the final nestedwrap position expansion. Final release gates will be recorded after that expansion. Use `.venv/bin/python -m pytest`; the environment's standalone pytest entry point omits the root scripts namespace from import resolution.


## Final pre-inference gates

- Final census:292 questions,20 qualitative families,250 distinct PNGs;72 hierarchy questions include both target positions for nested wrap alignment.
- `bunx tsc --noEmit`: passed.
- `bun test src`:13 passed,2180 assertions; browser hierarchy checks included.
- `.venv/bin/python -m pytest tests -q`:107 passed in13.92s.
- Independent rerender: all253 artifacts, including manifest and font assets, byte-identical.
- `git diff --check`: clean.
- Final simplifyfu and adversarial pass found no remaining substantive blocker. Cross-axis descriptions explicitly exclude the fill case from start/center/end.
- Full 13-configuration mock gate completed before release freeze and paid inference.


Final target-isolation control: the complete row in nestedwrap initially had spare width (12CSSpx for horizontal parent;76CSSpx for vertical parent), so it moved with the shorter row. A browser regression failed `Expected: <1 / Received:12`. Wrapped child widths now fill the complete row exactly; only the incomplete row responds to alignment. The independent validator rejects an altered complete row even with the target row unchanged. This correction was made before any paid inference; the draft release descriptor will be rebound to the validated dataset and protocol.


Final corrected gates:109 Python tests pass(14.80s);13 TypeScript/browser tests pass(2252 assertions after the full-row control); TypeScript typecheck clean; all253 render artifacts byte-identical. Final frozen-shape mock completes292/292 questions; the13-model harness matrix completes3796/3796 mock responses. Mock artifacts stay outside publication. Source differences preserve the original third-party font license and verbatim red logs, whose trailing whitespace is intentionally retained; source-only diff check is clean.

## Sealed campaign and final source gates

Campaign `qualitative-20260917` finished on 2026-09-17 at 03:28:03 UTC. Nine configurations completed all 292 questions. All four Claude configurations completed 221 questions before Anthropic credit exhaustion; their 884 answers and explicit availability reasons remain in the raw artifacts. The full comparison contains 2,628 answers from the nine complete configurations. The campaign retains 3,512 final answers and 3,515 attempt records, including three credit failures. No invalid answers occurred. The recorded $30.7923777 ledger includes six estimated-cost attempt records and is not an invoice total.

Raw checkpoint commit: `cb46d35`; sealed artifact commit: `ac17659d69c5c8fbd60abfade2b14edb06826b86`. The finalizer ran on a clean checkout, reconciled committed SQLite/export/scorecard evidence, and its offline verification passed. The separate publication auditor independently replayed all 3,512 raw predictions and verified the 292-question cohort, family metrics, costs, and paired hierarchy counts.

Final source validation: 117 Python tests passed in 13.47s; 20 TypeScript/browser tests passed with 2,270 assertions; TypeScript typechecking passed. Renderer guards now reject frozen release paths, their ancestors/descendants and symlink aliases; both current and archived rendering default to separate candidate directories. Renderer and documentation changes made after inference began do not alter the frozen dataset, catalog or evaluation protocol. Count-family content/repetition shortcuts and unmeasured human agreement remain explicit methodological limits.

The website import, data-grounded findings, browser checks and production deployment remain pending.

Final audit-parser review found that Python substring membership accepted empty and multi-letter choices in the independent audit (the frozen grader already uses a list and rejects them). A focused regression failed with `assert {'choice': ''} is None`; requiring one character fixes it, and reverting that condition reproduces the failure. All eight publication-audit tests pass. Replaying the 3,512 real answers after the correction produces byte-identical audit results. This change is outside the frozen evaluation protocol.
