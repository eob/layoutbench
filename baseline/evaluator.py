"""LayoutBench Multi-Attribute Evaluator and Task Grader."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from baseline.providers import PredictionClient, PredictionResponse, LayoutPrediction


def load_manifest(manifest_path: str) -> list[dict]:
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        return data.get("tasks", [])
    if isinstance(data, list):
        return data
    raise ValueError("Manifest must be a JSON object with 'tasks' or a JSON array")


@dataclass
class TaskEvaluationResult:
    task_id: str
    direction_gt: str
    justify_content_gt: str
    align_items_gt: str
    gap_gt: str
    padding_gt: str
    theme: str
    image_path: str
    raw_prediction: str
    predicted_direction: str
    predicted_justify_content: str
    predicted_align_items: str
    predicted_gap: str
    predicted_padding: str
    direction_correct: bool
    justify_content_correct: bool
    align_items_correct: bool
    gap_correct: bool
    padding_correct: bool
    all_correct: bool
    latency_sec: float
    input_tokens: int | None = None
    output_tokens: int | None = None
    request_attempts: int | None = None
    unmetered_attempts: int | None = None
    error: str | None = None
    error_kind: str | None = None
    model_name: str = ""
    provider: str = ""


@dataclass
class LayoutBenchScorecard:
    total_tasks: int
    overall_exact_match: float
    direction_accuracy: float
    justify_content_accuracy: float
    align_items_accuracy: float
    gap_accuracy: float
    padding_accuracy: float
    avg_latency_sec: float
    accuracy_by_theme: Dict[str, Dict[str, float]]
    accuracy_by_direction: Dict[str, Dict[str, float]]
    accuracy_by_gap: Dict[str, Dict[str, float]]
    accuracy_by_padding: Dict[str, Dict[str, float]]
    model_name: str
    timestamp: str
    expected_task_count: int = 0
    grading_version: str = "1"
    provider: str = "google"
    task_results: List[TaskEvaluationResult] = field(default_factory=list)


class BaselineEvaluator:
    def __init__(
        self,
        model_name: str = "gemini-3.5-flash",
        mock: bool = False,
        provider: str = "google",
        api_key_env: str | None = None,
        base_url: str | None = None,
        max_output_tokens: int = 1024,
    ):
        self.model_name = model_name
        self.provider = provider
        self.mock = mock
        self._client = None if mock else PredictionClient(
            provider, model_name, api_key_env=api_key_env,
            base_url=base_url, max_output_tokens=max_output_tokens,
        )

    def close(self) -> None:
        if self._client is not None:
            self._client.close()

    def predict_image(self, image_path: str, prompt: str) -> PredictionResponse:
        if self.mock:
            prediction = {
                "direction": "row",
                "justify_content": "start",
                "align_items": "center",
                "gap": "16px",
                "padding": "24px",
            }
            return PredictionResponse(json.dumps(prediction), prediction, input_tokens=0, output_tokens=0)
        return self._client.predict(image_path, prompt)

    def _eval_single_task(self, item: dict, prompt_default: str) -> TaskEvaluationResult:
        image_path = item["imagePath"]
        prompt = item.get("prompt", prompt_default)

        start_t = time.perf_counter()
        response = self.predict_image(image_path, prompt)
        latency = time.perf_counter() - start_t
        raw_pred = response.raw_text
        parsed_pred = response.parsed if not response.error else {}

        pred_direction = str(parsed_pred.get("direction", "")).strip().lower()
        pred_jc = str(parsed_pred.get("justify_content", "")).strip().lower()
        pred_ai = str(parsed_pred.get("align_items", "")).strip().lower()
        pred_gap = str(parsed_pred.get("gap", "")).strip().lower()
        pred_pad = str(parsed_pred.get("padding", "")).strip().lower()

        gt = item.get("groundTruth", {})
        gt_direction = str(gt.get("direction", "")).strip().lower()
        gt_jc = str(gt.get("justify_content", "")).strip().lower()
        gt_ai = str(gt.get("align_items", "")).strip().lower()
        gt_gap = str(gt.get("gap", "")).strip().lower()
        gt_pad = str(gt.get("padding", "")).strip().lower()
        theme = str(gt.get("theme", "light"))

        direction_correct = pred_direction == gt_direction
        jc_correct = pred_jc == gt_jc
        ai_correct = pred_ai == gt_ai
        gap_correct = pred_gap == gt_gap
        pad_correct = pred_pad == gt_pad

        all_correct = (
            not response.error
            and direction_correct
            and jc_correct
            and ai_correct
            and gap_correct
            and pad_correct
        )

        return TaskEvaluationResult(
            task_id=item["taskId"],
            direction_gt=gt_direction,
            justify_content_gt=gt_jc,
            align_items_gt=gt_ai,
            gap_gt=gt_gap,
            padding_gt=gt_pad,
            theme=theme,
            image_path=image_path,
            raw_prediction=raw_pred,
            predicted_direction=pred_direction,
            predicted_justify_content=pred_jc,
            predicted_align_items=pred_ai,
            predicted_gap=pred_gap,
            predicted_padding=pred_pad,
            direction_correct=direction_correct,
            justify_content_correct=jc_correct,
            align_items_correct=ai_correct,
            gap_correct=gap_correct,
            padding_correct=pad_correct,
            all_correct=all_correct,
            latency_sec=latency,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            request_attempts=response.request_attempts,
            unmetered_attempts=response.unmetered_attempts,
            error=response.error,
            error_kind=response.error_kind,
            model_name=self.model_name,
            provider=self.provider,
        )

    def score_results(self, results: list[TaskEvaluationResult], expected_task_count: int = 0) -> LayoutBenchScorecard:
        total = len(results)
        denom = float(expected_task_count) if expected_task_count > 0 else float(total or 1)

        exact_matches = sum(1 for r in results if r.all_correct)
        direction_matches = sum(1 for r in results if r.direction_correct)
        jc_matches = sum(1 for r in results if r.justify_content_correct)
        ai_matches = sum(1 for r in results if r.align_items_correct)
        gap_matches = sum(1 for r in results if r.gap_correct)
        pad_matches = sum(1 for r in results if r.padding_correct)

        avg_latency = (sum(r.latency_sec for r in results) / total) if total > 0 else 0.0

        def build_slice(key_fn) -> Dict[str, Dict[str, float]]:
            buckets: Dict[str, Dict[str, int]] = {}
            for r in results:
                k = key_fn(r)
                if k not in buckets:
                    buckets[k] = {"total": 0, "exact": 0, "direction": 0}
                buckets[k]["total"] += 1
                if r.all_correct:
                    buckets[k]["exact"] += 1
                if r.direction_correct:
                    buckets[k]["direction"] += 1
            out = {}
            for k, b in buckets.items():
                tot = b["total"]
                out[k] = {
                    "total": tot,
                    "exact_accuracy": round((b["exact"] / tot) * 100, 1) if tot > 0 else 0.0,
                    "direction_accuracy": round((b["direction"] / tot) * 100, 1) if tot > 0 else 0.0,
                }
            return out

        by_theme = build_slice(lambda r: r.theme)
        by_direction = build_slice(lambda r: r.direction_gt)
        by_gap = build_slice(lambda r: r.gap_gt)
        by_padding = build_slice(lambda r: r.padding_gt)

        return LayoutBenchScorecard(
            total_tasks=total,
            overall_exact_match=round((exact_matches / denom) * 100, 2),
            direction_accuracy=round((direction_matches / denom) * 100, 2),
            justify_content_accuracy=round((jc_matches / denom) * 100, 2),
            align_items_accuracy=round((ai_matches / denom) * 100, 2),
            gap_accuracy=round((gap_matches / denom) * 100, 2),
            padding_accuracy=round((pad_matches / denom) * 100, 2),
            avg_latency_sec=round(avg_latency, 3),
            accuracy_by_theme=by_theme,
            accuracy_by_direction=by_direction,
            accuracy_by_gap=by_gap,
            accuracy_by_padding=by_padding,
            model_name=self.model_name,
            timestamp=datetime.now(timezone.utc).isoformat(),
            expected_task_count=expected_task_count or total,
            provider=self.provider,
            task_results=results,
        )
