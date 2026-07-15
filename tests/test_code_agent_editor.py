import tempfile
import unittest
from pathlib import Path

from core.code_agent.editor import FileEdit, RepositoryEditor


class RepositoryEditorTests(unittest.TestCase):
    def test_writes_multiple_files_after_validating_all_targets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            changed = RepositoryEditor().write_many(
                str(root),
                [FileEdit("src/app.py", "print('app')\n"), FileEdit("README.md", "# App\n")],
            )

            self.assertEqual((root / "src" / "app.py").read_text(), "print('app')\n")
            self.assertEqual((root / "README.md").read_text(), "# App\n")

        self.assertEqual(changed, ["src/app.py", "README.md"])

    def test_rejects_duplicate_or_outside_paths_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            editor = RepositoryEditor()

            with self.assertRaises(ValueError):
                editor.write_many(str(root), [FileEdit("a.py", "a"), FileEdit("a.py", "b")])
            with self.assertRaises(ValueError):
                editor.write_many(str(root), [FileEdit("../outside.py", "x")])

            self.assertFalse((root / "a.py").exists())


if __name__ == "__main__":
    unittest.main()
