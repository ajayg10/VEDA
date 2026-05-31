from pydantic import BaseModel, Field
from typing import List, Dict, Any
from enum import Enum


class ToolType(str, Enum):
    SHELL_COMMAND = "shell_command"
    FILE_CREATE   = "file_create"
    FILE_READ     = "file_read"
    HTTP_REQUEST  = "http_request"
    PYTHON_SCRIPT = "python_script"
    NO_OP         = "no_op"


class TaskStep(BaseModel):
    step_id: int = Field(..., description="Sequential step number starting from 1")
    description: str = Field(..., description="Human-readable description of what this step does")
    tool: ToolType = Field(..., description="The tool/executor to use for this step")
    parameters: Dict[str, Any] = Field(..., description="Tool-specific input parameters")
    depends_on: List[int] = Field(default_factory=list, description="step_ids that must complete before this step runs")
    rationale: str = Field(..., description="Why this specific step is necessary for the goal")


class ExecutionPlan(BaseModel):
    goal: str = Field(..., description="The original user goal, rephrased for clarity")
    reasoning: str = Field(..., description="High-level approach and reasoning before listing steps")
    steps: List[TaskStep] = Field(..., description="Ordered list of atomic execution steps")
    estimated_complexity: str = Field(..., description="Must be exactly one of: low | medium | high")
    requires_confirmation: bool = Field(..., description="True if any step is potentially destructive")
    

class StepStatus(str, Enum):
    SUCCESS = "success"
    FAILED  = "failed"
    SKIPPED = "skipped"
    PENDING = "pending"


class StepResult(BaseModel):
    step_id:     int
    status:      StepStatus
    output:      str   = ""
    error:       str   = ""
    duration_ms: float = 0.0
    raw_body:    str   = "" 

class ExecutionResult(BaseModel):
    goal:             str
    status:           StepStatus
    step_results:     List[StepResult]
    total_duration_ms: float    