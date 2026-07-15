from dataclasses import dataclass, field


@dataclass
class ProjectInfo:

    root: str

    languages: list[str] = field(default_factory=list)

    frameworks: list[str] = field(default_factory=list)

    package_managers: list[str] = field(default_factory=list)

    uses_docker: bool = False

    dependencies: list[str] = field(default_factory=list)

    entrypoints: list[str] = field(default_factory=list)

    total_files: int = 0

    total_directories: int = 0
