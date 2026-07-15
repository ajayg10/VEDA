import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReviewFinding:
    path: str
    line: int
    rule: str
    message: str


class PythonCodeReviewer:
    """Report a small set of high-signal Python correctness risks."""

    def review(self, root: str, path: str) -> list[ReviewFinding]:
        root_path = Path(root).resolve()
        source_path = (root_path / path).resolve()
        try:
            relative_path = source_path.relative_to(root_path).as_posix()
        except ValueError as error:
            raise ValueError(f"File is outside repository root: {path}") from error
        if source_path.suffix != ".py" or not source_path.is_file():
            raise ValueError(f"Python repository file does not exist: {path}")

        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=relative_path)
        findings: list[ReviewFinding] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                findings.append(
                    ReviewFinding(relative_path, node.lineno, "bare-except", "Bare except catches system exceptions.")
                )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                findings.extend(self._mutable_default_findings(relative_path, node))
        return sorted(findings, key=lambda finding: (finding.line, finding.rule))

    @staticmethod
    def _mutable_default_findings(path: str, node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ReviewFinding]:
        findings: list[ReviewFinding] = []
        arguments = node.args.posonlyargs + node.args.args
        defaults = [None] * (len(arguments) - len(node.args.defaults)) + list(node.args.defaults)
        for argument, default in zip(arguments, defaults):
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                findings.append(
                    ReviewFinding(
                        path,
                        default.lineno,
                        "mutable-default",
                        f"Parameter '{argument.arg}' has a mutable default value.",
                    )
                )
        return findings
