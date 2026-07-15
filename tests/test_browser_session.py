import tempfile
import unittest
from pathlib import Path

from core.browser_agent.session import BrowserSession


class BrowserSessionTests(unittest.TestCase):
    def test_opens_a_local_website_and_returns_its_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            page = Path(directory) / "page.html"
            page.write_text("<title>VEDA Browser Test</title><h1>Ready</h1>", encoding="utf-8")

            with BrowserSession() as browser:
                snapshot = browser.open(page.as_uri())

        self.assertEqual(snapshot.title, "VEDA Browser Test")
        self.assertTrue(snapshot.url.endswith("page.html"))
        self.assertEqual(snapshot.status_code, 200)

    def test_clicks_a_page_element_in_the_active_session(self):
        with tempfile.TemporaryDirectory() as directory:
            page = Path(directory) / "page.html"
            page.write_text(
                "<title>Before</title><button id='go' onclick=\"document.title='After'\">Go</button>",
                encoding="utf-8",
            )

            with BrowserSession() as browser:
                browser.open(page.as_uri())
                snapshot = browser.click("#go")

        self.assertEqual(snapshot.title, "After")

    def test_types_into_a_page_input(self):
        with tempfile.TemporaryDirectory() as directory:
            page = Path(directory) / "page.html"
            page.write_text("<input id='name'>", encoding="utf-8")

            with BrowserSession() as browser:
                browser.open(page.as_uri())
                browser.type("#name", "VEDA")
                value = browser.page.input_value("#name")

        self.assertEqual(value, "VEDA")

    def test_fills_and_submits_a_login_form(self):
        with tempfile.TemporaryDirectory() as directory:
            page = Path(directory) / "login.html"
            page.write_text("<title>Login</title><input id='user'><input id='pass'><button id='submit' onclick=\"document.title='Signed in'\">Sign in</button>", encoding="utf-8")
            with BrowserSession() as browser:
                browser.open(page.as_uri())
                browser.login("#user", "#pass", "#submit", "ajay", "secret")
                title = browser.page.title()
        self.assertEqual(title, "Signed in")

    def test_supports_remaining_browser_operations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            upload = root / "upload.txt"; upload.write_text("file")
            page = root / "page.html"
            page.write_text("<form><input id='a'><input id='file' type='file'></form><main>VEDA content</main><div class='captcha-box'></div>", encoding="utf-8")
            with BrowserSession() as browser:
                browser.open(page.as_uri())
                browser.fill_form({"#a": "value"})
                browser.upload("#file", str(upload))
                browser.screenshot(str(root / "page.png"))
                browser.pdf(str(root / "page.pdf"))
                text = browser.scrape_text("main")
                tab = browser.new_tab()
                tab.goto(page.as_uri())
                captcha = browser.requires_captcha_assistance()
            self.assertTrue((root / "page.png").is_file())
            self.assertTrue((root / "page.pdf").is_file())
        self.assertEqual(text, "VEDA content")
        self.assertTrue(captcha)


if __name__ == "__main__":
    unittest.main()
