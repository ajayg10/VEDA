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

DOCKER_FILES = {
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
}

CI_FILES = {
    ".gitlab-ci.yml": "GitLab CI",
    "Jenkinsfile": "Jenkins",
    "azure-pipelines.yml": "Azure Pipelines",
    ".travis.yml": "Travis CI",
    "bitbucket-pipelines.yml": "Bitbucket Pipelines",
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


def detect_docker(path: Path) -> bool:
    """Return whether a file is a conventional Docker configuration file."""
    return path.name in DOCKER_FILES


def detect_ci_provider(path: Path) -> str | None:
    """Return the CI provider identified by a conventional configuration path."""
    if ".github" in path.parts and "workflows" in path.parts:
        return "GitHub Actions"
    if ".circleci" in path.parts and path.name == "config.yml":
        return "CircleCI"
    return CI_FILES.get(path.name)


def detect_test_file(path: Path) -> bool:
    """Return whether a path follows a common test file or directory convention."""
    name = path.name.lower()
    if any(part.lower() in {"test", "tests", "__tests__"} for part in path.parts):
        return True
    return (
        name.startswith("test_")
        or name.endswith("_test.py")
        or name.endswith(".test.js")
        or name.endswith(".test.ts")
        or name.endswith(".spec.js")
        or name.endswith(".spec.ts")
    )
