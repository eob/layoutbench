"""Replay the sealed thirteen-model continuation and publish descriptive evidence."""
import argparse
import csv
import importlib.util
import json
import os
from pathlib import Path

ROOT = Path(os.environ.get('LAYOUTBENCH_ROOT', Path.cwd())).resolve()
os.environ.setdefault('LAYOUTBENCH_RUN', str(ROOT / 'results/runs/full-roster/0.3.0/qualitative-20260917'))
spec = importlib.util.spec_from_file_location('prior_analysis', ROOT / 'tickets/evidence/feat-03-analysis/layoutbench-final-analysis.py')
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


def generate(output):
    findings = analysis.analyze()
    if findings['model_count'] != 13 or any(value['observed'] != 292 or value['run_status'] != 'complete' for value in findings['availability'].values()):
        raise ValueError('The full-roster analysis requires thirteen complete configurations.')
    raw = analysis.diag.diagnose()
    seal = json.loads((analysis.diag.RUN / 'final_results.json').read_text())
    sealed_models = {model['model_id']: model for model in seal['models']}
    metrics = []
    for family, definition in findings['families'].items():
        for model_id in findings['comparison_model_ids']:
            rows = [row for row in raw['models'][model_id]['answers'] if row['family'] == family]
            valid = sum(row['prediction'] is not None for row in rows)
            correct = sum(row['correct'] for row in rows)
            expected = sealed_models[model_id]['families'][family]
            assert (len(rows), valid, correct, correct / len(rows)) == (expected['count'], expected['valid_count'], expected['correct_count'], expected['accuracy'])
            assert len(rows) - valid == expected['invalid_count']
            metrics.append({'model_id': model_id, 'display_name': findings['model_names'][model_id], 'family': family,
                            'family_label': definition['label'], 'correct': correct, 'count': len(rows),
                            'valid': valid, 'invalid': len(rows) - valid, 'accuracy': correct / len(rows)})
    output.mkdir(parents=True, exist_ok=True)
    (output / 'diagnostics.json').write_text(json.dumps(findings, indent=2) + '\n')
    report = analysis.markdown(findings).replace(
        'Run `python3 tickets/evidence/feat-03-analysis/layoutbench-final-analysis.py --output-dir tickets/evidence/feat-03-analysis`.',
        'Run `LAYOUTBENCH_RUN=results/runs/full-roster/0.3.0/qualitative-20260917 python3 tickets/evidence/feat-04-analysis/run-analysis.py --output-dir tickets/evidence/feat-04-analysis`. This wrapper uses the unchanged independently replaying analyzer filed with the earlier cohort, checks all 260 model-family cells against the new seal, and generates the full family CSV and Claude table.').replace(
        '0 partial configurations are excluded from this comparison and preserved in availability.',
        'All thirteen configurations have complete coverage.')
    (output / 'observations.md').write_text(report)
    with (output / 'model-family-results.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(metrics[0]))
        writer.writeheader()
        writer.writerows(metrics)
    claude = [model for model in findings['comparison_model_ids'] if model.startswith('claude-')]
    lines = ['# Claude family results', '', 'Each fraction is correct answers / scored questions. Invalid answers remain in the denominator. All four configurations completed the same 292 questions; there is no combined score.', '',
             '| Family | ' + ' | '.join(findings['model_names'][model] for model in claude) + ' |',
             '| --- | ' + ' | '.join('---:' for _ in claude) + ' |']
    for family, definition in findings['families'].items():
        cells = [definition['by_model'][model] for model in claude]
        lines.append('| ' + definition['label'] + ' | ' + ' | '.join(f"{cell['correct']}/{cell['observed']}" for cell in cells) + ' |')
    lines += ['', 'Source: `diagnostics.json`, `families.*.by_model`. The generation command and sealed source digest are recorded in `observations.md`.']
    (output / 'claude-family-results.md').write_text('\n'.join(lines) + '\n')
    print(f"Verified {len(metrics)} model-family cells; wrote {output}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'tickets/evidence/feat-04-analysis')
    args = parser.parse_args()
    generate(args.output_dir)
