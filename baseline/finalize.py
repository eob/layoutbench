"""Seal a fixed publication cohort using saved responses, without provider requests."""

from __future__ import annotations

import argparse
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import subprocess

from baseline.evaluator import GRADING_VERSION
from baseline.statistics import family_metrics
from baseline.protocol import NUMERIC_SCORING
from baseline.model_config import _ModelConfig
from baseline.releases import REPO_ROOT, git_code_identity, load_release, model_config_fingerprint, validate_release
from baseline.reporting import _code_identity, _ledger_time, finite_nonnegative, scorecard_tasks, validate_task_result
from baseline.runner import _run_lock, write_json

IDENTITY_KEYS = ('schema_version', 'dataset_git_commit', 'dataset_fingerprint', 'expected_task_count')


def _json_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text())
    except (OSError, ValueError) as error:
        raise ValueError(f'Cannot read finalization artifact {path.name}') from error
    if not isinstance(value, dict):
        raise ValueError(f'Invalid finalization artifact {path.name}')
    return value


def _source(directory: Path, release: dict, items: list[dict]) -> dict:
    metadata, summary = (_read_json(directory / name) for name in ('run.json', 'summary.json'))
    identity = {key: release[key] for key in IDENTITY_KEYS}
    identity.update(run_id=directory.name, mock=False, grading_version=GRADING_VERSION,
                    release=release['benchmark_version'], evaluation_protocol=release['evaluation_protocol_fingerprint'])
    if any(record.get(key) != value for record in (metadata, summary) for key, value in identity.items()):
        raise ValueError('Run and summary disagree with the frozen release identity')
    created, updated = _ledger_time(metadata.get('created_at')), _ledger_time(summary.get('updated_at'))
    if _ledger_time(summary.get('created_at')) != created or updated < created:
        raise ValueError('Invalid run chronology')
    invocations = metadata.get('invocations')
    if not isinstance(invocations, list) or not invocations:
        raise ValueError('Missing invocation history')
    for invocation in invocations:
        if not isinstance(invocation, dict) or not isinstance(invocation.get('models'), list) or not invocation['models']:
            raise ValueError('Invalid invocation history')
        _code_identity(invocation)
        if not created <= _ledger_time(invocation.get('started_at')) <= _ledger_time(invocation.get('updated_at')) <= updated:
            raise ValueError('Invalid invocation chronology')
    if _code_identity(summary) != _code_identity(invocations[-1]):
        raise ValueError('Summary source code identity differs from its last invocation')
    database = directory / 'state.sqlite3'
    wal = directory / 'state.sqlite3-wal'
    if wal.exists() and wal.stat().st_size:
        raise ValueError('Checkpoint WAL is not closed; finish the runner before finalization')
    try:
        with closing(sqlite3.connect(f'{database.as_uri()}?mode=ro&immutable=1', uri=True)) as connection:
            if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('Checkpoint integrity check failed')
            runs = connection.execute('SELECT run_id,fingerprint,metadata_json FROM runs').fetchall()
            configs = {model: json.loads(raw) for model, raw in connection.execute('SELECT model_id,config_json FROM models WHERE run_id=?', (directory.name,))}
            model_states = {model: dict(status=status, reason=reason) for model, status, reason in connection.execute(
                'SELECT model_id,status,reason FROM models WHERE run_id=?', (directory.name,))}
            results = {(model, task): json.loads(raw) for model, task, raw in connection.execute('SELECT model_id,task_id,result_json FROM results WHERE run_id=?', (directory.name,))}
            attempts = [dict(sequence=sequence, attempt_id=attempt, run_id=run, model_id=model, task_id=task,
                             result=json.loads(raw), cost_usd=cost, created_at=at)
                        for sequence, attempt, run, model, task, raw, cost, at in connection.execute(
                            'SELECT rowid,attempt_id,run_id,model_id,task_id,result_json,cost_usd,created_at FROM attempts ORDER BY rowid')]
    except (sqlite3.Error, OSError, ValueError) as error:
        raise ValueError(f'Invalid checkpoint: {error}') from error
    if (any(not isinstance(config, dict) for config in configs.values())
            or any(not isinstance(result, dict) for result in results.values())
            or any(not isinstance(attempt['result'], dict) for attempt in attempts)):
        raise ValueError('Malformed checkpoint model or response rows')
    expected_run_hash = release['dataset_fingerprint']
    if len(runs) != 1 or runs[0][:2] != (directory.name, expected_run_hash) or any(
            json.loads(runs[0][2]).get(key) != value for key, value in identity.items()):
        raise ValueError('Checkpoint release identity differs from its metadata')
    if not configs or not isinstance(summary.get('models'), dict) or set(configs) != set(summary['models']):
        raise ValueError('Checkpoint model roster differs from summary')
    if metadata.get('model_configs') != configs:
        raise ValueError('Run model configurations differ from the checkpoint')
    try:
        exported = [json.loads(line) for line in (directory / 'attempts.jsonl').read_text().splitlines()]
    except (OSError, ValueError) as error:
        raise ValueError('Invalid attempt export') from error
    if exported != attempts:
        raise ValueError('Attempt export differs from the checkpoint ledger')
    items_by_id = {item['taskId']: item for item in items}
    latest, final_attempts = {}, {}
    for attempt in attempts:
        key = (attempt['model_id'], attempt['task_id'])
        result = attempt['result']
        if attempt['run_id'] != directory.name or key[0] not in configs or key[1] not in items_by_id:
            raise ValueError('Attempt refers to an unknown run, model, or release task')
        if not created <= _ledger_time(attempt.get('created_at')) <= updated:
            raise ValueError('Attempt falls outside its run chronology')
        if key in final_attempts:
            raise ValueError('Attempt follows an already final answer')
        if not finite_nonnegative(attempt['cost_usd']) or not math.isclose(attempt['cost_usd'], result.get('cost_usd') or 0, abs_tol=1e-12):
            raise ValueError('Attempt cost differs from its result')
        latest[key] = result
        if not result.get('error') or result.get('error_kind') == 'invalid_response':
            final_attempts[key] = attempt['attempt_id']
    if latest != results:
        raise ValueError('Checkpoint results differ from their final attempt records')
    cards = {}
    expected_cards = {f'scorecard_{model}.json' for model in configs}
    if {path.name for path in directory.glob('scorecard_*.json')} != expected_cards:
        raise ValueError('Scorecard roster differs from the checkpoint')
    for model_id, config in configs.items():
        validated = _ModelConfig.model_validate_json(json.dumps(config)).model_dump(mode='json')
        if config != validated or config['id'] != model_id:
            raise ValueError('Invalid checkpoint model configuration')
        card = _read_json(directory / f'scorecard_{model_id}.json')
        tasks = scorecard_tasks(card, dataset_fingerprint=release['dataset_fingerprint'])
        state = summary['models'][model_id]
        checkpoint_state = model_states[model_id]
        if (not isinstance(state, dict) or state.get('status') != checkpoint_state['status']
                or state.get('reason') != checkpoint_state['reason']
                or state.get('attempted_tasks') != sum(model == model_id for model, _ in results)):
            raise ValueError('Model availability status or reason differs from the checkpoint')
        if (any(card.get(key) != value for key, value in identity.items())
                or card.get('model_config') != config or state.get('model_config') != config
                or card.get('model_config_fingerprint') != model_config_fingerprint(config)
                or state.get('model_config_fingerprint') != model_config_fingerprint(config)
                or card.get('model_id') != model_id or card.get('model_name') != config['model']
                or card.get('provider') != config['provider'] or type(state.get('completed')) is not int
                or state.get('completed') != len(tasks) or card.get('max_output_tokens') != config['max_output_tokens']
                or state.get('max_output_tokens') != config['max_output_tokens']
                or {task['task_id']: task for task in tasks} != {
                    task: result for (model, task), result in results.items()
                    if model == model_id and (model, task) in final_attempts}):
            raise ValueError('Scorecard or summary differs from checkpoint final responses')
        model_costs = [attempt['result'].get('cost_usd') for attempt in attempts if attempt['model_id'] == model_id]
        if any(cost is None for cost in model_costs):
            if state.get('cost_usd') is not None:
                raise ValueError('Model cost completeness differs from its attempt ledger')
        elif (not finite_nonnegative(state.get('cost_usd'))
              or not math.isclose(state['cost_usd'], sum(model_costs), rel_tol=0, abs_tol=1e-12)):
            raise ValueError('Model cost differs from its attempt ledger')
        card_updated = _ledger_time(card.get('updated_at'))
        if (_ledger_time(card.get('created_at')) != created or not created <= card_updated <= updated
                or _code_identity(card) not in {_code_identity(invocation) for invocation in invocations}):
            raise ValueError('Invalid scorecard chronology or source code identity')
        for result in tasks:
            item = items_by_id[result['task_id']]
            validate_task_result(result, item, config)
            recorded = _ledger_time(result.get('recorded_at'))
            if not created <= recorded <= card_updated or not any(
                    config in invocation['models'] and _ledger_time(invocation['started_at']) <= recorded <= _ledger_time(invocation['updated_at'])
                    for invocation in invocations):
                raise ValueError('Saved response falls outside its model invocation')
        cards[model_id] = tasks
    spent = sum(attempt['cost_usd'] for attempt in attempts)
    if not finite_nonnegative(summary.get('spent_cost_usd')) or not math.isclose(spent, summary['spent_cost_usd'], abs_tol=1e-9):
        raise ValueError('Summary spending differs from attempt ledger')
    incomplete = any(attempt['result'].get('cost_usd') is None for attempt in attempts)
    if type(summary.get('cost_incomplete')) is not bool or summary['cost_incomplete'] != incomplete:
        raise ValueError('Summary cost completeness differs from attempt ledger')
    return dict(identity=identity, release_descriptor=release, metadata=metadata, summary=summary, configs=configs, cards=cards,
                results=results, final_attempts=final_attempts, attempts=attempts, model_states=model_states, updated=updated)


