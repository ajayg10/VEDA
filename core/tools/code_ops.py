"""
Code Agent tool implementations for the VEDA executor.

Each class wraps a core/code_agent module as an async executor tool,
making code operations callable from the planner via their tool names.

All tools operate on a `root` path (repository root) and a relative `path`
within it — never on absolute paths — to maintain sandboxing.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from core.tools.base import BaseTool
from shared.models import StepResult, StepStatus

from core.code_agent.reader import RepositoryReader
from core.code_agent.editor import FileEdit, RepositoryEditor
from core.code_agent.diff import DiffGenerator
from core.code_agent.patch import UnifiedPatchApplier
from core.code_agent.rename import PythonSymbolRenamer
from core.code_agent.documentation import PythonDocumentationGenerator
from core.code_agent.review import PythonCodeReviewer
from core.code_agent.tests import PythonTestScaffoldGenerator


def _start() -> float:
    return time.time()


def _ms(start: float) -> float:
    return (time.time() - start) * 1000


def _ok(step_id: int, output: str, start: float) -> StepResult:
    return StepResult(step_id=step_id, status=StepStatus.SUCCESS, output=output, duration_ms=_ms(start))


def _fail(step_id: int, error: str, start: float) -> StepResult:
    return StepResult(step_id=step_id, status=StepStatus.FAILED, error=error, duration_ms=_ms(start))


class CodeReadTool(BaseTool):
    """Read a file from a repository and return its contents.

    Parameters:
        root (str): Absolute path to the repository root.
        path (str): Relative path to the file within the repository.
        max_bytes (int, optional): Maximum bytes to read (default 100 000).
    """
    name        = "code_read"
    description = "Read a source file from a repository."

    async def execute(self, step, context=None) -> StepResult:
        t    = _start()
        root = step.parameters.get("root", "")
        path = step.parameters.get("path", "")
        max_bytes = int(step.parameters.get("max_bytes", 100_000))
        if not root or not path:
            return _fail(step.step_id, "code_read requires 'root' and 'path'", t)
        try:
            fc = RepositoryReader().read(root, path, max_bytes=max_bytes)
            suffix = "\n[truncated]" if fc.truncated else ""
            return _ok(step.step_id, fc.content + suffix, t)
        except Exception as e:
            return _fail(step.step_id, str(e), t)


class CodeEditTool(BaseTool):
    """Write new content to a file in a repository.

    Parameters:
        root    (str): Absolute path to the repository root.
        path    (str): Relative path to the file to create or overwrite.
        content (str): The new file content.
    """
    name        = "code_edit"
    description = "Create or overwrite a source file in a repository."

    async def execute(self, step, context=None) -> StepResult:
        t       = _start()
        root    = step.parameters.get("root", "")
        path    = step.parameters.get("path", "")
        content = step.parameters.get("content", "")
        if not root or not path:
            return _fail(step.step_id, "code_edit requires 'root' and 'path'", t)
        try:
            # Read old content for diff (best-effort)
            old_content = ""
            try:
                old_content = RepositoryReader().read(root, path).content
            except Exception:
                pass

            changed = RepositoryEditor().write_many(root, [FileEdit(path, content)])
            diff    = DiffGenerator().generate(path, old_content, content) if old_content else ""
            output  = f"Written: {changed[0]}"
            if diff:
                output += f"\n\nDiff:\n{diff}"
            return _ok(step.step_id, output, t)
        except Exception as e:
            return _fail(step.step_id, str(e), t)


class CodePatchTool(BaseTool):
    """Apply a unified diff patch to one or more files in a repository.

    Parameters:
        root  (str): Absolute path to the repository root.
        patch (str): A unified diff string (output of `git diff` or `diff -u`).
    """
    name        = "code_patch"
    description = "Apply a unified diff patch to repository files."

    async def execute(self, step, context=None) -> StepResult:
        t     = _start()
        root  = step.parameters.get("root", "")
        patch = step.parameters.get("patch", "")
        if not root or not patch:
            return _fail(step.step_id, "code_patch requires 'root' and 'patch'", t)
        try:
            changed = UnifiedPatchApplier().apply(root, patch)
            return _ok(step.step_id, f"Patched {len(changed)} file(s): {', '.join(changed)}", t)
        except Exception as e:
            return _fail(step.step_id, str(e), t)


class CodeReviewTool(BaseTool):
    """Run static analysis on a Python file and return findings.

    Parameters:
        root (str): Absolute path to the repository root.
        path (str): Relative path to the Python file to review.
    """
    name        = "code_review"
    description = "Run static analysis on a Python source file."

    async def execute(self, step, context=None) -> StepResult:
        t    = _start()
        root = step.parameters.get("root", "")
        path = step.parameters.get("path", "")
        if not root or not path:
            return _fail(step.step_id, "code_review requires 'root' and 'path'", t)
        try:
            findings = PythonCodeReviewer().review(root, path)
            if not findings:
                return _ok(step.step_id, f"No issues found in {path}.", t)
            lines = [f"Found {len(findings)} issue(s) in {path}:\n"]
            for f in findings:
                lines.append(f"  Line {f.line} [{f.rule}]: {f.message}")
            return _ok(step.step_id, "\n".join(lines), t)
        except Exception as e:
            return _fail(step.step_id, str(e), t)


class CodeRenameTool(BaseTool):
    """Rename a Python identifier (token-level) across all .py files in a repository.

    Parameters:
        root     (str): Absolute path to the repository root.
        old_name (str): The identifier to rename.
        new_name (str): The replacement identifier.
    """
    name        = "code_rename"
    description = "Rename a Python symbol across all source files."

    async def execute(self, step, context=None) -> StepResult:
        t        = _start()
        root     = step.parameters.get("root", "")
        old_name = step.parameters.get("old_name", "")
        new_name = step.parameters.get("new_name", "")
        if not root or not old_name or not new_name:
            return _fail(step.step_id, "code_rename requires 'root', 'old_name', and 'new_name'", t)
        try:
            changed = PythonSymbolRenamer().rename(root, old_name, new_name)
            if not changed:
                return _ok(step.step_id, f"Symbol '{old_name}' not found in any Python file.", t)
            return _ok(step.step_id, f"Renamed '{old_name}' → '{new_name}' in {len(changed)} file(s): {', '.join(changed)}", t)
        except Exception as e:
            return _fail(step.step_id, str(e), t)


class CodeDocsTool(BaseTool):
    """Generate Markdown API documentation from a Python source file.

    Parameters:
        root (str): Absolute path to the repository root.
        path (str): Relative path to the Python file.
    """
    name        = "code_docs"
    description = "Generate Markdown documentation for a Python source file."

    async def execute(self, step, context=None) -> StepResult:
        t    = _start()
        root = step.parameters.get("root", "")
        path = step.parameters.get("path", "")
        if not root or not path:
            return _fail(step.step_id, "code_docs requires 'root' and 'path'", t)
        try:
            docs = PythonDocumentationGenerator().generate(root, path)
            return _ok(step.step_id, docs, t)
        except Exception as e:
            return _fail(step.step_id, str(e), t)


class CodeDiffTool(BaseTool):
    """Generate a unified diff between two text strings.

    Parameters:
        path   (str): File path label used in the diff header.
        before (str): Original file content.
        after  (str): Modified file content.
    """
    name        = "code_diff"
    description = "Generate a unified diff between two text strings."

    async def execute(self, step, context=None) -> StepResult:
        t      = _start()
        path   = step.parameters.get("path", "file.txt")
        before = step.parameters.get("before", "")
        after  = step.parameters.get("after", "")
        try:
            diff = DiffGenerator().generate(path, before, after)
            return _ok(step.step_id, diff or "(no differences)", t)
        except Exception as e:
            return _fail(step.step_id, str(e), t)


class CodeGenTestsTool(BaseTool):
    """Generate a unittest scaffold for a Python source file.

    Parameters:
        root (str): Absolute path to the repository root.
        path (str): Relative path to the Python file to generate tests for.
    """
    name        = "code_gen_tests"
    description = "Generate a unittest scaffold for a Python file."

    async def execute(self, step, context=None) -> StepResult:
        t    = _start()
        root = step.parameters.get("root", "")
        path = step.parameters.get("path", "")
        if not root or not path:
            return _fail(step.step_id, "code_gen_tests requires 'root' and 'path'", t)
        try:
            scaffold = PythonTestScaffoldGenerator().generate(root, path)
            return _ok(step.step_id, scaffold, t)
        except Exception as e:
            return _fail(step.step_id, str(e), t)
