import ast
from pathlib import Path


class PythonDocumentationGenerator:
    """Generate concise Markdown API documentation from Python source structure."""

    def generate(self, root: str, path: str) -> str:
        root_path = Path(root).resolve()
        source_path = (root_path / path).resolve()
        try:
            relative_path = source_path.relative_to(root_path).as_posix()
        except ValueError as error:
            raise ValueError(f"File is outside repository root: {path}") from error
        if source_path.suffix != ".py" or not source_path.is_file():
            raise ValueError(f"Python repository file does not exist: {path}")

        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=relative_path)
        sections = [f"# `{relative_path}`"]
        if docstring := ast.get_docstring(tree):
            sections.extend(["", docstring.splitlines()[0]])

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                sections.extend(["", f"## Class `{node.name}`"])
                if docstring := ast.get_docstring(node):
                    sections.extend(["", docstring.splitlines()[0]])
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                sections.extend(["", f"## Function `{node.name}{self._signature(node)}`"])
                if docstring := ast.get_docstring(node):
                    sections.extend(["", docstring.splitlines()[0]])
        return "\n".join(sections) + "\n"

    @staticmethod
    def _signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        positional = node.args.posonlyargs + node.args.args
        required_count = len(positional) - len(node.args.defaults)
        arguments = [argument.arg for argument in positional[:required_count]]
        arguments.extend(
            f"{argument.arg}={ast.unparse(default)}"
            for argument, default in zip(positional[required_count:], node.args.defaults)
        )
        if node.args.vararg:
            arguments.append(f"*{node.args.vararg.arg}")
        arguments.extend(
            argument.arg if default is None else f"{argument.arg}={ast.unparse(default)}"
            for argument, default in zip(node.args.kwonlyargs, node.args.kw_defaults)
        )
        if node.args.kwarg:
            arguments.append(f"**{node.args.kwarg.arg}")
        return f"({', '.join(arguments)})"
