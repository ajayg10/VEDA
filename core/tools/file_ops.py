import os
import time
from shared.models import StepResult, StepStatus


async def run_file_create(step_id: int, parameters: dict) -> StepResult:
    filename = parameters.get("filename", "").strip()
    content  = parameters.get("content", "")

    if not filename:
        return StepResult(step_id=step_id, status=StepStatus.FAILED, error="No filename provided")

    start = time.time()
    try:
        # Create parent directories if they don't exist
        parent = os.path.dirname(filename)
        if parent:
            os.makedirs(parent, exist_ok=True)

        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)

        duration = (time.time() - start) * 1000
        return StepResult(
            step_id=step_id,
            status=StepStatus.SUCCESS,
            output=f"Created '{filename}' ({len(content)} chars)",
            duration_ms=duration,
        )
    except Exception as e:
        return StepResult(step_id=step_id, status=StepStatus.FAILED, error=str(e))


async def run_file_read(step_id: int, parameters: dict) -> StepResult:
    filename = parameters.get("filename", "").strip()

    if not filename:
        return StepResult(step_id=step_id, status=StepStatus.FAILED, error="No filename provided")

    start = time.time()
    try:
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()

        duration = (time.time() - start) * 1000
        return StepResult(
            step_id=step_id,
            status=StepStatus.SUCCESS,
            output=content,
            duration_ms=duration,
        )
    except FileNotFoundError:
        return StepResult(step_id=step_id, status=StepStatus.FAILED, error=f"File not found: {filename}")
    except Exception as e:
        return StepResult(step_id=step_id, status=StepStatus.FAILED, error=str(e))