def _measures(tasks: list[dict], config: dict) -> dict:
    costs, latencies = [], []
    for task in tasks:
        metered = (not task.get('cost_estimated') and task.get('unmetered_attempts') == 0
                   and all(type(task.get(key)) is int and task[key] >= 0 for key in ('input_tokens', 'output_tokens'))
                   and all(finite_nonnegative(config.get(key)) for key in ('input_per_m', 'output_per_m')))
        if metered:
            cost = (task['input_tokens'] * config['input_per_m'] + task['output_tokens'] * config['output_per_m']) / 1_000_000
            if not finite_nonnegative(task.get('cost_usd')) or not math.isclose(task['cost_usd'], cost, rel_tol=0, abs_tol=1e-12):
                raise ValueError('Recorded metered cost differs from token usage and pricing')
            costs.append(cost)
        if finite_nonnegative(task.get('latency_sec')):
            latencies.append(task['latency_sec'])
    return dict(mean_api_response_cost_usd=sum(costs)/len(tasks) if tasks and len(costs)==len(tasks) else None,
                cost_known_response_count=len(costs), mean_latency_sec=sum(latencies)/len(tasks) if tasks and len(latencies)==len(tasks) else None,
                latency_known_response_count=len(latencies))


def _report(source: dict, items: list[dict], scope: str, roster: list[str], provenance: dict) -> dict:
    if scope not in ('common', 'full'):
        raise ValueError('Publication scope must be common or full')
    if (not roster or any(not isinstance(model, str) for model in roster)
            or len(set(roster)) != len(roster) or not set(roster) <= set(source['configs'])):
        raise ValueError('Publication model roster must contain distinct known model IDs')
    cohort = set.intersection(*[{task['task_id'] for task in source['cards'][model]} for model in roster])
    if not cohort or scope == 'full' and len(cohort) != len(items):
        raise ValueError('Publication cohort is empty or missing inputs required for full coverage')
    models = []
    for model_id, config in sorted(source['configs'].items()):
        observed = source['cards'][model_id]
        selected = [task for task in observed if model_id in roster and task['task_id'] in cohort]
        state = source['model_states'][model_id]
        attempted = {key for key in source['results'] if key[0] == model_id}
        unresolved = attempted - source['final_attempts'].keys()
        if len(observed) == len(items):
            availability = 'complete'
        elif observed:
            availability = 'partial'
        elif unresolved or state['reason']:
            availability = 'unavailable'
        else:
            availability = 'not_run'
        families = {}
        for family in sorted({item['family'] for item in items}):
            subset = [task for task in selected if task['family'] == family]
            families[family] = {**family_metrics(subset, family), **_measures(subset, config),
                                'group_count': len({task['group_id'] for task in subset})}
        models.append(dict(model_id=model_id, model_config=config, model_config_fingerprint=model_config_fingerprint(config),
                           status='finalized', coverage_status='complete' if len(observed)==len(items) else 'partial',
                           included_in_comparison=model_id in roster, availability_status=availability,
                           run_status=state['status'], run_reason=state['reason'], attempted_task_count=len(attempted),
                           unresolved_infrastructure_task_count=len(unresolved),
                           observed_task_count=len(observed), expected_task_count=len(items), comparison_task_count=len(selected),
                           families=families, **_measures(selected, config)))
    error_kinds = Counter(attempt['result'].get('error_kind') or 'unclassified' for attempt in source['attempts']
                          if attempt['result'].get('error') and attempt['result'].get('error_kind') != 'invalid_response')
    release = source['release_descriptor']
    return {**source['identity'], **provenance, 'artifact_type': 'layoutbench-final-results', 'publication_status': 'finalized',
            'benchmark_id': 'layoutbench', 'version': release['benchmark_version'], 'status': 'pilot',
            'human_validation': 'not_performed', 'numeric_scoring': NUMERIC_SCORING,
            'dataset_manifest': release['dataset_manifest'], 'dataset_path': release['dataset_path'],
            'comparison': dict(scope=scope, count=len(cohort), task_ids=sorted(cohort),
                               cohort_fingerprint=hashlib.sha256(json.dumps(sorted(cohort)).encode()).hexdigest(), model_ids=sorted(roster)),
            'cost_basis': 'Recorded metered token usage multiplied by recorded model pricing per scored input; excludes unmetered reserves and separate infrastructure attempts.',
            'statistical_scope': 'Descriptive finite pilot. Related images share groups; no independent-sample confidence intervals or combined cross-family score.',
            'campaign': dict(final_response_count=len(source['final_attempts']), attempt_count=len(source['attempts']),
                             infrastructure_attempt_count=sum(error_kinds.values()), infrastructure_error_kinds=dict(sorted(error_kinds.items())),
                             unresolved_infrastructure_task_count=len(source['results']) - len(source['final_attempts']),
                             spent_cost_usd=source['summary']['spent_cost_usd'], budget_usd=source['summary'].get('budget_usd'),
                             cost_incomplete=source['summary'].get('cost_incomplete', True),
                             estimated_cost_attempt_count=sum(bool(attempt['result'].get('cost_estimated')) for attempt in source['attempts'])),
            'models': models,
            'attempts': source['attempts'],
            'specimens': [dict(task_id=item['taskId'], family=item['family'], group_id=item['groupId'],
                               image_filename=item['imageFilename'], image_sha256=item['imageSha256'],
                               ground_truth=item['groundTruth'], prompt=item['prompt'], design=item['design']) for item in items],
            'results': [dict(model_id=model, status='final', included_in_comparison=model in roster and task in cohort,
                             source_attempt_id=source['final_attempts'][(model,task)], result_sha256=_json_hash(result), result=result)
                        for (model,task),result in sorted(source['results'].items()) if (model, task) in source['final_attempts']]}


