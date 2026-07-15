import os
from collections.abc import Iterator
from pathlib import Path


def iter_repository_paths(root: Path, ignored_directories: set[str]) -> Iterator[Path]:
    """Yield repository paths while pruning ignored directories before descent."""
    for directory, directories, files in os.walk(root):
        directories[:] = sorted(
            name for name in directories if name not in ignored_directories
        )
        directory_path = Path(directory)
        yield from (directory_path / name for name in directories)
        yield from (directory_path / name for name in sorted(files))
