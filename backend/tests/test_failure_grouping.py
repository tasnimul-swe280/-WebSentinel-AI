from app.models import TestResult
from app.runner import group_duplicate_failures, summarize


def test_identical_failures_are_grouped_as_one_unique_bug():
    results = [
        TestResult(test_id=1, title="Invalid email is rejected", status="failed", error="Field remained valid"),
        TestResult(test_id=2, title="Invalid email is rejected", status="failed", error="Field remained valid"),
        TestResult(test_id=3, title="Careers link should not be broken", status="failed", error="HTTP 404"),
    ]
    grouped = group_duplicate_failures(results)
    assert len(grouped) == 2
    invalid_email = next(group for group in grouped if group["title"].startswith("Invalid email"))
    assert invalid_email["occurrences"] == 2
    assert invalid_email["result_indices"] == [0, 1]
    assert summarize(results)["unique_bugs"] == 2
