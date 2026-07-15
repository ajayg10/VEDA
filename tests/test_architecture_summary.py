import tempfile
import unittest
from pathlib import Path

from core.project.models import Entrypoint
from core.project.summary import ArchitectureSummarizer


class ArchitectureSummarizerTests(unittest.TestCase):
    def test_composes_scanner_and_graph_results(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src" / "main.py").write_text(
                'import src.service\nif __name__ == "__main__":\n    pass\n'
            )
            (root / "src" / "service.py").touch()
            (root / "Dockerfile").touch()
            (root / "requirements.txt").touch()
            (root / "tests").mkdir()
            (root / "tests" / "test_main.py").touch()

            summary = ArchitectureSummarizer().summarize(str(root))

        self.assertIn("src", summary.top_level_directories)
        self.assertEqual(summary.package_managers, ["pip"])
        self.assertTrue(summary.uses_docker)
        self.assertTrue(summary.has_tests)
        self.assertEqual(summary.entrypoints, [Entrypoint("src/main.py", "python")])
        self.assertEqual(summary.python_modules, 3)
        self.assertEqual(summary.internal_dependencies, 1)


if __name__ == "__main__":
    unittest.main()
