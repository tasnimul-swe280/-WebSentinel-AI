from fastapi.testclient import TestClient

from app import demo_site
from app.main import app


def client() -> TestClient:
    return TestClient(app)


def test_health_reports_engine_and_demo_url():
    with client() as c:
        body = c.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["demo_url"].endswith("/demo/")


def test_project_crud():
    with client() as c:
        created = c.post("/api/projects", json={"name": "Shop", "base_url": "http://example.com"})
        assert created.status_code == 201
        pid = created.json()["id"]
        assert c.get(f"/api/projects/{pid}").json()["name"] == "Shop"
        assert any(p["id"] == pid for p in c.get("/api/projects").json())
        assert c.delete(f"/api/projects/{pid}").status_code == 204
        assert c.get(f"/api/projects/{pid}").status_code == 404


def test_project_validation_rejects_bad_url():
    with client() as c:
        assert c.post("/api/projects", json={"name": "x", "base_url": "ftp://nope"}).status_code == 422
        assert c.post("/api/projects", json={"name": "", "base_url": "http://ok.com"}).status_code == 422


def test_generate_requires_crawl_first():
    with client() as c:
        pid = c.post("/api/projects", json={"name": "Shop", "base_url": "http://example.com"}).json()["id"]
        res = c.post(f"/api/projects/{pid}/generate")
    assert res.status_code == 400


def test_run_requires_tests():
    with client() as c:
        pid = c.post("/api/projects", json={"name": "Shop", "base_url": "http://example.com"}).json()["id"]
        assert c.post(f"/api/projects/{pid}/runs", json={}).status_code == 400


def test_demo_version_toggle():
    with client() as c:
        assert c.put("/api/demo/version", json={"version": 2}).json() == {"version": 2}
        assert 'id="signin-submit"' in c.get("/demo/login").text
        assert c.put("/api/demo/version", json={"version": 3}).status_code == 400
        c.put("/api/demo/version", json={"version": 1})
    assert demo_site.state["version"] == 1


def test_demo_site_intentional_bugs():
    with client() as c:
        assert c.get("/demo/careers").status_code == 404
        assert c.get("/demo/products", params={"q": "'"}).status_code == 500
        res = c.post("/demo/contact", data={"name": "a", "email": "not-an-email", "message": "hi"}, follow_redirects=False)
        assert res.status_code == 303


def test_demo_login():
    with client() as c:
        ok = c.post("/demo/login", data={"username": "demo", "password": "demo123"}, follow_redirects=False)
        assert ok.headers["location"] == "/demo/dashboard"
        bad = c.post("/demo/login", data={"username": "demo", "password": "x"})
        assert "Invalid username or password" in bad.text


def test_screenshot_path_traversal_blocked():
    with client() as c:
        assert c.get("/api/runs/1/screenshots/..%2F..%2Fetc").status_code in (400, 404)
