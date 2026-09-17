"""The spatial campaign uses the same native and Meta roster as its siblings."""

from collections import Counter
import json
from pathlib import Path

import pytest

from baseline.model_config import load_model_config
from test_model_config import MODEL, catalog


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_IDS = {
    "claude-fable-5-1", "claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5-20251001",
    "gpt-6-astra", "gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna",
    "gemini-3.1-pro-preview", "gemini-3.8-flash", "gemini-3.5-flash-lite",
    "muse-spark-1.2", "muse-spark-1.3",
}


def test_combined_catalog_contains_every_requested_configuration():
    path = ROOT / "config/models.all.json"
    assert path.is_file(), "The thirteen-model campaign catalog is missing"
    models = load_model_config(path)
    assert {model["id"] for model in models} == EXPECTED_IDS
    assert Counter(model["provider"] for model in models) == {"anthropic": 4, "openai": 6, "google": 3}
    legacy = json.loads((ROOT / "config/models.json").read_text())["models"]
    assert [model for model in json.loads(path.read_text())["models"] if not model["id"].startswith("muse-")] == legacy
    meta = [model for model in models if model["id"].startswith("muse-")]
    assert all(model["base_url"] == "https://api.meta.ai/v1"
               and model["max_output_tokens"] == 16384 and model["api_key_env"] == "MODEL_API_KEY"
               for model in meta)


def test_native_openai_and_meta_have_independent_endpoint_limits(tmp_path):
    native = [{**MODEL, "id": f"native-{index}"} for index in range(4)]
    meta = [{**MODEL, "id": f"meta-{index}", "base_url": "https://api.meta.ai/v1"} for index in range(2)]
    assert len(load_model_config(catalog(tmp_path, native + meta))) == 6


def test_explicit_default_endpoint_and_trailing_slash_cannot_bypass_limit(tmp_path):
    rows = [{**MODEL, "id": f"native-{index}"} for index in range(4)]
    rows += [{**MODEL, "id": "explicit", "base_url": "https://api.openai.com/v1"},
             {**MODEL, "id": "slash", "base_url": "https://api.openai.com/v1/"}]
    with pytest.raises(ValueError, match="five"):
        load_model_config(catalog(tmp_path, rows))
