"""Build portable, privacy-conscious bug reproduction capsules."""

from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any


def _safe_test(test: dict[str, Any]) -> dict[str, Any]:
    """Remove values that look like credentials or secrets before export."""
    safe = dict(test)
    safe_steps = []
    for raw_step in test.get("steps", []):
        step = dict(raw_step)
        description = f"{step.get('description', '')} {step.get('target', {})}".lower()
        if re.search(r"password|passwd|token|secret|api.?key|authorization", description):
            step["value"] = "[REDACTED]"
        safe_steps.append(step)
    safe["steps"] = safe_steps
    return safe


def build_reproduction_capsule(
    *,
    project: dict[str, Any],
    run: dict[str, Any],
    result_index: int,
    test: dict[str, Any] | None,
    artifact_dir: Path,
) -> bytes:
    results = run.get("results", [])
    if result_index < 0 or result_index >= len(results):
        raise IndexError("Result index is out of range")
    result = results[result_index]
    if result.get("status") not in {"failed", "error"}:
        raise ValueError("A reproduction capsule is only available for failed or error results")

    matching_causes = []
    summary = run.get("summary") or {}
    for cause in summary.get("root_causes", []):
        if result.get("title") in cause.get("affected_tests", []):
            matching_causes.append(cause)

    capsule = {
        "format": "WebSentinel-AI Bug Replay Capsule",
        "format_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project": {"name": project.get("name"), "base_url": project.get("base_url")},
        "run": {
            "id": run.get("id"),
            "started_at": run.get("started_at"),
            "finished_at": run.get("finished_at"),
        },
        "failure": {
            "result_index": result_index,
            "test_id": result.get("test_id"),
            "title": result.get("title"),
            "status": result.get("status"),
            "error": result.get("error"),
            "failed_step": result.get("failed_step"),
            "duration_ms": result.get("duration_ms"),
            "console_errors": result.get("console_errors", []),
            "healed": result.get("healed", []),
        },
        "test_case": _safe_test(test) if test else None,
        "likely_root_causes": matching_causes,
        "replay_guidance": [
            "Open the same project in WebSentinel-AI.",
            "Confirm the target website is reachable at the project URL.",
            "Open the project's Tests page and locate the test by test_id/title.",
            "Run only this test to reproduce the failure.",
            "Compare the new error, screenshot, and console messages with this capsule.",
        ],
        "evidence_files": [],
        "privacy_note": "Project credentials are not included. Step values matching common secret field names are redacted. Review this file before sharing because test input and error text may still contain personal data.",
    }

    output = BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "README.txt",
            "WebSentinel-AI Bug Replay Capsule\n\n"
            "This bundle captures one failed test, its steps, error evidence, related root-cause hints, "
            "and (when available) the failure screenshot.\n\n"
            "Replay it in WebSentinel-AI by opening the same project, locating the included test ID/title, "
            "and running that test alone. This is a reproduction aid, not proof of a root cause.\n",
        )
        screenshot_name = result.get("screenshot") or ""
        if screenshot_name and Path(screenshot_name).name == screenshot_name:
            screenshot_path = artifact_dir / screenshot_name
            if screenshot_path.is_file():
                archive.write(screenshot_path, f"evidence/{screenshot_name}")
                capsule["evidence_files"].append(f"evidence/{screenshot_name}")
        evidence_text = [
            f"Test: {result.get('title', '')}",
            f"Status: {result.get('status', '')}",
            f"Failed step (0-based): {result.get('failed_step')}",
            f"Error: {result.get('error', '')}",
            "Console errors:",
            *[f"- {item}" for item in result.get("console_errors", [])],
        ]
        archive.writestr("evidence/failure-evidence.txt", "\n".join(evidence_text))
        capsule["evidence_files"].append("evidence/failure-evidence.txt")
        # Rewrite JSON after the evidence manifest has been populated.
        archive.writestr("capsule.json", json.dumps(capsule, indent=2, ensure_ascii=False))
    return output.getvalue()
