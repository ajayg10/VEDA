import json
import re
from pathlib import Path

from .models import Entrypoint
from .scanner import ProjectScanner


PYTHON_MAIN_GUARD = re.compile(r"if\s+__name__\s*==\s*[\"']__main__[\"']\s*:")
GO_MAIN_FUNCTION = re.compile(r"func\s+main\s*\(")
CONVENTIONAL_PYTHON_ENTRYPOINTS = {"main.py", "app.py", "manage.py", "wsgi.py", "asgi.py"}


class EntrypointFinder:
    """Discover executable application entrypoints without executing repository code."""

    def find(self, root: str) -> list[Entrypoint]:
        root_path = Path(root).resolve()
        if not root_path.is_dir():
            raise ValueError(f"Repository root is not a directory: {root}")

        entrypoints: set[Entrypoint] = set()
        for path in root_path.rglob("*"):
            if any(part in ProjectScanner.IGNORE_DIRS for part in path.parts):
                continue
            if not path.is_file():
                continue

            relative_path = path.relative_to(root_path).as_posix()
            if path.suffix == ".py" and self._is_python_entrypoint(path):
                entrypoints.add(Entrypoint(relative_path, "python"))
            elif path.suffix == ".go" and self._contains(path, GO_MAIN_FUNCTION):
                entrypoints.add(Entrypoint(relative_path, "go"))
            elif path.name == "package.json":
                entrypoints.update(self._javascript_entrypoints(path, root_path))

        return sorted(entrypoints, key=lambda entrypoint: (entrypoint.path, entrypoint.kind))

    def _is_python_entrypoint(self, path: Path) -> bool:
        return path.name in CONVENTIONAL_PYTHON_ENTRYPOINTS or self._contains(path, PYTHON_MAIN_GUARD)

    def _javascript_entrypoints(self, package_path: Path, root: Path) -> set[Entrypoint]:
        try:
            package = json.loads(package_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return set()

        values: list[str] = []
        for key in ("main", "module"):
            if isinstance(package.get(key), str):
                values.append(package[key])
        binary = package.get("bin")
        if isinstance(binary, str):
            values.append(binary)
        elif isinstance(binary, dict):
            values.extend(value for value in binary.values() if isinstance(value, str))

        base = package_path.parent
        return {
            Entrypoint((base / value).resolve().relative_to(root).as_posix(), "javascript")
            for value in values
            if self._is_inside_root(base / value, root) and (base / value).is_file()
        }

    @staticmethod
    def _contains(path: Path, pattern: re.Pattern[str]) -> bool:
        try:
            return bool(pattern.search(path.read_text(encoding="utf-8")))
        except OSError:
            return False

    @staticmethod
    def _is_inside_root(path: Path, root: Path) -> bool:
        try:
            path.resolve().relative_to(root)
            return True
        except ValueError:
            return False
