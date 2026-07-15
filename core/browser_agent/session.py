from dataclasses import dataclass

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright


@dataclass(frozen=True)
class PageSnapshot:
    url: str
    title: str
    status_code: int | None


class BrowserSession:
    """Manage a Playwright Chromium session for VEDA browser capabilities."""

    def __init__(self, headless: bool = True) -> None:
        self.headless = headless
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self.page: Page | None = None

    def __enter__(self) -> "BrowserSession":
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        self._context = self._browser.new_context()
        self.page = self._context.new_page()
        return self

    def __exit__(self, *_: object) -> None:
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def open(self, url: str) -> PageSnapshot:
        if self.page is None:
            raise RuntimeError("BrowserSession must be used as a context manager")
        response = self.page.goto(url, wait_until="domcontentloaded")
        return PageSnapshot(self.page.url, self.page.title(), response.status if response else None)

    def click(self, selector: str) -> PageSnapshot:
        if self.page is None:
            raise RuntimeError("BrowserSession must be used as a context manager")
        self.page.click(selector)
        return PageSnapshot(self.page.url, self.page.title(), None)

    def type(self, selector: str, value: str) -> None:
        if self.page is None:
            raise RuntimeError("BrowserSession must be used as a context manager")
        self.page.locator(selector).fill(value)

    def login(self, username_selector: str, password_selector: str, submit_selector: str, username: str, password: str) -> None:
        self.type(username_selector, username)
        self.type(password_selector, password)
        self.click(submit_selector)

    def fill_form(self, values: dict[str, str]) -> None:
        for selector, value in values.items():
            self.type(selector, value)

    def upload(self, selector: str, file_path: str) -> None:
        if self.page is None:
            raise RuntimeError("BrowserSession must be used as a context manager")
        self.page.locator(selector).set_input_files(file_path)

    def screenshot(self, path: str) -> None:
        if self.page is None:
            raise RuntimeError("BrowserSession must be used as a context manager")
        self.page.screenshot(path=path, full_page=True)

    def pdf(self, path: str) -> None:
        if self.page is None:
            raise RuntimeError("BrowserSession must be used as a context manager")
        self.page.pdf(path=path)

    def scrape_text(self, selector: str = "body") -> str:
        if self.page is None:
            raise RuntimeError("BrowserSession must be used as a context manager")
        return self.page.locator(selector).inner_text()

    def new_tab(self) -> Page:
        if self._context is None:
            raise RuntimeError("BrowserSession must be used as a context manager")
        self.page = self._context.new_page()
        return self.page

    def requires_captcha_assistance(self) -> bool:
        if self.page is None:
            raise RuntimeError("BrowserSession must be used as a context manager")
        return self.page.locator("iframe[src*='recaptcha'], iframe[src*='hcaptcha'], [class*='captcha' i]").count() > 0
