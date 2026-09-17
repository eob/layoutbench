# feat-04-complete-roster: Publish all thirteen model configurations

- **Status**: In Progress
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
- [ ] Commit raw evidence, finalize all thirteen models, independently replay answers and audit lineage and costs.
- [ ] Recompute public findings and import the sealed source commit into the website.
- [ ] Validate publication, commit/push both repositories, and verify deployed graphs, tables, and source links.

## Decisions and durable findings

The original sealed directory remains immutable. The continuation keeps the same campaign ID and original invocation history under a distinct output-root path; its metadata records the exact source snapshot. The runner already supports alternate output roots and resumes only tasks without a final response. Public copy describes the complete cohort without a historical update narrative; raw timestamps and provenance remain accurate.

## Handoff & Takeover Log

- 2026-09-17: Started by codex on eob-dev2 at the user's request after Anthropic credits were replenished. Website work delegated to `website_survey`; independent continuation review delegated to `layout_audit`.

Continuation path: `results/runs/full-roster/0.3.0/qualitative-20260917`. All 17 copied raw artifacts matched the original sealed hashes before adding explicit lineage to `run.json`; original seal verification passed. Independent review by `layout_audit` confirmed runner/finalizer invariants.

## Execution evidence

The live continuation finished successfully at `2026-09-17T12:10:06.516568+00:00` (exit 0). All thirteen models have 292 answers. Exactly 284 new Claude attempts were appended; the original 3,515 attempt records and 3,512 final answer objects are unchanged. The original seal still verifies. Cumulative ledger: $34.56476570; incremental recorded cost: $3.77238800.

Command: `.venv/bin/python -u -m baseline.runner --release 0.3.0 --config config/models.all.json --output-dir results/runs/full-roster --run-id qualitative-20260917 --models claude-fable-5-1 claude-opus-5 claude-sonnet-5 claude-haiku-4-5-20251001 --concurrency 10 --budget-usd 100`. Runner invocation source: `0ba27f3`, clean.

Focused existing checks at base `0ba27f3`: `.venv/bin/python -m pytest tests/test_finalize_partial.py tests/test_qualitative_audit.py -q` — 13 passed.
