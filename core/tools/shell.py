import subprocess
import time
from shared.models import StepResult, StepStatus

# Patterns that are unconditionally blocked regardless of confirmation.
# requires_confirmation handles user-facing warnings for softer operations.
# This list stops the truly catastrophic ones at the engine level.
BLOCKED_PATTERNS = [
    "rm -rf /",
    "rm -rf ~",
    "mkfs",
    "dd if=/dev/zero",
    ":(){:|:&};:",   # fork bomb
    "> /dev/sda",
]


async def run_shell(step_id: int, parameters: dict) -> StepResult:
    command = parameters.get("command", "").strip()

    if not command:
        return StepResult(
            step_id=step_id,
            status=StepStatus.FAILED,
            error="No command provided in parameters"
        )

    for pattern in BLOCKED_PATTERNS:
        if pattern in command:
            return StepResult(
                step_id=step_id,
                status=StepStatus.FAILED,
                error=f"Blocked: command matches dangerous pattern '{pattern}'"
            )

    start = time.time()
    try:
        result = subprocess.run(
            command,
            shell=True,          # allows pipes, redirects, compound commands
            capture_output=True, # stdout and stderr captured separately
            text=True,           # decode bytes → str automatically
            timeout=30,          # kill if it hangs beyond 30s
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
        return StepResult(
            step_id=step_id,
            status=StepStatus.FAILED,
            error="Command timed out after 30 seconds",
        )
    except Exception as e:
        return StepResult(step_id=step_id, status=StepStatus.FAILED, error=str(e))