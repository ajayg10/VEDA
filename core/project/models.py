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
