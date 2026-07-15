import time
from typing import List, Set


from shared.models import (
    ExecutionPlan, TaskStep,
    StepResult, StepStatus, ExecutionResult,
    ToolType,
)
from core.tools.registry import ToolRegistry
from core.workspace import WorkspaceManager

class Executor:
# Mapping of ToolType to their async handler functions

    def __init__(self):
        self.registry = ToolRegistry()
        self.registry.load_builtin_tools()

    def _topological_sort(self, steps: List[TaskStep]) -> List[TaskStep]:
        step_map   = {s.step_id: s for s in steps} 
        in_degree  = {s.step_id: len(s.depends_on) for s in steps}
        queue      = [s for s in steps if len(s.depends_on) == 0]
        sorted_out: List[TaskStep] = []

        while queue:
            current = queue.pop(0)
            sorted_out.append(current)

            for step in steps:
                if current.step_id in step.depends_on:
                    in_degree[step.step_id] -= 1
                    if in_degree[step.step_id] == 0:
                        queue.append(step_map[step.step_id])

        # Append any remaining steps (cycle guard)
        seen = {s.step_id for s in sorted_out}
        for s in steps:
            if s.step_id not in seen:
                sorted_out.append(s)

        return sorted_out

    async def execute(self, plan: ExecutionPlan) -> ExecutionResult:
        workspace = WorkspaceManager().create()
        sorted_steps  = self._topological_sort(plan.steps)
        results:       List[StepResult] = []
        failed_steps:  Set[int]         = set()
        # Maps step_id → raw_body (or output if no raw_body) for downstream steps
        step_context = {
            "workspace": str(workspace)
        }
        start_total = time.time()

        for step in sorted_steps:
            if any(dep in failed_steps for dep in step.depends_on):
                results.append(StepResult(
                    step_id=step.step_id,
                    status=StepStatus.SKIPPED,
                    error=f"Skipped — dependency step(s) {step.depends_on} failed",
                ))
                failed_steps.add(step.step_id)
                continue

            result = await self._dispatch(step, step_context)
            results.append(result)

            # Store output for downstream steps to consume
            step_context[step.step_id] = result.raw_body or result.output

            if result.status == StepStatus.FAILED:
                failed_steps.add(step.step_id)

        total_duration = (time.time() - start_total) * 1000
        overall = StepStatus.FAILED if failed_steps else StepStatus.SUCCESS

        return ExecutionResult(
            goal=plan.goal,
            status=overall,
            step_results=results,
            total_duration_ms=total_duration,
        )
        
    async def _dispatch(self, step: TaskStep, context: dict) -> StepResult:
        
        tool = self.registry.get(step.tool.value)

        if tool is None:
            return StepResult(
                step_id=step.step_id,
                status=StepStatus.SUCCESS,
                output=step.parameters.get(
                    "note",
                    f"no_op: {step.description}"
                ),
            )

        return await tool.execute(step, context)