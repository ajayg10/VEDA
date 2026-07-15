import tempfile
import unittest
from pathlib import Path

from core.project.budget import TokenBudgeter
from core.project.models import ContextFile


class TokenBudgeterTests(unittest.TestCase):
    def test_keeps_ranked_files_within_the_budget_and_truncates_the_last_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "first.py").write_text("a" * 20)
            (root / "second.py").write_text("b" * 20)
            files = [
                ContextFile("first.py", 20, ("query match",)),
                ContextFile("second.py", 10, ("query match",)),
            ]

            budget = TokenBudgeter().build(str(root), files, max_tokens=8)

        self.assertEqual(budget.used_tokens, 8)
        self.assertEqual([snippet.path for snippet in budget.snippets], ["first.py", "second.py"])
        self.assertEqual(budget.snippets[1].content, "b" * 12)

    def test_rejects_files_outside_the_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            files = [ContextFile("../outside.py", 1, ("invalid",))]

            with self.assertRaises(ValueError):
                TokenBudgeter().build(directory, files, max_tokens=10)


if __name__ == "__main__":
    unittest.main()
