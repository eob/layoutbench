"""Controls for the read-only analysis; run from the repository root."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('final_analysis', Path(__file__).with_name('layoutbench-final-analysis.py'))
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


class AnalysisControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = analysis.diag.diagnose()
        cls.seal = json.loads((analysis.diag.RUN / 'final_results.json').read_text())
        cls.complete = {name: model for name, model in cls.raw['models'].items() if model['observed'] == 292}

    def test_parser_rejects_malformed_and_decodes_task_options(self):
        options = ['right', 'left', 'center']
        self.assertEqual(analysis.diag.prediction('{"choice":" b "}', options), 'left')
        for value in ['[]', '{}', '{"choice":2}', '{"choice":"D"}', '{"choice":"AA"}',
                      '{"choice":"A","extra":0}', '{"choice":"A","choice":"B"}', '```{"choice":"A"}```']:
            with self.subTest(value=value):
                self.assertIsNone(analysis.diag.prediction(value, options))

    def test_active_campaign_refuses_final_analysis(self):
        raw = deepcopy(self.raw)
        next(iter(raw['models'].values()))['run_status'] = 'running'
        with patch.object(analysis.diag, 'diagnose', return_value=raw):
            with self.assertRaisesRegex(ValueError, 'runner to finish'):
                analysis.analyze()

    def test_sealed_roster_mismatch_is_detected(self):
        seal = deepcopy(self.seal)
        seal['comparison']['model_ids'].pop()
        with self.assertRaisesRegex(AssertionError, 'Selected roster'):
            analysis.verify_seal(self.raw, self.complete, seal)

    def test_changed_sealed_response_is_detected(self):
        seal = deepcopy(self.seal)
        row = next(row for row in seal['results'] if row['included_in_comparison'])
        row['result']['raw_prediction'] = '{"choice":"changed"}'
        with self.assertRaises(AssertionError):
            analysis.verify_seal(self.raw, self.complete, seal)

    def test_partial_providers_remain_available_but_outside_every_comparison(self):
        result = analysis.analyze()
        self.assertEqual(result['model_count'], 9)
        self.assertEqual(len(result['availability']), 13)
        for name, model in result['availability'].items():
            if name not in self.complete:
                self.assertEqual(model['observed'], 221)
                self.assertFalse(model['included_in_comparison'])
                self.assertNotIn(name, result['hierarchy_pairs'])
                self.assertNotIn(name, result['nestedwrap'])
                self.assertTrue(all(name not in item['by_model'] for item in result['families'].values()))
                self.assertTrue(all(name not in {r['model'] for r in item['responses']} for item in result['examples'].values()))
        self.assertEqual(sum(row['pair_count'] for row in result['hierarchy_pairs'].values()), 216)
        self.assertEqual(sum(row['total']['observed'] for row in result['nestedwrap'].values()), 216)
        self.assertTrue(all(row['observed'] == 9 for row in result['examples'].values()))


if __name__ == '__main__':
    unittest.main()
