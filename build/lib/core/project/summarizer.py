import ast
from pathlib import Path

from .detectors import detect_language
from .models import CodeSummary


class CodeSummarizer:
    """Produce deterministic, execution-free summaries of repository files."""

    def summarize(self, root: str, path: str) -> CodeSummary:
        root_path = Path(root).resolve()
        source_path = (root_path / path).resolve()
        try:
            relative_path = source_path.relative_to(root_path).as_posix()
        except ValueError as error:
            raise ValueError(f"File is outside repository root: {path}") from error
        if not source_path.is_file():
            raise ValueError(f"Repository file does not exist: {path}")

        language = detect_language(source_path) or "Text"
        try:
            contents = source_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return CodeSummary(relative_path, language, "Binary file.", ())

        if source_path.suffix == ".py":
            return self._summarize_python(relative_path, contents)
        return CodeSummary(
            relative_path,
            language,
            f"{language} file with {len(contents.splitlines())} lines.",
            (),
        )

    def _summarize_python(self, path: str, contents: str) -> CodeSummary:
        try:
            tree = ast.parse(contents, filename=path)
        except SyntaxError:
            return CodeSummary(path, "Python", "Python file with syntax errors.", ())

        classes = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
        functions = [
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        imports = self._imports(tree)
        parts = ["Python module"]
        docstring = ast.get_docstring(tree)
        if docstring:
            parts.append(f"Docstring: {docstring.splitlines()[0]}")
        if classes:
            parts.append(f"Classes: {', '.join(classes)}")
        if functions:
            parts.append(f"Functions: {', '.join(functions)}")
        if imports:
            parts.append(f"Imports: {', '.join(imports)}")
        return CodeSummary(path, "Python", ". ".join(parts) + ".", tuple(classes + functions))

    @staticmethod
    def _imports(tree: ast.Module) -> list[str]:
        imports: list[str] = []
        for node in tree.body:
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        return sorted(set(imports))
