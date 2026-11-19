import json
import zipfile
from io import BytesIO

import pytest

from app.capsule import build_reproduction_capsule


def test_capsule_contains_failure_steps_and_screenshot(tmp_path):
    (tmp_path / "failure.png").write_bytes(b"fake-png")
    run = {
        "id": 7,
        "started_at": "2026-01-01T00:00:00Z",
        "finished_at": "2026-01-01T00:00:05Z",
        "results": [{
            "test_id": 12, "title": "Invalid email is rejected", "status": "failed",
            "error": "Field remained valid", "failed_step": 2, "duration_ms": 500,
            "screenshot": "failure.png", "console_errors": [], "healed": [],
        }],
        "summary": {"root_causes": [{"title": "Input validation", "affected_tests": ["Invalid email is rejected"]}]},
    }
    test = {"id": 12, "title": "Invalid email is rejected", "steps": [
        {"action": "fill", "value": "not-an-email", "description": "Fill email", "target": {"css": "#email"}},
    ]}
    payload = build_reproduction_capsule(
        project={"name": "Demo", "base_url": "http://localhost:8001"},
        run=run, result_index=0, test=test, artifact_dir=tmp_path,
    )
    with zipfile.ZipFile(BytesIO(payload)) as archive:
        assert "capsule.json" in archive.namelist()
        assert "evidence/failure.png" in archive.namelist()
        capsule = json.loads(archive.read("capsule.json"))
        assert capsule["failure"]["test_id"] == 12
        assert capsule["likely_root_causes"][0]["title"] == "Input validation"


def test_capsule_redacts_password_steps(tmp_path):
    run = {"results": [{"status": "failed", "title": "Login", "test_id": 1}]}
    test = {"title": "Login", "steps": [{"action": "fill", "value": "secret-value", "description": "Fill password"}]}
    payload = build_reproduction_capsule(
        project={"name": "Demo", "base_url": "http://localhost"}, run=run,
        result_index=0, test=test, artifact_dir=tmp_path,
    )
    with zipfile.ZipFile(BytesIO(payload)) as archive:
        capsule = json.loads(archive.read("capsule.json"))
    assert capsule["test_case"]["steps"][0]["value"] == "[REDACTED]"


def test_capsule_rejects_passed_test(tmp_path):
    with pytest.raises(ValueError):
        build_reproduction_capsule(
            project={}, run={"results": [{"status": "passed"}]}, result_index=0,
            test=None, artifact_dir=tmp_path,
        )


def test_capsule_always_includes_text_failure_evidence(tmp_path):
    run = {"results": [{
        "test_id": 5, "title": "Search handles quotes", "status": "failed",
        "error": "HTTP 500", "failed_step": 3, "console_errors": ["Uncaught error"],
    }]}
    payload = build_reproduction_capsule(
        project={"name": "Shop", "base_url": "http://localhost"}, run=run,
        result_index=0, test={"id": 5, "title": "Search handles quotes", "steps": []}, artifact_dir=tmp_path,
    )
    with zipfile.ZipFile(BytesIO(payload)) as archive:
        names = archive.namelist()
        assert names.count("capsule.json") == 1
        assert "evidence/failure-evidence.txt" in names
        evidence = archive.read("evidence/failure-evidence.txt").decode()
        assert "HTTP 500" in evidence
        assert "Uncaught error" in evidence
        capsule = json.loads(archive.read("capsule.json"))
        assert "evidence/failure-evidence.txt" in capsule["evidence_files"]
