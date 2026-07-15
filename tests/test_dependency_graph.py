import tempfile
import unittest
from pathlib import Path

from core.project.dependencies import DependencyGraphBuilder


class DependencyGraphBuilderTests(unittest.TestCase):
    def test_builds_edges_for_repository_local_absolute_and_relative_imports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "app"
            package.mkdir()
            (package / "__init__.py").touch()
            (package / "main.py").write_text("import app.service\nfrom . import helpers\n")
            (package / "service.py").write_text("import httpx\n")
            (package / "helpers.py").touch()

            graph = DependencyGraphBuilder().build(str(root))

        self.assertEqual(graph.dependencies["app/main.py"], ["app/helpers.py", "app/service.py"])
        self.assertEqual(graph.dependencies["app/service.py"], [])

    def test_ignores_syntax_errors_and_external_imports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "broken.py").write_text("def invalid(:\n")
            (root / "external.py").write_text("import requests\n")

            graph = DependencyGraphBuilder().build(str(root))

        self.assertEqual(graph.dependencies, {"broken.py": [], "external.py": []})


if __name__ == "__main__":
    unittest.main()
