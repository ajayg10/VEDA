import tempfile
import unittest
from pathlib import Path

from core.project.paths import iter_repository_paths


class RepositoryPathTests(unittest.TestCase):
    def test_prunes_ignored_directories_before_yielding_children(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src" / "app.py").touch()
            (root / ".venv").mkdir()
            (root / ".venv" / "ignored.py").touch()

            paths = [path.relative_to(root).as_posix() for path in iter_repository_paths(root, {".venv"})]

        self.assertEqual(paths, ["src", "src/app.py"])


if __name__ == "__main__":
    unittest.main()
