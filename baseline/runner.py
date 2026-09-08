"""Run LayoutBench model matrix with durable SQLite checkpoints and budget enforcement."""

from __future__ import annotations

import argparse
from collections import deque
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from contextlib import ExitStack, contextmanager
from dataclasses import asdict, fields
import hashlib
import json
import math
from pathlib import Path
import random
import re
import signal
import threading
from typing import Any

from baseline.evaluator import BaselineEvaluator, TaskEvaluationResult, load_manifest
from baseline.model_config import load_model_config
from baseline.run_state import RunStore


def dataset_fingerprint(items: list[dict]) -> str:
    digest = hashlib.sha256(b"layoutbench-grading-1\n")
    for item in sorted(items, key=lambda x: x["taskId"]):
        metadata = {k: v for k, v in item.items() if k not in {"imagePath", "imageFilename"}}
        digest.update(json.dumps(metadata, sort_keys=True, ensure_ascii=False).encode())
        img_p = Path(item["imagePath"])
        if img_p.exists():
            digest.update(hashlib.sha256(img_p.read_bytes()).digest())
    return digest.hexdigest()


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)


@contextmanager
def _run_lock(directory: Path):
    with (directory / ".runner.lock").open("a+b") as lock:
        try:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)
        except (ImportError, BlockingIOError) as e:
            raise RuntimeError(f"Benchmark run is already running: {directory}") from e


