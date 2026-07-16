"""
Repository Intelligence tool implementations for the VEDA executor.

These tools expose Module 8 (core/project) capabilities as planner-callable
executor actions. They allow the AI to analyze a codebase, build context for
code tasks, and understand repository structure before acting on it.
"""
from __future__ import annotations

import time

from core.tools.base import BaseTool
from shared.models import StepResult, StepStatus

from core.project.summary import ArchitectureSummarizer
from core.project.formatter import ArchitectureSummaryFormatter, FolderTreeFormatter
from core.project.graph import FolderTreeBuilder
from core.project.context import ImportantFileSelector, RelevantFileSelector
from core.project.budget import TokenBudgeter


def _start() -> float:
    return time.time()


def _ms(start: float) -> float:
    return (time.time() - start) * 1000


def _ok(step_id: int, output: str, start: float) -> StepResult:
    return StepResult(step_id=step_id, status=StepStatus.SUCCESS, output=output, duration_ms=_ms(start))


def _fail(step_id: int, error: str, start: float) -> StepResult:
    return StepResult(step_id=step_id, status=StepStatus.FAILED, error=error, duration_ms=_ms(start))


class ProjectScanTool(BaseTool):
    """Scan a repository and return a human-readable architecture summary.

    Returns language detection, framework identification, package managers,
    CI configuration, Docker usage, entrypoints, and Python module counts.

    Parameters:
        root (str): Absolute path to the repository root directory.
    """
    name        = "project_scan"
    description = "Scan a repository and return a full architecture summary."

    async def execute(self, step, context=None) -> StepResult:
        t    = _start()
        root = step.parameters.get("root", "")
        if not root:
            return _fail(step.step_id, "project_scan requires 'root' (absolute path to repo)", t)
        try:
            summary   = ArchitectureSummarizer().summarize(root)
            formatter = ArchitectureSummaryFormatter()
            output    = formatter.format(summary)
            return _ok(step.step_id, output, t)
        except Exception as e:
            return _fail(step.step_id, str(e), t)


class ProjectContextTool(BaseTool):
    """Select the most relevant repository files for a goal and return their contents.

    First selects files by lexical and dependency scoring against the query,
    then fits them within a token budget so the output is LLM-safe.

    Parameters:
        root       (str): Absolute path to the repository root directory.
        query      (str): Natural language description of the goal or task.
        max_tokens (int, optional): Token budget for file content (default 4000).
    """
    name        = "project_context"
    description = "Select and return the most relevant repository files for a coding goal."

    async def execute(self, step, context=None) -> StepResult:
        t          = _start()
        root       = step.parameters.get("root", "")
        query      = step.parameters.get("query", "")
        max_tokens = int(step.parameters.get("max_tokens", 4000))

        if not root or not query:
            return _fail(step.step_id, "project_context requires 'root' and 'query'", t)

        try:
            # Find relevant files for this query
            relevant = RelevantFileSelector().select(root, query, limit=15)

            if not relevant:
                # Fall back to important (structural) files
                relevant = ImportantFileSelector().select(root, limit=10)

            # Fit them into the token budget
            budget = TokenBudgeter().build(root, relevant, max_tokens)

            if not budget.snippets:
                return _ok(step.step_id, "No relevant files found for this query.", t)

            lines = [
                f"# Repository Context for: {query}\n",
                f"Showing {len(budget.snippets)} file(s) ({budget.used_tokens}/{budget.max_tokens} tokens)\n",
            ]
            for snippet in budget.snippets:
                lines.append(f"\n## {snippet.path}\n```\n{snippet.content}\n```")

            return _ok(step.step_id, "\n".join(lines), t)

        except Exception as e:
            return _fail(step.step_id, str(e), t)
