from pathlib import Path


LANGUAGE_MAP = {
    ".py":   "Python",
    ".js":   "JavaScript",
    ".ts":   "TypeScript",
    ".tsx":  "TypeScript",
    ".jsx":  "JavaScript",
    ".go":   "Go",
    ".java": "Java",
    ".rs":   "Rust",
    ".cpp":  "C++",
    ".cc":   "C++",
    ".c":    "C",
    ".cs":   "C#",
    ".rb":   "Ruby",
    ".php":  "PHP",
    ".swift":"Swift",
    ".kt":   "Kotlin",
    ".md":   "Markdown",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml":  "YAML",
    ".toml": "TOML",
    ".html": "HTML",
    ".css":  "CSS",
    ".scss": "SCSS",
    ".sh":   "Shell",
}

# Framework detection: (content_signals, filename_signals)
FRAMEWORK_SIGNALS: dict[str, tuple[list[str], list[str]]] = {
    "FastAPI": (
        ["from fastapi import", "import fastapi", "FastAPI("],
        [],
    ),
    "Django": (
        ["from django", "import django", "django.setup()", "INSTALLED_APPS"],
        ["manage.py", "wsgi.py", "asgi.py"],
    ),
    "Flask": (
        ["from flask import", "import flask", "Flask(__name__)"],
        [],
    ),
    "Starlette": (
        ["from starlette import", "import starlette", "Starlette("],
        [],
    ),
    "SQLAlchemy": (
        ["from sqlalchemy", "import sqlalchemy", "declarative_base()", "create_engine("],
        [],
    ),
    "Pytest": (
        ["import pytest", "from pytest import"],
        ["conftest.py", "pytest.ini", "setup.cfg"],
    ),
    "React": (
        ["import React", "from 'react'", 'from "react"', "ReactDOM.render", "createRoot("],
        [],
    ),
    "Next.js": (
        ["from 'next", 'from "next', "getServerSideProps", "getStaticProps", "NextPage"],
        ["next.config.js", "next.config.ts", "next.config.mjs"],
    ),
    "Vue": (
        ["from 'vue'", 'from "vue"', "createApp(", "defineComponent("],
        ["vue.config.js"],
    ),
    "Angular": (
        ["@NgModule", "@Component", "@Injectable", "platformBrowserDynamic"],
        ["angular.json"],
    ),
    "Express": (
        ["require('express')", 'require("express")', "from 'express'", 'from "express"', "express()"],
        [],
    ),
    "NestJS": (
        ["@Module(", "@Controller(", "@Injectable(", "NestFactory.create"],
        ["nest-cli.json"],
    ),
    "Spring Boot": (
        ["@SpringBootApplication", "SpringApplication.run", "import org.springframework"],
        [],
    ),
    "Rails": (
        ["require 'rails'", "Rails.application", "ActionController", "ActiveRecord"],
        ["config/routes.rb", "Gemfile"],
    ),
    "Laravel": (
        ["Illuminate\\", "use App\\", "Route::get(", "Artisan::command("],
        ["artisan"],
    ),
}

PACKAGE_MANAGER_FILES = {
    "package-lock.json":    "npm",
    "npm-shrinkwrap.json":  "npm",
    "yarn.lock":            "Yarn",
    "pnpm-lock.yaml":       "pnpm",
    "bun.lock":             "Bun",
    "bun.lockb":            "Bun",
    "poetry.lock":          "Poetry",
    "Pipfile.lock":         "Pipenv",
    "uv.lock":              "uv",
    "requirements.txt":     "pip",
    "Cargo.lock":           "Cargo",
    "go.sum":               "Go modules",
    "composer.lock":        "Composer",
    "Gemfile.lock":         "Bundler",
}

DOCKER_FILES = {
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
}

CI_FILES = {
    ".gitlab-ci.yml":           "GitLab CI",
    "Jenkinsfile":              "Jenkins",
    "azure-pipelines.yml":      "Azure Pipelines",
    ".travis.yml":              "Travis CI",
    "bitbucket-pipelines.yml":  "Bitbucket Pipelines",
}


def detect_language(path: Path) -> str | None:
    return LANGUAGE_MAP.get(path.suffix.lower())


def detect_framework(path: Path) -> list[str]:
    """Return any frameworks detected from this file's name or content."""
    frameworks: list[str] = []
    path_str = path.name.lower()

    # Try to read the file content once
    content: str | None = None
    if path.suffix.lower() in {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".rb", ".php"}:
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            pass

    for framework, (content_signals, filename_signals) in FRAMEWORK_SIGNALS.items():
        # Check filename signals first (cheap)
        if any(sig.lower() == path_str for sig in filename_signals):
            frameworks.append(framework)
            continue
        # Check content signals
        if content and any(sig in content for sig in content_signals):
            frameworks.append(framework)

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
    if any(part.lower() in {"test", "tests", "__tests__", "spec", "specs"} for part in path.parts):
        return True
    return (
        name.startswith("test_")
        or name.endswith("_test.py")
        or name.endswith(".test.js")
        or name.endswith(".test.ts")
        or name.endswith(".spec.js")
        or name.endswith(".spec.ts")
    )
