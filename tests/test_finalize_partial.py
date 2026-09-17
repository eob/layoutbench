"""A provider outage remains visible without blocking complete comparison models."""

import hashlib
import json
import subprocess

import httpx
from PIL import Image
import pytest

from baseline import finalize, runner
from baseline.evaluator import evaluation_protocol_fingerprint
from baseline.protocol import get_prompt


def git(root, *args):
    return subprocess.run(['git', *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def partial_campaign(tmp_path, monkeypatch, request):
    git(tmp_path, 'init', '-q')
    git(tmp_path, 'config', 'user.email', 'test@example.com')
    git(tmp_path, 'config', 'user.name', 'Test')
    data = tmp_path / 'dataset/frozen'
    data.mkdir(parents=True)
    image = data / 'sample.png'
    Image.new('RGB', (4, 4), 'white').save(image)
    items = [dict(taskId=f'task-{index}', family='flow', groupId=f'group-{index}',
                  groundTruth={'choice': 'A'}, imageFilename='sample.png', imagePath=str(image),
                  imageSha256=hashlib.sha256(image.read_bytes()).hexdigest(), prompt=get_prompt('flow'), design={})
             for index in range(3)]
    manifest = data / 'manifest.json'
    manifest.write_text(json.dumps(items))
    git(tmp_path, 'add', 'dataset')
    git(tmp_path, 'commit', '-qm', 'Freeze fixture')
    release = dict(schema_version=1, benchmark_version='1.0.0', dataset_manifest='dataset/frozen/manifest.json',
                   dataset_path='dataset/frozen', dataset_git_commit=git(tmp_path, 'rev-parse', 'HEAD'),
                   dataset_fingerprint=runner.dataset_fingerprint(items),
                   evaluation_protocol_fingerprint=evaluation_protocol_fingerprint(), expected_task_count=3)
    (tmp_path / 'releases').mkdir()
    (tmp_path / 'releases/1.0.0.json').write_text(json.dumps(release))
    configs = [dict(id=name, provider=provider, model=name, display_name=name, enabled=True,
                    api_key_env='FIXTURE_API_KEY', source_url='https://example.com/models',
                    max_output_tokens=64, input_per_m=1.0, output_per_m=2.0)
               for name, provider in [('good', 'openai'), ('blocked', 'google'), ('blocked-sibling', 'google')]]
    config = tmp_path / 'models.json'
    config.write_text(json.dumps(dict(version=1, verified_at='2026-09-17', models=configs)))
    monkeypatch.setenv('FIXTURE_API_KEY', 'fixture-only')
    monkeypatch.setattr(runner, 'load_release', lambda *args: release)
    monkeypatch.setattr(runner, 'release_manifest_path', lambda *args: manifest)
    monkeypatch.setattr(runner, 'validate_release', lambda *args: list(items))
    monkeypatch.setattr(finalize, 'validate_release', lambda *args, **kwargs: list(items))
    monkeypatch.setattr(runner, 'git_code_identity', lambda: dict(runner_git_commit=git(tmp_path, 'rev-parse', 'HEAD'), runner_git_dirty=False))
    requests = []
    invalid = getattr(request, 'param', False)
    recovered = {'google': False}

    def handle(message):
        requests.append(message)
        if 'generativelanguage.googleapis.com' in str(message.url):
            if not recovered['google']:
                return httpx.Response(400, json={'error': {'message': 'Your credit balance is too low'}})
            return httpx.Response(200, json={'candidates': [{'finishReason': 'STOP', 'content': {
                'parts': [{'text': '{"choice":"A"}'}]}}],
                'usageMetadata': {'promptTokenCount': 100, 'candidatesTokenCount': 10}})
        answer = 'not JSON' if invalid and len(requests) == 1 else '{"choice":"A"}'
        return httpx.Response(200, json={'status': 'completed', 'output': [
            {'type': 'message', 'content': [{'type': 'output_text', 'text': answer}]}],
            'usage': {'input_tokens': 100, 'output_tokens': 10}})

    original = httpx.Client
    monkeypatch.setattr('baseline.providers.httpx.Client', lambda **kwargs: original(transport=httpx.MockTransport(handle), **kwargs))
    args = dict(config_path=config, output_dir=tmp_path / 'results/runs', run_id='sample', release='1.0.0',
                mock=False, concurrency=1, budget_usd=10, max_tasks=3)
    runner.run_benchmark(**args)
    directory = tmp_path / 'results/runs/1.0.0/sample'
    git(tmp_path, 'add', '.')
    git(tmp_path, 'commit', '-qm', 'Record mixed provider availability')
    before = {path.name: path.read_bytes() for path in directory.iterdir() if path.name != '.runner.lock'}
    return dict(root=tmp_path, directory=directory, requests=requests, before=before, recovered=recovered, args=args)


def test_full_completed_subset_preserves_outage_roster_and_ledger(partial_campaign):
    campaign = partial_campaign
    report = finalize.finalize_run(campaign['directory'], scope='full', models=['good'], root=campaign['root'])
    assert report['comparison']['model_ids'] == ['good']
    assert report['comparison']['count'] == 3
    assert len(report['results']) == report['campaign']['final_response_count'] == 3
    assert len(report['attempts']) == report['campaign']['attempt_count'] == 4
    assert report['campaign']['unresolved_infrastructure_task_count'] == 1
    assert report['campaign']['infrastructure_error_kinds'] == {'credits': 1}
    assert all(row['model_id'] == 'good' for row in report['results'])
    assert any(row['result'].get('error_kind') == 'credits' for row in report['attempts'])
    models = {model['model_id']: model for model in report['models']}
    assert set(models) == {'good', 'blocked', 'blocked-sibling'}
    assert models['good']['availability_status'] == 'complete'
    assert models['good']['included_in_comparison'] is True
    for name in ['blocked', 'blocked-sibling']:
        assert models[name]['availability_status'] == 'unavailable'
        assert models[name]['run_status'] == 'paused'
        assert models[name]['run_reason'] == 'HTTP 400: Your credit balance is too low'
        assert models[name]['included_in_comparison'] is False
        assert models[name]['observed_task_count'] == models[name]['comparison_task_count'] == 0
        assert models[name]['families']['flow']['accuracy'] is None
    assert models['blocked']['attempted_task_count'] == models['blocked']['unresolved_infrastructure_task_count'] == 1
    assert models['blocked-sibling']['attempted_task_count'] == models['blocked-sibling']['unresolved_infrastructure_task_count'] == 0
    assert len(campaign['requests']) == 4
    assert all((campaign['directory'] / name).read_bytes() == content for name, content in campaign['before'].items())
    assert finalize.verify_finalization(campaign['directory'], root=campaign['root']) == report


def test_full_roster_still_requires_every_selected_model_complete(partial_campaign):
    campaign = partial_campaign
    with pytest.raises(ValueError, match='full|missing|complete'):
        finalize.finalize_run(campaign['directory'], scope='full', root=campaign['root'])
    assert not (campaign['directory'] / 'finalization.json').exists()


@pytest.mark.parametrize('partial_campaign', [True], indirect=True)
def test_invalid_model_answer_remains_scored_zero_not_provider_unavailability(partial_campaign):
    campaign = partial_campaign
    report = finalize.finalize_run(campaign['directory'], scope='full', models=['good'], root=campaign['root'])
    invalid = [row for row in report['results'] if row['result'].get('error_kind') == 'invalid_response']
    assert len(invalid) == 1 and invalid[0]['result']['score'] == 0
    good = next(model for model in report['models'] if model['model_id'] == 'good')
    assert good['families']['flow']['accuracy'] == pytest.approx(2 / 3)
    assert good['availability_status'] == 'complete'
    assert report['campaign']['infrastructure_attempt_count'] == 1


def test_summary_cannot_relabel_checkpoint_outage_reason(partial_campaign):
    campaign = partial_campaign
    path = campaign['directory'] / 'summary.json'
    summary = json.loads(path.read_text())
    summary['models']['blocked']['reason'] = 'Invented availability explanation'
    path.write_text(json.dumps(summary))
    with pytest.raises(ValueError, match='availability|status|reason'):
        finalize.finalize_run(campaign['directory'], scope='full', models=['good'], root=campaign['root'])


def test_recovered_provider_keeps_failed_attempt_without_double_counting(partial_campaign):
    campaign = partial_campaign
    campaign['recovered']['google'] = True
    runner.run_benchmark(**campaign['args'], selected_models=['blocked'])
    git(campaign['root'], 'add', '.')
    git(campaign['root'], 'commit', '-qm', 'Record recovered provider responses')
    report = finalize.finalize_run(campaign['directory'], scope='full', models=['good', 'blocked'], root=campaign['root'])
    assert len(report['results']) == report['campaign']['final_response_count'] == 6
    assert len(report['attempts']) == 7
    assert report['campaign']['infrastructure_attempt_count'] == 1
    assert report['campaign']['unresolved_infrastructure_task_count'] == 0
    blocked = next(model for model in report['models'] if model['model_id'] == 'blocked')
    assert blocked['availability_status'] == 'complete'
    assert blocked['run_reason'] is None
    assert blocked['attempted_task_count'] == 3
    assert finalize.verify_finalization(campaign['directory'], root=campaign['root']) == report
