"""Exercise independent audit refusals without reading a running campaign."""
import ast
import copy
from pathlib import Path
import unittest

path = Path(__file__).with_name('feat-04-independent-full-audit.py')
tree = ast.parse(path.read_text())
functions = ast.Module(body=[node for node in tree.body if isinstance(node, ast.FunctionDef)], type_ignores=[])
namespace = {}
exec(compile(functions, str(path), 'exec'), namespace)


class LineageControls(unittest.TestCase):
    def setUp(self):
        self.old = [{'model_id': 'old', 'task_id': 'one', 'result': {'raw_prediction': 'A'}}]
        self.new = copy.deepcopy(self.old) + [{'model_id': 'claude', 'task_id': 'two', 'result': {'raw_prediction': 'B'}}]
        self.old_final = {('old', 'one'): '{"choice":"A"}'}
        self.new_final = dict(self.old_final) | {('claude', 'two'): '{"choice":"B"}'}
        self.allowed = {('claude', 'two')}

    def check(self):
        namespace['check_lineage'](self.old, self.new, self.old_final, self.new_final, self.allowed)

    def test_valid_missing_answer_appended(self):
        self.check()

    def test_changed_prefix_refused(self):
        self.new[0]['result']['raw_prediction'] = 'B'
        with self.assertRaisesRegex(AssertionError, 'Historical attempt prefix'):
            self.check()

    def test_reordered_prefix_refused(self):
        self.new.reverse()
        with self.assertRaisesRegex(AssertionError, 'Historical attempt prefix'):
            self.check()

    def test_equivalent_but_rewritten_final_json_refused(self):
        self.new_final[('old', 'one')] = '{ "choice": "A" }'
        with self.assertRaisesRegex(AssertionError, 'Historical final JSON'):
            self.check()

    def test_missing_original_final_refused(self):
        del self.new_final[('old', 'one')]
        with self.assertRaisesRegex(AssertionError, 'Historical final JSON'):
            self.check()

    def test_repeated_completed_answer_refused(self):
        self.new.append(copy.deepcopy(self.old[0]))
        with self.assertRaisesRegex(AssertionError, 'Appended task is outside missing Claude set'):
            self.check()

    def test_unrequested_model_refused(self):
        self.new[-1]['model_id'] = 'gpt'
        with self.assertRaisesRegex(AssertionError, 'Appended task is outside missing Claude set'):
            self.check()

    def test_truncated_prefix_refused(self):
        self.new = []
        with self.assertRaisesRegex(AssertionError, 'Historical attempt prefix'):
            self.check()


if __name__ == '__main__':
    unittest.main()
