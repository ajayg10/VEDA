from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List

try:
    from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    _PLAYWRIGHT_AVAILABLE = False


@dataclass(frozen=True)
class PageSnapshot:
    url:         str
    title:       str
    status_code: int | None


class BrowserSession:
    """Async Playwright Chromium session wrapper for VEDA browser capabilities.

    Usage:
        async with BrowserSession() as browser:
            snapshot = await browser.open("https://example.com")
            text = await browser.scrape_text("h1")
    """

    def __init__(self, headless: bool = True) -> None:
        if not _PLAYWRIGHT_AVAILABLE:
            raise RuntimeError(
                "Playwright is not installed. Run: pip install playwright && playwright install chromium"
            )
        self.headless   = headless
        self._playwright: Playwright    | None = None
        self._browser:    Browser       | None = None
        self._context:    BrowserContext| None = None
        self.page:        Page          | None = None
        self._all_pages:  list[Page]           = []

    async def __aenter__(self) -> "BrowserSession":
        self._playwright = await async_playwright().start()
        self._browser    = await self._playwright.chromium.launch(headless=self.headless)
        self._context    = await self._browser.new_context()
        self.page        = await self._context.new_page()
        self._all_pages  = [self.page]
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    # Synchronous context manager fallback for backward compatibility
    def __enter__(self) -> "BrowserSession":
        import asyncio
        return asyncio.run(self.__aenter__())

    def __exit__(self, *args: object) -> None:
        import asyncio
        asyncio.run(self.__aexit__(*args))

    # ── Navigation ────────────────────────────────────────────────────────

    async def open(self, url: str) -> PageSnapshot:
        """Navigate to a URL and return page metadata."""
        self._require_page()
        response = await self.page.goto(url, wait_until="domcontentloaded")
        title    = await self.page.title()
        return PageSnapshot(self.page.url, title, response.status if response else None)

    async def get_current_url(self) -> str:
        """Return the current page URL."""
        self._require_page()
        return self.page.url

    # ── Interaction ───────────────────────────────────────────────────────

    async def click(self, selector: str) -> PageSnapshot:
        """Click an element. Waits for any resulting navigation to settle."""
        self._require_page()
        await self.page.click(selector)
        try:
            await self.page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        title = await self.page.title()
        return PageSnapshot(self.page.url, title, None)

    async def type(self, selector: str, value: str) -> None:
        """Fill an input element with value (clears existing content first)."""
        self._require_page()
        await self.page.locator(selector).fill(value)

    async def login(
        self,
        username_selector: str,
        password_selector: str,
        submit_selector:   str,
        username:          str,
        password:          str,
    ) -> None:
        """Fill and submit a login form."""
        await self.type(username_selector, username)
        await self.type(password_selector, password)
        await self.click(submit_selector)

    async def fill_form(self, values: dict[str, str]) -> None:
        """Fill multiple form fields. Keys are CSS selectors, values are input text."""
        for selector, value in values.items():
            await self.type(selector, value)

    async def upload(self, selector: str, file_path: str) -> None:
        """Set a file input to the given file path."""
        self._require_page()
        await self.page.locator(selector).set_input_files(file_path)

    async def wait_for_selector(self, selector: str, timeout_ms: int = 5000) -> None:
        """Wait until a selector appears on the page."""
        self._require_page()
        await self.page.wait_for_selector(selector, timeout=timeout_ms)

    # ── Extraction ────────────────────────────────────────────────────────

    async def scrape_text(self, selector: str = "body") -> str:
        """Return visible text content of elements matching the selector."""
        self._require_page()
        return await self.page.locator(selector).inner_text()

    async def scrape_links(self, selector: str = "a") -> List[str]:
        """Return all href values from elements matching the selector."""
        self._require_page()
        elements = await self.page.locator(selector).all()
        links = []
        for el in elements:
            href = await el.get_attribute("href")
            if href:
                links.append(href)
        return links

    async def requires_captcha_assistance(self) -> bool:
        """Return True if a CAPTCHA iframe is present on the page."""
        self._require_page()
        count = await self.page.locator(
            "iframe[src*='recaptcha'], iframe[src*='hcaptcha'], iframe[title*='captcha' i]"
        ).count()
        return count > 0

    # ── Output ────────────────────────────────────────────────────────────

    async def screenshot(self, path: str) -> None:
        """Save a full-page screenshot to the given path."""
        self._require_page()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        await self.page.screenshot(path=path, full_page=True)

    async def pdf(self, path: str) -> None:
        """Save the page as a PDF (headless Chromium only)."""
        self._require_page()
        if not self.headless:
            raise RuntimeError("PDF generation requires headless=True")
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        await self.page.pdf(path=path)

    async def download(self, url: str, save_path: str) -> str:
        """Trigger a download by navigating to a URL, return the saved path."""
        self._require_page()
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        async with self.page.expect_download() as download_info:
            await self.page.goto(url)
        download = await download_info.value
        await download.save_as(save_path)
        return save_path

    # ── Tabs ──────────────────────────────────────────────────────────────

    async def new_tab(self) -> Page:
        """Open a new browser tab. Subsequent operations use the new tab."""
        if self._context is None:
            raise RuntimeError("BrowserSession must be used as an async context manager")
        new_page = await self._context.new_page()
        self._all_pages.append(new_page)
        self.page = new_page
        return self.page

    def switch_to_tab(self, index: int) -> None:
        """Switch the active page to a previously opened tab by zero-based index."""
        if index < 0 or index >= len(self._all_pages):
            raise IndexError(f"Tab index {index} out of range (0–{len(self._all_pages) - 1})")
        self.page = self._all_pages[index]

    # ── Internal ──────────────────────────────────────────────────────────

    def _require_page(self) -> None:
        if self.page is None:
            raise RuntimeError("BrowserSession must be used as an async context manager")
