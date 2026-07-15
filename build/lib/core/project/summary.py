from .dependencies import DependencyGraphBuilder
from .entrypoints import EntrypointFinder
from .graph import FolderTreeBuilder
from .models import ArchitectureSummary
from .scanner import ProjectScanner


class ArchitectureSummarizer:
    """Compose existing repository analysis into a compact architecture view."""

    def summarize(self, root: str) -> ArchitectureSummary:
        project = ProjectScanner().scan(root)
        folder_tree = FolderTreeBuilder().build(root)
        entrypoints = EntrypointFinder().find(root)
        dependencies = DependencyGraphBuilder().build(root)

        return ArchitectureSummary(
            root=project.root,
            languages=project.languages,
            frameworks=project.frameworks,
            package_managers=project.package_managers,
            uses_docker=project.uses_docker,
            ci_providers=project.ci_providers,
            has_tests=project.has_tests,
            top_level_directories=[child.name for child in folder_tree.children],
            entrypoints=entrypoints,
            python_modules=len(dependencies.dependencies),
            internal_dependencies=sum(len(edges) for edges in dependencies.dependencies.values()),
        )
