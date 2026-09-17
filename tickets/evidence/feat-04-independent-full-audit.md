# Independent thirteen-model continuation audit

The completed continuation preserves the original campaign and produces a
complete thirteen-model comparison. Independent raw replay and committed-seal
verification found no discrepancies. This audit uses only the Python standard
library and imports no benchmark parser, grader, statistics, or finalizer.

The audited continuation is
`results/runs/full-roster/0.3.0/qualitative-20260917`, sealed in commit
`811dbd016689132a51ec1ffe80de7225751af095`. Its original source is
`results/runs/0.3.0/qualitative-20260917`, sealed in commit
`ac17659d69c5c8fbd60abfade2b14edb06826b86`.

| Independently verified invariant | Result |
| --- | --- |
| Original artifacts and seal | All original artifact hashes and committed bytes unchanged |
| Historical ledger | Original 3,515 attempts remain an exact JSONL byte prefix and exact SQLite value prefix, including serialized result JSON |
| Historical final answers | All 3,512 original SQLite `result_json` strings unchanged, including whitespace |
| Appended work | Exactly 284 attempts and 284 final answers, restricted to the original missing Claude task set |
| Invocation lineage | Original invocation retained; new invocation lists only the four Claude configurations with unchanged settings, timeout limits, and cumulative budget; timestamps fall within model invocations |
| Frozen inputs | Dataset, every PNG hash, protocol, release descriptor, model catalog, and archived model configurations match the original |
| Complete comparison | All thirteen models have all 292 questions: 3,796 final answers; zero malformed final answers |
| Retained campaign ledger | 3,799 runner attempts and 3,802 HTTP requests; three historical credit errors retained |
| New requests | 284 HTTP requests; no new infrastructure failures or unmetered requests |
| Published report | Full thirteen-model cohort, all twenty family metrics, confusion counts, chance baselines, grouping, latency, and cost coverage replay |
| New seal | Exact eighteen-artifact inventory and hashes match committed bytes; raw artifacts also match the raw source checkpoint; finalizer source is clean |

The frozen dataset fingerprint is
`fc531bdb2e7c9d10e2074519bd3e0d0f66bc8ec970d20f25cdb628054784c6de`;
the evaluation protocol fingerprint is
`deed0698dca65b5e24f3b06766d2d5344bbf0964e871167cebfc5e4aaba554fa`.

Reported token counts and configured rates give a cumulative **$33.99419170**
metered estimate. The original six unmetered HTTP requests retain their
**$0.57057400** reserve allowances, yielding a **$34.56476570** ledger total.
The continuation adds **$3.77238800**, entirely from reported token usage.
These are rate estimates and conservative budget reserves, not provider
invoices. The JSON preserves the insignificant floating-point residue in
stored ledger amounts. The three affected Gemini family cost means remain
null because their original successful requests included unmetered retries.

The script accepts explicit run paths, original and new sealed commits, and
an output path. Reproduce without inference requests:

```sh
.venv/bin/python tickets/evidence/feat-04-audit-controls.py
.venv/bin/python tickets/evidence/feat-04-independent-full-audit.py \
  --sealed-commit 811dbd016689132a51ec1ffe80de7225751af095 \
  --out /tmp/layoutbench-full-roster-audit.json
```

Eight isolated lineage controls cover a valid append, changed and reordered
prefixes, equivalent-but-rewritten historical JSON, missing original answers,
repeated completed tasks, unrequested models, and truncated history. They fail
before the lineage checker exists, pass with it, and fail again when it is
removed from a temporary copy. Nine strict-answer parser controls also pass
in the complete audit. Adjacent red, reversion, and green logs retain the
evidence. The final script removes unused imports and the earlier optional-seal
branch: this audit requires the completed continuation and its seal.

This audit establishes preservation and reproducibility from retained inputs,
responses, usage, and commits. It does not independently recover provider
envelopes, verify provider identity through external records, reconcile
invoices, or reconstruct individual internal retry errors. The existing
human-agreement, synthetic-scope, and count/content-cue limitations remain;
this continuation introduces no additional methodological publication blocker.
