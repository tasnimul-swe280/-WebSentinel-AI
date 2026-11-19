"""Explores a website with a real browser and builds a SiteMap of pages, forms and links."""

import re
from collections import deque
from urllib.parse import urldefrag, urlparse

from playwright.async_api import Browser, async_playwright

from .dom import EXTRACT_PAGE_JS
from .models import BrokenLink, Element, Fingerprint, Form, FormKind, Page, SiteMap

EMAIL_HINT = re.compile(r"e-?mail", re.I)
SEARCH_HINT = re.compile(r"search|query|^q$", re.I)
CONTACT_HINT = re.compile(r"message|comment|subject|feedback", re.I)


def normalize(url: str) -> str:
    return urldefrag(url)[0]


def in_scope(url: str, base_url: str) -> bool:
    parsed, base = urlparse(url), urlparse(base_url)
    if parsed.scheme not in ("http", "https") or parsed.netloc != base.netloc:
        return False
    base_path = base.path.rsplit("/", 1)[0] if not base.path.endswith("/") else base.path
    return parsed.path.startswith(base_path.rstrip("/") or "/")


def field_text(field: Element) -> str:
    fp = field.fingerprint
    return " ".join([fp.name, fp.id, fp.label, fp.placeholder, fp.aria_label, fp.type])


def is_email_field(field: Element) -> bool:
    return field.fingerprint.type == "email" or bool(EMAIL_HINT.search(field_text(field)))


def classify_form(fields: list[Element]) -> FormKind:
    if any(f.fingerprint.type == "password" for f in fields):
        return "login"
    # Search inputs are often labelled only by placeholder/aria-label, not name/id.
    if len(fields) <= 3 and any(
        f.fingerprint.type == "search" or SEARCH_HINT.search(field_text(f)) for f in fields
    ):
        return "search"
    if any(f.kind == "textarea" or CONTACT_HINT.search(field_text(f)) for f in fields):
        return "contact"
    return "generic"


class RefCounter:
    def __init__(self) -> None:
        self.count = 0

    def next(self, prefix: str = "e") -> str:
        self.count += 1
        return f"{prefix}{self.count}"


def build_page(url: str, status: int, raw: dict, refs: RefCounter) -> tuple[Page, list[str]]:
    """Convert raw DOM extraction output into a Page. Returns the page and absolute link URLs."""

    def element(d: dict) -> Element:
        return Element(
            ref=refs.next(),
            kind=d["kind"],
            css=d["css"],
            fingerprint=Fingerprint(**d["fingerprint"]),
            required=d.get("required", False),
        )

    links = [element(link) for link in raw.get("links", [])]
    buttons = [element(b) for b in raw.get("buttons", [])]
    forms = []
    for f in raw.get("forms", []):
        fields = [element(d) for d in f["fields"]]
        forms.append(
            Form(
                ref=refs.next("f"),
                action=f.get("action", ""),
                method=f.get("method", "get"),
                kind=classify_form(fields),
                fields=fields,
                submit=element(f["submit"]) if f.get("submit") else None,
            )
        )
    page = Page(url=url, title=raw.get("title", ""), status=status, links=links, buttons=buttons, forms=forms)
    absolute = [normalize(link["absolute"]) for link in raw.get("links", [])]
    return page, absolute


async def crawl_with_browser(browser: Browser, base_url: str, max_pages: int = 15) -> SiteMap:
    base_url = normalize(base_url)
    site = SiteMap(base_url=base_url)
    refs = RefCounter()
    queue: deque[tuple[str, str | None, dict | None]] = deque([(base_url, None, None)])
    seen = {base_url}
    context = await browser.new_context()
    page = await context.new_page()
    try:
        while queue and len(site.pages) < max_pages:
            url, found_on, link = queue.popleft()
            try:
                response = await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                status = response.status if response else 0
            except Exception:
                status = 0
            if status == 0 or status >= 400:
                site.broken_links.append(
                    BrokenLink(
                        url=url,
                        status=status,
                        found_on=found_on or "",
                        text=(link or {}).get("text", ""),
                        css=(link or {}).get("css", ""),
                        fingerprint=Fingerprint(**(link or {}).get("fingerprint", {})),
                    )
                )
                continue
            raw = await page.evaluate(EXTRACT_PAGE_JS)
            current = normalize(page.url)
            built, absolute = build_page(current, status, raw, refs)
            site.pages.append(built)
            for href, el in zip(absolute, built.links, strict=False):
                if href not in seen and in_scope(href, base_url):
                    seen.add(href)
                    queue.append(
                        (
                            href,
                            current,
                            {"text": el.fingerprint.text, "css": el.css, "fingerprint": el.fingerprint.model_dump()},
                        )
                    )
    finally:
        await context.close()
    return site


async def crawl(base_url: str, max_pages: int = 15) -> SiteMap:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        try:
            return await crawl_with_browser(browser, base_url, max_pages)
        finally:
            await browser.close()
