import io
import token
import tokenize
from pathlib import Path

from core.project.paths import iter_repository_paths
from core.project.scanner import ProjectScanner

from .editor import FileEdit, RepositoryEditor


class PythonSymbolRenamer:
    """Rename Python identifier tokens without touching comments or string literals."""

    def rename(self, root: str, old_name: str, new_name: str) -> list[str]:
        if not old_name.isidentifier() or not new_name.isidentifier():
            raise ValueError("Symbol names must be valid Python identifiers")

        root_path = Path(root).resolve()
        edits: list[FileEdit] = []
        for path in iter_repository_paths(root_path, ProjectScanner.IGNORE_DIRS):
            if path.suffix != ".py" or not path.is_file():
                continue
            contents = path.read_text(encoding="utf-8")
            renamed = self._rename_tokens(contents, old_name, new_name)
            if renamed != contents:
                edits.append(FileEdit(path.relative_to(root_path).as_posix(), renamed))

        return RepositoryEditor().write_many(root, edits)

    @staticmethod
    def _rename_tokens(contents: str, old_name: str, new_name: str) -> str:
        lines = contents.splitlines(keepends=True)
        offsets = [0]
        for line in lines:
            offsets.append(offsets[-1] + len(line))
        replacements: list[tuple[int, int]] = []

        for item in tokenize.generate_tokens(io.StringIO(contents).readline):
            if item.type == token.NAME and item.string == old_name:
                start = offsets[item.start[0] - 1] + item.start[1]
                end = offsets[item.end[0] - 1] + item.end[1]
                replacements.append((start, end))

        for start, end in reversed(replacements):
            contents = contents[:start] + new_name + contents[end:]
        return contents
