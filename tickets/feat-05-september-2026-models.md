# feat-05-september-2026-models: Add September 22 model observations

- **Status**: In Progress
- **Branch**: `main` (direct repository delivery requested)
- **Machine**: `layoutbench` workspace
- **Harness**: `codex`
- **Assignee**: Edward Benson

## Goal

Run the frozen LayoutBench 0.3.0 release only on GPT-6 Sol, GPT-6 Luna and Claude Opus 5.5, then publish sealed response evidence to this repository.

## Scope and sources

- OpenAI announced `gpt-6-sol` and `gpt-6-luna` on September 22, 2026: <https://developers.openai.com/api/docs/changelog>.
- Anthropic lists `claude-opus-5-5` with $4/$20 per million input/output tokens: <https://platform.claude.com/docs/en/models/overview>.
- Use `config/models.20260922.json` to select exactly these three models. Preserve the current 0.3.0 dataset, prompts, renderer, grading, evaluation protocol and previous model data.

## Red evidence

Before adding the new catalog, `load_model_config` found all three IDs absent from both `config/models.json` and `config/models.all.json`:

```text
config/models.json missing= ['claude-opus-5-5', 'gpt-6-luna', 'gpt-6-sol'] enabled_count= 11
config/models.all.json missing= ['claude-opus-5-5', 'gpt-6-luna', 'gpt-6-sol'] enabled_count= 13
```

## Execution and validation

1. Validate the three-model catalog and the existing release without changing the benchmark.
2. Run all 292 questions for only the three new models with a distinct run ID and a bounded budget.
3. Commit the complete checkpoint, finalize a full cohort and verify its seal.
4. Push the model catalog and sealed run evidence to this repository.

## Gate matrix and findings

Pending run completion.
