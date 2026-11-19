import pytest

from app import db


@pytest.fixture(autouse=True)
def fresh_db(monkeypatch, tmp_path):
    """Every test gets its own database and data directory."""
    monkeypatch.setenv("TESTPILOT_DATA_DIR", str(tmp_path))
    db.init_db()
    yield tmp_path
