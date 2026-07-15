import ast
from pathlib import Path


class PythonTestScaffoldGenerator:
    """Generate minimal unittest scaffolds for public top-level Python functions."""

    def generate(self, root: str, path: str) -> str:
        root_path = Path(root).resolve()
        source_path = (root_path / path).resolve()
        try:
            relative_path = source_path.relative_to(root_path)
        except ValueError as error:
            raise ValueError(f"File is outside repository root: {path}") from error
        if source_path.suffix != ".py" or not source_path.is_file():
            raise ValueError(f"Python repository file does not exist: {path}")

        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=relative_path.as_posix())
        functions = [
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_")
        ]
        module = ".".join(relative_path.with_suffix("").parts)
        lines = ["import unittest", "", f"import {module}", "", ""]
        class_name = f"{source_path.stem.title().replace('_', '')}Tests"
        lines.extend([f"class {class_name}(unittest.TestCase):"])
        if not functions:
            lines.append("    pass")
        for function in functions:
            lines.extend(
                [
                    f"    def test_{function}(self):",
                    f"        result = {module}.{function}()",
                    "        self.assertIsNotNone(result)",
                    "",
                ]
            )
        lines.extend(["", "if __name__ == \"__main__\":", "    unittest.main()", ""])
        return "\n".join(lines)
