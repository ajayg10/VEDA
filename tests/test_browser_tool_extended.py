"""
Tests for the extended browser tool (core/tools/browser.py).
These tests mock BrowserSession to avoid requiring a real browser.
"""
import asyncio
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from shared.models import StepStatus


def _make_step(step_id: int, parameters: dict) -> MagicMock:
    step = MagicMock()
    step.step_id    = step_id
    step.parameters = parameters
    return step


def _make_mock_session(title="Test Page", url="https://example.com", text="Hello World"):
    """Build a mock BrowserSession async context manager."""
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__  = AsyncMock(return_value=False)

    from core.browser_agent.session import PageSnapshot
    session.open            = AsyncMock(return_value=PageSnapshot(url=url, title=title, status_code=200))
    session.click           = AsyncMock(return_value=PageSnapshot(url=url, title="Clicked", status_code=None))
    session.type            = AsyncMock()
    session.fill_form       = AsyncMock()
    session.login           = AsyncMock()
    session.scrape_text     = AsyncMock(return_value=text)
    session.scrape_links    = AsyncMock(return_value=["https://a.com", "https://b.com"])
    session.screenshot      = AsyncMock()
    session.pdf             = AsyncMock()
    session.download        = AsyncMock(return_value="/tmp/file.zip")
    session.new_tab         = AsyncMock()
    session.wait_for_selector = AsyncMock()
    session.requires_captcha_assistance = AsyncMock(return_value=False)
    return session


class BrowserToolExtendedTests(unittest.IsolatedAsyncioTestCase):

    async def test_open_and_scrape_text(self):
        from core.tools.browser import BrowserTool
        session = _make_mock_session()
        with patch("core.tools.browser.BrowserSession", return_value=session):
            step   = _make_step(1, {
                "url": "https://example.com",
                "actions": [{"action": "scrape_text", "selector": "body"}],
            })
            result = await BrowserTool().execute(step)

        self.assertEqual(result.status, StepStatus.SUCCESS)
        data = json.loads(result.output)
        actions = {item["action"] for item in data}
        self.assertIn("open", actions)
        self.assertIn("scrape_text", actions)

    async def test_click_appends_result(self):
        """Clicking should now appear in the results list (bug fix)."""
        from core.tools.browser import BrowserTool
        session = _make_mock_session()
        with patch("core.tools.browser.BrowserSession", return_value=session):
            step   = _make_step(1, {
                "url": "https://example.com",
                "actions": [{"action": "click", "selector": "#btn"}],
            })
            result = await BrowserTool().execute(step)

        data    = json.loads(result.output)
        actions = [item["action"] for item in data]
        self.assertIn("click", actions)
        click_result = next(i for i in data if i["action"] == "click")
        self.assertEqual(click_result["selector"], "#btn")

    async def test_type_appends_result(self):
        from core.tools.browser import BrowserTool
        session = _make_mock_session()
        with patch("core.tools.browser.BrowserSession", return_value=session):
            step   = _make_step(1, {
                "url": "https://example.com",
                "actions": [{"action": "type", "selector": "#field", "value": "hello"}],
            })
            result = await BrowserTool().execute(step)

        data    = json.loads(result.output)
        actions = [item["action"] for item in data]
        self.assertIn("type", actions)

    async def test_type_without_value_does_not_crash(self):
        """type action missing 'value' key should not raise KeyError (bug fix)."""
        from core.tools.browser import BrowserTool
        session = _make_mock_session()
        with patch("core.tools.browser.BrowserSession", return_value=session):
            step   = _make_step(1, {
                "url": "https://example.com",
                "actions": [{"action": "type", "selector": "#field"}],
            })
            result = await BrowserTool().execute(step)
        self.assertEqual(result.status, StepStatus.SUCCESS)

    async def test_fill_form_appends_result(self):
        from core.tools.browser import BrowserTool
        session = _make_mock_session()
        with patch("core.tools.browser.BrowserSession", return_value=session):
            step   = _make_step(1, {
                "url": "https://example.com",
                "actions": [{"action": "fill_form", "values": {"#a": "1", "#b": "2"}}],
            })
            result = await BrowserTool().execute(step)

        data    = json.loads(result.output)
        actions = [item["action"] for item in data]
        self.assertIn("fill_form", actions)

    async def test_login_action(self):
        from core.tools.browser import BrowserTool
        session = _make_mock_session()
        with patch("core.tools.browser.BrowserSession", return_value=session):
            step   = _make_step(1, {
                "url": "https://example.com/login",
                "actions": [{
                    "action": "login",
                    "username_selector": "#user",
                    "password_selector": "#pass",
                    "submit_selector":   "[type=submit]",
                    "username":          "user@test.com",
                    "password":          "secret",
                }],
            })
            result = await BrowserTool().execute(step)

        self.assertEqual(result.status, StepStatus.SUCCESS)
        data = json.loads(result.output)
        self.assertTrue(any(i["action"] == "login" for i in data))

    async def test_scrape_links_action(self):
        from core.tools.browser import BrowserTool
        session = _make_mock_session()
        with patch("core.tools.browser.BrowserSession", return_value=session):
            step   = _make_step(1, {
                "url": "https://example.com",
                "actions": [{"action": "scrape_links", "selector": "a"}],
            })
            result = await BrowserTool().execute(step)

        data  = json.loads(result.output)
        links = next(i for i in data if i["action"] == "scrape_links")["links"]
        self.assertIn("https://a.com", links)

    async def test_screenshot_action(self):
        from core.tools.browser import BrowserTool
        session = _make_mock_session()
        with patch("core.tools.browser.BrowserSession", return_value=session):
            step   = _make_step(1, {
                "url": "https://example.com",
                "actions": [{"action": "screenshot", "path": "/tmp/test.png"}],
            })
            result = await BrowserTool().execute(step)

        self.assertEqual(result.status, StepStatus.SUCCESS)
        session.screenshot.assert_called_once_with("/tmp/test.png")

    async def test_captcha_check_action(self):
        from core.tools.browser import BrowserTool
        session = _make_mock_session()
        session.requires_captcha_assistance.return_value = True
        with patch("core.tools.browser.BrowserSession", return_value=session):
            step   = _make_step(1, {
                "url": "https://example.com",
                "actions": [{"action": "captcha_check"}],
            })
            result = await BrowserTool().execute(step)

        data         = json.loads(result.output)
        captcha_item = next(i for i in data if i["action"] == "captcha_check")
        self.assertTrue(captcha_item["requires_assistance"])

    async def test_unsupported_action_fails_with_helpful_message(self):
        from core.tools.browser import BrowserTool
        session = _make_mock_session()
        with patch("core.tools.browser.BrowserSession", return_value=session):
            step   = _make_step(1, {
                "url": "https://example.com",
                "actions": [{"action": "fly_to_moon"}],
            })
            result = await BrowserTool().execute(step)

        self.assertEqual(result.status, StepStatus.FAILED)
        self.assertIn("fly_to_moon", result.error)
        self.assertIn("Valid actions", result.error)

    async def test_missing_url_fails(self):
        from core.tools.browser import BrowserTool
        step   = _make_step(1, {"actions": []})
        result = await BrowserTool().execute(step)
        self.assertEqual(result.status, StepStatus.FAILED)

    async def test_missing_actions_fails(self):
        from core.tools.browser import BrowserTool
        step   = _make_step(1, {"url": "https://example.com"})
        result = await BrowserTool().execute(step)
        self.assertEqual(result.status, StepStatus.FAILED)


if __name__ == "__main__":
    unittest.main()
