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


if __name__ == "__main__":
    unittest.main()
