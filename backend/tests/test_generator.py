from app.generator import generate_tests, heuristic_tests
from app.models import Credentials, SiteMap


def fixture_site() -> SiteMap:
    page = {
        "url": "http://example.com/",
        "title": "Demo Store",
        "status": 200,
        "links": [
            {
                "ref": "e1",
                "kind": "link",
                "css": "#products-link",
                "fingerprint": {"tag": "a", "text": "Products", "href": "/products"},
            },
            {
                "ref": "e2",
                "kind": "link",
                "css": "#broken-link",
                "fingerprint": {"tag": "a", "text": "Careers", "href": "/careers"},
            },
        ],
        "buttons": [],
        "forms": [
            {
                "ref": "f1",
                "action": "/login",
                "method": "post",
                "kind": "login",
                "fields": [
                    {
                        "ref": "e3",
                        "kind": "input",
                        "css": "#username",
                        "fingerprint": {"tag": "input", "type": "text", "name": "username"},
                    },
                    {
                        "ref": "e4",
                        "kind": "input",
                        "css": "#password",
                        "fingerprint": {"tag": "input", "type": "password", "name": "password"},
                    },
                ],
                "submit": {
                    "ref": "e5",
                    "kind": "button",
                    "css": "#login-btn",
                    "fingerprint": {"tag": "button", "type": "submit", "text": "Sign in"},
                },
            }
        ],
    }
    products = {
        "url": "http://example.com/products",
        "title": "Products",
        "status": 200,
        "links": [],
        "buttons": [],
        "forms": [
            {
                "ref": "f2",
                "action": "/products",
                "method": "get",
                "kind": "search",
                "fields": [
                    {
                        "ref": "e6",
                        "kind": "input",
                        "css": "#search",
                        "fingerprint": {"tag": "input", "type": "search", "name": "q"},
                    }
                ],
                "submit": {
                    "ref": "e7",
                    "kind": "button",
                    "css": "#search-btn",
                    "fingerprint": {"tag": "button", "type": "submit", "text": "Search"},
                },
            }
        ],
    }
    return SiteMap.model_validate({"base_url": "http://example.com", "pages": [page, products], "broken_links": []})


def titles(tests):
    return [t.title for t in tests]


def test_smoke_test_for_every_page():
    tests = heuristic_tests(fixture_site(), None)
    assert "Page loads: Demo Store" in titles(tests)
    assert "Page loads: Products" in titles(tests)


def test_login_tests_cover_valid_invalid_and_empty():
    tests = heuristic_tests(fixture_site(), Credentials(username="demo", password="demo123"))
    login = [t for t in titles(tests) if "ogin" in t]
    assert any("valid credentials" in t for t in login)
    assert any("invalid credentials" in t for t in login)
    assert any("empty fields" in t for t in login)
    valid = next(t for t in tests if t.title.startswith("Login with valid credentials"))
    assert valid.steps[0].action == "goto"
    fills = [s for s in valid.steps if s.action == "fill"]
    assert [s.value for s in fills] == ["demo", "demo123"]


def test_login_valid_test_omitted_without_credentials():
    tests = heuristic_tests(fixture_site(), None)
    assert not any(t.startswith("Login with valid credentials") for t in titles(tests))


def test_search_tests_include_special_characters_security_test():
    tests = heuristic_tests(fixture_site(), None)
    search = [t for t in tests if "Search" in t.title]
    assert len(search) == 2
    assert any(t.category == "security" for t in search)


def test_every_test_has_steps_and_valid_actions():
    from app.models import ACTIONS_WITH_TARGET

    for t in heuristic_tests(fixture_site(), Credentials(username="a", password="b")):
        assert t.steps, t.title
        for step in t.steps:
            if step.action in ACTIONS_WITH_TARGET:
                assert step.target is not None, (t.title, step.action)


async def test_generate_with_llm_adds_ai_tests():

    class FakeLLM:
        name = "fake"

        async def complete_json(self, system, prompt):
            return {
                "tests": [
                    {
                        "title": "Search page rejects HTML injection",
                        "description": "Edge case",
                        "category": "security",
                        "severity": "high",
                        "page_url": "http://example.com/products",
                        "steps": [
                            {"action": "goto", "value": "http://example.com/products"},
                            {"action": "fill", "ref": "e6", "value": "<script>"},
                            {"action": "click", "ref": "e7"},
                            {"action": "expect_status_ok"},
                        ],
                    },
                    {"title": "Broken AI test with bad ref", "steps": [{"action": "click", "ref": "nope"}]},
                ]
            }

    tests = await generate_tests(fixture_site(), None, FakeLLM())  # type: ignore[arg-type]
    ai = [t for t in tests if t.source == "ai"]
    assert len(ai) == 1
    assert ai[0].steps[1].target is not None
    assert ai[0].steps[1].target.css == "#search"


def test_invalid_email_test_asserts_field_validation_not_url():
    site = SiteMap.model_validate({
        "base_url": "http://example.com",
        "pages": [{
            "url": "http://example.com/subscribe", "title": "Subscribe", "status": 200,
            "links": [], "buttons": [],
            "forms": [{
                "ref": "form1", "action": "/subscribe", "method": "post", "kind": "generic",
                "fields": [{
                    "ref": "email", "kind": "input", "css": "#email",
                    "fingerprint": {"tag": "input", "type": "text", "name": "email", "id": "email"}
                }],
                "submit": {"ref": "submit", "kind": "button", "css": "#submit",
                           "fingerprint": {"tag": "button", "type": "submit", "text": "Subscribe"}}
            }]
        }], "broken_links": []
    })
    invalid = next(t for t in heuristic_tests(site, None) if t.title.startswith("Invalid email"))
    assert invalid.steps[-1].action == "expect_field_invalid"
    assert invalid.steps[-1].target is not None
    assert invalid.steps[-1].target.css == "#email"


def test_search_form_is_classified_from_placeholder_and_type():
    from app.crawler import classify_form
    from app.models import Element, Fingerprint

    field = Element(
        ref="search", kind="input", css="#query",
        fingerprint=Fingerprint(tag="input", type="search", placeholder="Search products"),
    )
    assert classify_form([field]) == "search"


def test_duplicate_generated_test_cases_are_removed():
    from app.generator import deduplicate_tests
    from app.models import Step, TestCase

    first = TestCase(title="Invalid email is rejected", page_url="http://x", steps=[
        Step(action="goto", value="http://x"), Step(action="expect_status_ok")
    ])
    duplicate = TestCase(title="Invalid email is rejected", page_url="http://x", steps=[
        Step(action="goto", value="http://x"), Step(action="expect_status_ok")
    ])
    assert len(deduplicate_tests([first, duplicate])) == 1


def test_required_data_form_generation_does_not_reference_undefined_path():
    data = fixture_site().model_dump()
    data["pages"][1]["forms"].append(
        {
            "ref": "f3",
            "action": "/contact",
            "method": "post",
            "kind": "contact",
            "fields": [
                {
                    "ref": "e8",
                    "kind": "input",
                    "css": "#contact-email",
                    "required": True,
                    "fingerprint": {"tag": "input", "type": "email", "name": "email"},
                }
            ],
            "submit": {
                "ref": "e9",
                "kind": "button",
                "css": "#contact-submit",
                "fingerprint": {"tag": "button", "type": "submit", "text": "Send"},
            },
        }
    )
    site = SiteMap.model_validate(data)
    tests = heuristic_tests(site, None)
    required_test = next(t for t in tests if t.title.startswith("Required fields are enforced"))
    assert required_test.steps[-1].action == "expect_field_invalid"
    assert required_test.steps[-1].target.css == "#contact-email"
