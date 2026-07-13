import os
import time
import subprocess
import tempfile
import json
from shared.models import StepResult, StepStatus

SANDBOX_IMAGE   = "python:3.11-alpine"
TIMEOUT_SECONDS = 30

async def run_python_script(step_id: int, parameters: dict, context: dict | None = None) -> StepResult:
    code = parameters.get("code", "").strip()
    if not code:
        return StepResult(step_id=step_id, status=StepStatus.FAILED, error="No code provided")

    # Inject step_outputs context
    context_injection = ""
    if context:
        context_injection = f"step_outputs = {json.dumps(context)}\n"

    full_code = context_injection + code

    start = time.time()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, dir="/tmp") as f:
        f.write(full_code)
        tmp_path = f.name

    try:
        docker_cmd = [
            "docker", "run", "--rm",
            "--network", "none",
            "--memory", "128m",
            "--cpus", "0.5",
            "--read-only",
            "--user", "65534",
            "--tmpfs", "/tmp:size=32m",
            "-v", f"{tmp_path}:/tmp/script.py:ro",
            SANDBOX_IMAGE,
            "python", "/tmp/script.py"
        ]

        result = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS + 5,
        )
        duration = (time.time() - start) * 1000

        if result.returncode == 0:
            return StepResult(
                step_id=step_id,
                status=StepStatus.SUCCESS,
                output=result.stdout.strip() or "(script ran, no output)",
                duration_ms=duration,
            )
        else:
            return StepResult(
                step_id=step_id,
                status=StepStatus.FAILED,
                error=result.stderr.strip() or f"Exited with code {result.returncode}",
                duration_ms=duration,
            )

    except subprocess.TimeoutExpired:
        return StepResult(
            step_id=step_id,
            status=StepStatus.FAILED,
            error=f"Script timed out after {TIMEOUT_SECONDS} seconds",
        )
    except FileNotFoundError:
        return StepResult(
            step_id=step_id,
            status=StepStatus.FAILED,
            error="Docker not available in executor",
        )
    except Exception as e:
        return StepResult(step_id=step_id, status=StepStatus.FAILED, error=str(e))
    finally:
        os.unlink(tmp_path)


from core.tools.base import BaseTool

class PythonTool(BaseTool):
    name = "python_script"
    description = "Run Python code in a sandbox"
    async def execute(self, step, context=None):
        return await run_python_script(step.step_id, step.parameters, context)        
from core.tools.base import BaseTool

class PythonTool(BaseTool):
    name = "python_script"
    description = "Run Python code in a sandbox"
    async def execute(self, step, context=None):
        return await run_python_script(step.step_id, step.parameters, context)
