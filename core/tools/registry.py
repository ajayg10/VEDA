from typing import Dict

from .base import BaseTool

# Core tools
from .shell import ShellTool
from .http import HttpTool
from .file_ops import FileCreateTool, FileReadTool
from .python_runner import PythonTool
from .browser import BrowserTool

# Module 9 — Code Agent tools
from .code_ops import (
    CodeReadTool,
    CodeEditTool,
    CodePatchTool,
    CodeReviewTool,
    CodeRenameTool,
    CodeDocsTool,
    CodeDiffTool,
    CodeGenTestsTool,
)

# Module 8 — Repository Intelligence tools
from .project_ops import ProjectScanTool, ProjectContextTool


class ToolRegistry:
    """Central registry mapping tool names to their async handler instances."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list(self) -> list[BaseTool]:
        return list(self._tools.values())

    def tool_names(self) -> list[str]:
        return sorted(self._tools.keys())

    def load_builtin_tools(self) -> None:
        """Register all built-in VEDA tools."""
        # Core execution tools
        self.register(ShellTool())
        self.register(HttpTool())
        self.register(FileCreateTool())
        self.register(FileReadTool())
        self.register(PythonTool())
        self.register(BrowserTool())

        # Module 9 — Code Agent
        self.register(CodeReadTool())
        self.register(CodeEditTool())
        self.register(CodePatchTool())
        self.register(CodeReviewTool())
        self.register(CodeRenameTool())
        self.register(CodeDocsTool())
        self.register(CodeDiffTool())
        self.register(CodeGenTestsTool())

        # Module 8 — Repository Intelligence
        self.register(ProjectScanTool())
        self.register(ProjectContextTool())
