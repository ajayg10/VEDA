import tempfile
import unittest
from pathlib import Path

from core.code_agent.dependencies import RequirementsUpdater


class RequirementsUpdaterTests(unittest.TestCase):
    def test_updates_an_explicit_requirement_and_preserves_its_comment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            requirements = root / "requirements.txt"
            requirements.write_text("httpx>=0.24 # client\nfastapi>=0.100\n")

            changed = RequirementsUpdater().update(str(root), "requirements.txt", "httpx", "==0.28.1")

            self.assertEqual(requirements.read_text(), "httpx==0.28.1 # client\nfastapi>=0.100\n")

        self.assertEqual(changed, "requirements.txt")

    def test_rejects_missing_dependencies_and_invalid_specifiers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "requirements.txt").write_text("httpx>=0.24\n")
            updater = RequirementsUpdater()

            with self.assertRaises(ValueError):
                updater.update(str(root), "requirements.txt", "fastapi", "==1.0")
            with self.assertRaises(ValueError):
                updater.update(str(root), "requirements.txt", "httpx", "1.0")


if __name__ == "__main__":
    unittest.main()
