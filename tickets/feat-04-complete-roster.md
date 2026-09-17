# feat-04-complete-roster: Publish all thirteen model configurations

- **Status**: Completed
- **Branch**: `feat-04-complete-roster`
- **Machine**: eob-dev2
- **Harness**: codex
- **Session ID**: `01a0ad34-d16c-7a82-b973-d59084daaf32`
- **PR**: https://github.com/eob/layoutbench/pull/4
- **Assignee**: Edward Benson

## Goal

Complete the four Claude configurations on the frozen 292-question LayoutBench 0.3.0 release and publish one thirteen-model comparison, including all graphs, tables, findings, and examples. Commit and push both the benchmark and website repositories.

## Baseline evidence

At source base `7247bda6bc6a418352b295ab2695f06567cd9e55`, the sealed comparison contains nine models. The checkpoint reports:

```text
Published comparison models: 9
claude-fable-5-1 221 paused
claude-haiku-4-5-20251001 221 paused
claude-opus-5 221 paused
claude-sonnet-5 221 paused
```

## Plan and validation

- [x] Preserve the original seal; verify a separate continuation checkpoint has identical historical answers and attempts.
- [x] Execute only the 284 missing Claude answers using unchanged release, protocol, model settings, and cumulative budget.
- [x] Commit raw evidence, finalize all thirteen models, independently replay answers and audit lineage and costs.
- [x] Recompute public findings and import the sealed source commit into the website.
- [x] Validate publication, commit/push both repositories, and verify deployed graphs, tables, and source links.

## Decisions and durable findings

The original sealed directory remains immutable. The continuation keeps the same campaign ID and original invocation history under a distinct output-root path; its metadata records the exact source snapshot. The runner already supports alternate output roots and resumes only tasks without a final response. Public copy describes the complete cohort without a historical update narrative; raw timestamps and provenance remain accurate.

## Handoff & Takeover Log

- 2026-09-17: Started by codex on eob-dev2 at the user's request after Anthropic credits were replenished. Website work delegated to `website_survey`; independent continuation review delegated to `layout_audit`.

Continuation path: `results/runs/full-roster/0.3.0/qualitative-20260917`. All 17 copied raw artifacts matched the original sealed hashes before adding explicit lineage to `run.json`; original seal verification passed. Independent review by `layout_audit` confirmed runner/finalizer invariants.

## Execution evidence

The live continuation finished successfully at `2026-09-17T12:10:06.516568+00:00` (exit 0). All thirteen models have 292 answers. Exactly 284 new Claude attempts were appended; the original 3,515 attempt records and 3,512 final answer objects are unchanged. The original seal still verifies. Cumulative ledger: $34.56476570; incremental recorded cost: $3.77238800.

Command: `.venv/bin/python -u -m baseline.runner --release 0.3.0 --config config/models.all.json --output-dir results/runs/full-roster --run-id qualitative-20260917 --models claude-fable-5-1 claude-opus-5 claude-sonnet-5 claude-haiku-4-5-20251001 --concurrency 10 --budget-usd 100`. Runner invocation source: `0ba27f3`, clean.

Focused existing checks at base `0ba27f3`: `.venv/bin/python -m pytest tests/test_finalize_partial.py tests/test_qualitative_audit.py -q` — 13 passed.

## Final source validation

Raw checkpoint: `bd67717`. Sealed artifact commit: `811dbd016689132a51ec1ffe80de7225751af095` (pushed). Final results SHA-256: `e5686b10f3040e44eed007cbf860a5170d9e0e97edd6b7aa222bac37d2f94938`. Finalizer source was clean. All release, dataset, configuration, and evaluation protocol bytes remain unchanged.

| Gate | Source | Result |
| --- | --- | --- |
| Finalizer verification | `811dbd0` | Complete 13-model, 292-question comparison; 3,796 final answers |
| [Independent ledger and lineage replay](evidence/feat-04-independent-full-audit.md) | `811dbd0` | Zero discrepancies; original seal and every historical attempt/answer byte-value intact |
| Independent audit tamper controls | `811dbd0` plus evidence scripts | 8 passed; refusal and reversion evidence retained |
| Raw-answer and semantic analysis | `811dbd0` | All 260 model-family cells verified; two complete-cohort controls passed |
| Existing analysis guard tests | `811dbd0` | 5 passed, 8 subtests |
| Website data comparison | `811dbd0` | All 260 imported family metric objects exactly match the sealed source |