def _artifact_names(directory: Path) -> set[str]:
    return {'state.sqlite3', 'attempts.jsonl', 'run.json', 'summary.json', 'final_results.json',
            *(path.name for path in directory.glob('scorecard_*.json'))}


def _committed_source(directory: Path, repository: Path, commit: str) -> None:
    if not directory.is_relative_to(repository):
        raise ValueError('Source checkpoint is outside its Git repository')
    relative = directory.relative_to(repository).as_posix()
    for name in _artifact_names(directory) - {'final_results.json'}:
        path = directory / name
        committed = subprocess.run(['git', 'show', f'{commit}:{relative}/{name}'], cwd=repository, capture_output=True)
        if path.is_symlink() or committed.returncode or committed.stdout != path.read_bytes():
            raise ValueError(f'Source checkpoint artifact differs from its committed bytes: {name}')


def _verify(directory: Path, root: Path) -> dict:
    seal = _read_json(directory / 'finalization.json')
    hashes = seal.get('artifact_sha256')
    if not isinstance(hashes, dict) or set(hashes) != _artifact_names(directory):
        raise ValueError('Finalization artifact hash inventory changed')
    for name, digest in hashes.items():
        path = directory / name
        if not path.is_file() or path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f'Sealed artifact hash changed: {name}')
    report = _read_json(directory / 'final_results.json')
    release = load_release(report.get('release'), root=root)
    items = validate_release(release, root=root)
    source = _source(directory, release, items)
    provenance_keys = ('finalized_at', 'source_git_commit', 'finalizer_git_commit', 'finalizer_git_dirty', 'source_updated_at')
    provenance = {key: report.get(key) for key in provenance_keys}
    for key in ('source_git_commit', 'finalizer_git_commit'):
        value = provenance[key]
        if not isinstance(value, str) or len(value) != 40 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError('Invalid finalization Git provenance')
    if (not isinstance(provenance['finalizer_git_dirty'], bool)
            or _ledger_time(provenance['source_updated_at']) != source['updated']
            or _ledger_time(provenance['finalized_at']) < source['updated']):
        raise ValueError('Invalid finalization chronology')
    _committed_source(directory, root, provenance['source_git_commit'])
    comparison = report.get('comparison')
    if not isinstance(comparison, dict) or not isinstance(comparison.get('model_ids'), list):
        raise ValueError('Invalid final comparison cohort')
    expected = _report(source, items, comparison.get('scope'), comparison['model_ids'], provenance)
    if report != expected:
        raise ValueError('Final results differ from their independently scored comparison and source responses')
    expected_seal = {**source['identity'], **provenance, 'artifact_type': 'layoutbench-finalization',
                     'publication_status': 'finalized', 'comparison': report['comparison'], 'artifact_sha256': hashes}
    if seal != expected_seal:
        raise ValueError('Finalization seal identity or comparison differs from final results')
    return report


