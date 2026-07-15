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


if __name__ == "__main__":
    unittest.main()
