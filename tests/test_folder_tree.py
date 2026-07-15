import tempfile
import unittest
from pathlib import Path

from core.project.graph import FolderTreeBuilder


class FolderTreeBuilderTests(unittest.TestCase):
    def test_builds_a_repository_relative_tree_and_ignores_build_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").touch()
            (root / "src").mkdir()
            (root / "src" / "app.py").touch()
            (root / "node_modules").mkdir()
            (root / "node_modules" / "ignored.js").touch()

            tree = FolderTreeBuilder().build(str(root))

        self.assertEqual(tree.path, ".")
        self.assertEqual(tree.files, ["README.md"])
        self.assertEqual(tree.children[0].path, "src")
        self.assertEqual(tree.children[0].files, ["app.py"])
        self.assertEqual(len(tree.children), 1)

    def test_rejects_a_non_directory_root(self):
        with tempfile.TemporaryDirectory() as directory:
            file_path = Path(directory) / "file.py"
            file_path.touch()

            with self.assertRaises(ValueError):
                FolderTreeBuilder().build(str(file_path))


if __name__ == "__main__":
    unittest.main()
