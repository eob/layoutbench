# Offline finalization

Finish the runner, close its SQLite checkpoint, and commit the run evidence before sealing it. Finalization makes no provider requests and does not rewrite saved responses.

```sh
git add -f results/runs/0.3.0/qualitative-20260917
git commit -m "Record LayoutBench pilot observations"
.venv/bin/python -m baseline.finalize --run-dir results/runs/0.3.0/qualitative-20260917 --scope full
.venv/bin/python -m baseline.finalize --run-dir results/runs/0.3.0/qualitative-20260917 --verify
```

`full` requires every selected model to have all release questions. `common` publishes the explicit intersection of final task IDs, with a cohort fingerprint, and marks coverage partial. `--models` can fix a subset of recorded model IDs. Responses outside the publication cohort remain in the evidence. If an account is unavailable, select the complete model IDs with `--models`; the full requested roster, availability status/reason and every infrastructure attempt remain in the sealed report. Unavailable models have null accuracy and are excluded from the comparison, not scored as wrong. No cross-family aggregate score is computed.

For each choice family, accuracy includes invalid responses in its denominator and reports the available-option chance rate (16.7%, 25%, 33.3%, or 50% in 0.3.0). Archived numeric families each receive a separate mean bounded score over all responses, with invalid responses scored zero. The documented score is `100 * (1 - min(err_px / 16, 1))`; it is an engineering normalization, not a just-noticeable-difference threshold. Tight scores use a 4px ceiling, and within-band flags mark estimates within 1, 2, 4, and 8px (for two-key header estimates, a flag means both sides are within the band). Mean, median and linearly interpolated p90 px errors describe valid predictions only and appear beside validity counts.

Costs and latency use the same responses as each model or family score. API-response costs require complete metered tokens and recorded prices; any unknown measurement makes that mean null. Campaign spending also retains separate infrastructure attempts and estimated budget reserves, whose count is published.

The finalizer independently reconciles SQLite, the attempt export, scorecards, invocation timestamps, model configurations, per-model costs, and the committed source checkpoint. It reparses raw answers using the expected task family and recomputes grades and report metrics. `final_results.json` records the cohort, per-family results and source rows. `finalization.json` hashes the checkpoint, ledgers, scorecards, metadata, and report. Verification replays these checks instead of merely trusting the hash list.

Either finalization artifact prevents resuming that run. A finalized scope or roster cannot change. An interrupted seal with only `final_results.json` requires inspection; the tool fails closed rather than silently replacing it. Shared images retain their groups and are not treated as independent observations for confidence intervals.
