"""Recompute published grades/metrics from raw answers without benchmark imports."""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
CHOICES = dict(flow=4, distribute=5, align=4, gap=7, pad=5, columns=3,
               textjustify=4, headerpad=3, regionpad=5, tablepad=4)
KEYS = dict(gapnum=['gap_px'], headerpx=['above_px', 'below_px'], regionpx=['pad_px'])


def unique_object(pairs):
    if len(dict(pairs)) != len(pairs):
        raise ValueError('duplicate key')
    return dict(pairs)


def parse(raw, family):
    answer = json.loads(raw, object_pairs_hook=unique_object)
    if family in CHOICES:
        if not isinstance(answer, dict) or set(answer) != {'choice'} or not isinstance(answer['choice'], str):
            raise ValueError('invalid choice object')
        answer = {'choice': answer['choice'].strip().upper()}
        if answer['choice'] not in 'ABCDEFG'[:CHOICES[family]]:
            raise ValueError('invalid letter')
    elif (not isinstance(answer, dict) or set(answer) != set(KEYS[family])
          or any(type(x) is not int or not 0 <= x <= 800 for x in answer.values())):
        raise ValueError('invalid numeric object')
    return answer


def same(actual, expected):
    if type(expected) in (int, float):
        assert type(actual) in (int, float) and math.isclose(actual, expected, abs_tol=1e-10), (actual, expected)
    else:
        assert actual == expected, (actual, expected)


def check_geometry(manifest):
    checked = 0
    for task in manifest.values():
        family, design = task['family'], task['design']
        boxes = {r['role']: r for r in task['rendered']['regions']}
        measured = None
        if family in ('gap', 'gapnum', 'pad'):
            items = [r for r in task['rendered']['regions'] if r['role'] == 'item']
            if family == 'pad':
                stage = boxes['stage']
                measured = min(min(r['x']-stage['x'], r['y']-stage['y'],
                                   stage['x']+stage['width']-r['x']-r['width'],
                                   stage['y']+stage['height']-r['y']-r['height']) for r in items)
            else:
                axis, size = ('x', 'width') if design['direction'] == 'row' else ('y', 'height')
                items.sort(key=lambda r: r[axis])
                gaps = [b[axis]-a[axis]-a[size] for a,b in zip(items,items[1:])]
                assert max(gaps)-min(gaps) < 0.2
                measured = min(gaps)
        elif family in ('headerpad', 'headerpx'):
            above = boxes['header']['y']-boxes['card']['y']-1
            below = boxes['tbody']['y']-boxes['header']['y']-boxes['header']['height']
            if family == 'headerpx':
                assert task['groundTruth'] == dict(above_px=round(above), below_px=round(below))
            else:
                assert task['groundTruth']['choice'] == ('A' if above>below else 'B' if below>above else 'C')
            checked += 1
            continue
        elif family in ('regionpad', 'regionpx'):
            c = boxes['content']
            frame = boxes['card'] if design['bordered'] else dict(x=0,y=0,width=800,height=600)
            border = 1 if design['bordered'] else 0
            pads = [c['x']-frame['x']-border, c['y']-frame['y']-border,
                    frame['x']+frame['width']-border-c['x']-c['width'],
                    frame['y']+frame['height']-border-c['y']-c['height']]
            assert max(pads)-min(pads) < 0.2
            measured = min(pads)
        elif family == 'tablepad':
            texts = {r['id']: r for r in task['rendered']['regions'] if r['role']=='celltext'}
            pads = [texts[r['id']]['x']-r['x']-1 for r in task['rendered']['regions'] if r['role']=='cell']
            assert max(pads)-min(pads) < 0.2
            measured = min(pads)
        if measured is not None:
            expected = (next(iter(task['groundTruth'].values())) if family in KEYS else
                        int(design['options'][ord(task['groundTruth']['choice'])-65][:-2]))
            assert abs(measured-expected) < 0.2, (task['taskId'], measured, expected)
            checked += 1
    return checked


