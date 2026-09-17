"""Read-only, raw-answer diagnostics for the live LayoutBench checkpoint."""
import json
import os
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get('LAYOUTBENCH_ROOT', Path.cwd())).resolve()
MANIFEST = ROOT / 'dataset/layoutbench-v0.3/manifest.json'
RUN = Path(os.environ.get('LAYOUTBENCH_RUN', ROOT / 'results/runs/0.3.0/qualitative-20260917')).resolve()


def object_without_duplicates(pairs):
    if len(dict(pairs)) != len(pairs):
        raise ValueError('duplicate key')
    return dict(pairs)


def prediction(raw, options):
    try:
        value = json.loads(raw, object_pairs_hook=object_without_duplicates)
        if not isinstance(value, dict) or set(value) != {'choice'} or not isinstance(value['choice'], str):
            return None
        letter = value['choice'].strip().upper()
        if len(letter) != 1 or not 0 <= ord(letter) - 65 < len(options):
            return None
        return options[ord(letter) - 65]
    except (ValueError, TypeError):
        return None


def diagnose():
    tasks = {row['taskId']: row for row in json.loads(MANIFEST.read_text())}
    expected = Counter(row['family'] for row in tasks.values())
    database = RUN / 'state.sqlite3'
    with sqlite3.connect(f'{database.as_uri()}?mode=ro', uri=True) as connection:
        connection.execute('BEGIN')
        states = {model: {'run_status': status, 'run_reason': reason} for model, status, reason in connection.execute('SELECT model_id,status,reason FROM models')}
        latest = [(model, task, json.loads(raw)) for model, task, raw in connection.execute('SELECT model_id,task_id,result_json FROM results')]
        attempts = list(connection.execute('SELECT model_id,task_id,created_at FROM attempts'))
    rows = defaultdict(dict)
    infrastructure = []
    task_errors = defaultdict(list)
    for model, task_id, saved in latest:
        task = tasks[task_id]
        if saved.get('error') and saved.get('error_kind') != 'invalid_response':
            infrastructure.append({'model': model, 'task_id': task_id, 'kind': saved.get('error_kind'), 'error': saved['error']})
            continue
        actual = prediction(saved['raw_prediction'], task['design']['options'])
        truth = task['design']['options'][ord(task['groundTruth']['choice']) - 65]
        correct = actual == truth
        assert truth == task['design']['answer']
        assert saved['valid'] == (actual is not None)
        assert saved['correct'] == correct
        assert saved['score'] == (100 if correct else 0)
        row = {'task_id': task_id, 'family': task['family'], 'group_id': task['groupId'], 'image': task['imageFilename'],
               'truth': truth, 'prediction': actual, 'correct': correct, 'raw': saved['raw_prediction'],
               'theme': task['design']['theme'], 'variant': task['design']['variant'], 'factors': task['design']['factors']}
        rows[model][task_id] = row
        if not correct:
            task_errors[task_id].append({'model': model, 'prediction': actual, 'raw': saved['raw_prediction']})
    result = {'snapshot_utc': datetime.now(timezone.utc).isoformat(), 'latest_attempt_utc': max((row[2] for row in attempts), default=None),
              'expected_tasks_per_model': len(tasks), 'attempt_count': len(attempts), 'infrastructure_failures': infrastructure,
              'models': {}, 'task_errors': {}}
    for model, state in states.items():
        observed = list(rows[model].values())
        families = {}
        for family, expected_count in expected.items():
            subset = [row for row in observed if row['family'] == family]
            families[family] = {'correct': sum(row['correct'] for row in subset), 'observed': len(subset), 'expected': expected_count}
        grouped = defaultdict(dict)
        for row in observed:
            if row['family'] in {'topflow', 'nestedflow'}:
                grouped[row['group_id']][row['family']] = row
        complete_pairs = [pair for pair in grouped.values() if set(pair) == {'topflow', 'nestedflow'}]
        pair_counts = Counter('both' if pair['topflow']['correct'] and pair['nestedflow']['correct'] else 'outer_only' if pair['topflow']['correct'] else 'inner_only' if pair['nestedflow']['correct'] else 'neither' for pair in complete_pairs)
        pair_details = [{'outer': pair['topflow'], 'inner': pair['nestedflow']} for pair in complete_pairs if not (pair['topflow']['correct'] and pair['nestedflow']['correct'])]
        wrap_groups = {}
        for parent in ['row', 'column']:
            for variant in [0, 1]:
                for answer in ['left', 'center', 'right']:
                    subset = [row for row in observed if row['family'] == 'nestedwrap' and row['factors']['parent'] == parent and row['variant'] == variant and row['truth'] == answer]
                    wrap_groups[f'{parent}|position-{variant + 1}|{answer}'] = {'correct': sum(row['correct'] for row in subset), 'observed': len(subset), 'expected': 2}
        result['models'][model] = {**state, 'observed': len(observed), 'families': families,
            'ceiling_families_complete': [family for family, value in families.items() if value['correct'] == value['observed'] == value['expected']],
            'hierarchy_pairs_observed': len(complete_pairs), 'hierarchy_pairs_expected': 24,
            'hierarchy_pair_counts': {key: pair_counts[key] for key in ['both', 'outer_only', 'inner_only', 'neither']},
            'hierarchy_pair_errors': pair_details, 'nestedwrap_cells': wrap_groups,
            'answers': observed, 'errors': [row for row in observed if not row['correct']]}
    for task_id, wrong in sorted(task_errors.items(), key=lambda pair: (-len(pair[1]), pair[0])):
        task = tasks[task_id]
        result['task_errors'][task_id] = {'truth': task['design']['answer'], 'image': task['imageFilename'],
            'observed_models': sum(task_id in model_rows for model_rows in rows.values()), 'wrong_models': wrong}
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = diagnose()
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'snapshot_utc': report['snapshot_utc'], 'attempt_count': report['attempt_count'], 'observed_by_model': {model: data['observed'] for model, data in report['models'].items()}, 'error_count_by_model': {model: len(data['errors']) for model, data in report['models'].items()}}, indent=2))
