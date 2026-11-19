"""Evidence-based root-cause grouping for failed automated tests.

This first version is deterministic and offline. It reports likely causes, not
proven diagnoses; every finding includes the failed tests and observed evidence.
"""

import re
from collections import defaultdict
from typing import Any


def _classify(title: str, error: str, console_errors: list[str]) -> tuple[str, str, str, str] | None:
    text = f"{title} {error}".lower()
    if re.search(r"email|invalid input|validation|field invalid|form was not accepted", text):
        return (
            "input_validation",
            "Input validation may be missing or ineffective",
            "Validate the field on both client and server; verify invalid values are rejected and a clear error is shown.",
            "high",
        )
    if re.search(r"http\s*[45]\d\d|status\s*[45]\d\d|broken link|careers", text):
        return (
            "broken_resource",
            "A linked page or resource is unavailable",
            "Check the destination URL, route configuration, and server response for the failing link.",
            "high",
        )
    if re.search(r"element not found|selector|locator|strict mode violation", text):
        return (
            "locator_failure",
            "A page element could not be located reliably",
            "Inspect the element after page load; prefer stable data-testid, accessible role, or label selectors.",
            "medium",
        )
    if re.search(r"timeout|timed out|waiting for", text):
        return (
            "timing_or_loading",
            "The page or element did not become ready within the expected time",
            "Check network latency and asynchronous loading; wait for a meaningful ready state rather than adding arbitrary delays.",
            "medium",
        )
    if console_errors:
        return (
            "javascript_console",
            "The browser reported JavaScript console errors",
            "Inspect the browser console stack trace and fix the first application error; then rerun the affected test.",
            "medium",
        )
    if re.search(r"navigation|url|redirect|navigate", text):
        return (
            "navigation_failure",
            "Expected navigation or URL state was not reached",
            "Verify the link or submit action, route, redirect rules, and expected destination.",
            "medium",
        )
    if re.search(r"connection|refused|network|net::|dns", text):
        return (
            "network_failure",
            "The browser could not reliably reach a required resource",
            "Check server availability, network connectivity, DNS, and API endpoint responses.",
            "high",
        )
    return None


def analyze_root_causes(results: list[Any]) -> list[dict[str, Any]]:
    """Group related failed results into transparent, evidence-backed findings."""
    groups: dict[str, list[Any]] = defaultdict(list)
    definitions: dict[str, tuple[str, str, str, str]] = {}

    for result in results:
        if getattr(result, "status", "") not in ("failed", "error"):
            continue
        title = getattr(result, "title", "")
        error = getattr(result, "error", "")
        console_errors = list(getattr(result, "console_errors", []) or [])
        classified = _classify(title, error, console_errors)
        if classified is None:
            # Unknown failures are not assigned a speculative root cause.
            continue
        key, *_ = classified
        definitions[key] = classified
        groups[key].append(result)

    findings: list[dict[str, Any]] = []
    for key, items in groups.items():
        _, title, suggestion, severity = definitions[key]
        evidence = []
        affected = []
        for item in items:
            if item.title not in affected:
                affected.append(item.title)
            detail = item.error.strip() or (item.console_errors[0] if item.console_errors else "Test failed")
            if detail and detail not in evidence:
                evidence.append(detail[:240])
        # Confidence describes confidence in the classification pattern, not certainty
        # that this is the sole underlying defect.
        confidence = 0.92 if key in {"input_validation", "broken_resource"} else 0.82
        if len(items) > 1:
            confidence = min(0.97, confidence + 0.03)
        findings.append(
            {
                "id": key,
                "title": title,
                "severity": severity,
                "confidence": round(confidence, 2),
                "affected_tests": affected,
                "occurrences": len(items),
                "evidence": evidence[:5],
                "suggested_fix": suggestion,
                "method": "offline rule-based analysis",
            }
        )
    findings.sort(key=lambda item: (item["severity"] != "high", -item["occurrences"], item["title"]))
    return findings
