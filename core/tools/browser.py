import asyncio
import json
import time

from core.browser_agent.session import BrowserSession
from core.tools.base import BaseTool
from shared.models import StepResult, StepStatus


class BrowserTool(BaseTool):
    name = "browser_action"
    description = "Open a website and perform browser actions in one session."

    async def execute(self, step, context=None) -> StepResult:
        return await asyncio.to_thread(self._execute_sync, step)

    def _execute_sync(self, step) -> StepResult:
        url = str(step.parameters.get("url", "")).strip()
        actions = step.parameters.get("actions", [])
        if not url or not isinstance(actions, list):
            return StepResult(step_id=step.step_id, status=StepStatus.FAILED, error="Browser action requires url and actions")

        start = time.time()
        try:
            results = []
            with BrowserSession() as browser:
                snapshot = browser.open(url)
                results.append({"action": "open", "url": snapshot.url, "title": snapshot.title, "status": snapshot.status_code})
                for action in actions:
                    name = action.get("action")
                    if name == "click":
                        browser.click(action["selector"])
                    elif name == "type":
                        browser.type(action["selector"], action["value"])
                    elif name == "fill_form":
                        browser.fill_form(action["values"])
                    elif name == "scrape_text":
                        results.append({"action": name, "text": browser.scrape_text(action.get("selector", "body"))})
                    elif name == "captcha_check":
                        results.append({"action": name, "requires_assistance": browser.requires_captcha_assistance()})
                    else:
                        raise ValueError(f"Unsupported browser action: {name}")
            output = json.dumps(results)
            return StepResult(step_id=step.step_id, status=StepStatus.SUCCESS, output=output, raw_body=output, duration_ms=(time.time() - start) * 1000)
        except Exception as error:
            return StepResult(step_id=step.step_id, status=StepStatus.FAILED, error=str(error), duration_ms=(time.time() - start) * 1000)
