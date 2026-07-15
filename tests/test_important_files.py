import tempfile
import unittest
from pathlib import Path

from core.project.context import ImportantFileSelector


class ImportantFileSelectorTests(unittest.TestCase):
    def test_selects_documentation_configuration_and_entrypoints(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").touch()
            (root / "pyproject.toml").touch()
            (root / "main.py").write_text('if __name__ == "__main__":\n    pass\n')
            (root / "node_modules").mkdir()
            (root / "node_modules" / "package.json").touch()

            files = ImportantFileSelector().select(str(root))

        self.assertEqual([file.path for file in files], ["README.md", "pyproject.toml", "main.py"])
        self.assertEqual(files[2].reasons, ("python entrypoint",))

    def test_returns_no_files_for_a_non_positive_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(ImportantFileSelector().select(directory, limit=0), [])


if __name__ == "__main__":
    unittest.main()
