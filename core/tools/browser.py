import json
import time

from core.browser_agent.session import BrowserSession
from core.tools.base import BaseTool
from shared.models import StepResult, StepStatus


class BrowserTool(BaseTool):
    name        = "browser_action"
    description = "Open a website and perform browser actions (click, type, scrape, screenshot, etc.) in one session."

    async def execute(self, step, context=None) -> StepResult:
        url     = str(step.parameters.get("url", "")).strip()
        actions = step.parameters.get("actions", [])
        if not url or not isinstance(actions, list):
            return StepResult(
                step_id=step.step_id,
                status=StepStatus.FAILED,
                error="Browser action requires 'url' (string) and 'actions' (list)",
            )

        start = time.time()
        try:
            results = []
            async with BrowserSession() as browser:
                snapshot = await browser.open(url)
                results.append({
                    "action": "open",
                    "url":    snapshot.url,
                    "title":  snapshot.title,
                    "status": snapshot.status_code,
                })

                for action in actions:
                    action_name = action.get("action")

                    if action_name == "click":
                        selector = action.get("selector", "")
                        snap = await browser.click(selector)
                        results.append({"action": "click", "selector": selector, "url": snap.url, "title": snap.title})

                    elif action_name == "type":
                        selector = action.get("selector", "")
                        value    = action.get("value", "")
                        await browser.type(selector, value)
                        results.append({"action": "type", "selector": selector, "value": value})

                    elif action_name == "fill_form":
                        values = action.get("values", {})
                        await browser.fill_form(values)
                        results.append({"action": "fill_form", "fields": list(values.keys())})

                    elif action_name == "login":
                        await browser.login(
                            username_selector=action.get("username_selector", "#username"),
                            password_selector=action.get("password_selector", "#password"),
                            submit_selector=action.get("submit_selector", "[type=submit]"),
                            username=action.get("username", ""),
                            password=action.get("password", ""),
                        )
                        results.append({"action": "login", "username": action.get("username", "")})

                    elif action_name == "scrape_text":
                        text = await browser.scrape_text(action.get("selector", "body"))
                        results.append({"action": "scrape_text", "text": text})

                    elif action_name == "scrape_links":
                        links = await browser.scrape_links(action.get("selector", "a"))
                        results.append({"action": "scrape_links", "links": links})

                    elif action_name == "screenshot":
                        path = action.get("path", "/tmp/veda_screenshot.png")
                        await browser.screenshot(path)
                        results.append({"action": "screenshot", "path": path})

                    elif action_name == "pdf":
                        path = action.get("path", "/tmp/veda_page.pdf")
                        await browser.pdf(path)
                        results.append({"action": "pdf", "path": path})

                    elif action_name == "download":
                        save_path = action.get("save_path", "/tmp/veda_download")
                        dl_url    = action.get("url", url)
                        await browser.download(dl_url, save_path)
                        results.append({"action": "download", "save_path": save_path})

                    elif action_name == "new_tab":
                        new_url = action.get("url", "")
                        if new_url:
                            await browser.new_tab()
                            snap = await browser.open(new_url)
                            results.append({"action": "new_tab", "url": snap.url, "title": snap.title})
                        else:
                            await browser.new_tab()
                            results.append({"action": "new_tab"})

                    elif action_name == "wait":
                        selector   = action.get("selector", "body")
                        timeout_ms = int(action.get("timeout_ms", 5000))
                        await browser.wait_for_selector(selector, timeout_ms)
                        results.append({"action": "wait", "selector": selector})

                    elif action_name == "captcha_check":
                        needs_help = await browser.requires_captcha_assistance()
                        results.append({"action": "captcha_check", "requires_assistance": needs_help})

                    else:
                        raise ValueError(f"Unsupported browser action: '{action_name}'. "
                                         f"Valid actions: click, type, fill_form, login, scrape_text, "
                                         f"scrape_links, screenshot, pdf, download, new_tab, wait, captcha_check")

            output = json.dumps(results, ensure_ascii=False)
            return StepResult(
                step_id=step.step_id,
                status=StepStatus.SUCCESS,
                output=output,
                raw_body=output,
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as error:
            return StepResult(
                step_id=step.step_id,
                status=StepStatus.FAILED,
                error=str(error),
                duration_ms=(time.time() - start) * 1000,
            )
