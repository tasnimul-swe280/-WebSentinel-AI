"""Turns a SiteMap into executable test cases using rules + (optionally) an LLM."""

import json
import logging
from urllib.parse import urljoin, urlparse

from pydantic import ValidationError

from .crawler import is_email_field
from .llm import LLMClient
from .models import (
    ACTIONS_WITH_TARGET,
    Credentials,
    Element,
    Form,
    Locator,
    Page,
    SiteMap,
    Step,
    TestCase,
)

log = logging.getLogger(__name__)

MAX_NAV_TESTS = 6
INVALID_EMAIL = "not-an-email"
SPECIAL_CHARS = "<script>alert('x')</script>%'\""


def path_of(url: str) -> str:
    return urlparse(url).path or "/"


def sample_value(field: Element) -> str:
    fp = field.fingerprint
    hint = f"{fp.name} {fp.id} {fp.label} {fp.placeholder}".lower()
    if is_email_field(field):
        return "qa.tester@example.com"
    if fp.type == "tel" or "phone" in hint:
        return "01712345678"
    if fp.type == "number" or "age" in hint or "qty" in hint:
        return "5"
    if fp.type == "url" or "website" in hint:
        return "https://example.com"
    if fp.type == "date":
        return "2026-01-15"
    if field.kind == "textarea" or "message" in hint:
        return "This is an automated test message from WebSentinel-AI."
    if "name" in hint:
        return "QA Tester"
    return "Test input"


def fill_steps(form: Form, overrides: dict[str, str] | None = None) -> list[Step]:
    steps = []
    for field in form.fields:
        if field.kind == "select" or field.fingerprint.type in ("checkbox", "radio", "file"):
            continue
        value = (overrides or {}).get(field.ref, sample_value(field))
        steps.append(Step(action="fill", target=field.locator(), value=value, description=f"Fill {field.fingerprint.describe()}"))
    return steps


def submit_step(form: Form) -> Step:
    assert form.submit is not None
    return Step(action="click", target=form.submit.locator(), description=f"Click {form.submit.fingerprint.describe()}")


def goto(url: str) -> Step:
    return Step(action="goto", value=url, description=f"Open {path_of(url)}")


def page_name(page: Page) -> str:
    return page.title or path_of(page.url)


def smoke_test(page: Page) -> TestCase:
    steps = [goto(page.url), Step(action="expect_status_ok", description="Page responds without error")]
    if page.title:
        steps.append(Step(action="expect_title_contains", value=page.title, description="Title is correct"))
    return TestCase(
        title=f"Page loads: {page_name(page)}",
        description=f"Verify {path_of(page.url)} loads successfully with the right title.",
        category="smoke",
        severity="high",
        page_url=page.url,
        steps=steps,
    )


def navigation_tests(site: SiteMap) -> list[TestCase]:
    if not site.pages:
        return []
    home = site.pages[0]
    known = {path_of(p.url): p for p in site.pages}
    tests, used = [], set()
    for link in home.links:
        target_path = path_of(urljoin(home.url, link.fingerprint.href))
        target = known.get(target_path)
        if not target or target.url == home.url or target_path in used:
            continue
        used.add(target_path)
        label = link.fingerprint.text or target_path
        tests.append(
            TestCase(
                title=f"Navigate from home to '{label}'",
                description=f"Clicking '{label}' on the home page opens {target_path}.",
                category="navigation",
                severity="medium",
                page_url=home.url,
                steps=[
                    goto(home.url),
                    Step(action="click", target=link.locator(), description=f"Click link '{label}'"),
                    Step(action="expect_url_contains", value=target_path, description=f"URL contains {target_path}"),
                    Step(action="expect_status_ok", description="Target page responds without error"),
                ],
            )
        )
        if len(tests) >= MAX_NAV_TESTS:
            break
    return tests


