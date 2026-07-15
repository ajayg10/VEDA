from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FileContents:
    path: str
    content: str
    size_bytes: int
    truncated: bool


class RepositoryReader:
    """Read text files from a repository without allowing path traversal."""

    def read(self, root: str, path: str, max_bytes: int = 100_000) -> FileContents:
        if max_bytes < 1:
            raise ValueError("max_bytes must be positive")

        root_path = Path(root).resolve()
        source_path = (root_path / path).resolve()
        try:
            relative_path = source_path.relative_to(root_path).as_posix()
        except ValueError as error:
            raise ValueError(f"File is outside repository root: {path}") from error
        if not source_path.is_file():
            raise ValueError(f"Repository file does not exist: {path}")

        with source_path.open("rb") as source:
            contents = source.read(max_bytes + 1)
        truncated = len(contents) > max_bytes
        contents = contents[:max_bytes]
        try:
            text = contents.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError(f"Repository file is not UTF-8 text: {path}") from error
        return FileContents(relative_path, text, len(contents), truncated)
