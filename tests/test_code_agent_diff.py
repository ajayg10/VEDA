import unittest

from core.code_agent.diff import DiffGenerator


class DiffGeneratorTests(unittest.TestCase):
    def test_generates_a_unified_diff_with_repository_paths(self):
        diff = DiffGenerator().generate("src/app.py", "value = 1\n", "value = 2\n")

        self.assertIn("--- a/src/app.py", diff)
        self.assertIn("+++ b/src/app.py", diff)
        self.assertIn("-value = 1", diff)
        self.assertIn("+value = 2", diff)

    def test_returns_an_empty_diff_when_content_is_unchanged(self):
        self.assertEqual(DiffGenerator().generate("app.py", "same\n", "same\n"), "")


if __name__ == "__main__":
    unittest.main()
