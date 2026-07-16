from typing import Dict

from .base import BaseTool

from .shell import ShellTool
from .http import HttpTool
from .file_ops import FileCreateTool, FileReadTool
from .python_runner import PythonTool
from .browser import BrowserTool


class ToolRegistry:

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool

    def get(self, name: str):
        return self._tools.get(name)

    def list(self):
        return list(self._tools.values())

    def load_builtin_tools(self):
        self.register(ShellTool())
        self.register(HttpTool())
        self.register(FileCreateTool())
        self.register(FileReadTool())
        self.register(PythonTool())
        self.register(BrowserTool())
