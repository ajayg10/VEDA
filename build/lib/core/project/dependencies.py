import ast
from pathlib import Path

from .models import DependencyGraph
from .paths import iter_repository_paths
from .scanner import ProjectScanner


class DependencyGraphBuilder:
    """Build a static graph of repository-local Python imports."""

    def build(self, root: str) -> DependencyGraph:
        root_path = Path(root).resolve()
        if not root_path.is_dir():
            raise ValueError(f"Repository root is not a directory: {root}")

        module_paths = self._module_paths(root_path)
        dependencies = {
            path: self._dependencies_for(path, module, module_paths, root_path)
            for module, path in module_paths.items()
        }
        return DependencyGraph(dependencies=dependencies)

    def _module_paths(self, root: Path) -> dict[str, str]:
        modules: dict[str, str] = {}
        for path in iter_repository_paths(root, ProjectScanner.IGNORE_DIRS):
            if path.suffix != ".py" or not path.is_file():
                continue
            relative = path.relative_to(root)
            module = self._module_name(relative)
            if module:
                modules[module] = relative.as_posix()
        return modules

    @staticmethod
    def _module_name(path: Path) -> str | None:
        parts = list(path.with_suffix("").parts)
        if parts[-1] == "__init__":
            parts.pop()
        return ".".join(parts) or None

    def _dependencies_for(
        self,
        path: str,
        module: str,
        module_paths: dict[str, str],
        root: Path,
    ) -> list[str]:
        source_path = root / path
        try:
            tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=path)
        except (OSError, SyntaxError, UnicodeDecodeError):
            return []

        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.update(self._from_imports(node, module, module_paths))

        return sorted(
            module_paths[imported]
            for imported in imports
            if imported in module_paths and module_paths[imported] != path
        )

    def _from_imports(
        self,
        node: ast.ImportFrom,
        source_module: str,
        module_paths: dict[str, str],
    ) -> set[str]:
        base_module = self._from_base_module(node, source_module)
        if not base_module:
            return set()

        candidates = {base_module} if node.module else set()
        candidates.update(
            f"{base_module}.{alias.name}"
            for alias in node.names
            if alias.name != "*"
        )
        return {candidate for candidate in candidates if candidate in module_paths}

    @staticmethod
    def _from_base_module(node: ast.ImportFrom, source_module: str) -> str:
        if node.level == 0:
            return node.module or ""

        package_parts = source_module.split(".")[:-1]
        parent_parts = package_parts[: len(package_parts) - node.level + 1]
        if node.level > len(package_parts) + 1:
            return ""
        module_parts = parent_parts + (node.module.split(".") if node.module else [])
        return ".".join(part for part in module_parts if part)
