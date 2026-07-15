from difflib import unified_diff


class DiffGenerator:
    """Generate reviewable unified diffs for repository file changes."""

    def generate(self, path: str, before: str, after: str) -> str:
        return "".join(
            unified_diff(
                before.splitlines(keepends=True),
                after.splitlines(keepends=True),
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
            )
        )
