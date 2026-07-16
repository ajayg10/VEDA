import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from core.tools.browser import BrowserTool
from shared.models import TaskStep, ToolType


class BrowserToolTests(unittest.TestCase):
    def test_opens_and_scrapes_a_page_in_one_tool_step(self):
        with tempfile.TemporaryDirectory() as directory:
            page = Path(directory) / "page.html"
            page.write_text("<title>VEDA</title><main>Deployed test content</main>", encoding="utf-8")
            step = TaskStep(step_id=1, description="Test browser", tool=ToolType.BROWSER_ACTION, parameters={"url": page.as_uri(), "actions": [{"action": "scrape_text", "selector": "main"}]}, rationale="test")
            result = asyncio.run(BrowserTool().execute(step))

        self.assertEqual(result.status, "success")
        self.assertEqual(json.loads(result.output)[1]["text"], "Deployed test content")
