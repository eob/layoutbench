"""Independent audit: standard library only, no benchmark parsing/grading imports."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
import argparse
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import subprocess

ROOT = Path(__file__).resolve().parents[2] if Path(__file__).parent.name == 'evidence' else Path.cwd()
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run', default='results/runs/full-roster/0.3.0/qualitative-20260917')
parser.add_argument('--original-run', default='results/runs/0.3.0/qualitative-20260917')
parser.add_argument('--original-sealed-commit', default='ac17659d69c5c8fbd60abfade2b14edb06826b86')
parser.add_argument('--sealed-commit', required=True)
parser.add_argument('--out', default='/tmp/layoutbench-full-roster-audit.json')
args = parser.parse_args()
RUN, ORIGINAL = ROOT / args.run, ROOT / args.original_run
SEALED_COMMIT, ORIGINAL_COMMIT = args.sealed_commit, args.original_sealed_commit
OUT = Path(args.out)
def read(path): return json.loads(path.read_text())
def hash_bytes(data): return hashlib.sha256(data).hexdigest()
def stable_hash(value): return hash_bytes(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode())
def timestamp(value): return datetime.fromisoformat(value.replace('Z', '+00:00'))
def require(condition, message):
    if not condition: raise AssertionError(message)
def identical(actual, expected, label):
    require(actual == expected, f'{label}: {actual!r} != {expected!r}')
def numeric(actual, expected, label):
    if expected is None: identical(actual, None, label)
    else: require(type(actual) in (float, int) and math.isfinite(actual) and abs(actual - expected) <= 1e-10, label)
def strict_object(pairs):
    require(len(dict(pairs)) == len(pairs), 'Duplicate raw JSON key')
    return dict(pairs)
def parse(raw, option_count):
    try:
        parsed = json.loads(raw, object_pairs_hook=strict_object)
        if not isinstance(parsed, dict) or set(parsed) != {'choice'} or not isinstance(parsed['choice'], str): return None
        answer = parsed['choice'].strip().upper()
        return {'choice': answer} if len(answer) == 1 and answer in 'ABCDEF'[:option_count] else None
    except (ValueError, TypeError, AssertionError): return None

parser_controls = [
    ('{"choice":"A"}', 3, {'choice': 'A'}),
    ('{"choice":" b "}', 3, {'choice': 'B'}),
    ('{"choice":""}', 3, None),
    ('{"choice":"AB"}', 3, None),
    ('{"choice":"BC"}', 3, None),
    ('{"choice":"D"}', 3, None),
    ('{"choice":true}', 3, None),
    ('{"choice":"A","choice":"B"}', 3, None),
    ('{"choice":"A","explanation":"x"}', 3, None),
]
for raw, option_count, expected in parser_controls:
    identical(parse(raw, option_count), expected, f'Independent parser control {raw}')

def check_lineage(original_attempts, continued_attempts, original_final_json, continued_final_json, missing):
    identical(continued_attempts[:len(original_attempts)], original_attempts, 'Historical attempt prefix')
    for key, raw in original_final_json.items():
        identical(continued_final_json.get(key), raw, f'Historical final JSON {key}')
    for attempt in continued_attempts[len(original_attempts):]:
        require((attempt['model_id'], attempt['task_id']) in missing, 'Appended task is outside missing Claude set')

release = read(ROOT / 'releases/0.3.0.json')
manifest_path = ROOT / release['dataset_manifest']
manifest = read(manifest_path)
tasks = {t['taskId']: t for t in manifest}
catalog = read(ROOT / 'config/qualitative.json')
models = {m['id']: m for m in read(ROOT / 'config/models.all.json')['models'] if m.get('enabled', True)}
run, summary = read(RUN / 'run.json'), read(RUN / 'summary.json')
identical(len(tasks), 292, 'Question count')
identical(len(models), 13, 'Requested model count')
identical(set(t['family'] for t in manifest), set(catalog), 'Family set')
identical(len(set(t['imageFilename'] for t in manifest)), 250, 'Image count')
identical(summary['status'], 'complete', 'Complete terminal runner')
require(not (RUN / 'state.sqlite3-wal').exists() or (RUN / 'state.sqlite3-wal').stat().st_size == 0, 'Runner WAL remains live')
committed = subprocess.check_output(['git', 'show', f"{release['dataset_git_commit']}:{release['dataset_manifest']}"], cwd=ROOT)
identical(committed, manifest_path.read_bytes(), 'Committed manifest')
digest = hashlib.sha256(b'layoutbench-dataset-1\n')
image_hashes = {}
for task in sorted(manifest, key=lambda t: t['taskId']):
    name = task['imageFilename']
    if name not in image_hashes: image_hashes[name] = hashlib.sha256((manifest_path.parent / name).read_bytes()).digest()
    identical(image_hashes[name].hex(), task['imageSha256'], 'Frozen image hash')
    metadata = {k: v for k, v in task.items() if k not in {'imagePath', 'imageFilename'}}
    digest.update(json.dumps(metadata, sort_keys=True, ensure_ascii=False, allow_nan=False).encode())
    digest.update(image_hashes[name])
identical(digest.hexdigest(), release['dataset_fingerprint'], 'Dataset fingerprint')
protocol = hashlib.sha256(b'layoutbench-protocol-1\n')
for name in ('prompts.json', 'protocol.py', 'evaluator.py', 'statistics.py', 'reporting.py', 'validate_dataset.py', 'qualitative_validation.py', '../config/qualitative.json', 'finalize.py', 'providers.py'):
    protocol.update((ROOT / 'baseline' / name).read_bytes())
identical(protocol.hexdigest(), release['evaluation_protocol_fingerprint'], 'Protocol fingerprint')
for record in (run, summary):
    identical(record['dataset_fingerprint'], digest.hexdigest(), 'Run dataset')
    identical(record['evaluation_protocol'], protocol.hexdigest(), 'Run protocol')
    identical(record['expected_task_count'], 292, 'Run task count')
    identical(record['mock'], False, 'Live observations')

with sqlite3.connect(f'file:{RUN}/state.sqlite3?mode=ro&immutable=1', uri=True) as connection:
    identical(connection.execute('PRAGMA integrity_check').fetchone()[0], 'ok', 'SQLite integrity')
    attempts = [dict(sequence=seq, attempt_id=aid, run_id=rid, model_id=mid, task_id=tid, result=json.loads(raw), cost_usd=cost, created_at=at)
                for seq,aid,rid,mid,tid,raw,cost,at in connection.execute('SELECT rowid,attempt_id,run_id,model_id,task_id,result_json,cost_usd,created_at FROM attempts ORDER BY rowid')]
    current_json = {(m,t): raw for m,t,raw in connection.execute('SELECT model_id,task_id,result_json FROM results')}
    current = {key: json.loads(raw) for key,raw in current_json.items()}
    sql_attempts = list(connection.execute('SELECT rowid,attempt_id,run_id,model_id,task_id,result_json,cost_usd,created_at FROM attempts ORDER BY rowid'))
    configs = {m: json.loads(raw) for m,raw in connection.execute('SELECT model_id,config_json FROM models')}
identical(attempts, [json.loads(line) for line in (RUN / 'attempts.jsonl').read_text().splitlines()], 'Attempt export')
identical(configs, run['model_configs'], 'Archived model configurations')
identical(set(configs), set(models), 'Checkpoint model roster')
original_run, original_seal = read(ORIGINAL/'run.json'), read(ORIGINAL/'finalization.json')
for name, expected_hash in original_seal['artifact_sha256'].items():
    data = (ORIGINAL/name).read_bytes()
    identical(hash_bytes(data), expected_hash, f'Original immutable artifact {name}')
    committed = subprocess.check_output(['git', 'show', f'{ORIGINAL_COMMIT}:{ORIGINAL.relative_to(ROOT)}/{name}'], cwd=ROOT)
    identical(data, committed, f'Original committed artifact {name}')
identical((ORIGINAL/'finalization.json').read_bytes(), subprocess.check_output(['git', 'show', f'{ORIGINAL_COMMIT}:{ORIGINAL.relative_to(ROOT)}/finalization.json'], cwd=ROOT), 'Original committed seal')
for name in ('config/models.all.json', 'releases/0.3.0.json'):
    identical((ROOT/name).read_bytes(), subprocess.check_output(['git','show',f'{ORIGINAL_COMMIT}:{name}'],cwd=ROOT), f'Unchanged frozen configuration {name}')
original_bytes = (ORIGINAL/'attempts.jsonl').read_bytes()
require((RUN/'attempts.jsonl').read_bytes().startswith(original_bytes), 'Historical JSONL byte prefix')
original_attempts = [json.loads(line) for line in original_bytes.splitlines()]
identical(len(original_attempts), 3515, 'Original attempt count')
with sqlite3.connect(f'file:{ORIGINAL}/state.sqlite3?mode=ro&immutable=1', uri=True) as connection:
    original_sql = list(connection.execute('SELECT rowid,attempt_id,run_id,model_id,task_id,result_json,cost_usd,created_at FROM attempts ORDER BY rowid'))
    original_json = {(m,t): raw for m,t,raw in connection.execute('SELECT model_id,task_id,result_json FROM results')}
    original_configs = {m:json.loads(raw) for m,raw in connection.execute('SELECT model_id,config_json FROM models')}
identical(sql_attempts[:len(original_sql)], original_sql, 'Historical SQLite byte-value prefix')
identical(configs, original_configs, 'Unchanged archived model configurations')
original_finals = {key:raw for key,raw in original_json.items() if not json.loads(raw).get('error') or json.loads(raw)['error_kind']=='invalid_response'}
identical(len(original_finals),3512,'Original final answer count')
claude = {mid for mid, config in configs.items() if config['provider']=='anthropic'}
identical(len(claude),4,'Continuation Claude roster')
missing = {(mid,tid) for mid in configs for tid in tasks} - set(original_finals)
identical(len(missing),284,'Missing final answer count')
identical({mid for mid,_ in missing},claude,'Only Claude missing answers')
check_lineage(original_attempts, attempts, original_finals, current_json, missing)
identical({k:v for k,v in run.items() if k not in ('invocations','continuation')}, {k:v for k,v in original_run.items() if k!='invocations'}, 'Unchanged campaign metadata')
identical(run['invocations'][:len(original_run['invocations'])],original_run['invocations'],'Historical invocation prefix')
require(len(run['invocations']) > len(original_run['invocations']), 'Missing continuation invocation')
for invocation in run['invocations'][len(original_run['invocations']):]:
    identical({m['id']:m for m in invocation['models']},{m:configs[m] for m in claude},'Continuation invocation models')
    identical(invocation['runner_git_dirty'],False,'Clean continuation runner')
    identical(invocation['status'],'complete','Complete continuation invocation')
    identical(invocation['budget_usd'],original_run['invocations'][-1]['budget_usd'],'Unchanged cumulative budget')
    identical(invocation['max_tasks'],None,'Unrestricted completion invocation')
    identical(invocation['request_timeouts_sec'],{m:original_run['invocations'][-1]['request_timeouts_sec'][m] for m in claude},'Unchanged request timeouts')
lineage=run['continuation']
for field,expected in (('source_run_path',str(ORIGINAL.relative_to(ROOT))),('source_artifact_commit',ORIGINAL_COMMIT),('source_finalization_sha256',hash_bytes((ORIGINAL/'finalization.json').read_bytes())),('copied_final_response_count',3512),('copied_attempt_count',3515)):
    identical(lineage[field],expected,f'Explicit continuation lineage {field}')
start, end = timestamp(run['created_at']), timestamp(summary['updated_at'])
require(timestamp(original_run['invocations'][-1]['finished_at']) <= timestamp(lineage['copied_at']) <= timestamp(run['invocations'][len(original_run['invocations'])]['started_at']), 'Continuation copy chronology')
latest, finals, source_attempts = {}, {}, {}
metered, allowance, ledger = Decimal(0), Decimal(0), Decimal(0)
http_requests = unmetered_requests = 0
uncertain = []
errors = Counter()
for attempt in attempts:
    mid, tid, row = attempt['model_id'], attempt['task_id'], attempt['result']
    key = (mid, tid)
    identical(attempt['run_id'],run['run_id'],'Campaign identity')
    require(any(mid in {m['id'] for m in invocation['models']} and timestamp(invocation['started_at']) <= timestamp(row['recorded_at']) <= timestamp(invocation['finished_at']) for invocation in run['invocations']), 'Response outside model invocation')
    require(key not in finals, f'Attempt follows a final answer: {key}')
    require(mid in models and tid in tasks, 'Unknown observation identity')
    require(start <= timestamp(attempt['created_at']) <= end, 'Attempt chronology')
    require(start <= timestamp(row['recorded_at']) <= end, 'Response chronology')
    config, task = configs[mid], tasks[tid]
    for name in ('model', 'provider', 'api_key_env', 'max_output_tokens', 'input_per_m', 'output_per_m'):
        identical(config[name], models[mid][name], f'Configured {name}')
    identical(config.get('base_url'), models[mid].get('base_url'), 'Configured endpoint')
    identical(row['model_name'], config['model'], 'Response requested model')
    identical(row['provider'], config['provider'], 'Response provider')
    identical(row['task_id'], tid, 'Response task')
    identical(row['ground_truth'], task['groundTruth'], 'Ground truth')
    identical(row['family'], task['family'], 'Task family')
    identical(row['group_id'], task['groupId'], 'Task image group')
    identical(row['prompt_sha256'], hash_bytes(task['prompt'].encode()), 'Prompt digest')
    identical(Path(row['image_path']).name, task['imageFilename'], 'Image sent')
    for field in ('request_attempts', 'unmetered_attempts'):
        require(type(row[field]) is int and row[field] >= 0, 'Request accounting type')
    require(row['request_attempts'] >= 1 and row['unmetered_attempts'] <= row['request_attempts'], 'Request accounting bounds')
    http_requests += row['request_attempts']; unmetered_requests += row['unmetered_attempts']
    for field in ('input_tokens', 'output_tokens'):
        require(row[field] is None or type(row[field]) is int and row[field] >= 0, 'Usage count type')
    measured = (Decimal(row['input_tokens'] or 0) * Decimal(str(config['input_per_m'])) + Decimal(row['output_tokens'] or 0) * Decimal(str(config['output_per_m']))) / Decimal(1000000)
    reserve = (Decimal(5000) * Decimal(str(config['input_per_m'])) + Decimal(config['max_output_tokens']) * Decimal(str(config['output_per_m']))) / Decimal(1000000)
    extra = reserve * Decimal(row['unmetered_attempts'])
    numeric(row['cost_usd'], float(measured + extra), 'Response token/reserve cost')
    numeric(attempt['cost_usd'], float(measured + extra), 'Ledger token/reserve cost')
    identical(row['cost_estimated'], bool(row['unmetered_attempts']), 'Estimated-cost flag')
    metered += measured; allowance += extra; ledger += Decimal(str(attempt['cost_usd']))
    if row['unmetered_attempts']:
        uncertain.append({'model_id':mid,'task_id':tid,'http_requests':row['request_attempts'],'unmetered_requests':row['unmetered_attempts'],'reserve_usd':str(extra),'final_error_kind':row['error_kind']})
    latest[key] = row
    if row.get('error') and row['error_kind'] != 'invalid_response':
        errors[row['error_kind']] += 1
        continue
    parsed = parse(row['raw_prediction'], len(task['design']['options']))
    correct = parsed is not None and parsed == task['groundTruth']
    identical(row['prediction'], parsed or {}, 'Raw prediction replay')
    identical(row['valid'], parsed is not None, 'Validity replay')
    identical(row['correct'], correct, 'Correctness replay')
    identical(row['score'], 100 if correct else 0, 'Score replay')
    identical(row['error_kind'], None if parsed else 'invalid_response', 'Final-answer error taxonomy')
    require(type(row['latency_sec']) in (int,float) and math.isfinite(row['latency_sec']) and row['latency_sec'] > 0, 'Final latency')
    finals[key] = row; source_attempts[key] = attempt['attempt_id']
identical(latest, current, 'Checkpoint current results')
numeric(summary['spent_cost_usd'], float(ledger), 'Summary spending')
identical(len(finals), 3796, 'Final observation count')
identical(set(finals)-set(original_finals),missing,'Exactly missing Claude final answers appended')
identical(set(current),set(finals),'Every current observation is final')
require(len(attempts) >= 3799, 'Full ledger lost historical errors')
roster = sorted(m for m in configs if sum(k[0] == m for k in finals) == 292)
identical(len(roster), 13, 'Complete comparison roster')
families, pairs = {}, {}
for mid in configs:
    rows = [row for (m,_),row in finals.items() if m == mid]
    card = read(RUN / f'scorecard_{mid}.json')
    identical({r['task_id']: r for r in card['tasks']}, {r['task_id']: r for r in rows}, 'Scorecard rows')
    identical(summary['models'][mid]['completed'], len(rows), 'Model completion count')
    identical({r['task_id'] for r in rows}, set(tasks), 'Full question coverage')
    identical(summary['models'][mid]['status'],'complete','Complete model status')
    families[mid] = {}
    paired = defaultdict(dict)
    for family,spec in catalog.items():
        selected = [r for r in rows if r['family'] == family]
        n = len(selected); valid = sum(r['valid'] for r in selected); correct = sum(r['correct'] for r in selected)
        metrics = card['families'][family]
        for field,value in (('count',n),('valid_count',valid),('invalid_count',n-valid),('correct_count',correct)):
            identical(metrics[field], value, f'Raw family {field}')
        numeric(metrics['accuracy'], correct/n if n else None, 'Raw family accuracy')
        semantic = defaultdict(Counter)
        for row in selected:
            task=tasks[row['task_id']]; options=task['design']['options']
            semantic[options[ord(task['groundTruth']['choice'])-65]][options[ord(row['prediction']['choice'])-65] if row['valid'] else 'invalid'] += 1
            if family in ('topflow','nestedflow'): paired[row['group_id']][family] = row['correct']
        families[mid][family]={'correct':correct,'count':n,'valid':valid,'semantic_confusion':{k:dict(v) for k,v in semantic.items()}}
    counts=Counter('both' if p['topflow'] and p['nestedflow'] else 'outer_only' if p['topflow'] else 'inner_only' if p['nestedflow'] else 'neither' for p in paired.values() if set(p)=={'topflow','nestedflow'})
    pairs[mid]={key:counts[key] for key in ('both','outer_only','inner_only','neither')}

seal_checked = False
require((RUN/'finalization.json').exists(), 'Continuation seal is required')
seal, report = read(RUN/'finalization.json'), read(RUN/'final_results.json')
expected_artifacts = {'state.sqlite3','run.json','summary.json','attempts.jsonl','final_results.json', *[f'scorecard_{mid}.json' for mid in configs]}
identical(set(seal['artifact_sha256']),expected_artifacts,'Complete seal inventory')
identical(seal['finalizer_git_dirty'],False,'Clean finalizer source identity')
for name,digest in seal['artifact_sha256'].items():
    identical(hash_bytes((RUN/name).read_bytes()), digest, f'Sealed {name}')
    committed = subprocess.check_output(['git','show',f'{SEALED_COMMIT}:{RUN.relative_to(ROOT)}/{name}'],cwd=ROOT)
    identical(committed,(RUN/name).read_bytes(),f'Committed sealed {name}')
    if name != 'final_results.json':
        source = subprocess.check_output(['git','show',f"{seal['source_git_commit']}:{RUN.relative_to(ROOT)}/{name}"],cwd=ROOT)
        identical(source,(RUN/name).read_bytes(),f'Committed raw source {name}')
committed_seal = subprocess.check_output(['git','show',f'{SEALED_COMMIT}:{RUN.relative_to(ROOT)}/finalization.json'],cwd=ROOT)
identical(committed_seal,(RUN/'finalization.json').read_bytes(),'Committed seal bytes')
identical(seal['comparison'],report['comparison'],'Seal cohort and report cohort')
identical(report['comparison']['scope'], 'full', 'Publication scope')
identical(report['comparison']['model_ids'], roster, 'Published comparison roster')
identical(set(report['comparison']['task_ids']), set(tasks), 'Published full question set')
identical(report['comparison']['count'],292,'Publication question count')
identical(report['comparison']['cohort_fingerprint'],hash_bytes(json.dumps(sorted(tasks)).encode()),'Publication cohort fingerprint')
identical(len(report['results']),len(finals),'All retained final responses')
identical({(w['model_id'],w['result']['task_id']) for w in report['results']},set(finals),'No duplicate or omitted final observations')
identical({m['model_id'] for m in report['models']},set(configs),'Published full requested roster')
identical(len(report['models']),len(configs),'No duplicate published models')
for field,value in (('final_response_count',len(finals)),('attempt_count',len(attempts)),('infrastructure_attempt_count',sum(errors.values())),('estimated_cost_attempt_count',len(uncertain))): identical(report['campaign'][field],value,f'Published campaign {field}')
identical(report['campaign']['infrastructure_error_kinds'],dict(errors),'Published credit failures')
numeric(report['campaign']['spent_cost_usd'],float(ledger),'Published campaign spending')
identical(report['attempts'],attempts,'Sealed attempt records')
for wrapper in report['results']:
    key=(wrapper['model_id'],wrapper['result']['task_id'])
    identical(wrapper['result'],finals[key],'Sealed response')
    identical(wrapper['source_attempt_id'],source_attempts[key],'Source attempt identity')
    identical(wrapper['result_sha256'],stable_hash(finals[key]),'Sealed canonical response hash')
    identical(wrapper['included_in_comparison'],key[0] in roster,'Observation inclusion')
for model in report['models']:
    mid=model['model_id'];included=mid in roster
    identical(model['included_in_comparison'],included,'Model inclusion')
    identical(model['observed_task_count'],292,'Published observed coverage')
    identical(model['comparison_task_count'],292 if included else 0,'Published comparison coverage')
    identical(model['availability_status'],'complete' if included else 'partial','Published availability')
    identical(set(model['families']),set(catalog),'Published family set')
    for family,stored in model['families'].items():
        rows=[r for (m,_),r in finals.items() if m==mid and r['family']==family] if included else []
        n=len(rows);valid=sum(r['valid'] for r in rows);correct=sum(r['correct'] for r in rows)
        for field,value in (('count',n),('valid_count',valid),('invalid_count',n-valid),('correct_count',correct),('group_count',len({r['group_id'] for r in rows}))): identical(stored[field],value,f'Published {field}')
        numeric(stored['accuracy'],correct/n if n else None,'Published accuracy')
        numeric(stored['validity_rate'],valid/n if n else None,'Published validity')
        numeric(stored['chance_accuracy'],1/len(catalog[family]['options']),'Chance baseline')
        labels='ABCDEF'[:len(catalog[family]['options'])]
        confusion={label:dict(Counter(r['prediction']['choice'] if r['valid'] else 'invalid' for r in rows if r['ground_truth']['choice']==label)) for label in labels}
        identical(stored['confusion'],confusion,'Published label confusion')
        known=[r for r in rows if not r['cost_estimated'] and r['unmetered_attempts']==0 and r['input_tokens'] is not None and r['output_tokens'] is not None]
        costs=[(r['input_tokens']*configs[mid]['input_per_m']+r['output_tokens']*configs[mid]['output_per_m'])/1e6 for r in known]
        numeric(stored['mean_api_response_cost_usd'],sum(costs)/n if n and len(known)==n else None,'Published metered family mean')
        identical(stored['cost_known_response_count'],len(known),'Published metered response count')
        numeric(stored['mean_latency_sec'],sum(r['latency_sec'] for r in rows)/n if n else None,'Published latency mean')
        identical(stored['latency_known_response_count'],n,'Published latency coverage')
seal_checked=True
output={'audited_at':datetime.now(timezone.utc).isoformat(),'sealed_artifact_commit':SEALED_COMMIT,'dataset_fingerprint':release['dataset_fingerprint'],'protocol_fingerprint':protocol.hexdigest(),'question_count':292,'unique_images':250,'requested_models':13,'complete_models':roster,'full_comparison_responses':len(roster)*292,'retained_partial_claude_responses':0,'final_responses':len(finals),'runner_attempts':len(attempts),'http_requests':http_requests,'infrastructure_error_kinds':dict(errors),'invalid_final_responses':sum(not r['valid'] for r in finals.values()),'recorded_metered_subtotal_usd':str(metered),'unmetered_reserve_allowance_usd':str(allowance),'ledger_total_decimal_usd':str(ledger),'unmetered_http_requests':unmetered_requests,'uncertain_attempts':uncertain,'seal_checked':seal_checked,'discrepancies':[],'family_metrics_all_retained_models':families,'hierarchy_pairs_all_retained_models':pairs,'limits':'Independent replay uses retained raw answer text, reported usage, and frozen inputs. Recorded token-rate estimates and conservative reserves are not provider invoices. No inference requests were made; provider identity/envelopes and individual internal retry errors are not independently recoverable.'}
original_ledger = sum((Decimal(str(a['cost_usd'])) for a in original_attempts),Decimal(0))
original_http = sum(a['result']['request_attempts'] for a in original_attempts)
output['lineage'] = {
    'original_run':str(ORIGINAL.relative_to(ROOT)), 'original_sealed_commit':ORIGINAL_COMMIT,
    'historical_attempt_prefix':len(original_attempts), 'historical_final_json_unchanged':len(original_finals),
    'appended_attempts':len(attempts)-len(original_attempts), 'appended_final_answers':len(missing),
    'appended_models':sorted(claude), 'appended_http_requests':http_requests-original_http,
    'original_ledger_decimal_usd':str(original_ledger), 'incremental_ledger_decimal_usd':str(ledger-original_ledger),
}
OUT.write_text(json.dumps(output,indent=2)+'\n')
print(json.dumps({k:v for k,v in output.items() if k not in {'family_metrics_all_retained_models','hierarchy_pairs_all_retained_models'}},indent=2))