def verify_finalization(run_dir: str | Path, *, root: str | Path | None = None) -> dict:
    directory = Path(run_dir).resolve()
    if not directory.is_dir():
        raise ValueError('Run directory does not exist')
    with _run_lock(directory):
        try:
            return _verify(directory, Path(root or REPO_ROOT).resolve())
        except (KeyError, TypeError, AttributeError) as error:
            raise ValueError('Malformed finalization metadata or checkpoint') from error


def finalize_run(run_dir: str | Path, *, scope: str, models: list[str] | None = None,
                 root: str | Path | None = None) -> dict:
    directory, repository = Path(run_dir).resolve(), Path(root or REPO_ROOT).resolve()
    if not directory.is_dir() or not directory.is_relative_to(repository):
        raise ValueError('Run directory must exist within its source repository')
    with _run_lock(directory):
        if (directory / 'finalization.json').exists():
            report = _verify(directory, repository)
            if report['comparison']['scope'] != scope or models is not None and sorted(models) != report['comparison']['model_ids']:
                raise ValueError('Finalized publication scope and model roster cannot change')
            return report
        if (directory / 'final_results.json').exists():
            raise ValueError('Unsealed final results already exist; inspect the interrupted finalization first')
        metadata = _read_json(directory / 'run.json')
        release = load_release(metadata.get('release'), root=repository)
        items = validate_release(release, root=repository)
        source = _source(directory, release, items)
        relative = directory.relative_to(repository).as_posix()
        try:
            commit = subprocess.run(['git', 'log', '-1', '--format=%H', '--', relative], cwd=repository,
                                    check=True, capture_output=True, text=True).stdout.strip()
        except subprocess.CalledProcessError as error:
            raise ValueError('Cannot establish source checkpoint Git commit') from error
        if len(commit) != 40:
            raise ValueError('Source checkpoint must be committed before finalization')
        _committed_source(directory, repository, commit)
        code = git_code_identity(root=repository)
        if code['runner_git_commit'] is None:
            raise ValueError('Finalizer Git identity is unavailable')
        provenance = dict(finalized_at=datetime.now(timezone.utc).isoformat(), source_updated_at=source['summary']['updated_at'],
                          source_git_commit=commit, finalizer_git_commit=code['runner_git_commit'], finalizer_git_dirty=code['runner_git_dirty'])
        report = _report(source, items, scope, sorted(source['configs']) if models is None else models, provenance)
        write_json(directory / 'final_results.json', report)
        hashes = {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in sorted(_artifact_names(directory))}
        seal = {**source['identity'], **provenance, 'artifact_type': 'layoutbench-finalization',
                'publication_status': 'finalized', 'comparison': report['comparison'], 'artifact_sha256': hashes}
        write_json(directory / 'finalization.json', seal)
        return _verify(directory, repository)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', required=True)
    parser.add_argument('--scope', choices=['common', 'full'])
    parser.add_argument('--models', nargs='+', help='Explicit publication roster; defaults to every recorded model')
    parser.add_argument('--verify', action='store_true', help='Verify an existing seal without changing it')
    args = parser.parse_args()
    if args.verify:
        if args.scope or args.models:
            parser.error('--verify cannot change publication scope or model roster')
        report = verify_finalization(args.run_dir)
    else:
        if not args.scope:
            parser.error('Choose --scope common or --scope full')
        report = finalize_run(args.run_dir, scope=args.scope, models=args.models)
    print(json.dumps({key: report[key] for key in ('run_id', 'release', 'publication_status', 'comparison', 'campaign')}, indent=2))


if __name__ == '__main__':
    main()