The campaign contains 3,799 attempt records and 3,802 HTTP requests. The 284 new requests were fully metered and returned valid answers, with no new infrastructure failures. Cumulative metered subtotal is $33.99419170; existing conservative allowances total $0.57057400. These are recorded token-rate costs, not provider invoices.

[Full findings](evidence/feat-04-analysis/findings.md), [Claude family table](evidence/feat-04-analysis/claude-family-results.md), and [all model-family results](evidence/feat-04-analysis/model-family-results.csv) are generated from the complete cohort. The website imports the same sealed commit. The simplifyfu and comment-hygiene pass found no runtime changes or unnecessary abstractions; evidence scripts reuse the existing analyzer and retain independent ledger parsing.

Website PR [#1644](https://github.com/eob/kaya-web/pull/1644) merged into `edwardbenson-prod` at `6dd07b2f0a743ae1f1ae1c9edb1c76b7329c26d9`. Website validation passed: seven preflight lanes (117 final corpus tests), 57 focused tests / 1,732 assertions, app typecheck/build, 69 navigation tests, nine final focused browser tests, and desktop/mobile visual review. Hosted GitHub CI could not start because of its billing limit; the repository-authorized full local preflight passed. Production deployment `Gk9YgaWg7RiZUSubSkD44zwB6w8C` succeeded. Live verification passed: nine browser tests across mobile, tablet, and desktop (36.3 seconds), all thirteen models on 292 questions, all twenty original specimen PNG hashes, both public source artifact hashes, and benchmark/collection links. The page presents one complete comparison without an update narrative. Website ticket closure PR [#1645](https://github.com/eob/kaya-web/pull/1645) merged at `7ee9c096bdf5f41405417f6f65bc774604019303`; its product files are identical to the verified deployment.

## Merge Summary

**Merged:** 2026-09-17T12:16:11Z

**Pull request:** https://github.com/eob/layoutbench/pull/4

**Merge commit:** `49ee0b631baed1ebb5c33095076b3fd9034e6114`

### PR title

Publish complete thirteen-model LayoutBench results

### PR description

## Summary
Publish a complete LayoutBench 0.3.0 comparison covering all thirteen configurations on the same 292 questions: 3,796 final answers, including all four Claude models.

## What changed
Complete the 284 missing Claude answers from a separate continuation checkpoint. Preserve the original sealed snapshot, all 3,515 historical attempt records, and all 3,512 historical answer JSON strings. Record explicit lineage, original timestamps, unchanged model settings, and the complete ledger; seal the full roster at `811dbd016689132a51ec1ffe80de7225751af095`.

Publish the full model-family CSV, Claude table, and raw-answer findings. All models recognize both levels of flow in the paired hierarchy images; nested final-row alignment distinguishes Haiku (17/24) from the other twelve configurations (24/24). README links the complete cohort and evidence.

## Validation
- Finalizer replay and independent standard-library audit: zero discrepancies across 3,796 answers, 3,799 attempts, and 3,802 HTTP requests; frozen inputs and both committed seals verified.
- Historical ledger and answer byte-values unchanged; exactly 284 missing Claude tasks appended, all valid and fully metered.
- Existing finalizer/audit tests: 13 passed. Lineage tamper controls: 8 passed, with red/reversion evidence. Existing analysis guards: 5 passed; complete-cohort controls: 2 passed.
- All 260 derived model-family cells and all 260 imported website family metric objects match the seal.
- Incremental recorded cost: $3.772388; cumulative ledger: $34.56476570, including $0.57057400 of prior conservative allowances.

## Risks and follow-ups
Human agreement and transfer to arbitrary interfaces remain unmeasured. Costs are recorded token-rate estimates rather than provider invoices. Website presentation imports this exact sealed artifact through a separate production-line PR.

## Ticket
[tickets/feat-04-complete-roster.md](https://github.com/eob/layoutbench/blob/feat-04-complete-roster/tickets/feat-04-complete-roster.md)

### Agent Metadata
- Harness: codex
- Machine: eob-dev2
- Session ID: `01a0ad34-d16c-7a82-b973-d59084daaf32`
