import ast
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReviewFinding:
    path:    str
    line:    int
    rule:    str
    message: str


TODO_PATTERN = re.compile(r"\b(TODO|FIXME|HACK|XXX|NOQA)\b", re.IGNORECASE)


class PythonCodeReviewer:
    """Report Python code quality risks via static AST and text analysis."""

    def review(self, root: str, path: str) -> list[ReviewFinding]:
        root_path   = Path(root).resolve()
        source_path = (root_path / path).resolve()
        try:
            relative_path = source_path.relative_to(root_path).as_posix()
        except ValueError as error:
            raise ValueError(f"File is outside repository root: {path}") from error
        if source_path.suffix != ".py" or not source_path.is_file():
            raise ValueError(f"Python repository file does not exist: {path}")

        source = source_path.read_text(encoding="utf-8")
        tree   = ast.parse(source, filename=relative_path)
        is_test_file = (
            source_path.stem.startswith("test_")
            or source_path.stem.endswith("_test")
            or "tests" in source_path.parts
        )

        findings: list[ReviewFinding] = []

        for node in ast.walk(tree):
            # Rule: bare except
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                findings.append(ReviewFinding(
                    relative_path, node.lineno,
                    "bare-except",
                    "Bare `except:` catches system exceptions (KeyboardInterrupt, SystemExit). "
                    "Use `except Exception:` or a specific exception type.",
                ))

            # Rule: mutable default arguments
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                findings.extend(self._mutable_default_findings(relative_path, node))

                # Rule: public function missing return type annotation (non-test files only)
                if (
                    not is_test_file
                    and not node.name.startswith("_")
                    and node.returns is None
                    and not isinstance(node, ast.AsyncFunctionDef)  # skip async for now
                ):
                    findings.append(ReviewFinding(
                        relative_path, node.lineno,
                        "missing-return-annotation",
                        f"Public function `{node.name}` has no return type annotation.",
                    ))

            # Rule: assert in non-test production code
            elif isinstance(node, ast.Assert) and not is_test_file:
                findings.append(ReviewFinding(
                    relative_path, node.lineno,
                    "assert-in-production",
                    "`assert` is stripped when Python runs with `-O`. "
                    "Use explicit `if/raise` for runtime validation.",
                ))

            # Rule: print() call in non-test production code
            elif (
                not is_test_file
                and isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "print"
            ):
                findings.append(ReviewFinding(
                    relative_path, node.lineno,
                    "print-statement",
                    "Use `logging` instead of `print()` for production code.",
                ))

        # Text-based rules (scan source lines directly)
        for lineno, line in enumerate(source.splitlines(), start=1):
            m = TODO_PATTERN.search(line)
            if m:
                tag = m.group(1).upper()
                findings.append(ReviewFinding(
                    relative_path, lineno,
                    "todo-comment",
                    f"{tag} comment found — consider tracking this in an issue tracker.",
                ))

        return sorted(findings, key=lambda f: (f.line, f.rule))

    @staticmethod
    def _mutable_default_findings(
        path: str,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> list[ReviewFinding]:
        findings: list[ReviewFinding] = []
        arguments = node.args.posonlyargs + node.args.args
        defaults  = [None] * (len(arguments) - len(node.args.defaults)) + list(node.args.defaults)
        for argument, default in zip(arguments, defaults):
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                findings.append(ReviewFinding(
                    path,
                    default.lineno,
                    "mutable-default",
                    f"Parameter `{argument.arg}` has a mutable default value. "
                    "This is shared across all callers — use `None` and assign inside the function.",
                ))
        return findings
