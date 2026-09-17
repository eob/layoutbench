"""Run LayoutBench model matrix with durable SQLite checkpoints and budget enforcement."""

from __future__ import annotations

import argparse
from collections import deque
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from contextlib import ExitStack, contextmanager
from dataclasses import asdict, fields
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import signal
import threading
from typing import Any

import httpx

from baseline.evaluator import GRADING_VERSION, BaselineEvaluator, TaskEvaluationResult, evaluation_protocol_fingerprint, load_manifest
from baseline.model_config import load_model_config
from baseline.providers import PROVIDERS
from baseline.releases import (
    DEFAULT_RELEASE,
    git_code_identity,
    load_release,
    model_config_fingerprint,
    release_manifest_path,
    validate_release,
)
from baseline.run_state import RunStore
from baseline.validate_dataset import require_valid_dataset

META_API_BASE_URL = "https://api.meta.ai/v1"
META_REQUEST_TIMEOUT = 300.0


def dataset_fingerprint(items: list[dict]) -> str:
    digest = hashlib.sha256(b"layoutbench-dataset-1\n")
    for item in sorted(items, key=lambda x: x["taskId"]):
        metadata = {k: v for k, v in item.items() if k not in {"imagePath", "imageFilename"}}
        digest.update(json.dumps(metadata, sort_keys=True, ensure_ascii=False, allow_nan=False).encode())
        digest.update(hashlib.sha256(Path(item["imagePath"]).read_bytes()).digest())
    return digest.hexdigest()


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)


