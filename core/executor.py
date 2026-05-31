import time
from typing import List, Set
from shared.models import (
    ExecutionPlan, TaskStep,
    StepResult, StepStatus, ExecutionResult,
    ToolType,
)
from core.tools.shell         import run_shell
from core.tools.file_ops      import run_file_create, run_file_read
from core.tools.http          import run_http_request
from core.tools.python_runner import run_python_script


class Executor:
# Mapping of ToolType to their async handler functions

    _HANDLERS = {
        ToolType.SHELL_COMMAND: run_shell,
        ToolType.FILE_CREATE:   run_file_create,
        ToolType.FILE_READ:     run_file_read,
        ToolType.HTTP_REQUEST:  run_http_request,
        ToolType.PYTHON_SCRIPT: run_python_script,
    }

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
        sorted_steps  = self._topological_sort(plan.steps)
        results:       List[StepResult] = []
        failed_steps:  Set[int]         = set()
        # Maps step_id → raw_body (or output if no raw_body) for downstream steps
        step_context:  dict             = {}
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
        handler = self._HANDLERS.get(step.tool)

        if not handler:
            return StepResult(
                step_id=step.step_id,
                status=StepStatus.SUCCESS,
                output=step.parameters.get("note", f"no_op: {step.description}"),
            )

        # python_script needs context; other handlers ignore it
        if step.tool == ToolType.PYTHON_SCRIPT:
            return await handler(step.step_id, step.parameters, context)

        return await handler(step.step_id, step.parameters)