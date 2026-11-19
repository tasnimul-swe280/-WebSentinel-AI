from types import SimpleNamespace

from app.root_cause import analyze_root_causes


def result(test_id: int, title: str, error: str, status: str = "failed"):
    return SimpleNamespace(
        test_id=test_id,
        title=title,
        error=error,
        status=status,
        console_errors=[],
    )


def test_groups_related_email_validation_failures():
    results = [
        result(1, "Invalid email is rejected", "Expected field to be invalid, but it accepted the value"),
        result(2, "Invalid email is rejected", "Expected field to be invalid, but it accepted the value"),
    ]
    findings = analyze_root_causes(results)
    assert len(findings) == 1
    assert findings[0]["id"] == "input_validation"
    assert findings[0]["occurrences"] == 2
    assert findings[0]["confidence"] > 0.9


def test_does_not_invent_root_cause_for_unknown_error():
    findings = analyze_root_causes([result(3, "Some test", "Unexpected custom failure")])
    assert findings == []


def test_ignores_passed_results():
    findings = analyze_root_causes([result(4, "Broken link", "HTTP 404", status="passed")])
    assert findings == []
