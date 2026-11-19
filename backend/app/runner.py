"""Executes test cases in a real browser, with self-healing locators and live progress events."""

import base64
import contextlib
import re
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

from playwright.async_api import Browser, Page, async_playwright, expect
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Locator as PWLocator

from .dom import CANDIDATES_JS
from .healer import best_match
from .models import Fingerprint, HealEvent, Locator, Step, TestCase, TestResult

Emit = Callable[[dict], Awaitable[None]]


async def _noop(_: dict) -> None:
    return None


class StepFailure(Exception):
    pass


class TestRunner:
    __test__ = False

    def __init__(
        self,
        artifacts_dir: Path,
        emit: Emit = _noop,
        self_heal: bool = True,
        find_timeout_ms: int = 1000,
        expect_timeout_ms: int = 4000,
        live_frames: bool = True,
    ) -> None:
        self.artifacts_dir = artifacts_dir
        self.emit = emit
        self.self_heal = self_heal
        self.find_timeout_ms = find_timeout_ms
        self.expect_timeout_ms = expect_timeout_ms
        self.live_frames = live_frames
        self.heal_cache: dict[str, tuple[str, float]] = {}

    async def run(self, tests: list[TestCase], headless: bool = True, slow_mo: int = 0) -> list[TestResult]:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=headless, slow_mo=slow_mo)
            try:
                return [await self.run_test(browser, test, i) for i, test in enumerate(tests)]
            finally:
                await browser.close()

    async def run_test(self, browser: Browser, test: TestCase, index: int = 0) -> TestResult:
        await self.emit({"type": "test_started", "index": index, "test_id": test.id, "title": test.title})
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()
        state = {"status": 0}
        console_errors: list[str] = []

        def on_response(response) -> None:  # type: ignore[no-untyped-def]
            # Track main-document responses, including HTTP 4xx/5xx returned after form submit.
            if response.frame == page.main_frame and response.request.is_navigation_request():
                state["status"] = response.status

        page.on("response", on_response)
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)

        result = TestResult(test_id=test.id, title=test.title, status="passed")
        started = time.perf_counter()
        try:
            for i, step in enumerate(test.steps):
                await self.emit(
                    {
                        "type": "step",
                        "index": index,
                        "test_id": test.id,
                        "step": i,
                        "description": step.description or step.action,
                    }
                )
                heal = await self.run_step(page, step, i, state)
                if heal:
                    result.healed.append(heal)
                    step.target = Locator(css=heal.new_css, fingerprint=step.target.fingerprint)  # type: ignore[union-attr]
                    await self.emit({"type": "healed", "index": index, "test_id": test.id, **heal.model_dump()})
                await self.send_frame(page, index)
            if result.healed:
                result.status = "healed"
        except StepFailure as exc:
            result.status = "failed"
            result.error = str(exc)
            result.failed_step = i
        except (PlaywrightError, AssertionError) as exc:
            result.status = "failed"
            result.error = clean_error(str(exc))
            result.failed_step = i
        except Exception as exc:  # unexpected errors are reported, never crash the run
            result.status = "error"
            result.error = f"{type(exc).__name__}: {exc}"
            result.failed_step = i
        result.duration_ms = int((time.perf_counter() - started) * 1000)
        result.console_errors = console_errors[:10]
        result.screenshot = await self.screenshot(page, test, index)
        await self.send_frame(page, index)
        await context.close()
        await self.emit({"type": "test_finished", "index": index, "result": result.model_dump()})
        return result

    async def run_step(self, page: Page, step: Step, index: int, state: dict) -> HealEvent | None:
        heal: HealEvent | None = None
        element: PWLocator | None = None
        if step.target is not None and step.action in ("fill", "click", "press", "expect_visible", "expect_field_invalid"):
            element, heal = await self.resolve(page, step.target, index)

        timeout = self.expect_timeout_ms
        if step.action == "goto":
            response = await page.goto(step.value, wait_until="load")
            state["status"] = response.status if response else 0
        elif step.action == "fill":
            await element.fill(step.value)  # type: ignore[union-attr]
        elif step.action == "click":
            await element.click()  # type: ignore[union-attr]
            await settle(page)
        elif step.action == "press":
            await element.press(step.value or "Enter")  # type: ignore[union-attr]
            await settle(page)
        elif step.action == "expect_visible":
            await expect(element).to_be_visible(timeout=timeout)  # type: ignore[arg-type]
        elif step.action == "expect_field_invalid":
            # Accept native HTML validation or an explicit custom-validation signal.
            invalid = await element.evaluate(
                "el => !el.checkValidity() || el.getAttribute('aria-invalid') === 'true'"
            )  # type: ignore[union-attr]
            if not invalid:
                raise StepFailure(
                    f"Expected field to reject invalid input, but it remained valid ({step.target.css})"
                )  # type: ignore[union-attr]
        elif step.action == "expect_text":
            await expect(page.locator("body")).to_contain_text(step.value, timeout=timeout)
        elif step.action == "expect_no_text":
            await expect(page.locator("body")).not_to_contain_text(step.value, timeout=timeout)
        elif step.action == "expect_url_contains":
            try:
                await expect(page).to_have_url(re.compile(re.escape(step.value)), timeout=timeout)
            except AssertionError:
                raise StepFailure(f"Expected URL to contain '{step.value}' but it was {page.url}") from None
        elif step.action == "expect_url_not_contains":
            try:
                await expect(page).not_to_have_url(re.compile(re.escape(step.value)), timeout=timeout)
            except AssertionError:
                raise StepFailure(f"Expected URL not to contain '{step.value}' but it was {page.url}") from None
        elif step.action == "expect_status_ok":
            if not 0 < state["status"] < 400:
                raise StepFailure(f"Page returned HTTP {state['status']} ({page.url})")
        elif step.action == "expect_title_contains":
            try:
                await expect(page).to_have_title(re.compile(re.escape(step.value)), timeout=timeout)
            except AssertionError:
                raise StepFailure(f"Expected title to contain '{step.value}' but it was '{await page.title()}'") from None
        return heal

    async def resolve(self, page: Page, target: Locator, step_index: int) -> tuple[PWLocator, HealEvent | None]:
        cached = self.heal_cache.get(target.css)
        if cached and self.self_heal and await page.locator(target.css).count() == 0 and await self.is_present(page, cached[0]):
            heal = HealEvent(
                step_index=step_index,
                old_css=target.css,
                new_css=cached[0],
                score=cached[1],
                element=target.fingerprint.describe(),
            )
            return page.locator(cached[0]).first, heal
        if await self.is_present(page, target.css):
            return page.locator(target.css).first, None
        if not self.self_heal:
            raise StepFailure(f"Element not found: {target.css} ({target.fingerprint.describe()})")
        candidates = await page.evaluate(CANDIDATES_JS)
        scored = [(c["css"], Fingerprint(**c["fingerprint"])) for c in candidates]
        match = best_match(target.fingerprint, scored)
        if match is None:
            raise StepFailure(
                f"Element not found and self-healing found no similar element: {target.css} ({target.fingerprint.describe()})"
            )
        new_css, score = match
        # Never continue with a selector that is missing or resolves ambiguously.
        candidate = page.locator(new_css)
        candidate_count = await candidate.count()
        if candidate_count != 1 or not await candidate.is_visible():
            raise StepFailure(
                f"Self-healing candidate was not unique and visible: {new_css} "
                f"(matched {candidate_count} elements)"
            )
        self.heal_cache[target.css] = match
        heal = HealEvent(
            step_index=step_index, old_css=target.css, new_css=new_css, score=score, element=target.fingerprint.describe()
        )
        return page.locator(new_css).first, heal

    async def is_present(self, page: Page, css: str) -> bool:
        """Fast check first (page is already loaded); only wait briefly for late-rendered elements."""
        locator = page.locator(css).first
        try:
            if await page.locator(css).count() > 0 and await locator.is_visible():
                return True
            await locator.wait_for(state="visible", timeout=self.find_timeout_ms)
            return True
        except PlaywrightError:
            return False

    async def screenshot(self, page: Page, test: TestCase, index: int) -> str:
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        path = self.artifacts_dir / f"test_{test.id or index}.png"
        try:
            await page.screenshot(path=str(path))
        except PlaywrightError:
            return ""
        return path.name

    async def send_frame(self, page: Page, index: int) -> None:
        if not self.live_frames:
            return
        try:
            jpeg = await page.screenshot(type="jpeg", quality=45)
        except PlaywrightError:
            return
        await self.emit({"type": "frame", "index": index, "url": page.url, "image": base64.b64encode(jpeg).decode()})


