"""
Human-readable renderers for repository intelligence data structures.

These formatters convert internal dataclass models into plain text or
markdown strings suitable for display in the CLI, LLM prompts, or API responses.
"""
from __future__ import annotations

from .models import ArchitectureSummary, FolderNode


class ArchitectureSummaryFormatter:
    """Render an ArchitectureSummary as compact markdown."""

    def format(self, summary: ArchitectureSummary) -> str:
        lines: list[str] = []

        lines.append(f"# Repository: `{summary.root}`\n")

        # Core characteristics
        langs = ", ".join(summary.languages)     if summary.languages     else "—"
        fw    = ", ".join(summary.frameworks)    if summary.frameworks    else "—"
        pm    = ", ".join(summary.package_managers) if summary.package_managers else "—"
        ci    = ", ".join(summary.ci_providers)  if summary.ci_providers  else "—"

        lines.append("## Overview")
        lines.append(f"- **Languages**: {langs}")
        lines.append(f"- **Frameworks**: {fw}")
        lines.append(f"- **Package managers**: {pm}")
        lines.append(f"- **CI/CD**: {ci}")
        lines.append(f"- **Docker**: {'yes' if summary.uses_docker else 'no'}")
        lines.append(f"- **Tests detected**: {'yes' if summary.has_tests else 'no'}")
        lines.append(f"- **Python modules**: {summary.python_modules}")
        lines.append(f"- **Internal dependencies**: {summary.internal_dependencies}")
        lines.append(f"- **Top-level directories**: {', '.join(summary.top_level_directories) or '—'}")

        # Entrypoints
        if summary.entrypoints:
            lines.append("\n## Entrypoints")
            for ep in summary.entrypoints:
                lines.append(f"- `{ep.path}` ({ep.kind})")

        return "\n".join(lines) + "\n"

    def format_for_prompt(self, summary: ArchitectureSummary) -> str:
        """Compact single-paragraph summary for LLM context injection."""
        langs = ", ".join(summary.languages) or "unknown language"
        fw    = f" using {', '.join(summary.frameworks)}" if summary.frameworks else ""
        pm    = f" (package manager: {summary.package_managers[0]})" if summary.package_managers else ""
        docker = " Dockerised." if summary.uses_docker else ""
        tests  = " Has test suite." if summary.has_tests else " No tests detected."
        eps    = (
            f" Entrypoints: {', '.join(ep.path for ep in summary.entrypoints)}."
            if summary.entrypoints else ""
        )
        ci = f" CI: {', '.join(summary.ci_providers)}." if summary.ci_providers else ""

        return (
            f"Repository at {summary.root}: {langs}{fw}{pm}."
            f" {summary.python_modules} Python modules,"
            f" {summary.internal_dependencies} internal imports."
            f"{docker}{tests}{eps}{ci}"
        )


class FolderTreeFormatter:
    """Render a FolderNode tree as indented text."""

    def format(self, node: FolderNode, max_depth: int = 4) -> str:
        lines: list[str] = []
        self._render(node, lines, depth=0, max_depth=max_depth, prefix="")
        return "\n".join(lines)

    def _render(
        self,
        node:      FolderNode,
        lines:     list[str],
        depth:     int,
        max_depth: int,
        prefix:    str,
    ) -> None:
        if depth > max_depth:
            lines.append(f"{prefix}…")
            return

        # Root node label
        label = f"📁 {node.name}/" if depth > 0 else f"📁 {node.name}/"
        lines.append(f"{prefix}{label}")

        child_prefix = prefix + "  "

        # Subdirectories first
        for child in node.children:
            self._render(child, lines, depth + 1, max_depth, child_prefix)

        # Files
        for filename in node.files:
            lines.append(f"{child_prefix}📄 {filename}")
