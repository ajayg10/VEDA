"""
Tests for Module 8 Repository Intelligence executor tools (core/tools/project_ops.py).
Uses the VEDA project itself as the test repository where an absolute path is needed.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# Path to the VEDA project root for tests that need a real repository
VEDA_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _make_step(step_id: int, parameters: dict) -> MagicMock:
    step = MagicMock()
    step.step_id    = step_id
    step.parameters = parameters
    return step


class ProjectScanToolTests(unittest.TestCase):
    def test_scans_veda_project(self):
        from core.tools.project_ops import ProjectScanTool
        import asyncio
        step   = _make_step(1, {"root": VEDA_ROOT})
        result = asyncio.run(ProjectScanTool().execute(step))
        self.assertEqual(result.status.value, "success")
        # Should detect Python and FastAPI
        self.assertIn("Python", result.output)
        self.assertIn("FastAPI", result.output)

    def test_fails_on_missing_root(self):
        from core.tools.project_ops import ProjectScanTool
        import asyncio
        step   = _make_step(1, {})
        result = asyncio.run(ProjectScanTool().execute(step))
        self.assertEqual(result.status.value, "failed")
        self.assertIn("requires", result.error)

    def test_fails_on_nonexistent_directory(self):
        from core.tools.project_ops import ProjectScanTool
        import asyncio
        step   = _make_step(1, {"root": "/nonexistent/path/xyz"})
        result = asyncio.run(ProjectScanTool().execute(step))
        self.assertEqual(result.status.value, "failed")

    def test_output_contains_markdown_structure(self):
        from core.tools.project_ops import ProjectScanTool
        import asyncio
        step   = _make_step(1, {"root": VEDA_ROOT})
        result = asyncio.run(ProjectScanTool().execute(step))
        # Check markdown structure
        self.assertIn("# Repository", result.output)
        self.assertIn("## Overview", result.output)


class ProjectContextToolTests(unittest.TestCase):
    def test_returns_relevant_files_for_query(self):
        from core.tools.project_ops import ProjectContextTool
        import asyncio
        step   = _make_step(1, {
            "root":  VEDA_ROOT,
            "query": "planner execution",
        })
        result = asyncio.run(ProjectContextTool().execute(step))
        self.assertEqual(result.status.value, "success")
        # Should find planner.py or executor.py
        self.assertIn("planner", result.output.lower())

    def test_fails_on_missing_parameters(self):
        from core.tools.project_ops import ProjectContextTool
        import asyncio
        step   = _make_step(1, {"root": VEDA_ROOT})  # missing query
        result = asyncio.run(ProjectContextTool().execute(step))
        self.assertEqual(result.status.value, "failed")
        self.assertIn("requires", result.error)

    def test_respects_token_budget(self):
        from core.tools.project_ops import ProjectContextTool
        import asyncio
        step = _make_step(1, {
            "root":       VEDA_ROOT,
            "query":      "memory store retrieve",
            "max_tokens": 500,   # very tight budget
        })
        result = asyncio.run(ProjectContextTool().execute(step))
        self.assertEqual(result.status.value, "success")
        # Output should be non-empty even with tight budget
        self.assertGreater(len(result.output), 0)

    def test_works_with_minimal_repository(self):
        from core.tools.project_ops import ProjectContextTool
        import asyncio
        with tempfile.TemporaryDirectory() as root:
            # Create a minimal Python module
            (Path(root) / "calculator.py").write_text(
                "def add(a, b):\n    return a + b\n\ndef subtract(a, b):\n    return a - b\n",
                encoding="utf-8",
            )
            step   = _make_step(1, {"root": root, "query": "addition subtraction calculator"})
            result = asyncio.run(ProjectContextTool().execute(step))
        self.assertEqual(result.status.value, "success")
        self.assertIn("calculator", result.output.lower())


if __name__ == "__main__":
    unittest.main()