async def settle(page: Page) -> None:
    """Give clicks time to trigger navigation, then wait for the page to finish loading."""
    await page.wait_for_timeout(250)
    with contextlib.suppress(PlaywrightError):
        await page.wait_for_load_state("load", timeout=5000)


def clean_error(message: str) -> str:
    first = message.strip().splitlines()[0] if message.strip() else "Unknown error"
    return re.sub(r"\x1b\[[0-9;]*m", "", first)[:300]


def group_duplicate_failures(results: list[TestResult]) -> list[dict]:
    """Group repeated failures by normalized test intent and failure message."""
    groups: dict[tuple[str, str], dict] = {}
    for result_index, result in enumerate(results):
        if result.status not in ("failed", "error"):
            continue
        title = re.sub(r"\s+", " ", result.title.lower()).strip()
        error = re.sub(r"\s+", " ", result.error.lower()).strip()
        # Ignore volatile values such as line numbers and URLs' query strings.
        error = re.sub(r"\bline \d+\b", "line #", error)
        key = (title, error)
        if key not in groups:
            groups[key] = {
                "title": result.title,
                "error": result.error,
                "occurrences": 0,
                "result_indices": [],
                "screenshots": [],
            }
        group = groups[key]
        group["occurrences"] += 1
        group["result_indices"].append(result_index)
        if result.screenshot:
            group["screenshots"].append(result.screenshot)
    return list(groups.values())


def summarize(results: list[TestResult]) -> dict:
    total = len(results)
    counts = {s: sum(1 for r in results if r.status == s) for s in ("passed", "failed", "healed", "error")}
    ok = counts["passed"] + counts["healed"]
    return {
        "total": total,
        **counts,
        "pass_rate": round(100 * ok / total, 1) if total else 0.0,
        "healed_locators": sum(len(r.healed) for r in results),
        "duration_ms": sum(r.duration_ms for r in results),
        "unique_bugs": len(group_duplicate_failures(results)),
        "bugs": group_duplicate_failures(results),
    }
