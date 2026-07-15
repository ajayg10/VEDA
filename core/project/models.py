from dataclasses import dataclass, field


@dataclass
class ProjectInfo:

    root: str

    languages: list[str] = field(default_factory=list)

    frameworks: list[str] = field(default_factory=list)

    package_managers: list[str] = field(default_factory=list)

    uses_docker: bool = False

    ci_providers: list[str] = field(default_factory=list)

    has_tests: bool = False

    dependencies: list[str] = field(default_factory=list)

    entrypoints: list[str] = field(default_factory=list)

    total_files: int = 0

    total_directories: int = 0


@dataclass
class FolderNode:
    name: str
    path: str
    files: list[str] = field(default_factory=list)
    children: list["FolderNode"] = field(default_factory=list)


@dataclass(frozen=True)
class Entrypoint:
    path: str
    kind: str


@dataclass
class DependencyGraph:
    dependencies: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class ArchitectureSummary:
    root: str
    languages: list[str]
    frameworks: list[str]
    package_managers: list[str]
    uses_docker: bool
    ci_providers: list[str]
    has_tests: bool
    top_level_directories: list[str]
    entrypoints: list[Entrypoint]
    python_modules: int
    internal_dependencies: int


@dataclass(frozen=True)
class ContextFile:
    path: str
    score: int
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class CodeSummary:
    path: str
    language: str
    summary: str
    symbols: tuple[str, ...]


@dataclass(frozen=True)
class ContextSnippet:
    path: str
    content: str
    estimated_tokens: int


@dataclass(frozen=True)
class ContextBudget:
    max_tokens: int
    used_tokens: int
    snippets: tuple[ContextSnippet, ...]
