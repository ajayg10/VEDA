import json
import tempfile
import unittest
from pathlib import Path

from core.project.entrypoints import EntrypointFinder
from core.project.models import Entrypoint


class EntrypointFinderTests(unittest.TestCase):
    def test_discovers_python_go_and_javascript_entrypoints(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "cli.py").write_text('if __name__ == "__main__":\n    main()\n')
            (root / "server.go").write_text("package main\nfunc main() {}\n")
            (root / "src").mkdir()
            (root / "src" / "index.js").touch()
            (root / "package.json").write_text(json.dumps({"main": "src/index.js"}))

            entrypoints = EntrypointFinder().find(str(root))

        self.assertEqual(
            entrypoints,
            [
                Entrypoint("cli.py", "python"),
                Entrypoint("server.go", "go"),
                Entrypoint("src/index.js", "javascript"),
            ],
        )

    def test_ignores_package_entrypoints_outside_the_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text(json.dumps({"main": "../outside.js"}))

            entrypoints = EntrypointFinder().find(str(root))

        self.assertEqual(entrypoints, [])

    def test_ignores_missing_package_entrypoints(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text(json.dumps({"main": "missing.js"}))

            entrypoints = EntrypointFinder().find(str(root))

        self.assertEqual(entrypoints, [])


if __name__ == "__main__":
    unittest.main()
