"""LayoutBench baseline evaluation: load frozen tasks, query models, grade answers."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from baseline.protocol import CHOICE_FAMILIES, NUMERIC_KEYS, grade_prediction, parse_prediction
from baseline.providers import PredictionClient, PredictionResponse

GRADING_VERSION = "1"

PROTOCOL_FILES = ("prompts.json", "protocol.py", "evaluator.py", "statistics.py",
                  "reporting.py", "validate_dataset.py", "finalize.py")


def evaluation_protocol_fingerprint() -> str:
    digest = hashlib.sha256(b"layoutbench-protocol-1\n")
    for name in PROTOCOL_FILES:
        digest.update(Path(__file__).with_name(name).read_bytes())
    return digest.hexdigest()


def cohort_fingerprint(task_ids: list[str]) -> str:
    return hashlib.sha256(json.dumps(sorted(task_ids)).encode()).hexdigest()


def load_manifest(manifest_path: str) -> list[dict]:
    """Read tasks and resolve each image filename to an existing file path."""
    manifest = Path(manifest_path)
    try:
        items = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError(f"Cannot load LayoutBench manifest {manifest_path}: {error}") from error
    if not isinstance(items, list) or not items:
        raise ValueError("LayoutBench manifest must be a nonempty array")
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Manifest tasks must be objects")
        for key in ("taskId", "family", "groupId", "imageFilename", "groundTruth", "prompt"):
            if key not in item:
                raise ValueError(f"Manifest task is missing {key}")
        image = (manifest.parent / item["imageFilename"]).resolve()
        if not image.is_file() or image.suffix.lower() != ".png":
            raise ValueError(f"Task image is not a PNG file: {item['taskId']}")
        item["imagePath"] = str(image)
    return items


@dataclass
class TaskEvaluationResult:
    task_id: str = ""
    family: str = ""
    group_id: str = ""
    ground_truth: dict = field(default_factory=dict)
    prompt_sha256: str = ""
    image_path: str = ""
    raw_prediction: str = ""
    prediction: dict = field(default_factory=dict)
    valid: bool = False
    correct: bool | None = None
    score: float = 0.0
    tight_score: float | None = None
    err: float | None = None
    key_errors: dict | None = None
    within_bands: dict | None = None
    latency_sec: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    request_attempts: int = 0
    unmetered_attempts: int = 0
    error: str | None = None
    error_kind: str | None = None
    model_name: str = ""
    provider: str = ""


@dataclass
class LayoutBenchScorecard:
    total_tasks: int
    expected_task_count: int
    families: dict
    avg_latency_sec: float | None
    model_name: str
    provider: str
    timestamp: str
    grading_version: str
    evaluation_protocol: str
    cohort_sha256: str
    status: str
    task_results: list[TaskEvaluationResult] = field(default_factory=list)


MOCK_PREDICTIONS = {
    "flow": {"choice": "A"},
    "distribute": {"choice": "A"},
    "align": {"choice": "A"},
    "gap": {"choice": "A"},
    "pad": {"choice": "A"},
    "columns": {"choice": "A"},
    "textjustify": {"choice": "A"},
    "headerpad": {"choice": "A"},
    "regionpad": {"choice": "A"},
    "tablepad": {"choice": "A"},
    "gapnum": {"gap_px": 16},
    "headerpx": {"above_px": 16, "below_px": 16},
    "regionpx": {"pad_px": 16},
}


class BaselineEvaluator:
    def __init__(self, model_name="gemini-2.5-flash", mock=False, provider="google",
                 api_key_env=None, base_url=None, max_output_tokens=1024):
        self.model_name, self.mock, self.provider = model_name, mock, provider
        self._client = None if mock else PredictionClient(provider, model_name, api_key_env=api_key_env,
                                                          base_url=base_url, max_output_tokens=max_output_tokens)

    def close(self):
        if self._client is not None:
            self._client.close()

    def predict_image(self, image_path: str, prompt: str, family: str) -> PredictionResponse:
        if self.mock:
            prediction = MOCK_PREDICTIONS[family]
            return PredictionResponse(json.dumps(prediction), prediction, input_tokens=0, output_tokens=0)
        return self._client.predict(image_path, prompt, family)

    def _eval_single_task(self, item: dict, prompt_default: str = "") -> TaskEvaluationResult:
        prompt = item.get("prompt", prompt_default)
        start = time.perf_counter()
        response = self.predict_image(item["imagePath"], prompt, item["family"])
        latency = time.perf_counter() - start
        parsed = None
        if not response.error:
            try:
                parsed = parse_prediction(response.raw_text, item["family"])
            except ValueError as error:
                response.error, response.error_kind = str(error), "invalid_response"
        return TaskEvaluationResult(task_id=item["taskId"], family=item["family"], group_id=item["groupId"],
                                    ground_truth=item["groundTruth"], prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),
                                    image_path=item["imagePath"], raw_prediction=response.raw_text, prediction=parsed or {},
                                    **grade_prediction(item["family"], parsed, item["groundTruth"]), latency_sec=latency,
                                    input_tokens=response.input_tokens, output_tokens=response.output_tokens,
                                    request_attempts=response.request_attempts, unmetered_attempts=response.unmetered_attempts,
                                    error=response.error, error_kind=response.error_kind,
                                    model_name=self.model_name, provider=self.provider)

    def score_results(self, results: list[TaskEvaluationResult], expected_task_count: int = 0) -> LayoutBenchScorecard:
        from baseline.statistics import metrics
        observed = [result for result in results if not result.error or result.error_kind == "invalid_response"]
        total = len(observed)
        expected = expected_task_count or total
        latencies = [row.latency_sec for row in observed]
        latency = sum(latencies) / total if total and all(value is not None for value in latencies) else None
        return LayoutBenchScorecard(total_tasks=total, expected_task_count=expected, families=metrics([asdict(row) for row in observed]),
                                   avg_latency_sec=latency, model_name=self.model_name, provider=self.provider,
                                   timestamp=datetime.now(timezone.utc).isoformat(), grading_version=GRADING_VERSION,
                                   evaluation_protocol=evaluation_protocol_fingerprint(),
                                   cohort_sha256=cohort_fingerprint([row.task_id for row in observed]),
                                   status="complete" if total == expected else "partial", task_results=observed)
