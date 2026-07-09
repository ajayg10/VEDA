from abc import ABC, abstractmethod
from shared.models import TaskStep, StepResult


class BaseTool(ABC):
    """
    Base class for every executable tool in VEDA.
    """

    name: str
    description: str = ""

    @abstractmethod
    async def execute(self, step: TaskStep, context: dict | None = None) -> StepResult:
        """
        Execute a task step.
        """
        raise NotImplementedError