def broken_link_tests(site: SiteMap) -> list[TestCase]:
    tests = []
    for link in site.broken_links:
        if not link.found_on or not link.css:
            continue
        label = link.text or path_of(link.url)
        tests.append(
            TestCase(
                title=f"Link '{label}' should not be broken",
                description=f"Link to {link.url} on {path_of(link.found_on)} returned HTTP {link.status} during crawl.",
                category="navigation",
                severity="high",
                page_url=link.found_on,
                steps=[
                    goto(link.found_on),
                    Step(
                        action="click",
                        target=Locator(css=link.css, fingerprint=link.fingerprint),
                        description=f"Click link '{label}'",
                    ),
                    Step(action="expect_status_ok", description="Linked page responds without error"),
                ],
            )
        )
    return tests


def login_tests(page: Page, form: Form, creds: Credentials | None) -> list[TestCase]:
    path = path_of(page.url)
    user_field = next((f for f in form.fields if f.fingerprint.type != "password"), None)
    pass_field = next((f for f in form.fields if f.fingerprint.type == "password"), None)
    if not pass_field or not form.submit:
        return []
    tests = []

    def creds_steps(username: str, password: str) -> list[Step]:
        steps = [goto(page.url)]
        if user_field:
            steps.append(Step(action="fill", target=user_field.locator(), value=username, description="Enter username"))
        steps.append(Step(action="fill", target=pass_field.locator(), value=password, description="Enter password"))
        steps.append(submit_step(form))
        return steps

    if creds and creds.username and creds.password:
        tests.append(
            TestCase(
                title="Login with valid credentials succeeds",
                description="A registered user can sign in and is redirected away from the login page.",
                category="functional",
                severity="critical",
                page_url=page.url,
                steps=creds_steps(creds.username, creds.password)
                + [Step(action="expect_url_not_contains", value=path, description="User left the login page")],
            )
        )
    tests.append(
        TestCase(
            title="Login with invalid credentials is rejected",
            description="Wrong username/password must not grant access.",
            category="negative",
            severity="critical",
            page_url=page.url,
            steps=creds_steps("wrong_user_tp", "WrongPass!123")
            + [Step(action="expect_url_contains", value=path, description="User stays on the login page")],
        )
    )
    tests.append(
        TestCase(
            title="Login with empty fields is blocked",
            description="Submitting the login form without input must not log the user in.",
            category="validation",
            severity="medium",
            page_url=page.url,
            steps=[
                goto(page.url),
                submit_step(form),
                Step(action="expect_url_contains", value=path, description="User stays on the login page"),
            ],
        )
    )
    return tests


def search_tests(page: Page, form: Form) -> list[TestCase]:
    field = next((f for f in form.fields if f.kind in ("input", "textarea")), None)
    if not field or not form.submit:
        return []

    def search(value: str) -> list[Step]:
        return [
            goto(page.url),
            Step(action="fill", target=field.locator(), value=value, description=f"Type '{value}' in search"),
            submit_step(form),
            Step(action="expect_status_ok", description="Search results load without server error"),
        ]

    return [
        TestCase(
            title=f"Search works on {page_name(page)}",
            description="A normal search query returns a results page.",
            category="functional",
            severity="medium",
            page_url=page.url,
            steps=search("test"),
        ),
        TestCase(
            title=f"Search handles special characters on {page_name(page)}",
            description="Input with quotes and HTML must be handled safely (no crash, no injection).",
            category="security",
            severity="high",
            page_url=page.url,
            steps=search(SPECIAL_CHARS),
        ),
    ]


