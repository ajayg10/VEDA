import re
from pathlib import Path

from .editor import FileEdit, RepositoryEditor


REQUIREMENT_NAME = re.compile(r"^(?P<name>[A-Za-z0-9_.-]+)(?P<suffix>.*)$")
VERSION_SPECIFIER = re.compile(r"^(==|!=|>=|<=|~=|>|<).+")


class RequirementsUpdater:
    """Update one explicit dependency version in a repository requirements file."""

    def update(self, root: str, path: str, dependency: str, version_specifier: str) -> str:
        if not VERSION_SPECIFIER.fullmatch(version_specifier):
            raise ValueError("version_specifier must begin with a supported comparison operator")

        root_path = Path(root).resolve()
        requirements_path = (root_path / path).resolve()
        try:
            relative_path = requirements_path.relative_to(root_path).as_posix()
        except ValueError as error:
            raise ValueError(f"File is outside repository root: {path}") from error
        if not requirements_path.is_file():
            raise ValueError(f"Requirements file does not exist: {path}")

        lines = requirements_path.read_text(encoding="utf-8").splitlines(keepends=True)
        updated = False
        new_lines: list[str] = []
        for line in lines:
            match = REQUIREMENT_NAME.match(line.strip())
            if match and self._same_dependency(match.group("name"), dependency):
                newline = "\n" if line.endswith("\n") else ""
                comment = line[line.find("#") :].rstrip("\n") if "#" in line else ""
                new_lines.append(f"{dependency}{version_specifier}{' ' if comment else ''}{comment}{newline}")
                updated = True
            else:
                new_lines.append(line)

        if not updated:
            raise ValueError(f"Dependency not found: {dependency}")
        RepositoryEditor().write_many(root, [FileEdit(relative_path, "".join(new_lines))])
        return relative_path

    @staticmethod
    def _same_dependency(left: str, right: str) -> bool:
        return re.sub(r"[-_.]+", "-", left).lower() == re.sub(r"[-_.]+", "-", right).lower()
