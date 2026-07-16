import tempfile
import unittest
from pathlib import Path

from core.code_agent.review import PythonCodeReviewer


class PythonCodeReviewerTests(unittest.TestCase):
    def test_reports_high_signal_python_correctness_risks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "risky.py").write_text("def run(items=[]) -> None:\n    try:\n        pass\n    except:\n        pass\n")

            findings = PythonCodeReviewer().review(str(root), "risky.py")

        self.assertEqual([finding.rule for finding in findings], ["mutable-default", "bare-except"])

    def test_reports_no_finding_for_a_typed_exception_and_none_default(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "safe.py").write_text("def run(items=None) -> None:\n    try:\n        pass\n    except ValueError:\n        pass\n")

            findings = PythonCodeReviewer().review(str(root), "safe.py")

        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
