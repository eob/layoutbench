"""Check cohort selection and complete evidence generation without source writes."""
import csv
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('full_analysis', Path(__file__).with_name('run-analysis.py'))
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


class FullRosterAnalysisControls(unittest.TestCase):
    def test_prior_nine_model_cohort_is_rejected_without_output(self):
        with TemporaryDirectory() as temporary:
            output = Path(temporary) / 'evidence'
            prior = analysis.ROOT / 'results/runs/0.3.0/qualitative-20260917'
            with patch.object(analysis.analysis.diag, 'RUN', prior):
                with self.assertRaisesRegex(ValueError, 'thirteen complete'):
                    analysis.generate(output)
            self.assertFalse(output.exists())

    def test_full_roster_generation_keeps_every_model_and_denominator(self):
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            analysis.generate(output)
            result = json.loads((output / 'diagnostics.json').read_text())
            with (output / 'model-family-results.csv').open() as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 260)
            self.assertEqual(len({row['model_id'] for row in rows}), 13)
            self.assertEqual(sum(int(row['count']) for row in rows), 3796)
            self.assertEqual(sum(int(row['invalid']) for row in rows), 0)
            self.assertEqual(sum(row['pair_count'] for row in result['hierarchy_pairs'].values()), 312)
            self.assertTrue(all(row['observed'] == 13 for row in result['examples'].values()))
            self.assertEqual(result['nestedwrap']['claude-haiku-4-5-20251001']['total']['correct'], 17)
            self.assertIn('tickets/evidence/feat-04-analysis/run-analysis.py', (output / 'observations.md').read_text())


if __name__ == '__main__':
    unittest.main()
