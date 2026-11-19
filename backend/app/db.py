import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from .config import get_settings
from .models import SiteMap, TestCase, TestResult

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    base_url TEXT NOT NULL,
    credentials TEXT,
    site_map TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS test_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    data TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    summary TEXT,
    started_at TEXT NOT NULL,
    finished_at TEXT
);
CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    data TEXT NOT NULL
);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


def _project(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "base_url": row["base_url"],
        "credentials": json.loads(row["credentials"]) if row["credentials"] else None,
        "site_map": json.loads(row["site_map"]) if row["site_map"] else None,
        "created_at": row["created_at"],
    }


def create_project(name: str, base_url: str, credentials: dict | None) -> dict[str, Any]:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO projects (name, base_url, credentials, created_at) VALUES (?, ?, ?, ?)",
            (name, base_url, json.dumps(credentials) if credentials else None, now()),
        )
        project_id = cur.lastrowid
    return get_project(project_id)  # type: ignore[return-value]


def list_projects() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """SELECT p.*,
                (SELECT COUNT(*) FROM test_cases t WHERE t.project_id = p.id) AS test_count,
                (SELECT summary FROM runs r WHERE r.project_id = p.id AND r.status = 'finished'
                 ORDER BY r.id DESC LIMIT 1) AS last_summary
               FROM projects p ORDER BY p.id DESC"""
        ).fetchall()
    projects = []
    for row in rows:
        project = _project(row)
        project.pop("site_map")
        project["test_count"] = row["test_count"]
        project["last_summary"] = json.loads(row["last_summary"]) if row["last_summary"] else None
        projects.append(project)
    return projects


def get_project(project_id: int) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    return _project(row) if row else None


def delete_project(project_id: int) -> bool:
    with connect() as conn:
        cur = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    return cur.rowcount > 0


def save_site_map(project_id: int, site_map: SiteMap) -> None:
    with connect() as conn:
        conn.execute("UPDATE projects SET site_map = ? WHERE id = ?", (site_map.model_dump_json(), project_id))


def replace_tests(project_id: int, tests: list[TestCase]) -> list[TestCase]:
    with connect() as conn:
        conn.execute("DELETE FROM test_cases WHERE project_id = ?", (project_id,))
        for test in tests:
            cur = conn.execute(
                "INSERT INTO test_cases (project_id, data, created_at) VALUES (?, ?, ?)",
                (project_id, test.model_dump_json(exclude={"id"}), now()),
            )
            test.id = cur.lastrowid
    return tests


def list_tests(project_id: int) -> list[TestCase]:
    with connect() as conn:
        rows = conn.execute("SELECT id, data FROM test_cases WHERE project_id = ? ORDER BY id", (project_id,)).fetchall()
    return [TestCase.model_validate({**json.loads(r["data"]), "id": r["id"]}) for r in rows]


def update_test(test: TestCase) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE test_cases SET data = ? WHERE id = ?",
            (test.model_dump_json(exclude={"id"}), test.id),
        )


def delete_test(project_id: int, test_id: int) -> bool:
    with connect() as conn:
        cur = conn.execute("DELETE FROM test_cases WHERE id = ? AND project_id = ?", (test_id, project_id))
    return cur.rowcount > 0


def create_run(project_id: int) -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO runs (project_id, status, started_at) VALUES (?, 'running', ?)",
            (project_id, now()),
        )
    return cur.lastrowid  # type: ignore[return-value]


def finish_run(run_id: int, status: str, summary: dict, results: list[TestResult]) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE runs SET status = ?, summary = ?, finished_at = ? WHERE id = ?",
            (status, json.dumps(summary), now(), run_id),
        )
        conn.executemany(
            "INSERT INTO results (run_id, data) VALUES (?, ?)",
            [(run_id, r.model_dump_json()) for r in results],
        )


def _run(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "project_id": row["project_id"],
        "status": row["status"],
        "summary": json.loads(row["summary"]) if row["summary"] else None,
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
    }


def list_runs(project_id: int) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM runs WHERE project_id = ? ORDER BY id DESC", (project_id,)).fetchall()
    return [_run(r) for r in rows]


def get_run(run_id: int) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if not row:
            return None
        results = conn.execute("SELECT data FROM results WHERE run_id = ? ORDER BY id", (run_id,)).fetchall()
    run = _run(row)
    run["results"] = [json.loads(r["data"]) for r in results]
    return run
