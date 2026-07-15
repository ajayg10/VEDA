from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FileEdit:
    path: str
    content: str


class RepositoryEditor:
    """Apply validated text edits to multiple repository files."""

    def write_many(self, root: str, edits: list[FileEdit]) -> list[str]:
        root_path = Path(root).resolve()
        if not root_path.is_dir():
            raise ValueError(f"Repository root is not a directory: {root}")

        resolved_edits: list[tuple[Path, FileEdit]] = []
        seen_paths: set[Path] = set()
        for edit in edits:
            target_path = (root_path / edit.path).resolve()
            try:
                target_path.relative_to(root_path)
            except ValueError as error:
                raise ValueError(f"File is outside repository root: {edit.path}") from error
            if target_path in seen_paths:
                raise ValueError(f"Duplicate edit path: {edit.path}")
            seen_paths.add(target_path)
            resolved_edits.append((target_path, edit))

        for target_path, edit in resolved_edits:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(edit.content, encoding="utf-8")

        return [target_path.relative_to(root_path).as_posix() for target_path, _ in resolved_edits]
