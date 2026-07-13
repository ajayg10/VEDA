async def run_python_script(step_id: int, parameters: dict, context: dict | None = None) -> StepResult:
    code = parameters.get("code", "").strip()
    if not code:
        return StepResult(step_id=step_id, status=StepStatus.FAILED, error="No code provided")

    context_injection = ""
    if context:
        context_injection = f"step_outputs = {json.dumps(context)}\n"

    full_code = context_injection + code

    start = time.time()

    try:
        docker_cmd = [
            "docker", "run", "--rm",
            "--network", "none",
            "--memory", "128m",
            "--cpus", "0.5",
            "--read-only",
            "--user", "65534",
            "--tmpfs", "/tmp:size=32m",
            "-i",
            SANDBOX_IMAGE,
            "python", "-"
        ]

        result = subprocess.run(
            docker_cmd,
            input=full_code,
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