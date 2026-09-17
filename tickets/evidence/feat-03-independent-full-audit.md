# Independent final raw-run and seal audit

Audited the live campaign `qualitative-20260917` after terminal exit, against
sealed artifact commit `ac17659d69c5c8fbd60abfade2b14edb06826b86` and raw
checkpoint `cb46d35ccc1f411b2aa23376adfd37b4c3baa8cb`. The standard-library
audit script imports no benchmark parser, grader, statistics, or finalizer.
It completed with no discrepancies and `seal_checked: true`.

| Independently replayed item | Result |
| --- | --- |
| Frozen inputs | 292 questions, 250 PNGs; committed manifest, every image SHA, dataset and protocol fingerprints match |
| Raw ledger | SQLite integrity passes; 3,515 runner attempts exactly match JSONL and latest checkpoint rows |
| Final responses | 3,512 strict JSON responses; no invalid final answers; every choice, score, source attempt, prompt, image, and task identity replays |
| Full comparison | Nine models each cover all 292 questions: 2,628 responses |
| Retained partial observations | Four Claude models each have 221 responses: 884 retained and excluded from the full comparison |
| Infrastructure | Three recorded credit errors; no other infrastructure error class; 3,518 HTTP requests in retained usage accounting |
| Published families | All 20 families, confusion counts, validity, chance, group counts, latency, and cost coverage replay |
| Seal and provenance | Exact 18-artifact inventory and hashes match committed bytes; 17 raw artifacts also match the committed raw checkpoint; seal bytes match the sealed commit |

The full cohort comprises Gemini 3.1 Pro Preview, Gemini 3.5 Flash Lite,
Gemini 3.8 Flash, GPT-5.6 Luna/Sol/Terra, GPT-6 Astra, and Muse Spark 1.2/1.3.
Fable, Opus, and Sonnet encountered credit errors at `groupgap-009`;
Haiku was paused through the shared Anthropic account scope. All 13 requested
models remain represented in the published availability and retained raw data.

Reported token usage and configured rates give a **$30.22180370** metered
subtotal. Six HTTP requests lack usage, contributing **$0.57057400** in
conservative reserve allowances and a **$30.79237770** ledger total. These
are rate estimates and budget reserves, not provider invoices. The JSON
preserves the small binary-float residue in the sum of stored ledger values.
Three successful Gemini responses contain an unmetered internal retry; the
affected family mean-cost fields correctly remain null. Three other unmetered
requests are the credit failures. `summary.cost_incomplete: false` means the
ledger has a numeric amount for each attempt; it does not establish complete
provider usage or billing information.

Nine parser controls cover valid normalization, empty and multi-letter
choices, out-of-range choices, nonstring choices, duplicate keys, and extra
keys. Empty-choice rejection failed before the single-character guard and
failed again with that guard removed from a temporary copy; the final full
audit passes. See the adjacent red, reversion, and green logs.

Reproduce without inference requests:

```sh
.venv/bin/python tickets/evidence/feat-03-independent-full-audit.py /tmp/layoutbench-independent-final-audit.json
```

The independent replay uses retained response text, reported usage, and frozen
inputs. It cannot independently recover provider response envelopes, establish
provider identity from external records, reconcile invoices, or reconstruct
individual internal retry errors. Existing methodology limitations remain:
human agreement was not measured, synthetic observations do not establish
transfer to general interfaces, and exact content repetition in the three
count families permits nonspatial cues. The audit supplies no evidence that
models used those cues. No additional methodological publication blocker was
found within this review.
