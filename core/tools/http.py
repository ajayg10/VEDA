import time
import httpx
from shared.models import StepResult, StepStatus
from core.tools.base import BaseTool


async def run_http_request(step_id: int, parameters: dict) -> StepResult:
    method  = parameters.get("method", "GET").upper()
    url     = parameters.get("url", "").strip()
    headers = parameters.get("headers", {})
    body    = parameters.get("body") or None

    if not url:
        return StepResult(step_id=step_id, status=StepStatus.FAILED, error="No URL provided")

    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                json=body,
            )

        duration = (time.time() - start) * 1000

        # Truncate large responses so the terminal doesn't get flooded
        body_preview = response.text[:3000]
        if len(response.text) > 3000:
            body_preview += f"\n... [{len(response.text) - 3000} chars truncated]"

        output = f"HTTP {response.status_code} {response.reason_phrase}\n{body_preview}"

        if response.is_success:
            return StepResult(
                step_id=step_id,
                status=StepStatus.SUCCESS,
                output=output,          
                raw_body=response.text, 
                duration_ms=duration,
            )
        else:
            return StepResult(
                step_id=step_id,
                status=StepStatus.FAILED,
                error=output,
                duration_ms=duration,
                raw_body=response.text,
            )

    except httpx.TimeoutException:
        return StepResult(step_id=step_id, status=StepStatus.FAILED, error="Request timed out after 30s")
    except httpx.RequestError as e:
        return StepResult(step_id=step_id, status=StepStatus.FAILED, error=f"Request error: {e}")
    except Exception as e:
        return StepResult(step_id=step_id, status=StepStatus.FAILED, error=str(e))

class HttpTool(BaseTool):

    name = "http_request"

    description = "HTTP Requests"

    async def execute(self, step, context=None):
        return await run_http_request(
            step.step_id,
            step.parameters,
        )    