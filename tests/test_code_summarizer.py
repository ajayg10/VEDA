import tempfile
import unittest
from pathlib import Path

from core.project.summarizer import CodeSummarizer


class CodeSummarizerTests(unittest.TestCase):
    def test_summarizes_python_symbols_docstring_and_imports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "worker.py").write_text(
                '"""Handles jobs."""\nimport httpx\n\nclass Worker:\n    pass\n\ndef run():\n    pass\n'
            )

            summary = CodeSummarizer().summarize(str(root), "worker.py")

        self.assertEqual(summary.symbols, ("Worker", "run"))
        self.assertIn("Handles jobs", summary.summary)
        self.assertIn("Imports: httpx", summary.summary)

    def test_rejects_paths_outside_the_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                CodeSummarizer().summarize(directory, "../outside.py")


if __name__ == "__main__":
    unittest.main()
