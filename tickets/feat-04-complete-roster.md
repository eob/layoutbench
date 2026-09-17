# feat-04-complete-roster: Publish all thirteen model configurations

- **Status**: In Progress
- **Branch**: `feat-04-complete-roster`
- **Machine**: eob-dev2
- **Harness**: codex
- **Session ID**: `01a0ad34-d16c-7a82-b973-d59084daaf32`
- **PR**: Pending
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

- [ ] Preserve the original seal; verify a separate continuation checkpoint has identical historical answers and attempts.
- [ ] Execute only the 284 missing Claude answers using unchanged release, protocol, model settings, and cumulative budget.
- [ ] Commit raw evidence, finalize all thirteen models, independently replay answers and audit lineage and costs.
- [ ] Recompute public findings and import the sealed source commit into the website.
- [ ] Validate publication, commit/push both repositories, and verify deployed graphs, tables, and source links.

## Decisions and durable findings

The original sealed directory remains immutable. The continuation keeps the same campaign ID and original invocation history under a distinct output-root path; its metadata records the exact source snapshot. The runner already supports alternate output roots and resumes only tasks without a final response. Public copy describes the complete cohort without a historical update narrative; raw timestamps and provenance remain accurate.

## Handoff & Takeover Log

- 2026-09-17: Started by codex on eob-dev2 at the user's request after Anthropic credits were replenished. Website work delegated to `website_survey`; independent continuation review delegated to `layout_audit`.
