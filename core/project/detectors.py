from pathlib import Path


LANGUAGE_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".jsx": "JavaScript",
    ".go": "Go",
    ".java": "Java",
    ".rs": "Rust",
    ".cpp": "C++",
    ".cc": "C++",
    ".c": "C",
    ".cs": "C#",
    ".md": "Markdown",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
}

FASTAPI_SIGNALS = [
    "from fastapi import",
    "import fastapi",
    "FastAPI(",
]

PACKAGE_MANAGER_FILES = {
    "package-lock.json": "npm",
    "npm-shrinkwrap.json": "npm",
    "yarn.lock": "Yarn",
    "pnpm-lock.yaml": "pnpm",
    "bun.lock": "Bun",
    "bun.lockb": "Bun",
    "poetry.lock": "Poetry",
    "Pipfile.lock": "Pipenv",
    "uv.lock": "uv",
    "requirements.txt": "pip",
    "Cargo.lock": "Cargo",
    "go.sum": "Go modules",
    "composer.lock": "Composer",
}

def detect_language(path: Path) -> str | None:
    return LANGUAGE_MAP.get(path.suffix.lower())

def detect_framework(path: Path) -> list[str]:
    frameworks = []

    if path.suffix.lower() == ".py":
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                for signal in FASTAPI_SIGNALS:
                    if signal in content:
                        frameworks.append("FastAPI")
                        break
        except Exception:
            pass

    return frameworks


def detect_package_manager(path: Path) -> str | None:
    """Return the package manager identified by a manifest or lockfile."""
    return PACKAGE_MANAGER_FILES.get(path.name)
