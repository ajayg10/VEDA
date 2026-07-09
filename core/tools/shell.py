import subprocess
import time
from shared.models import StepResult, StepStatus
from core.tools.base import BaseTool


SANDBOX_IMAGE = "python:3.11-alpine"
TIMEOUT_SECONDS = 30

async def run_shell(step_id: int, parameters: dict) -> StepResult:
    command = parameters.get("command", "").strip()
    if not command:
        return StepResult(
            step_id=step_id,
            status=StepStatus.FAILED,
            error="No command provided in parameters"
        )

    start = time.time()
    try:
        # Run inside a throwaway Docker container:
        # --rm          → destroyed immediately after command finishes
        # --network none → no internet access (prevents data exfiltration)
        # --memory 128m → caps RAM so one user can't OOM the host
        # --cpus 0.5    → caps CPU to half a core
        # --read-only   → filesystem is read-only (no writes to host)
        # --user 65534  → runs as nobody (unprivileged)
        docker_cmd = [
            "docker", "run", "--rm",
            "--network", "none",
            "--memory", "128m",
            "--cpus", "0.5",
            "--read-only",
            "--user", "65534",
            "--tmpfs", "/tmp:size=32m",   # writable /tmp inside container only
            SANDBOX_IMAGE,
            "sh", "-c", command
        ]

        result = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS + 5,  # outer timeout slightly longer than docker's
        )

        duration = (time.time() - start) * 1000

        if result.returncode == 0:
            return StepResult(
                step_id=step_id,
                status=StepStatus.SUCCESS,
                output=result.stdout.strip() or "(no output)",
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
        # Kill the dangling container
        subprocess.run(["docker", "ps", "-q", "--filter", "ancestor=" + SANDBOX_IMAGE],
                      capture_output=True)
        return StepResult(
            step_id=step_id,
            status=StepStatus.FAILED,
            error=f"Command timed out after {TIMEOUT_SECONDS} seconds",
        )
    except FileNotFoundError:
        return StepResult(
            step_id=step_id,
            status=StepStatus.FAILED,
            error="Docker not available in executor — socket not mounted",
        )
    except Exception as e:
        return StepResult(step_id=step_id, status=StepStatus.FAILED, error=str(e))
    
class ShellTool(BaseTool):

    name = "shell_command"
    description = "Execute shell commands"

    async def execute(self, step, context=None):
        return await run_shell(
            step.step_id,
            step.parameters,
        )    