def run_benchmark(
    manifest_path: str | Path = "dataset/layoutbench-1/manifest.json",
    config_path: str | Path = "config/models.json",
    output_dir: str | Path = "results/runs",
    run_id: str = "default",
    selected_models: list[str] | None = None,
    budget_usd: float | None = 25.0,
    max_tasks: int | None = None,
    concurrency: int = 3,
    mock: bool = False,
) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", run_id):
        raise ValueError("run_id must be a simple name, without directory separators")
    if budget_usd is not None and (budget_usd < 0 or not math.isfinite(budget_usd)):
        raise ValueError("budget_usd must be finite and non-negative")
    if concurrency < 1 or (max_tasks is not None and max_tasks < 0):
        raise ValueError("concurrency must be positive and max_tasks non-negative")

    models = load_model_config(config_path)
    if selected_models:
        unknown = set(selected_models) - {model["id"] for model in models}
        if unknown:
            raise ValueError(f"Unknown or disabled models: {', '.join(sorted(unknown))}")
        models = [model for model in models if model["id"] in selected_models]
    if not models:
        raise ValueError("No enabled models selected")

    items = load_manifest(str(manifest_path))
    fingerprint = dataset_fingerprint(items)
    items.sort(key=lambda x: x["taskId"])
    selected_items = items[:max_tasks] if max_tasks is not None else items

    directory = Path(output_dir) / (f"mock-{run_id}" if mock else run_id)
    directory.mkdir(parents=True, exist_ok=True)

    with _run_lock(directory), ExitStack() as resources:
        state_path = directory / "state.sqlite3"
        result_fields = {f.name for f in fields(TaskEvaluationResult)}
        clients = {}
        for model in models:
            client = BaselineEvaluator(
                model_name=model["model"],
                provider=model["provider"],
                mock=mock,
                api_key_env=model.get("api_key_env"),
                base_url=model.get("base_url"),
                max_output_tokens=model.get("max_output_tokens", 1024),
            )
            resources.callback(client.close)
            clients[model["id"]] = client

        model_by_id = {model["id"]: model for model in models}
        reserve = {
            model["id"]: 0.0 if mock else (
                (5000 * (model.get("input_per_m") or 1.0) + model.get("max_output_tokens", 1024) * (model.get("output_per_m") or 1.0)) / 1_000_000
            ) for model in models
        }

        with RunStore(state_path) as store:
            store.register_run(
                run_id, fingerprint,
                {"manifest_path": str(Path(manifest_path).resolve()), "mock": mock, "expected_task_count": len(items)}
            )
            for model in models:
                store.register_model(run_id, model["id"], model)

            reported_models = [state["config"] for state in store.model_states(run_id).values()]
            completed = {model["id"]: store.completed_results(run_id, model["id"]) for model in reported_models}
            pending = deque(
                (model["id"], item)
                for item in selected_items
                for model in models
                if item["taskId"] not in completed[model["id"]]
            )
            blocked_providers: set[str] = set()
            blocked_models: set[str] = set()
            status = "running"
            scorecards = {}
            attempted_ids = {model["id"]: set(store.results(run_id, model["id"])) for model in reported_models}

            def snapshot(changed_model_id: str | None = None) -> dict:
                state = store.model_states(run_id)
                summary = {
                    "run_id": run_id,
                    "dataset_fingerprint": fingerprint,
                    "mock": mock,
                    "expected_task_count": len(items),
                    "budget_usd": budget_usd,
                    "spent_cost_usd": store.spent_cost(run_id),
                    "status": status,
                    "models": {},
                }
                for model in reported_models:
                    m_id = model["id"]
                    saved = completed[m_id]
                    if changed_model_id is None or changed_model_id == m_id:
                        eval_results = [
                            TaskEvaluationResult(**{k: v for k, v in res.items() if k in result_fields})
                            for res in saved.values()
                        ]
                        scorer = clients.get(m_id) or next(iter(clients.values()))
                        scorecard = asdict(scorer.score_results(eval_results, len(items)))
                        scorecard.pop("task_results", None)
                        scorecard["tasks"] = list(saved.values())
                        scorecard.update(
                            mock=mock,
                            dataset_fingerprint=fingerprint,
                            model_id=m_id,
                            model_name=model["model"],
                            display_name=model.get("display_name", m_id),
                            provider=model["provider"],
                            pricing={
                                "input_per_m": model.get("input_per_m"),
                                "output_per_m": model.get("output_per_m"),
                            },
                        )
                        write_json(directory / f"scorecard_{m_id}.json", scorecard)
                        scorecards[m_id] = scorecard

                    scorecard = scorecards[m_id]
                    cur = state.get(m_id, {})
                    summary["models"][m_id] = {
                        "provider": model["provider"],
                        "model": model["model"],
                        "display_name": model.get("display_name", m_id),
                        "completed": len(saved),
                        "attempted_tasks": len(attempted_ids[m_id]),
                        "status": "complete" if len(saved) == len(items) else cur.get("status", "pending"),
                        "cost_usd": store.spent_cost(run_id, m_id),
                        "all_correct_accuracy": scorecard["overall_exact_match"],
                        "direction_accuracy": scorecard["direction_accuracy"],
                        "justify_content_accuracy": scorecard["justify_content_accuracy"],
                        "align_items_accuracy": scorecard["align_items_accuracy"],
                        "gap_accuracy": scorecard["gap_accuracy"],
                        "padding_accuracy": scorecard["padding_accuracy"],
                        "avg_latency_sec": scorecard["avg_latency_sec"],
                    }
                write_json(directory / "summary.json", summary)
                return summary

            interrupted = False
            interruption_signal = signal.SIGINT
            fatal_error: Exception | None = None

            def request_stop(signum, frame):
                nonlocal interrupted, interruption_signal
                interrupted = True
                interruption_signal = signum

            if threading.current_thread() is threading.main_thread():
                for stop_signal in (signal.SIGINT, signal.SIGTERM):
                    prev = signal.signal(stop_signal, request_stop)
                    resources.callback(signal.signal, stop_signal, prev)

            snapshot()
            running = {}
            reserved_cost = 0.0

            def checkpoint(future):
                nonlocal reserved_cost, fatal_error, status
                m_id, task_id, req_reserve = running.pop(future)
                reserved_cost -= req_reserve
                model = model_by_id[m_id]
                worker_failed = False
                try:
                    eval_result = future.result()
                    res_dict = asdict(eval_result)
                except Exception as error:
                    worker_failed = True
                    fatal_error = fatal_error or error
                    status = "failed"
                    pending.clear()
                    res_dict = {
                        "task_id": task_id,
                        "model_name": model["model"],
                        "provider": model["provider"],
                        "error": f"{type(error).__name__}: {error}",
                        "error_kind": "other",
                    }

                if mock:
                    res_dict["cost_usd"] = 0.0
                elif worker_failed:
                    res_dict["cost_usd"] = req_reserve
                else:
                    in_m = model.get("input_per_m") or 0.0
                    out_m = model.get("output_per_m") or 0.0
                    metered = ((res_dict.get("input_tokens") or 0) * in_m + (res_dict.get("output_tokens") or 0) * out_m) / 1_000_000
                    res_dict["cost_usd"] = metered

                store.save_result(run_id, m_id, task_id, res_dict)
                failure = res_dict.get("error_kind")
                attempted_ids[m_id].add(task_id)

                if not res_dict.get("error") or failure == "invalid_response":
                    completed[m_id][task_id] = res_dict

                if failure in {"credits", "authentication", "rate_limit"}:
                    blocked_providers.add(model["provider"])
                    for sib in models:
                        if sib["provider"] == model["provider"]:
                            store.save_model_state(run_id, sib["id"], "paused", res_dict.get("error"))
                elif res_dict.get("error") and failure != "invalid_response":
                    blocked_models.add(m_id)
                    store.save_model_state(run_id, m_id, "paused", res_dict.get("error"))

                status_label = "all_correct" if res_dict.get("all_correct") else ("error: " + str(failure) if failure else "miss")
                print(f"[{m_id}] {task_id}: {status_label} | total spent: ${store.spent_cost(run_id):.4f}", flush=True)
                snapshot(m_id)

            with ThreadPoolExecutor(max_workers=concurrency) as pool:
                while pending or running:
                    try:
                        if interrupted or fatal_error:
                            pending.clear()
                        while pending and len(running) < concurrency and not interrupted:
                            m_id, item = pending.popleft()
                            model = model_by_id[m_id]
                            if m_id in blocked_models or model["provider"] in blocked_providers:
                                continue
                            req_reserve = 2 * (reserve[m_id] or 0.0)
                            if budget_usd is not None and store.spent_cost(run_id) + req_reserve > budget_usd + 1e-9:
                                status = "budget_exhausted"
                                blocked_models.add(m_id)
                                store.save_model_state(run_id, m_id, "budget_exhausted", "Increase --budget-usd")
                                continue
                            if budget_usd is not None and store.spent_cost(run_id) + reserved_cost + req_reserve > budget_usd + 1e-9:
                                pending.appendleft((m_id, item))
                                break
                            store.save_model_state(run_id, m_id, "running")
                            future = pool.submit(clients[m_id]._eval_single_task, item, item.get("prompt", ""))
                            running[future] = (m_id, item["taskId"], req_reserve)
                            reserved_cost += req_reserve

                        if not running:
                            break
                        done, _ = wait(running, return_when=FIRST_COMPLETED)
                        for fut in done:
                            checkpoint(fut)
                    except KeyboardInterrupt:
                        interrupted = True
                    except Exception as error:
                        fatal_error = fatal_error or error
                        status = "failed"
                        pending.clear()

            if fatal_error:
                status = "failed"
            elif interrupted:
                status = "interrupted"
            elif all(len(completed[m["id"]]) == len(items) for m in models):
                status = "complete"

            for model in models:
                m_id = model["id"]
                if len(completed[m_id]) == len(items):
                    store.save_model_state(run_id, m_id, "complete")

            summary = snapshot()
            if fatal_error:
                raise fatal_error
            return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="dataset/layoutbench-1/manifest.json")
    parser.add_argument("--config", default="config/models.json")
    parser.add_argument("--output-dir", default="results/runs")
    parser.add_argument("--run-id", default="default")
    parser.add_argument("--models", nargs="+")
    parser.add_argument("--budget-usd", type=float, default=25.0)
    parser.add_argument("--no-budget-limit", action="store_true")
    parser.add_argument("--max-tasks", type=int)
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--mock", action="store_true")
    args = parser.parse_args()

    summary = run_benchmark(
        manifest_path=args.manifest,
        config_path=args.config,
        output_dir=args.output_dir,
        run_id=args.run_id,
        selected_models=args.models,
        budget_usd=None if args.no_budget_limit else args.budget_usd,
        max_tasks=args.max_tasks,
        concurrency=args.concurrency,
        mock=args.mock,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