def audit(path):
    report = json.loads(path.read_text())
    manifest = {x['taskId']: x for x in json.loads((ROOT / report['dataset_manifest']).read_text())}
    assert len(manifest) == report['expected_task_count'] == 208
    assert check_geometry(manifest) == 128
    groups = defaultdict(list)
    for observation in report['results']:
        row = observation['result']
        task, family = manifest[row['task_id']], row['family']
        assert row['ground_truth'] == task['groundTruth'] and row['group_id'] == task['groupId']
        assert row['prompt_sha256'] == hashlib.sha256(task['prompt'].encode()).hexdigest()
        try:
            answer = parse(row['raw_prediction'], family)
        except (ValueError, TypeError):
            answer = None
        assert row['valid'] == (answer is not None)
        assert row['prediction'] == (answer or {})
        truth = task['groundTruth']
        if family in CHOICES:
            correct = answer is not None and answer == truth
            same(row['correct'], correct)
            same(row['score'], 100 if correct else 0)
            for key in ('err', 'key_errors', 'tight_score', 'within_bands'):
                same(row[key], None)
        else:
            errors = {key: abs(answer[key] - truth[key]) for key in KEYS[family]} if answer else None
            error = statistics.mean(errors.values()) if errors else None
            same(row['correct'], None)
            same(row['err'], error)
            same(row['key_errors'], errors)
            for field, ceiling in [('score', 16), ('tight_score', 4)]:
                same(row[field], 100 * max(0, 1 - error / ceiling) if answer else 0)
            same(row['within_bands'], {str(b): max(errors.values()) <= b for b in (1, 2, 4, 8)} if answer else None)
        if observation['included_in_comparison']:
            groups[observation['model_id'], family].append(row)
    summaries = {}
    for model in report['models']:
        model_id, config = model['model_id'], model['model_config']
        summaries[model_id] = {}
        for family, stored in model['families'].items():
            rows = groups[model_id, family]
            n = len(rows)
            valid = [r for r in rows if r['valid']]
            same(stored['count'], n)
            same(stored['valid_count'], len(valid))
            same(stored['invalid_count'], n - len(valid))
            same(stored['validity_rate'], len(valid) / n)
            same(stored['group_count'], len({r['group_id'] for r in rows}))
            if family in CHOICES:
                correct = sum(r['correct'] for r in rows)
                same(stored['accuracy'], correct / n)
                same(stored['correct_count'], correct)
                same(stored['chance_accuracy'], 1 / CHOICES[family])
                confusion = {c: dict(Counter(r['prediction']['choice'] if r['valid'] else 'invalid'
                                            for r in rows if r['ground_truth']['choice'] == c))
                             for c in 'ABCDEFG'[:CHOICES[family]]}
                same(stored['confusion'], confusion)
                summaries[model_id][family] = dict(correct=correct, count=n, accuracy=correct/n)
                if family in ('gap', 'pad', 'regionpad', 'tablepad'):
                    values = defaultdict(Counter)
                    for row in rows:
                        options = manifest[row['task_id']]['design']['options']
                        truth = options[ord(row['ground_truth']['choice']) - 65]
                        predicted = options[ord(row['prediction']['choice']) - 65] if row['valid'] else 'invalid'
                        values[truth][predicted] += 1
                    summaries[model_id][family]['value_confusion'] = {k: dict(v) for k,v in values.items()}
            else:
                errors = [r['err'] for r in valid]
                same(stored['mean_score'], statistics.mean(r['score'] for r in rows))
                same(stored['mean_tight_score'], statistics.mean(r['tight_score'] for r in rows))
                for field, value in [('mean_err', statistics.mean(errors) if errors else None),
                                     ('median_err', statistics.median(errors) if errors else None),
                                     ('p90_err', statistics.quantiles(errors, n=10, method='inclusive')[8] if len(errors)>1 else errors[0] if errors else None)]:
                    same(stored[field], value)
                for key in KEYS[family]:
                    if valid:
                        same(stored['mean_key_errors'][key], statistics.mean(r['key_errors'][key] for r in valid))
                        same(stored['key_known_count'][key], len(valid))
                for band in ('1', '2', '4', '8'):
                    same(stored['band_hit_rate'][band], sum(r['within_bands'][band] for r in valid)/len(valid) if valid else None)
                constant = [statistics.mean(abs(16 - value) for value in r['ground_truth'].values()) for r in rows]
                same(stored['constant16_mean_err'], statistics.mean(constant))
                same(stored['constant16_mean_score'], statistics.mean(100*max(0,1-e/16) for e in constant))
                summaries[model_id][family] = {k: stored[k] for k in ('count','valid_count','mean_score','mean_err','p90_err','constant16_mean_score')}
            costs = []
            for row in rows:
                if not row['cost_estimated'] and row['unmetered_attempts'] == 0 and type(row['input_tokens']) is int and type(row['output_tokens']) is int:
                    cost = (row['input_tokens']*config['input_per_m'] + row['output_tokens']*config['output_per_m'])/1e6
                    same(row['cost_usd'], cost)
                    costs.append(cost)
            same(stored['cost_known_response_count'], len(costs))
            same(stored['mean_api_response_cost_usd'], statistics.mean(costs) if len(costs)==n else None)
            latencies = [r['latency_sec'] for r in rows if r['latency_sec'] is not None]
            same(stored['latency_known_response_count'], len(latencies))
            same(stored['mean_latency_sec'], statistics.mean(latencies) if len(latencies)==n else None)
    attempts = [json.loads(line) for line in (path.parent/'attempts.jsonl').read_text().splitlines()]
    same(report['campaign']['spent_cost_usd'], sum(row['cost_usd'] for row in attempts))
    return dict(release=report['release'], run_id=report['run_id'], response_count=len(report['results']),
                source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), models=summaries)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('final_results', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    summary = audit(args.final_results)
    if args.output:
        args.output.write_text(json.dumps(summary, indent=2)+'\n')
    print(f"Independently replayed {summary['response_count']} raw answers and every family metric for {len(summary['models'])} models in {summary['release']}.")
