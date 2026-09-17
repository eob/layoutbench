# Thirteen-model inventory and read-only readiness

Base revision: `80b30a11ca413c8ce240c51c1eba63f92ba972d7`.

`config/models.all.json` is byte-identical to ColorBench's combined catalog at
`55204df`. The original eleven-model `config/models.json` remains unchanged.
The combined catalog adds the two Muse configurations with their recorded
16,384-token output limits and Meta endpoint. Campaign callers must select
`--config config/models.all.json`.

The existing catalog loader counted all OpenAI-compatible services as one
provider, rejecting four native OpenAI plus two Meta configurations. Counting
the provider and canonical endpoint permits the intended roster while retaining
the five-model bound per endpoint. The default endpoint and an explicitly
specified equivalent endpoint share the same limit. Runner and provider
implementations were not changed.

| Gate | Result |
| --- | --- |
| New inventory tests against base | 2 failed as intended: missing combined catalog and provider-only limit; 1 passed |
| Temporary reversion with tests retained | Same two failures; implementation restored |
| `pytest tests/test_model_inventory.py tests/test_model_config.py -q` | 27 passed |
| Combined catalog SHA-256 comparison | Both files `7926c195c48349f00ecdacb0cd01a5171149f920cb499f35449b98f10e313451` |
| Authenticated GET model listings | HTTP 200 from OpenAI, Anthropic, Google, and Meta; all thirteen configured IDs listed |

The adjacent red, reversion, and green logs preserve verbatim test output.
`feat-03-model-readiness.json` records sanitized observations from September 17,
2026. API keys were read from existing environment variables; only presence
booleans were recorded. No credential values or response bodies were retained,
and no paid inference requests were made. Listings establish neither available
credits nor successful vision inference. Anthropic workspace override was absent.

The simplification pass retained the narrow loader fix and three complementary
inventory tests; no provider abstractions or extra configuration layers were added.
