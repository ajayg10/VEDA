import ast
from pathlib import Path


class PythonTestScaffoldGenerator:
    """Generate minimal unittest scaffolds for public top-level Python functions.

    Generated tests call each function with sensible placeholder arguments
    derived from its signature rather than always passing zero arguments.
    """

    # Placeholder values by parameter name hint
    _NAME_HINTS: dict[str, str] = {
        "path": '"/tmp/example"',
        "root": '"/tmp"',
        "url":  '"https://example.com"',
        "name": '"test"',
        "text": '"hello"',
        "query":"'test query'",
        "key":  '"key"',
        "value":'"value"',
        "n":    "1",
        "k":    "3",
        "limit":"10",
        "max":  "100",
        "min":  "0",
        "data": "{}",
        "items":"[]",
    }

    def generate(self, root: str, path: str) -> str:
        root_path   = Path(root).resolve()
        source_path = (root_path / path).resolve()
        try:
            relative_path = source_path.relative_to(root_path)
        except ValueError as error:
            raise ValueError(f"File is outside repository root: {path}") from error
        if source_path.suffix != ".py" or not source_path.is_file():
            raise ValueError(f"Python repository file does not exist: {path}")

        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=relative_path.as_posix())
        module = ".".join(relative_path.with_suffix("").parts)

        # Collect public top-level functions with their argument lists
        functions: list[tuple[str, list[str]]] = []
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
                args = self._required_args(node)
                functions.append((node.name, args))

        lines = ["import unittest", "", f"import {module}", "", ""]
        class_name = f"{source_path.stem.title().replace('_', '')}Tests"
        lines.append(f"class {class_name}(unittest.TestCase):")

        if not functions:
            lines.append("    pass")
        else:
            for func_name, args in functions:
                call_args = ", ".join(self._placeholder(a) for a in args)
                lines.extend([
                    f"    def test_{func_name}(self):",
                    f"        result = {module}.{func_name}({call_args})",
                    "        self.assertIsNotNone(result)",
                    "",
                ])

        lines.extend(["", 'if __name__ == "__main__":', "    unittest.main()", ""])
        return "\n".join(lines)

    def _required_args(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
        """Return names of required positional arguments (no defaults, not self/cls)."""
        positional = node.args.posonlyargs + node.args.args
        n_defaults = len(node.args.defaults)
        n_required = len(positional) - n_defaults
        required   = [a.arg for a in positional[:n_required]]
        # Drop self / cls for methods (though this generator targets module-level functions)
        return [a for a in required if a not in ("self", "cls")]

    def _placeholder(self, param_name: str) -> str:
        """Return a plausible placeholder value for a parameter name."""
        lower = param_name.lower()
        for hint, value in self._NAME_HINTS.items():
            if hint in lower:
                return value
        return "None"