@contextmanager
def _run_lock(directory: Path):
    import fcntl
    with (directory / ".runner.lock").open("a+b") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError(f"Benchmark run is already running: {directory}") from error
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def run_benchmark(
    manifest_path: str | Path | None = None,
    config_path: str | Path = "config/models.all.json",
    output_dir: str | Path = "results/runs",
    run_id: str | None = None,
    release: str | None = None,
    selected_models: list[str] | None = None,
    budget_usd: float | None = 25.0,
    max_tasks: int | None = None,
    concurrency: int = 3,
    mock: bool = False,
) -> dict[str, Any]:
    if manifest_path is not None and release is not None:
        raise ValueError("Choose either --release or an unversioned custom --manifest")
    descriptor = load_release(DEFAULT_RELEASE if release is None else release) if manifest_path is None else None
    if run_id is None:
        run_id = "run-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
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
    if not mock and budget_usd is not None and any(
        model.get("input_per_m") is None or model.get("output_per_m") is None for model in models
    ):
        raise ValueError("A budgeted live run requires known input and output prices")

    anthropic_workspace_id = None
    if not mock and any(model["provider"] == "anthropic" for model in models):
        anthropic_workspace_id = os.environ.get("ANTHROPIC_WORKSPACE_ID", "").strip() or None
        if anthropic_workspace_id and not re.fullmatch(r"wrkspc_[A-Za-z0-9]+", anthropic_workspace_id):
            raise ValueError("ANTHROPIC_WORKSPACE_ID must be a wrkspc_ workspace ID")

    if descriptor is not None:
        manifest_path = release_manifest_path(descriptor)
        items = validate_release(descriptor)
    else:
        assert manifest_path is not None
        if not mock:
            require_valid_dataset(manifest_path)
        items = load_manifest(str(manifest_path))
    fingerprint = dataset_fingerprint(items)
    items.sort(key=lambda x: x["taskId"])
    random.Random(0).shuffle(items)
    selected_items = items[:max_tasks] if max_tasks is not None else items

    version = descriptor["benchmark_version"] if descriptor else None
    leaf = f"mock-{run_id}" if mock else run_id
    directory = Path(output_dir) / version / leaf if version else Path(output_dir) / leaf
    directory.mkdir(parents=True, exist_ok=True)
    code_identity = git_code_identity()
    protocol = evaluation_protocol_fingerprint()

    with _run_lock(directory), ExitStack() as resources:
        if any((directory / name).exists() for name in ("finalization.json", "final_results.json")):
            raise ValueError("This run is finalized or awaiting its seal; use a new run ID")
        state_path = directory / "state.sqlite3"
        if not state_path.exists() and (
            any((directory / name).exists() for name in ("run.json", "summary.json", "attempts.jsonl"))
            or any(directory.glob("scorecard_*.json"))
        ):
            raise ValueError("Existing run artifacts have no checkpoint; restore state.sqlite3 before resuming")
        result_fields = {f.name for f in fields(TaskEvaluationResult)}
        clients = {}
        request_timeouts = {}
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
            if client._client is not None:
                if model["provider"] == "anthropic" and anthropic_workspace_id:
                    client._client._http.headers["anthropic-workspace-id"] = anthropic_workspace_id
                if (model.get("base_url") or "").rstrip("/") == META_API_BASE_URL:
                    # FontBench observed Muse reasoning exceeding the default transport wait.
                    client._client._http.timeout = httpx.Timeout(META_REQUEST_TIMEOUT)
                request_timeouts[model["id"]] = client._client._http.timeout.read
            clients[model["id"]] = client

        model_by_id = {model["id"]: model for model in models}
        provider_scopes = {
            model["id"]: (model["provider"], (model.get("base_url") or PROVIDERS[model["provider"]][0]).rstrip("/"),
                          model.get("api_key_env") or PROVIDERS[model["provider"]][1])
            for model in models
        }
        reserve = {
            model["id"]: 0.0 if mock else None if model.get("input_per_m") is None or model.get("output_per_m") is None else (
                5000 * model["input_per_m"] + model.get("max_output_tokens", 1024) * model["output_per_m"]
            ) / 1_000_000 for model in models
        }

        with RunStore(state_path) as store:
            run_path = directory / "run.json"
            identity = {
                "schema_version": 1, "run_id": run_id, "grading_version": GRADING_VERSION,
                "release": version,
                "dataset_git_commit": descriptor["dataset_git_commit"] if descriptor else None,
                "dataset_fingerprint": fingerprint,
                "evaluation_protocol": protocol,
                "manifest_path": str(Path(manifest_path).resolve()),
                "mock": mock,
                "expected_task_count": len(items),
            }
            prior = {run["run_id"]: run for run in store.list_runs()}.get(run_id)
            checkpoint_states = store.model_states(run_id)
            if prior is not None and (prior["fingerprint"] != fingerprint or any(
                prior["metadata"].get(key) != value for key, value in identity.items()
            )):
                raise ValueError("Checkpoint disagrees with the dataset/evaluation protocol identity")
            if budget_usd is not None and store.has_unknown_costs(run_id):
                raise ValueError("Cannot enforce a cumulative budget: prior attempts have unknown costs")
            for model in models:
                if model["id"] in checkpoint_states and checkpoint_states[model["id"]]["config"] != model:
                    raise ValueError(f"Model {model['id']!r} already has a different config")
            if run_path.exists():
                try:
                    run_metadata = json.loads(run_path.read_text(encoding="utf-8"))
                except (OSError, ValueError) as error:
                    raise ValueError(f"Run metadata {run_path} is unreadable: {error}") from error
                if not isinstance(run_metadata, dict) or any(
                    run_metadata.get(key) != value for key, value in identity.items()
                ):
                    raise ValueError("Run metadata disagrees with the checkpoint/release identity")
                history = run_metadata.get("invocations")
                if (not isinstance(history, list) or not history or any(
                    not isinstance(entry, dict) or not isinstance(entry.get("models"), list)
                    or not entry["models"] or any(not isinstance(model, dict) for model in entry["models"])
                    for entry in history
                )):
                    raise ValueError("Run metadata has malformed invocation history")
                historical_configs = [model for entry in history for model in entry["models"]]
                if any(state["config"] not in historical_configs or
                       run_metadata.get("model_configs", {}).get(model_id) != state["config"]
                       for model_id, state in checkpoint_states.items()):
                    raise ValueError("Run metadata has lost or changed a checkpoint model configuration")
            else:
                if any((directory / name).exists() for name in ("summary.json", "attempts.jsonl")) or store.list_runs():
                    raise ValueError("Existing checkpoint has lost run metadata. Restore run.json before resuming.")
                run_metadata = {
                    **identity,
                    **code_identity,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "invocations": [],
                    "model_configs": {},
                }
            invocation = {
                **code_identity,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "max_tasks": max_tasks,
                "budget_usd": budget_usd,
                "concurrency": concurrency,
                "models": models,
                "request_timeouts_sec": request_timeouts,
            }
            if anthropic_workspace_id:
                invocation["anthropic_workspace_id"] = anthropic_workspace_id
            store.register_run(run_id, fingerprint, identity)
            for model in models:
                store.register_model(run_id, model["id"], model)
            run_metadata["invocations"].append(invocation)
            for model in models:
                run_metadata["model_configs"][model["id"]] = model

            reported_models = [state["config"] for state in store.model_states(run_id).values()]
            completed = {model["id"]: store.completed_results(run_id, model["id"]) for model in reported_models}
            known_tasks = {item["taskId"] for item in items}
            foreign = sorted(
                {task_id for model in reported_models for task_id in store.results(run_id, model["id"])} - known_tasks
            )
            if foreign:
                raise ValueError(
                    f"Checkpoint for run {run_id!r} contains {len(foreign)} unknown task IDs "
                    f"(e.g. {foreign[0]!r}); restore the matching manifest or use a new run ID"
                )
            from baseline.reporting import validate_task_result
            by_id = {item["taskId"]: item for item in items}
            for model in reported_models:
                for task_id, result in completed[model["id"]].items():
                    validate_task_result(result, by_id[task_id], model)
            pending = deque(
                (model["id"], item)
                for item in selected_items
                for model in models
                if item["taskId"] not in completed[model["id"]]
            )
            blocked_providers: set[tuple[str, str, str]] = set()
            blocked_models: set[str] = set()
            status = "running"
            scorecards = {}
            attempted_ids = {model["id"]: set(store.results(run_id, model["id"])) for model in reported_models}

            def snapshot(changed_model_id: str | None = None) -> dict:
                state = store.model_states(run_id)
                updated_at = datetime.now(timezone.utc).isoformat()
                provenance = {**identity, **code_identity, "created_at": run_metadata["created_at"], "updated_at": updated_at}
                summary = {
                    **provenance,
                    "budget_usd": budget_usd,
                    "spent_cost_usd": store.spent_cost(run_id),
                    "cost_incomplete": store.has_unknown_costs(run_id),
                    "interruption_signal": int(interruption_signal) if interrupted else None,
                    "status": status,
                    "models": {},
                    "invocations": len(run_metadata["invocations"]),
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
                            **provenance,
                            model_config=model,
                            model_config_fingerprint=model_config_fingerprint(model),
                            max_output_tokens=model.get("max_output_tokens", 1024),
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
                        "model_config": model,
                        "model_config_fingerprint": model_config_fingerprint(model),
                        "max_output_tokens": model.get("max_output_tokens", 1024),
                        "provider": model["provider"],
                        "model": model["model"],
                        "display_name": model.get("display_name", m_id),
                        "completed": len(saved),
                        "attempted_tasks": len(attempted_ids[m_id]),
                        "status": "complete" if len(saved) == len(items) else cur.get("status", "pending"),
                        "reason": cur.get("reason"),
                        "cost_usd": None if any(a["result"].get("cost_usd") is None for a in store.attempts(run_id, m_id)) else store.spent_cost(run_id, m_id),
                        "families": scorecard["families"],
                        "avg_latency_sec": scorecard["avg_latency_sec"],
                    }
                write_json(directory / "summary.json", summary)
                invocation.update(status=status, updated_at=updated_at)
                if status != "running":
                    invocation["finished_at"] = updated_at
                write_json(run_path, run_metadata)
                attempts_path = directory / "attempts.jsonl"
                attempts_temporary = attempts_path.with_suffix(".jsonl.tmp")
                attempts_temporary.write_text(
                    "".join(
                        json.dumps(attempt, sort_keys=True, ensure_ascii=False) + "\n"
                        for attempt in store.attempts(run_id)
                    ),
                    encoding="utf-8",
                )
                attempts_temporary.replace(attempts_path)
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
                elif reserve[m_id] is None:
                    res_dict["cost_usd"] = None
                elif worker_failed:
                    res_dict["cost_usd"] = req_reserve
                else:
                    in_m = model.get("input_per_m") or 0.0
                    out_m = model.get("output_per_m") or 0.0
                    metered = ((res_dict.get("input_tokens") or 0) * in_m + (res_dict.get("output_tokens") or 0) * out_m) / 1_000_000
                    res_dict["cost_usd"] = metered + reserve[m_id] * (res_dict.get("unmetered_attempts") or 0)
                res_dict["cost_estimated"] = worker_failed or bool(res_dict.get("unmetered_attempts"))
                res_dict["recorded_at"] = datetime.now(timezone.utc).isoformat()

                store.save_result(run_id, m_id, task_id, res_dict)
                failure = res_dict.get("error_kind")
                attempted_ids[m_id].add(task_id)

                if not res_dict.get("error") or failure == "invalid_response":
                    completed[m_id][task_id] = res_dict

                if failure in {"credits", "authentication", "rate_limit"}:
                    blocked_providers.add(provider_scopes[m_id])
                    for sib in models:
                        if provider_scopes[sib["id"]] == provider_scopes[m_id]:
                            store.save_model_state(run_id, sib["id"], "paused", res_dict.get("error"))
                elif res_dict.get("error") and failure != "invalid_response":
                    blocked_models.add(m_id)
                    store.save_model_state(run_id, m_id, "paused", res_dict.get("error"))

                status_label = "valid" if res_dict.get("valid") else ("error: " + str(failure) if failure else "invalid")
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
                            if m_id in blocked_models or provider_scopes[m_id] in blocked_providers:
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
            elif all(len(saved) == len(items) for saved in completed.values()):
                status = "complete"
            elif status != "budget_exhausted":
                status = "paused" if blocked_providers or blocked_models else "partial"

            for model in models:
                m_id = model["id"]
                if len(completed[m_id]) == len(items):
                    store.save_model_state(run_id, m_id, "complete")
                elif m_id not in blocked_models and provider_scopes[m_id] not in blocked_providers:
                    reason = str(fatal_error) if fatal_error else "Interrupted; resume to continue" if interrupted else None
                    store.save_model_state(run_id, m_id, "paused" if fatal_error or interrupted else "partial", reason)

            summary = snapshot()
            invocation.update(status=status, finished_at=summary["updated_at"])
            write_json(run_path, run_metadata)
            if fatal_error:
                raise fatal_error
            return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=None, help="Unversioned custom manifest (excluded from release comparisons)")
    parser.add_argument("--release", default=None, help=f"Frozen benchmark version (default: {DEFAULT_RELEASE})")
    parser.add_argument("--config", default="config/models.all.json")
    parser.add_argument("--output-dir", default="results/runs")
    parser.add_argument("--run-id", default=None, help="Run name; a unique one is generated when omitted")
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
        release=args.release,
        selected_models=args.models,
        budget_usd=None if args.no_budget_limit else args.budget_usd,
        max_tasks=args.max_tasks,
        concurrency=args.concurrency,
        mock=args.mock,
    )
    print(json.dumps(summary, indent=2))
    if summary["status"] == "interrupted":
        raise SystemExit(128 + summary["interruption_signal"])


if __name__ == "__main__":
    main()
