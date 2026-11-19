"""End-to-end: crawl the built-in demo site, generate tests, run them, then verify self-healing on v2."""

import socket
import threading
import time

import pytest
import uvicorn

from app import demo_site
from app.crawler import crawl
from app.generator import heuristic_tests
from app.main import app
from app.models import Credentials
from app.runner import TestRunner, summarize


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def demo_url():
    port = free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}/demo/"
    server.should_exit = True
    thread.join(timeout=5)


@pytest.mark.e2e
async def test_full_pipeline_finds_bugs_and_self_heals(demo_url, tmp_path):
    demo_site.state["version"] = 1
    site = await crawl(demo_url)
    assert {p.title.split(" |")[0] for p in site.pages} >= {"Home", "Products", "Contact", "Login"}
    assert [b.status for b in site.broken_links] == [404]

    tests = heuristic_tests(site, Credentials(username="demo", password="demo123"))
    for i, t in enumerate(tests):
        t.id = i
    runner = TestRunner(tmp_path, live_frames=False)

    results = await runner.run(tests)
    failed = {r.title for r in results if r.status == "failed"}
    assert any("Careers" in t for t in failed)
    assert any("special characters" in t for t in failed)
    assert any("Invalid email" in t for t in failed)
    assert summarize(results)["failed"] == 3

    demo_site.state["version"] = 2
    try:
        healed_results = await TestRunner(tmp_path, live_frames=False).run(tests)
        login_tests = [t for t in tests if t.title.startswith("Login with valid")]
        # Healing updates selectors in place, so the next run passes without healing.
        rerun = await TestRunner(tmp_path, live_frames=False, self_heal=False).run(login_tests)
    finally:
        demo_site.state["version"] = 1
    summary = summarize(healed_results)
    assert summary["failed"] == 3, [(r.title, r.error) for r in healed_results if r.status == "failed"]
    assert summary["healed"] >= 5
    login = next(r for r in healed_results if r.title.startswith("Login with valid"))
    assert login.status == "healed"
    assert {h.new_css for h in login.healed} == {"#user-login", "#user-pass", "#signin-submit"}
    assert rerun[0].status == "passed"
