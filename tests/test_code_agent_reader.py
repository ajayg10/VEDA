import tempfile
import unittest
from pathlib import Path

from core.code_agent.reader import RepositoryReader


class RepositoryReaderTests(unittest.TestCase):
    def test_reads_a_repository_file_and_applies_a_size_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "module.py").write_text("abcdef")

            result = RepositoryReader().read(str(root), "module.py", max_bytes=4)

        self.assertEqual(result.path, "module.py")
        self.assertEqual(result.content, "abcd")
        self.assertTrue(result.truncated)

    def test_rejects_paths_outside_the_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                RepositoryReader().read(directory, "../outside.py")


if __name__ == "__main__":
    unittest.main()
