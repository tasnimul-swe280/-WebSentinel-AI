from typing import Literal

from pydantic import BaseModel, Field

Action = Literal[
    "goto",
    "fill",
    "click",
    "press",
    "expect_text",
    "expect_no_text",
    "expect_url_contains",
    "expect_url_not_contains",
    "expect_visible",
    "expect_field_invalid",
    "expect_status_ok",
    "expect_title_contains",
]
ACTIONS_WITH_TARGET = {"fill", "click", "press", "expect_visible", "expect_field_invalid"}

Category = Literal["smoke", "navigation", "functional", "validation", "negative", "security"]
Severity = Literal["critical", "high", "medium", "low"]


class Fingerprint(BaseModel):
    """Attributes of a DOM element, used to find it again when its selector breaks."""

    tag: str = ""
    id: str = ""
    name: str = ""
    type: str = ""
    text: str = ""
    label: str = ""
    placeholder: str = ""
    aria_label: str = ""
    classes: list[str] = Field(default_factory=list)
    href: str = ""
    role: str = ""
    form: str = ""
    path: str = ""

    def describe(self) -> str:
        for value in (self.label, self.text, self.aria_label, self.placeholder, self.name, self.id):
            if value:
                return f"{self.tag} '{value}'"
        return self.tag or "element"


class Locator(BaseModel):
    css: str
    fingerprint: Fingerprint = Field(default_factory=Fingerprint)


class Element(BaseModel):
    ref: str
    kind: Literal["link", "button", "input", "select", "textarea"]
    css: str
    fingerprint: Fingerprint
    required: bool = False

    def locator(self) -> Locator:
        return Locator(css=self.css, fingerprint=self.fingerprint)


FormKind = Literal["login", "search", "contact", "generic"]


class Form(BaseModel):
    ref: str
    action: str = ""
    method: str = "get"
    kind: FormKind = "generic"
    fields: list[Element] = Field(default_factory=list)
    submit: Element | None = None


class Page(BaseModel):
    url: str
    title: str = ""
    status: int = 200
    links: list[Element] = Field(default_factory=list)
    buttons: list[Element] = Field(default_factory=list)
    forms: list[Form] = Field(default_factory=list)


class BrokenLink(BaseModel):
    url: str
    status: int
    found_on: str
    text: str = ""
    css: str = ""
    fingerprint: Fingerprint = Field(default_factory=Fingerprint)


class SiteMap(BaseModel):
    base_url: str
    pages: list[Page] = Field(default_factory=list)
    broken_links: list[BrokenLink] = Field(default_factory=list)


class Step(BaseModel):
    action: Action
    target: Locator | None = None
    value: str = ""
    description: str = ""


class TestCase(BaseModel):
    __test__ = False

    id: int | None = None
    title: str
    description: str = ""
    category: Category = "functional"
    severity: Severity = "medium"
    source: Literal["ai", "heuristic", "manual"] = "heuristic"
    page_url: str = ""
    steps: list[Step]


class HealEvent(BaseModel):
    step_index: int
    old_css: str
    new_css: str
    score: float
    element: str


class TestResult(BaseModel):
    __test__ = False

    test_id: int | None
    title: str
    status: Literal["passed", "failed", "healed", "error"]
    duration_ms: int = 0
    error: str = ""
    failed_step: int | None = None
    screenshot: str = ""
    healed: list[HealEvent] = Field(default_factory=list)
    console_errors: list[str] = Field(default_factory=list)


class Credentials(BaseModel):
    username: str = ""
    password: str = ""


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    base_url: str = Field(pattern=r"^https?://")
    credentials: Credentials | None = None


class RunRequest(BaseModel):
    test_ids: list[int] | None = None
    headless: bool | None = None
    slow_mo: int = Field(default=0, ge=0, le=3000)
    self_heal: bool = True
