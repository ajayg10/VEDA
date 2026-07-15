from collections import defaultdict
from pathlib import Path
import re

from .dependencies import DependencyGraphBuilder
from .entrypoints import EntrypointFinder
from .models import ContextFile
from .paths import iter_repository_paths
from .scanner import ProjectScanner


ROOT_CONFIGURATION_FILES = {
    "README.md": (100, "project documentation"),
    "pyproject.toml": (95, "Python project configuration"),
    "package.json": (95, "JavaScript project configuration"),
    "Cargo.toml": (95, "Rust project configuration"),
    "go.mod": (95, "Go module configuration"),
    "docker-compose.yml": (90, "container orchestration"),
    "docker-compose.yaml": (90, "container orchestration"),
    "compose.yml": (90, "container orchestration"),
    "compose.yaml": (90, "container orchestration"),
    "Dockerfile": (85, "container build"),
}
TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_]+")
MAX_CONTEXT_FILE_BYTES = 1_000_000


class ImportantFileSelector:
    """Select stable, high-signal repository files for initial context."""

    def select(self, root: str, limit: int = 10) -> list[ContextFile]:
        if limit < 1:
            return []

        root_path = Path(root).resolve()
        if not root_path.is_dir():
            raise ValueError(f"Repository root is not a directory: {root}")

        candidates: dict[str, tuple[int, set[str]]] = defaultdict(lambda: (0, set()))
        for path in iter_repository_paths(root_path, ProjectScanner.IGNORE_DIRS):
            if not path.is_file():
                continue
            relative_path = path.relative_to(root_path).as_posix()
            if path.name in ROOT_CONFIGURATION_FILES:
                score, reason = ROOT_CONFIGURATION_FILES[path.name]
                self._add_candidate(candidates, relative_path, score, reason)

        for entrypoint in EntrypointFinder().find(root):
            self._add_candidate(candidates, entrypoint.path, 90, f"{entrypoint.kind} entrypoint")

        selected = [
            ContextFile(path, score, tuple(sorted(reasons)))
            for path, (score, reasons) in candidates.items()
        ]
        return sorted(selected, key=lambda item: (-item.score, item.path))[:limit]

    @staticmethod
    def _add_candidate(
        candidates: dict[str, tuple[int, set[str]]], path: str, score: int, reason: str
    ) -> None:
        existing_score, existing_reasons = candidates[path]
        candidates[path] = (max(existing_score, score), existing_reasons | {reason})


class RelevantFileSelector:
    """Select files related to a goal using lexical and dependency signals."""

    def select(self, root: str, query: str, limit: int = 10) -> list[ContextFile]:
        if limit < 1:
            return []

        tokens = self._tokens(query)
        if not tokens:
            return []

        root_path = Path(root).resolve()
        if not root_path.is_dir():
            raise ValueError(f"Repository root is not a directory: {root}")

        candidates: dict[str, tuple[int, set[str]]] = {}
        for path in iter_repository_paths(root_path, ProjectScanner.IGNORE_DIRS):
            if not path.is_file():
                continue
            relative_path = path.relative_to(root_path).as_posix()
            score, reasons = self._lexical_score(path, tokens)
            if score:
                candidates[relative_path] = (score, reasons)

        self._add_dependency_neighbors(candidates, DependencyGraphBuilder().build(root).dependencies)
        selected = [
            ContextFile(path, score, tuple(sorted(reasons)))
            for path, (score, reasons) in candidates.items()
        ]
        return sorted(selected, key=lambda item: (-item.score, item.path))[:limit]

    @staticmethod
    def _tokens(query: str) -> set[str]:
        return {token.lower() for token in TOKEN_PATTERN.findall(query) if len(token) > 1}

    def _lexical_score(self, path: Path, tokens: set[str]) -> tuple[int, set[str]]:
        matched_filename_tokens = tokens & self._tokens(path.stem)
        score = len(matched_filename_tokens) * 20
        reasons = {"filename matches query"} if matched_filename_tokens else set()

        if path.stat().st_size > MAX_CONTEXT_FILE_BYTES:
            return score, reasons
        try:
            contents = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return score, reasons

        content_matches = sum(contents.lower().count(token) for token in tokens)
        if content_matches:
            score += min(content_matches, 20) * 10
            reasons.add("content matches query")
        return score, reasons

    @staticmethod
    def _add_dependency_neighbors(
        candidates: dict[str, tuple[int, set[str]]], dependencies: dict[str, list[str]]
    ) -> None:
        direct_matches = set(candidates)
        for source, targets in dependencies.items():
            for target in targets:
                if source in direct_matches and target not in candidates:
                    candidates[target] = (5, {"depends on a query match"})
                if target in direct_matches and source not in candidates:
                    candidates[source] = (5, {"used by a query match"})
