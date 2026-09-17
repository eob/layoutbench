# Frozen releases

The current release is **0.3.0**, with 292 qualitative questions in 20 families and 250 unique images. Human agreement has not been measured. See [the methodology](../docs/methodology.md) and [question catalog](../config/qualitative.json).

A descriptor records `schema_version`, `benchmark_version`, `dataset_path`, `dataset_manifest`, `dataset_git_commit`, `dataset_fingerprint`, `evaluation_protocol_fingerprint`, and `expected_task_count`. Commit the validated dataset before creating its descriptor. The dataset fingerprint covers manifest content and actual PNG bytes. The release gate verifies committed artifact bytes, exact inventory, prompts, geometry-derived answers, complete options, label balance, nuisance crossings, font usage, image sharing and decoded-image evidence.

The protocol fingerprint covers answer contracts, parsing, grading, prompts, provider request code, statistics, reporting, finalization, and both dataset validators, including `config/qualitative.json`. Protocol changes require freezing a new compatible release before more paid observations.

```sh
bun run validate
.venv/bin/python -m baseline.releases --release 0.3.0
.venv/bin/python -m baseline.runner --release 0.3.0 --config config/models.all.json --run-id qualitative-20260917 --concurrency 6 --budget-usd 100
```

The combined catalog has 13 enabled configurations across four API accounts. Metadata preserves configuration, recorded rates, endpoint timeouts, source commit and invocation chronology without storing API keys. The budget reserves output costs before dispatch; unknown usage is explicitly estimated and cannot become a reported metered mean.

Resume partial work with the same ID and unchanged release/configuration. Invalid answers are final observations scored incorrect; infrastructure failures remain retryable and retain every attempt. Frozen runs cannot resume once sealed. Publication selects an explicit verified seal, never the newest-looking file. See [FINALIZATION.md](FINALIZATION.md).

Archived releases retain their own immutable datasets, descriptors and response evidence. Replay requires the compatible source checkout recorded by their seal; current code deliberately refuses a mismatched protocol.
