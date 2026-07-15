from pathlib import Path

from .models import FolderNode
from .scanner import ProjectScanner


class FolderTreeBuilder:
    """Build a deterministic, repository-relative folder tree."""

    def __init__(self, ignored_directories: set[str] | None = None) -> None:
        self.ignored_directories = ignored_directories or ProjectScanner.IGNORE_DIRS

    def build(self, root: str) -> FolderNode:
        root_path = Path(root).resolve()
        if not root_path.is_dir():
            raise ValueError(f"Repository root is not a directory: {root}")
        return self._build_directory(root_path, root_path)

    def _build_directory(self, root: Path, directory: Path) -> FolderNode:
        relative_path = directory.relative_to(root)
        node = FolderNode(
            name=directory.name,
            path="." if relative_path == Path(".") else relative_path.as_posix(),
        )

        for path in sorted(directory.iterdir(), key=lambda item: item.name.lower()):
            if path.is_symlink():
                continue
            if path.is_dir():
                if path.name not in self.ignored_directories:
                    node.children.append(self._build_directory(root, path))
            elif path.is_file():
                node.files.append(path.name)

        return node
