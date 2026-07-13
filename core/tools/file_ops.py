import os
import time
import subprocess
import tempfile
from shared.models import StepResult, StepStatus

SANDBOX_IMAGE   = "python:3.11-alpine"
TIMEOUT_SECONDS = 30

# Safe base directory — all file operations confined here
FILES_BASE = "/tmp/veda_files"

def _safe_path(filename: str) -> str:
    """Resolve path and ensure it stays within FILES_BASE."""
    safe = os.path.realpath(os.path.join(FILES_BASE, filename.lstrip("/")))
    if not safe.startswith(FILES_BASE):
        raise ValueError(f"Path traversal blocked: {filename}")
    return safe

async def run_file_create(step_id: int, parameters: dict) -> StepResult:
    filename = parameters.get("filename", "").strip()
    content  = parameters.get("content", "")
    if not filename:
        return StepResult(step_id=step_id, status=StepStatus.FAILED, error="No filename provided")
    start = time.time()
    try:
        safe = _safe_path(filename)
        os.makedirs(os.path.dirname(safe), exist_ok=True)
        with open(safe, "w", encoding="utf-8") as f:
            f.write(content)
        duration = (time.time() - start) * 1000
        return StepResult(
            step_id=step_id,
            status=StepStatus.SUCCESS,
            output=f"Created '{filename}' ({len(content)} chars)",
            duration_ms=duration,
        )
    except ValueError as e:
        return StepResult(step_id=step_id, status=StepStatus.FAILED, error=str(e))
    except Exception as e:
        return StepResult(step_id=step_id, status=StepStatus.FAILED, error=str(e))

async def run_file_read(step_id: int, parameters: dict) -> StepResult:
    filename = parameters.get("filename", "").strip()
    if not filename:
        return StepResult(step_id=step_id, status=StepStatus.FAILED, error="No filename provided")
    start = time.time()
    try:
        safe = _safe_path(filename)
        with open(safe, "r", encoding="utf-8") as f:
            content = f.read()
        duration = (time.time() - start) * 1000
        return StepResult(
            step_id=step_id,
            status=StepStatus.SUCCESS,
            output=content,
            duration_ms=duration,
        )
    except ValueError as e:
        return StepResult(step_id=step_id, status=StepStatus.FAILED, error=str(e))
    except FileNotFoundError:
        return StepResult(step_id=step_id, status=StepStatus.FAILED, error=f"File not found: {filename}")
    except Exception as e:
        return StepResult(step_id=step_id, status=StepStatus.FAILED, error=str(e))