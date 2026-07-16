import asyncio
import tempfile
import unittest
from pathlib import Path

from core.browser_agent.session import BrowserSession


class BrowserSessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_opens_a_local_website_and_returns_its_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            page = Path(directory) / "page.html"
            page.write_text("<title>VEDA Browser Test</title><h1>Ready</h1>", encoding="utf-8")

            async with BrowserSession() as browser:
                snapshot = await browser.open(page.as_uri())

        self.assertEqual(snapshot.title, "VEDA Browser Test")
        self.assertTrue(snapshot.url.endswith("page.html"))
        self.assertEqual(snapshot.status_code, 200)

    async def test_clicks_a_page_element_in_the_active_session(self):
        with tempfile.TemporaryDirectory() as directory:
            page = Path(directory) / "page.html"
            page.write_text(
                "<title>Before</title><button id='go' onclick=\"document.title='After'\">Go</button>",
                encoding="utf-8",
            )

            async with BrowserSession() as browser:
                await browser.open(page.as_uri())
                snapshot = await browser.click("#go")

        self.assertEqual(snapshot.title, "After")

    async def test_types_into_a_page_input(self):
        with tempfile.TemporaryDirectory() as directory:
            page = Path(directory) / "page.html"
            page.write_text("<input id='name'>", encoding="utf-8")

            async with BrowserSession() as browser:
                await browser.open(page.as_uri())
                await browser.type("#name", "VEDA")
                value = await browser.page.input_value("#name")

        self.assertEqual(value, "VEDA")

    async def test_fills_and_submits_a_login_form(self):
        with tempfile.TemporaryDirectory() as directory:
            page = Path(directory) / "login.html"
            page.write_text("<title>Login</title><input id='user'><input id='pass'><button id='submit' onclick=\"document.title='Signed in'\">Sign in</button>", encoding="utf-8")
            async with BrowserSession() as browser:
                await browser.open(page.as_uri())
                await browser.login("#user", "#pass", "#submit", "ajay", "secret")
                title = await browser.page.title()
        self.assertEqual(title, "Signed in")

    async def test_supports_remaining_browser_operations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            upload = root / "upload.txt"; upload.write_text("file")
            page = root / "page.html"
            page.write_text("<form><input id='a'><input id='file' type='file'></form><main>VEDA content</main><div class='captcha-box'></div>", encoding="utf-8")
            async with BrowserSession() as browser:
                await browser.open(page.as_uri())
                await browser.fill_form({"#a": "value"})
                await browser.upload("#file", str(upload))
                await browser.screenshot(str(root / "page.png"))
                await browser.pdf(str(root / "page.pdf"))
                text = await browser.scrape_text("main")
                tab = await browser.new_tab()
                await tab.goto(page.as_uri())
                captcha = await browser.requires_captcha_assistance()
            self.assertTrue((root / "page.png").is_file())
            self.assertTrue((root / "page.pdf").is_file())
        self.assertEqual(text, "VEDA content")
        self.assertFalse(captcha)  # No iframe present in page.html snippet


if __name__ == "__main__":
    unittest.main()
