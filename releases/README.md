# Frozen releases

`0.1.0` is a 208-question perception pilot in 13 families: abstract flow
(16), axis distribution (20), cross-axis alignment (16), gap tokens
(16), and container padding (16); document column counting (12), text
justification (16), header above/below comparison (18), content-region
padding with bordered-card vs bare-canvas crossing (16), and table cell
padding (12); plus numeric gap (16), header above/below (18), and
region padding (16) estimates that share images with their choice
siblings. The 8 intersecting columns/justification cells also share one
render each. There are 150 distinct images. Human agreement has not
been measured. Scores never transfer across releases.

Cost basis: a full 0.1.0 campaign is 2,288 responses (208 × 11 models)
at catalog prices, estimated ≈$15 under the $25 budget cap. The runner
reserves worst-case output cost per request before sending.

A descriptor records `schema_version`, `benchmark_version`,
`dataset_path`, `dataset_manifest`, `dataset_git_commit`,
`dataset_fingerprint`, `evaluation_protocol_fingerprint`, and
`expected_task_count`. Freeze the dataset in Git before creating the
descriptor. The dataset fingerprint covers every manifest property
except location fields and hashes actual PNG bytes. The release gate
checks committed artifact bytes and inventory, canonical prompts,
decoded spacing targets, option uniqueness and balance, alignment
decodes from line rects, repeated-group identity, bundled font
evidence, and background/border pixel probes.

The protocol fingerprint includes the family schemas, numeric score
definition, prompts, parser, evaluator, statistics, reporting, and
dataset validation. Any change requires a new protocol release.

```sh
.venv/bin/python -m baseline.validate_dataset
.venv/bin/python -m baseline.releases --release 0.1.0
.venv/bin/python -m baseline.runner --release 0.1.0 --run-id pilot-20260913 --max-tasks 208 --concurrency 6 --budget-usd 25
```

The catalog contains 11 enabled configurations: four Anthropic, four
OpenAI, and three Google models. Pricing dates and official source
links remain attached to each catalog. Run metadata preserves
configurations, endpoint timeouts, source commits, invocation
chronology, and an optional Anthropic workspace ID, without storing
API keys.

Partial work can resume with the same run ID and unchanged identity.
Invalid model answers are final observations and receive zero credit;
infrastructure failures remain retryable, with prior attempt costs
retained. The budget uses conservative reservations for unmetered
attempts, marked `cost_estimated`. Those reserves never become
reported mean API-response costs. Reports show unknown means as null
and retain known-value counts. Paid work is refused if frozen
artifacts or the protocol differ.

Historical prototype artifacts (the 100-task corpus whose titles
printed answers into pixels) remain historical. They are not eligible
for pilot comparisons. Publication accepts an explicitly named,
verified sealed run rather than selecting scorecards by file
modification time. See [FINALIZATION.md](FINALIZATION.md).
