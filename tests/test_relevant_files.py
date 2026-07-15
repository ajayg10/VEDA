import tempfile
import unittest
from pathlib import Path

from core.project.context import RelevantFileSelector


class RelevantFileSelectorTests(unittest.TestCase):
    def test_selects_query_matches_and_connected_modules(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = root / "app"
            app.mkdir()
            (app / "main.py").write_text("import app.billing\n")
            (app / "billing.py").write_text("def create_invoice():\n    return 'invoice'\n")
            (app / "auth.py").write_text("def login():\n    return True\n")

            files = RelevantFileSelector().select(str(root), "fix invoice creation")

        paths = [file.path for file in files]
        self.assertIn("app/billing.py", paths)
        self.assertIn("app/main.py", paths)
        self.assertNotIn("app/auth.py", paths)
        self.assertGreater(files[0].score, 5)

    def test_returns_no_context_for_an_empty_query(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(RelevantFileSelector().select(directory, ""), [])


if __name__ == "__main__":
    unittest.main()
