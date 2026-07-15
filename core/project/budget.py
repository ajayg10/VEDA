import math
from pathlib import Path

from .models import ContextBudget, ContextFile, ContextSnippet


class TokenBudgeter:
    """Fit ranked repository files into a deterministic approximate token budget."""

    CHARS_PER_TOKEN = 4

    def build(self, root: str, files: list[ContextFile], max_tokens: int) -> ContextBudget:
        if max_tokens < 0:
            raise ValueError("max_tokens must be non-negative")

        root_path = Path(root).resolve()
        if not root_path.is_dir():
            raise ValueError(f"Repository root is not a directory: {root}")

        snippets: list[ContextSnippet] = []
        used_tokens = 0
        for file in files:
            remaining_tokens = max_tokens - used_tokens
            if remaining_tokens == 0:
                break

            contents = self._read_repository_file(root_path, file.path)
            if contents is None:
                continue

            estimated_tokens = self.estimate_tokens(contents)
            if estimated_tokens <= remaining_tokens:
                snippets.append(ContextSnippet(file.path, contents, estimated_tokens))
                used_tokens += estimated_tokens
                continue

            truncated = contents[: remaining_tokens * self.CHARS_PER_TOKEN]
            snippets.append(ContextSnippet(file.path, truncated, self.estimate_tokens(truncated)))
            used_tokens += snippets[-1].estimated_tokens
            break

        return ContextBudget(max_tokens, used_tokens, tuple(snippets))

    @classmethod
    def estimate_tokens(cls, contents: str) -> int:
        return math.ceil(len(contents) / cls.CHARS_PER_TOKEN)

    @staticmethod
    def _read_repository_file(root: Path, path: str) -> str | None:
        file_path = (root / path).resolve()
        try:
            file_path.relative_to(root)
        except ValueError as error:
            raise ValueError(f"File is outside repository root: {path}") from error
        if not file_path.is_file():
            return None
        try:
            return file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None
