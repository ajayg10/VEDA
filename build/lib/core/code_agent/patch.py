import re
from dataclasses import dataclass, field
from pathlib import Path

from .editor import FileEdit, RepositoryEditor


HUNK_HEADER = re.compile(r"@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? \+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@")


@dataclass
class _FilePatch:
    old_path: str
    new_path: str
    hunks: list[list[str]] = field(default_factory=list)


class UnifiedPatchApplier:
    """Apply unified text patches after validating every changed file context."""

    def apply(self, root: str, patch: str) -> list[str]:
        root_path = Path(root).resolve()
        file_patches = self._parse(patch)
        edits: list[FileEdit] = []
        deletions: list[Path] = []

        for file_patch in file_patches:
            if file_patch.old_path == "/dev/null":
                before = []
                target_path = file_patch.new_path
            else:
                before = self._read_lines(root_path, file_patch.old_path)
                target_path = file_patch.old_path

            after = self._apply_hunks(before, file_patch.hunks)
            if file_patch.new_path == "/dev/null":
                deletions.append(self._safe_path(root_path, target_path))
            else:
                edits.append(FileEdit(file_patch.new_path, "".join(after)))

        changed = RepositoryEditor().write_many(root, edits)
        for path in deletions:
            path.unlink()
            changed.append(path.relative_to(root_path).as_posix())
        return changed

    def _parse(self, patch: str) -> list[_FilePatch]:
        lines = patch.splitlines(keepends=True)
        file_patches: list[_FilePatch] = []
        current: _FilePatch | None = None
        current_hunk: list[str] | None = None

        for line in lines:
            if line.startswith("--- "):
                current = _FilePatch(self._header_path(line[4:]), "")
                file_patches.append(current)
                current_hunk = None
            elif line.startswith("+++ ") and current is not None:
                current.new_path = self._header_path(line[4:])
            elif line.startswith("@@ ") and current is not None:
                if not HUNK_HEADER.match(line):
                    raise ValueError(f"Invalid unified diff hunk header: {line.strip()}")
                current_hunk = [line]
                current.hunks.append(current_hunk)
            elif current_hunk is not None and line[:1] in {" ", "+", "-", "\\"}:
                current_hunk.append(line)

        if not file_patches or any(not item.new_path or not item.hunks for item in file_patches):
            raise ValueError("Patch must contain a file header and at least one hunk")
        return file_patches

    @staticmethod
    def _header_path(value: str) -> str:
        path = value.strip().split("\t", 1)[0]
        if path in {"/dev/null", ""}:
            return path
        if path.startswith("a/") or path.startswith("b/"):
            return path[2:]
        return path

    def _read_lines(self, root: Path, path: str) -> list[str]:
        source_path = self._safe_path(root, path)
        if not source_path.is_file():
            raise ValueError(f"Patch source file does not exist: {path}")
        return source_path.read_text(encoding="utf-8").splitlines(keepends=True)

    def _apply_hunks(self, before: list[str], hunks: list[list[str]]) -> list[str]:
        output: list[str] = []
        cursor = 0
        for hunk in hunks:
            match = HUNK_HEADER.match(hunk[0])
            assert match is not None
            start = max(int(match.group("old_start")) - 1, 0)
            if start < cursor or start > len(before):
                raise ValueError("Patch hunks overlap or target an invalid line")
            output.extend(before[cursor:start])
            cursor = start

            for line in hunk[1:]:
                if line.startswith("\\"):
                    continue
                content = line[1:]
                if line.startswith("+"):
                    output.append(content)
                    continue
                if cursor >= len(before) or before[cursor] != content:
                    raise ValueError("Patch context does not match the repository file")
                if line.startswith(" "):
                    output.append(before[cursor])
                cursor += 1

        output.extend(before[cursor:])
        return output

    @staticmethod
    def _safe_path(root: Path, path: str) -> Path:
        resolved_path = (root / path).resolve()
        try:
            resolved_path.relative_to(root)
        except ValueError as error:
            raise ValueError(f"Patch file is outside repository root: {path}") from error
        return resolved_path
