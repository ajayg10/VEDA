import tempfile
import unittest
from pathlib import Path

from core.code_agent.tests import PythonTestScaffoldGenerator


class PythonTestScaffoldGeneratorTests(unittest.TestCase):
    def test_generates_test_stubs_for_public_functions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "calculator.py").write_text("def add():\n    return 1\n\ndef _private():\n    return 2\n")

            scaffold = PythonTestScaffoldGenerator().generate(str(root), "calculator.py")

        self.assertIn("import calculator", scaffold)
        self.assertIn("def test_add", scaffold)
        self.assertNotIn("test__private", scaffold)

    def test_rejects_paths_outside_the_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                PythonTestScaffoldGenerator().generate(directory, "../outside.py")


if __name__ == "__main__":
    unittest.main()
