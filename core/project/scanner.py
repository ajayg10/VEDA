from pathlib import Path

from .models import ProjectInfo
from .detectors import (
    detect_ci_provider,
    detect_docker,
    detect_framework,
    detect_language,
    detect_package_manager,
    detect_test_file,
)

class ProjectScanner:

    IGNORE_DIRS = {
        ".git",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
        ".idea",
        ".vscode",
        "dist",
        "build",
    }

    def scan(self, root: str) -> ProjectInfo:
        root_path = Path(root)
        info = ProjectInfo(root=root)

        for path in root_path.rglob("*"):

            # Skip ignored directories
            if any(part in self.IGNORE_DIRS for part in path.parts):
                continue

            if path.is_dir():
                info.total_directories += 1

            elif path.is_file():

                info.total_files += 1

                language = detect_language(path)
                frameworks = detect_framework(path)
                package_manager = detect_package_manager(path)
                uses_docker = detect_docker(path)
                ci_provider = detect_ci_provider(path)
                has_tests = detect_test_file(path)

                for framework in frameworks:
                    if framework not in info.frameworks:
                        info.frameworks.append(framework)

                if language and language not in info.languages:
                    info.languages.append(language)

                if package_manager and package_manager not in info.package_managers:
                    info.package_managers.append(package_manager)

                if uses_docker:
                    info.uses_docker = True

                if ci_provider and ci_provider not in info.ci_providers:
                    info.ci_providers.append(ci_provider)

                if has_tests:
                    info.has_tests = True

        return info
