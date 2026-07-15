import tempfile
import unittest
from pathlib import Path

from core.code_agent.rename import PythonSymbolRenamer


class PythonSymbolRenamerTests(unittest.TestCase):
    def test_renames_identifier_tokens_without_changing_strings_or_comments(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "app.py"
            path.write_text('value = 1\nprint(value)\n# value\nmessage = "value"\n')

            changed = PythonSymbolRenamer().rename(str(root), "value", "total")

            contents = path.read_text()

        self.assertEqual(changed, ["app.py"])
        self.assertIn("total = 1", contents)
        self.assertIn("print(total)", contents)
        self.assertIn("# value", contents)
        self.assertIn('"value"', contents)

    def test_rejects_invalid_identifier_names(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                PythonSymbolRenamer().rename(directory, "valid", "not-valid")


if __name__ == "__main__":
    unittest.main()
