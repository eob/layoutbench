"""Produce final-only LayoutBench descriptive analysis outside the frozen protocol."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location('layoutbench_diagnostics', Path(__file__).with_name('layoutbench-diagnostics.py'))
diag = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diag)
ROOT = diag.ROOT


def summary(rows, expected):
    return {'correct': sum(row['correct'] for row in rows), 'observed': len(rows), 'expected': expected}


def verify_seal(raw, models, seal):
    assert set(seal['comparison']['model_ids']) == set(models), 'Selected roster differs from sealed comparison'
    assert seal['comparison']['count'] == raw['expected_tasks_per_model']
    source_rows = {(model, row['task_id']): row for model, values in models.items() for row in values['answers']}
    sealed_rows = {(entry['model_id'], entry['result']['task_id']): entry['result'] for entry in seal['results'] if entry['included_in_comparison']}
    assert len(sealed_rows) == sum(entry['included_in_comparison'] for entry in seal['results']), 'Duplicate sealed comparison row'
    assert set(source_rows) == set(sealed_rows), 'Sealed comparison coverage differs from checkpoint'
    for key, row in source_rows.items():
        final = sealed_rows[key]
        assert final['raw_prediction'] == row['raw']
        assert final['correct'] == row['correct']
        assert final['valid'] == (row['prediction'] is not None)
        assert final['score'] == (100 if row['correct'] else 0)


def analyze():
    raw = diag.diagnose()
    source_models = raw['models']
    expected = raw['expected_tasks_per_model']
    pending = {name: model['observed'] for name, model in source_models.items() if model['run_status'] in {'running', 'pending'}}
    models = {name: model for name, model in source_models.items() if model['observed'] == expected}
    if pending or not models:
        raise ValueError(f'Final analysis requires the runner to finish; active coverage {pending}')
    manifest = {t['taskId']: t for t in json.loads(diag.MANIFEST.read_text())}
    seal_path = diag.RUN / 'final_results.json'
    seal = json.loads(seal_path.read_text())
    verify_seal(raw, models, seal)
    catalog = json.loads((ROOT / 'config/qualitative.json').read_text())
    metadata = json.loads((diag.RUN / 'run.json').read_text())
    names = {name: config['display_name'] for name, config in metadata['model_configs'].items()}
    findings = {'snapshot_utc': raw['snapshot_utc'], 'source_run': str(diag.RUN),
                'manifest_sha256': hashlib.sha256(diag.MANIFEST.read_bytes()).hexdigest(),
                'final_results_sha256': hashlib.sha256(seal_path.read_bytes()).hexdigest(),
                'source_git_commit': seal['source_git_commit'],
                'source_attempt_count': raw['attempt_count'],
                'expected_tasks_per_model': expected, 'model_count': len(models), 'model_names': names,
                'comparison_model_ids': sorted(models),
                'availability': {name: {'included_in_comparison': name in models, 'observed': model['observed'], 'expected': expected, 'run_status': model['run_status'], 'run_reason': model['run_reason']} for name, model in source_models.items()},
                'scope': 'Descriptive fixed-corpus counts. One response per model and question; related stimuli are correlated. No causal mechanism, population estimate, or confidence interval is inferred.',
                'families': {}, 'hierarchy_pairs': {}, 'nestedwrap': {}, 'examples': {}, 'confusion_candidates': []}
    all_answers = [dict(model=model, **row) for model, values in models.items() for row in values['answers']]
    for family, definition in catalog.items():
        answers = [row for row in all_answers if row['family'] == family]
        by_truth = {}
        for truth in definition['options']:
            selected = [row for row in answers if row['truth'] == truth]
            by_truth[truth] = {'observed': len(selected), 'predictions': dict(Counter(row['prediction'] or 'invalid' for row in selected))}
        findings['families'][family] = {**summary(answers, len(answers)), 'label': definition['label'],
            'by_model': {model: value['families'][family] for model, value in models.items()}, 'semantic_confusion': by_truth}
        task_ids = sorted(task['taskId'] for task in manifest.values() if task['family'] == family)
        task_answers = {task: [row for row in answers if row['task_id'] == task] for task in task_ids}
        chosen = min(task_ids, key=lambda task: (sum(row['correct'] for row in task_answers[task]), task))
        task = manifest[chosen]
        findings['examples'][family] = {'task_id': chosen, 'image': task['imageFilename'], 'prompt': task['prompt'],
            'truth': task['design']['answer'], 'correct': sum(row['correct'] for row in task_answers[chosen]), 'observed': len(task_answers[chosen]),
            'responses': [{k: row[k] for k in ['model', 'prediction', 'correct', 'raw']} for row in task_answers[chosen]]}
    for model, values in models.items():
        assert values['hierarchy_pairs_observed'] == values['hierarchy_pairs_expected'] == 24
        findings['hierarchy_pairs'][model] = {'pair_count': 24, **values['hierarchy_pair_counts'], 'errors': values['hierarchy_pair_errors']}
        nested = [row for row in values['answers'] if row['family'] == 'nestedwrap']
        assert len(nested) == 24
        findings['nestedwrap'][model] = {'total': summary(nested, 24),
            'by_parent': {parent: summary([row for row in nested if row['factors']['parent'] == parent], 12) for parent in ['row', 'column']},
            'by_position': {str(pos + 1): summary([row for row in nested if row['variant'] == pos], 12) for pos in [0, 1]},
            'by_alignment': {alignment: summary([row for row in nested if row['truth'] == alignment], 8) for alignment in ['left', 'center', 'right']},
            'joint_cells': values['nestedwrap_cells'], 'errors': [row for row in nested if not row['correct']]}
    confusion_keys = Counter((row['family'], row['truth'], row['prediction'] or 'invalid') for row in all_answers if not row['correct'])
    for (family, truth, predicted), wrong_count in sorted(confusion_keys.items(), key=lambda item: (-item[1], item[0])):
        truth_rows = [row for row in all_answers if row['family'] == family and row['truth'] == truth]
        by_model = {}
        for model in models:
            selected = [row for row in truth_rows if row['model'] == model]
            count = sum((row['prediction'] or 'invalid') == predicted for row in selected)
            if count:
                by_model[model] = {'confusion_count': count, 'truth_observed': len(selected)}
        findings['confusion_candidates'].append({'family': family, 'truth': truth, 'predicted': predicted,
            'confusion_count': wrong_count, 'truth_observed': len(truth_rows), 'by_model': by_model})
    findings['ceiling_families_all_models'] = [family for family, value in findings['families'].items() if value['correct'] == value['observed']]
    findings['fully_correct_models_by_family'] = {family: [model for model, value in info['by_model'].items() if value['correct'] == value['observed'] == value['expected']] for family, info in findings['families'].items()}
    return findings


def markdown(findings):
    names = findings['model_names']
    lines = ['# LayoutBench final descriptive analysis', '', findings['scope'], '',
             f"{findings['model_count']} complete configurations, {findings['expected_tasks_per_model']} questions each. {len(findings['availability']) - findings['model_count']} partial configurations are excluded from this comparison and preserved in availability. Manifest SHA-256: `{findings['manifest_sha256']}`.", '',
             f"Source checkpoint commit: `{findings['source_git_commit']}`. Sealed final_results.json SHA-256: `{findings['final_results_sha256']}`. The selected roster and all comparison raw answers, validity flags, scores and correctness flags were checked against that sealed artifact.", '',
             '## Reproduction', '', 'Run `python3 tickets/evidence/feat-03-analysis/layoutbench-final-analysis.py --output-dir tickets/evidence/feat-03-analysis`. The script reads one SQLite snapshot without writes, reparses each raw response using that task’s shuffled options, and verifies valid/correct/score against the stored row. The final-only guard requires terminal model states, then includes only configurations with all 292 questions. Partial configurations remain in availability and in the source raw ledger, outside every pooled metric, example denominator and hierarchy count. Run this command from the repository root. LAYOUTBENCH_ROOT and LAYOUTBENCH_RUN optionally override the repository and run paths; the source run and manifest digest are recorded in diagnostics.json. The separately sealed source and independent publication audit remain authoritative.', '', '## Shared-image parent/child questions', '', 'Each of the 24 images has two independently asked questions: the top-level arrangement and the flow inside Field notes. This compares answers on the same image. The scenes use clear outlined section boundaries; a ceiling here does not establish general hierarchical understanding. Flat-versus-nested families use separate stimuli and cannot establish a causal effect of nesting.', '',
             '| Model | Both correct | Outer only | Inner only | Neither | Pair denominator |',
             '| --- | ---: | ---: | ---: | ---: | ---: |']
    for model, values in findings['hierarchy_pairs'].items():
        lines.append(f"| {names[model]} | {values['both']} | {values['outer_only']} | {values['inner_only']} | {values['neither']} | 24 |")
    lines += ['', '## Nested final-row alignment', '',
              'Columns below retain their own denominators; theme and copy/position variants are designed cases, not independent replications.', '',
              '| Model | All | Parent row | Parent column | First position | Second position | Left truth | Center truth | Right truth |',
              '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    show = lambda cell: f"{cell['correct']}/{cell['observed']}"
    for model, values in findings['nestedwrap'].items():
        cells = [values['total'], values['by_parent']['row'], values['by_parent']['column'], values['by_position']['1'], values['by_position']['2'], values['by_alignment']['left'], values['by_alignment']['center'], values['by_alignment']['right']]
        lines.append('| ' + names[model] + ' | ' + ' | '.join(show(cell) for cell in cells) + ' |')
    lines += ['', '## Semantic confusion candidates', '', 'Each denominator counts all responses with that semantic truth in that family. Named-model fractions count this particular wrong prediction, not total error rate. These are descriptive confusions, not inferred mechanisms.']
    for value in findings['confusion_candidates'][:10]:
        details = '; '.join(f"{names[model]}: {cell['confusion_count']}/{cell['truth_observed']}" for model, cell in value['by_model'].items())
        lines += ['', f"- {findings['families'][value['family']]['label']}: truth **{value['truth']}** was answered **{value['predicted']}** in **{value['confusion_count']}/{value['truth_observed']}** responses. {details}."]
    lines += ['', '## Complete-family ceilings', '', ', '.join(findings['families'][family]['label'] for family in findings['ceiling_families_all_models']) or 'None.', '', '## Lowest-accuracy example per family', '', 'Selection uses the same rule as the website: fewest correct answers, then task ID. These are deliberately selected examples.']
    for family, example in findings['examples'].items():
        errors = [f"{names[row['model']]} → {row['prediction'] or 'invalid'}" for row in example['responses'] if not row['correct']]
        lines += ['', f"### {findings['families'][family]['label']}: {example['task_id']}", '',
                  f"Image: `{example['image']}`. Correct answer: **{example['truth']}**. Correct responses: **{example['correct']}/{example['observed']}**.", '',
                  '; '.join(errors) if errors else 'Every configuration answered this example correctly.']
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path, default=Path('/tmp/layoutbench-final-analysis'))
    args = parser.parse_args()
    try:
        findings = analyze()
    except ValueError as error:
        parser.exit(2, str(error) + '\n')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / 'diagnostics.json').write_text(json.dumps(findings, indent=2) + '\n')
    (args.output_dir / 'observations.md').write_text(markdown(findings))
    print(args.output_dir)
