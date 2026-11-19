import ast

from app.exporter import export_pytest, slug
from app.models import Locator, Step, TestCase
from app.report import build_pdf


def sample_tests() -> list[TestCase]:
    return [
        TestCase(
            id=1,
            title="Login with invalid credentials is rejected",
            severity="critical",
            category="negative",
            steps=[
                Step(action="goto", value="http://x.com/login"),
                Step(action="fill", target=Locator(css="#user"), value="bad'user"),
                Step(action="click", target=Locator(css="#login")),
                Step(action="expect_url_contains", value="/login"),
                Step(action="expect_status_ok"),
            ],
        ),
        TestCase(id=2, title="Login with invalid credentials is rejected", steps=[Step(action="goto", value="http://x.com")]),
    ]


def test_export_is_valid_python_with_unique_test_names():
    code = export_pytest(sample_tests())
    tree = ast.parse(code)
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(names) == 2
    assert len(set(names)) == 2
    assert all(n.startswith("test_") for n in names)
    assert "bad'user" in code


def test_slug():
    assert slug("Hello, World! 123") == "hello_world_123"
    assert slug("!!!") == "case"


def test_pdf_report_builds(tmp_path):
    run = {
        "id": 7,
        "started_at": "2026-01-01",
        "finished_at": "2026-01-01",
        "summary": {"total": 2, "passed": 1, "failed": 1, "healed": 0, "error": 0, "pass_rate": 50.0, "duration_ms": 1000},
        "results": [
            {
                "test_id": 1,
                "title": "A <b>",
                "status": "failed",
                "duration_ms": 500,
                "error": "boom & bust",
                "failed_step": 2,
                "screenshot": "",
                "healed": [],
            },
            {
                "test_id": 2,
                "title": "B",
                "status": "healed",
                "duration_ms": 500,
                "error": "",
                "screenshot": "",
                "healed": [{"step_index": 1, "old_css": "#a", "new_css": "#b", "score": 0.9, "element": "button"}],
            },
        ],
    }
    pdf = build_pdf({"name": "P", "base_url": "http://x"}, run, {1: {"severity": "high", "category": "smoke"}}, tmp_path)
    assert pdf.startswith(b"%PDF")