def data_form_tests(page: Page, form: Form) -> list[TestCase]:
    if not form.submit or not form.fields:
        return []
    name = "contact form" if form.kind == "contact" else "form"
    tests = [
        TestCase(
            title=f"Submit {name} with valid data on {page_name(page)}",
            description="Filling every field with valid data submits successfully.",
            category="functional",
            severity="high",
            page_url=page.url,
            steps=[
                goto(page.url),
                *fill_steps(form),
                submit_step(form),
                Step(action="expect_status_ok", description="Submission succeeds"),
            ],
        )
    ]
    required_field = next((field for field in form.fields if field.required), None)
    if required_field is not None:
        tests.append(
            TestCase(
                title=f"Required fields are enforced on {page_name(page)}",
                description="Submitting the empty form must be blocked by required-field validation.",
                category="validation",
                severity="medium",
                page_url=page.url,
                steps=[
                    goto(page.url),
                    submit_step(form),
                    Step(
                        action="expect_field_invalid",
                        target=required_field.locator(),
                        description="The required field must remain invalid when the form is submitted empty",
                    ),
                ],
            )
        )
    email = next((f for f in form.fields if is_email_field(f)), None)
    if email:
        tests.append(
            TestCase(
                title=f"Invalid email is rejected on {page_name(page)}",
                description=f"Entering '{INVALID_EMAIL}' in the email field must show a validation error.",
                category="validation",
                severity="high",
                page_url=page.url,
                steps=[
                    goto(page.url),
                    *fill_steps(form, {email.ref: INVALID_EMAIL}),
                    submit_step(form),
                    Step(
                        action="expect_field_invalid",
                        target=email.locator(),
                        description="Email field must reject an invalid email address",
                    ),
                ],
            )
        )
    return tests


def deduplicate_tests(tests: list[TestCase]) -> list[TestCase]:
    """Remove exact/near-identical generated tests while preserving distinct scenarios."""
    import re

    unique: list[TestCase] = []
    seen: set[tuple] = set()
    for test in tests:
        title = re.sub(r"[^a-z0-9]+", " ", test.title.lower()).strip()
        validation_step = next((step for step in test.steps if step.action == "expect_field_invalid"), None)
        if validation_step and validation_step.target:
            # The same invalid-email assertion can be emitted by both heuristic and LLM engines
            # with slightly different titles/descriptions; the field locator identifies the issue.
            key = ("field-validation", validation_step.target.css.lower())
        else:
            steps = tuple(
                (step.action, step.target.css if step.target else "", step.value.strip().lower())
                for step in test.steps
            )
            key = (title, steps)
        if key in seen:
            continue
        seen.add(key)
        unique.append(test)
    return unique


def heuristic_tests(site: SiteMap, creds: Credentials | None = None) -> list[TestCase]:
    tests: list[TestCase] = [smoke_test(p) for p in site.pages]
    tests += navigation_tests(site)
    tests += broken_link_tests(site)
    for page in site.pages:
        for form in page.forms:
            if form.kind == "login":
                tests += login_tests(page, form, creds)
            elif form.kind == "search":
                tests += search_tests(page, form)
            else:
                tests += data_form_tests(page, form)
    return deduplicate_tests(tests)


SYSTEM_PROMPT = """You are a senior QA automation engineer. You design high-value end-to-end test cases
for web applications. You only use the elements and actions you are given. Reply with JSON only."""

PROMPT_TEMPLATE = """Website pages (elements are referenced by "ref"):
{pages}

Existing tests (do NOT duplicate these):
{existing}

Design up to {count} NEW test cases that find real bugs: edge cases, boundary values, negative paths,
security inputs (XSS/SQL injection strings), and important user journeys.

Allowed actions:
- goto (value = absolute URL)
- fill (ref + value), click (ref), press (ref + value = key name like "Enter")
- expect_text / expect_no_text (value = text on the page)
- expect_url_contains / expect_url_not_contains (value = URL fragment)
- expect_visible (ref), expect_status_ok, expect_title_contains (value)

Return JSON exactly in this shape:
{{"tests": [{{"title": "...", "description": "...", "category": "functional|validation|negative|security|navigation",
"severity": "critical|high|medium|low", "page_url": "...",
"steps": [{{"action": "goto", "value": "..."}}, {{"action": "fill", "ref": "e3", "value": "..."}}]}}]}}"""


