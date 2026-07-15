import tempfile
import unittest
from pathlib import Path

from core.code_agent.documentation import PythonDocumentationGenerator


class PythonDocumentationGeneratorTests(unittest.TestCase):
    def test_generates_markdown_for_documented_python_symbols(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "api.py").write_text(
                '"""Public API."""\n\nclass Client:\n    """Calls the service."""\n\ndef fetch(item, *, limit=10):\n    """Fetch items."""\n'
            )

            documentation = PythonDocumentationGenerator().generate(str(root), "api.py")

        self.assertIn("# `api.py`", documentation)
        self.assertIn("## Class `Client`", documentation)
        self.assertIn("## Function `fetch(item, limit=10)`", documentation)
        self.assertIn("Fetch items", documentation)

    def test_rejects_non_python_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").touch()
            with self.assertRaises(ValueError):
                PythonDocumentationGenerator().generate(str(root), "README.md")


if __name__ == "__main__":
    unittest.main()
