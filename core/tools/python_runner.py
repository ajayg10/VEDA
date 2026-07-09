import sys
import io
import time
from shared.models import StepResult, StepStatus
from core.tools.base import BaseTool


_BLOCKED = {"open", "eval", "exec", "compile"}

def _safe_builtins() -> dict:
    """Return a restricted __builtins__ dict without dangerous functions."""
    import builtins
    safe = {
        name: getattr(builtins, name)
        for name in dir(builtins)
        if name not in _BLOCKED and not name.startswith("__")
    }
    safe["__import__"] = builtins.__import__
    return safe

async def run_python_script(step_id: int, parameters: dict, context: dict | None = None) -> StepResult:
    code = parameters.get("code", "").strip()

    if not code:
        return StepResult(step_id=step_id, status=StepStatus.FAILED, error="No code provided")

    old_stdout = sys.stdout
    sys.stdout  = buffer = io.StringIO()

    start = time.time()
    try:
        safe_globals = {
            "__builtins__": _safe_builtins(),
            "json":         __import__("json"),
            "re":           __import__("re"),
            "math":         __import__("math"),
            "step_outputs": context or {},
        }
        exec(code, safe_globals)  # noqa: S102
        output = buffer.getvalue().strip()
        duration = (time.time() - start) * 1000

        return StepResult(
            step_id=step_id,
            status=StepStatus.SUCCESS,
            output=output or "(script ran, no output)",
            duration_ms=duration,
        )
    except Exception as e:
        return StepResult(step_id=step_id, status=StepStatus.FAILED, error=f"{type(e).__name__}: {e}")
    finally:
        sys.stdout = old_stdout


class PythonTool(BaseTool):

    name = "python_script"
    description = "Execute Python code"

    async def execute(self, step, context=None):
        return await run_python_script(
            step.step_id,
            step.parameters,
            context,
        )        