"""
Tests for Module 9 Code Agent executor tools (core/tools/code_ops.py).
Uses temporary directories to avoid touching real repository files.
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock


def _make_step(step_id: int, tool: str, parameters: dict) -> MagicMock:
    step = MagicMock()
    step.step_id    = step_id
    step.tool       = tool
    step.parameters = parameters
    return step


class CodeReadToolTests(unittest.TestCase):
    def test_reads_existing_file(self):
        from core.tools.code_ops import CodeReadTool
        import asyncio
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "hello.py").write_text("print('hello')", encoding="utf-8")
            step   = _make_step(1, "code_read", {"root": root, "path": "hello.py"})
            result = asyncio.run(CodeReadTool().execute(step))
        self.assertEqual(result.status.value, "success")
        self.assertIn("print('hello')", result.output)

    def test_fails_on_missing_file(self):
        from core.tools.code_ops import CodeReadTool
        import asyncio
        with tempfile.TemporaryDirectory() as root:
            step   = _make_step(1, "code_read", {"root": root, "path": "nonexistent.py"})
            result = asyncio.run(CodeReadTool().execute(step))
        self.assertEqual(result.status.value, "failed")

    def test_fails_missing_parameters(self):
        from core.tools.code_ops import CodeReadTool
        import asyncio
        step   = _make_step(1, "code_read", {})
        result = asyncio.run(CodeReadTool().execute(step))
        self.assertEqual(result.status.value, "failed")
        self.assertIn("requires", result.error)


class CodeEditToolTests(unittest.TestCase):
    def test_creates_new_file(self):
        from core.tools.code_ops import CodeEditTool
        import asyncio
        with tempfile.TemporaryDirectory() as root:
            content = "def hello():\n    return 42\n"
            step    = _make_step(1, "code_edit", {"root": root, "path": "new_file.py", "content": content})
            result  = asyncio.run(CodeEditTool().execute(step))
            written = (Path(root) / "new_file.py").read_text()
        self.assertEqual(result.status.value, "success")
        self.assertEqual(written, content)

    def test_overwrites_existing_file_and_shows_diff(self):
        from core.tools.code_ops import CodeEditTool
        import asyncio
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "existing.py"
            path.write_text("x = 1\n", encoding="utf-8")
            step   = _make_step(1, "code_edit", {"root": root, "path": "existing.py", "content": "x = 2\n"})
            result = asyncio.run(CodeEditTool().execute(step))
        self.assertEqual(result.status.value, "success")
        self.assertIn("Diff", result.output)
        self.assertIn("-x = 1", result.output)
        self.assertIn("+x = 2", result.output)


class CodePatchToolTests(unittest.TestCase):
    def test_applies_valid_patch(self):
        from core.tools.code_ops import CodePatchTool
        import asyncio
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "file.py"
            path.write_text("x = 1\n", encoding="utf-8")
            patch = "--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-x = 1\n+x = 42\n"
            step  = _make_step(1, "code_patch", {"root": root, "patch": patch})
            result = asyncio.run(CodePatchTool().execute(step))
        self.assertEqual(result.status.value, "success")
        self.assertIn("file.py", result.output)

    def test_fails_on_invalid_patch(self):
        from core.tools.code_ops import CodePatchTool
        import asyncio
        with tempfile.TemporaryDirectory() as root:
            step   = _make_step(1, "code_patch", {"root": root, "patch": "not a real patch"})
            result = asyncio.run(CodePatchTool().execute(step))
        self.assertEqual(result.status.value, "failed")


class CodeReviewToolTests(unittest.TestCase):
    def test_detects_bare_except(self):
        from core.tools.code_ops import CodeReviewTool
        import asyncio
        with tempfile.TemporaryDirectory() as root:
            code = "def f():\n    try:\n        pass\n    except:\n        pass\n"
            (Path(root) / "module.py").write_text(code, encoding="utf-8")
            step   = _make_step(1, "code_review", {"root": root, "path": "module.py"})
            result = asyncio.run(CodeReviewTool().execute(step))
        self.assertEqual(result.status.value, "success")
        self.assertIn("bare-except", result.output)

    def test_no_issues_on_clean_file(self):
        from core.tools.code_ops import CodeReviewTool
        import asyncio
        with tempfile.TemporaryDirectory() as root:
            code = "# clean module\n\nVALUE = 42\n"
            (Path(root) / "clean.py").write_text(code, encoding="utf-8")
            step   = _make_step(1, "code_review", {"root": root, "path": "clean.py"})
            result = asyncio.run(CodeReviewTool().execute(step))
        self.assertEqual(result.status.value, "success")
        self.assertIn("No issues", result.output)


class CodeRenameToolTests(unittest.TestCase):
    def test_renames_identifier_across_files(self):
        from core.tools.code_ops import CodeRenameTool
        import asyncio
        with tempfile.TemporaryDirectory() as root:
            f1 = Path(root) / "a.py"
            f2 = Path(root) / "b.py"
            f1.write_text("def old_func(): pass\n", encoding="utf-8")
            f2.write_text("from a import old_func\nold_func()\n", encoding="utf-8")
            step   = _make_step(1, "code_rename", {"root": root, "old_name": "old_func", "new_name": "new_func"})
            result = asyncio.run(CodeRenameToolTests._run(CodeRenameTool().execute(step)))
            self.assertEqual(result.status.value, "success")
            self.assertIn("new_func", f1.read_text())
            self.assertIn("new_func", f2.read_text())

    @staticmethod
    async def _run(coro):
        return await coro


class CodeDocsToolTests(unittest.TestCase):
    def test_generates_markdown_docs(self):
        from core.tools.code_ops import CodeDocsTool
        import asyncio
        with tempfile.TemporaryDirectory() as root:
            code = '"""Module docstring."""\n\ndef greet(name: str) -> str:\n    """Return greeting."""\n    return f"Hello {name}"\n'
            (Path(root) / "greet.py").write_text(code, encoding="utf-8")
            step   = _make_step(1, "code_docs", {"root": root, "path": "greet.py"})
            result = asyncio.run(CodeDocsTool().execute(step))
        self.assertEqual(result.status.value, "success")
        self.assertIn("greet", result.output)
        self.assertIn("#", result.output)  # markdown heading


class CodeDiffToolTests(unittest.TestCase):
    def test_generates_unified_diff(self):
        from core.tools.code_ops import CodeDiffTool
        import asyncio
        step   = _make_step(1, "code_diff", {
            "path":   "example.py",
            "before": "x = 1\n",
            "after":  "x = 2\n",
        })
        result = asyncio.run(CodeDiffTool().execute(step))
        self.assertEqual(result.status.value, "success")
        self.assertIn("--- a/example.py", result.output)
        self.assertIn("+x = 2", result.output)

    def test_returns_no_differences_for_identical_content(self):
        from core.tools.code_ops import CodeDiffTool
        import asyncio
        step   = _make_step(1, "code_diff", {
            "path": "same.py", "before": "x = 1\n", "after": "x = 1\n",
        })
        result = asyncio.run(CodeDiffTool().execute(step))
        self.assertIn("no differences", result.output)


class CodeGenTestsToolTests(unittest.TestCase):
    def test_generates_test_scaffold(self):
        from core.tools.code_ops import CodeGenTestsTool
        import asyncio
        with tempfile.TemporaryDirectory() as root:
            code = "def add(a, b):\n    return a + b\n"
            (Path(root) / "math_utils.py").write_text(code, encoding="utf-8")
            step   = _make_step(1, "code_gen_tests", {"root": root, "path": "math_utils.py"})
            result = asyncio.run(CodeGenTestsTool().execute(step))
        self.assertEqual(result.status.value, "success")
        self.assertIn("unittest", result.output)
        self.assertIn("test_add", result.output)


if __name__ == "__main__":
    unittest.main()