def summarize_site(site: SiteMap) -> str:
    pages = []
    for page in site.pages:
        entry: dict = {"url": page.url, "title": page.title}
        entry["links"] = [{"ref": e.ref, "text": e.fingerprint.text, "href": e.fingerprint.href} for e in page.links[:15]]
        entry["forms"] = [
            {
                "kind": f.kind,
                "fields": [
                    {
                        "ref": e.ref,
                        "type": e.fingerprint.type or e.kind,
                        "label": e.fingerprint.label or e.fingerprint.placeholder or e.fingerprint.name,
                        "required": e.required,
                    }
                    for e in f.fields
                ],
                "submit": {"ref": f.submit.ref, "text": f.submit.fingerprint.text} if f.submit else None,
            }
            for f in page.forms
        ]
        if page.buttons:
            entry["buttons"] = [{"ref": e.ref, "text": e.fingerprint.text} for e in page.buttons[:10]]
        pages.append(entry)
    return json.dumps(pages, indent=1)


def element_index(site: SiteMap) -> dict[str, Element]:
    index: dict[str, Element] = {}
    for page in site.pages:
        for el in [*page.links, *page.buttons]:
            index[el.ref] = el
        for form in page.forms:
            for el in form.fields:
                index[el.ref] = el
            if form.submit:
                index[form.submit.ref] = form.submit
    return index


def parse_llm_tests(data: dict, site: SiteMap) -> list[TestCase]:
    """Validate LLM output and resolve element refs into real locators. Invalid tests are dropped."""
    index = element_index(site)
    tests = []
    for raw in data.get("tests", []) if isinstance(data, dict) else []:
        try:
            steps = []
            for s in raw.get("steps", []):
                ref = s.get("ref")
                target = index[ref].locator() if ref in index else None
                step = Step(action=s.get("action"), value=str(s.get("value", "")), target=target)
                if step.action in ACTIONS_WITH_TARGET and target is None:
                    raise ValueError(f"unknown ref {ref!r}")
                step.description = s.get("description") or describe_step(step)
                steps.append(step)
            if not steps:
                continue
            page_url = raw.get("page_url") or site.base_url
            if steps[0].action != "goto":
                steps.insert(0, goto(page_url))
            tests.append(
                TestCase(
                    title=str(raw["title"])[:120],
                    description=str(raw.get("description", ""))[:400],
                    category=raw.get("category", "functional"),
                    severity=raw.get("severity", "medium"),
                    source="ai",
                    page_url=page_url,
                    steps=steps,
                )
            )
        except (KeyError, ValueError, ValidationError, TypeError, AttributeError) as exc:
            log.info("Dropping invalid AI test: %s", exc)
    return deduplicate_tests(tests)


def describe_step(step: Step) -> str:
    target = step.target.fingerprint.describe() if step.target else ""
    return {
        "goto": f"Open {step.value}",
        "fill": f"Fill {target} with '{step.value}'",
        "click": f"Click {target}",
        "press": f"Press {step.value} on {target}",
        "expect_text": f"Page shows '{step.value}'",
        "expect_no_text": f"Page does not show '{step.value}'",
        "expect_url_contains": f"URL contains '{step.value}'",
        "expect_url_not_contains": f"URL does not contain '{step.value}'",
        "expect_visible": f"{target} is visible",
        "expect_field_invalid": f"{target} rejects invalid input",
        "expect_status_ok": "Page responds without error",
        "expect_title_contains": f"Title contains '{step.value}'",
    }[step.action]


async def ai_tests(llm: LLMClient, site: SiteMap, existing: list[TestCase], count: int = 8) -> list[TestCase]:
    prompt = PROMPT_TEMPLATE.format(
        pages=summarize_site(site),
        existing="\n".join(f"- {t.title}" for t in existing),
        count=count,
    )
    try:
        data = await llm.complete_json(SYSTEM_PROMPT, prompt)
    except Exception as exc:  # network/model errors must never break generation
        log.warning("LLM generation failed (%s); using heuristic tests only", exc)
        return []
    known = {t.title.lower() for t in existing}
    return [t for t in parse_llm_tests(data, site) if t.title.lower() not in known]


async def generate_tests(site: SiteMap, creds: Credentials | None, llm: LLMClient | None) -> list[TestCase]:
    tests = heuristic_tests(site, creds)
    if llm is not None:
        tests += await ai_tests(llm, site, tests)
    return deduplicate_tests(tests)
