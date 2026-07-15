from collections import defaultdict
from pathlib import Path

from .entrypoints import EntrypointFinder
from .models import ContextFile
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


class ImportantFileSelector:
    """Select stable, high-signal repository files for initial context."""

    def select(self, root: str, limit: int = 10) -> list[ContextFile]:
        if limit < 1:
            return []

        root_path = Path(root).resolve()
        if not root_path.is_dir():
            raise ValueError(f"Repository root is not a directory: {root}")

        candidates: dict[str, tuple[int, set[str]]] = defaultdict(lambda: (0, set()))
        for path in root_path.rglob("*"):
            if any(part in ProjectScanner.IGNORE_DIRS for part in path.parts) or not path.is_file():
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
