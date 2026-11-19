import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import __version__, db, demo_site
from .config import get_settings
from .capsule import build_reproduction_capsule
from .crawler import crawl
from .events import broker
from .exporter import export_pytest
from .generator import generate_tests
from .llm import get_llm
from .models import Credentials, ProjectCreate, RunRequest, SiteMap, TestCase
from .report import build_pdf
from .root_cause import analyze_root_causes
from .runner import TestRunner, summarize

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("websentinel-ai")
background_tasks: set[asyncio.Task] = set()


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    get_settings().artifacts_dir.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="WebSentinel-AI", version=__version__, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(demo_site.router, prefix="/demo", tags=["demo site"])


def project_or_404(project_id: int) -> dict:
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@app.get("/api/health")
async def health(request: Request) -> dict:
    llm = await get_llm()
    return {
        "status": "ok",
        "version": __version__,
        "ai_engine": llm.name if llm else "rule engine (offline)",
        "demo_url": str(request.base_url) + "demo/",
    }


@app.get("/api/projects")
def list_projects() -> list[dict]:
    return db.list_projects()


@app.post("/api/projects", status_code=201)
def create_project(body: ProjectCreate) -> dict:
    creds = body.credentials.model_dump() if body.credentials else None
    return db.create_project(body.name.strip(), body.base_url.strip(), creds)


@app.get("/api/projects/{project_id}")
def get_project(project_id: int) -> dict:
    return project_or_404(project_id)


@app.delete("/api/projects/{project_id}", status_code=204)
def delete_project(project_id: int) -> Response:
    if not db.delete_project(project_id):
        raise HTTPException(404, "Project not found")
    return Response(status_code=204)


class CrawlRequest(BaseModel):
    max_pages: int = 15


@app.post("/api/projects/{project_id}/crawl")
async def crawl_project(project_id: int, body: CrawlRequest | None = None) -> dict:
    project = project_or_404(project_id)
    try:
        site = await crawl(project["base_url"], max_pages=(body or CrawlRequest()).max_pages)
    except Exception as exc:
        log.exception("Crawl failed")
        raise HTTPException(502, f"Could not crawl website: {exc}") from exc
    if not site.pages:
        raise HTTPException(502, "Could not load any page from this URL")
    db.save_site_map(project_id, site)
    return site.model_dump()


@app.post("/api/projects/{project_id}/generate")
async def generate(project_id: int) -> dict:
    project = project_or_404(project_id)
    if not project["site_map"]:
        raise HTTPException(400, "Crawl the website first")
    site = SiteMap.model_validate(project["site_map"])
    creds = Credentials(**project["credentials"]) if project["credentials"] else None
    llm = await get_llm()
    tests = db.replace_tests(project_id, await generate_tests(site, creds, llm))
    return {
        "engine": llm.name if llm else "rule engine (offline)",
        "count": len(tests),
        "ai_count": sum(1 for t in tests if t.source == "ai"),
        "tests": [t.model_dump() for t in tests],
    }


@app.get("/api/projects/{project_id}/tests")
def list_tests(project_id: int) -> list[dict]:
    project_or_404(project_id)
    return [t.model_dump() for t in db.list_tests(project_id)]


@app.delete("/api/projects/{project_id}/tests/{test_id}", status_code=204)
def delete_test(project_id: int, test_id: int) -> Response:
    if not db.delete_test(project_id, test_id):
        raise HTTPException(404, "Test not found")
    return Response(status_code=204)


@app.get("/api/projects/{project_id}/export.py", response_class=PlainTextResponse)
def export(project_id: int) -> PlainTextResponse:
    project_or_404(project_id)
    filename = f"test_project_{project_id}.py"
    return PlainTextResponse(
        export_pytest(db.list_tests(project_id), filename),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def execute_run(run_id: int, project_id: int, tests: list[TestCase], body: RunRequest) -> None:
    settings = get_settings()

    async def emit(event: dict) -> None:
        await broker.publish(run_id, {**event, "run_id": run_id})

    runner = TestRunner(settings.artifacts_dir / f"run_{run_id}", emit=emit, self_heal=body.self_heal)
    await emit({"type": "run_started", "total": len(tests)})
    try:
        headless = settings.headless if body.headless is None else body.headless
        results = await runner.run(tests, headless=headless, slow_mo=body.slow_mo)
        for test, result in zip(tests, results, strict=False):
            if result.healed:
                db.update_test(test)
        summary = summarize(results)
        summary["root_causes"] = analyze_root_causes(results)
        db.finish_run(run_id, "finished", summary, results)
        await emit({"type": "run_finished", "summary": summary})
    except Exception as exc:
        log.exception("Run %s failed", run_id)
        db.finish_run(run_id, "error", {"error": str(exc)}, [])
        await emit({"type": "run_finished", "summary": None, "error": str(exc)})


@app.post("/api/projects/{project_id}/runs", status_code=202)
async def start_run(project_id: int, body: RunRequest | None = None) -> dict:
    project_or_404(project_id)
    body = body or RunRequest()
    tests = db.list_tests(project_id)
    if body.test_ids:
        wanted = set(body.test_ids)
        tests = [t for t in tests if t.id in wanted]
    if not tests:
        raise HTTPException(400, "No tests to run. Generate tests first.")
    run_id = db.create_run(project_id)
    task = asyncio.create_task(execute_run(run_id, project_id, tests, body))
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)
    return {"run_id": run_id, "total": len(tests)}


@app.get("/api/projects/{project_id}/runs")
def list_runs(project_id: int) -> list[dict]:
    project_or_404(project_id)
    return db.list_runs(project_id)


@app.get("/api/runs/{run_id}")
def get_run(run_id: int) -> dict:
    run = db.get_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return run


@app.get("/api/runs/{run_id}/events")
async def run_events(run_id: int) -> StreamingResponse:
    if not db.get_run(run_id):
        raise HTTPException(404, "Run not found")

    async def stream():
        async for event in broker.subscribe(run_id):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@app.get("/api/runs/{run_id}/screenshots/{name}")
def screenshot(run_id: int, name: str) -> FileResponse:
    if "/" in name or ".." in name:
        raise HTTPException(400, "Invalid file name")
    path = get_settings().artifacts_dir / f"run_{run_id}" / name
    if not path.is_file():
        raise HTTPException(404, "Screenshot not found")
    return FileResponse(path)


@app.get("/api/runs/{run_id}/capsules/{result_index}")
def reproduction_capsule(run_id: int, result_index: int) -> Response:
    run = db.get_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    project = project_or_404(run["project_id"])
    results = run.get("results", [])
    if result_index < 0 or result_index >= len(results):
        raise HTTPException(404, "Test result not found")
    result = results[result_index]
    tests = {t.id: t.model_dump() for t in db.list_tests(project["id"])}
    test = tests.get(result.get("test_id"))
    try:
        bundle = build_reproduction_capsule(
            project=project,
            run=run,
            result_index=result_index,
            test=test,
            artifact_dir=get_settings().artifacts_dir / f"run_{run_id}",
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except IndexError as exc:
        raise HTTPException(404, "Test result not found") from exc
    filename = f"websentinel-bug-capsule-run-{run_id}-result-{result_index + 1}.zip"
    return Response(
        bundle,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/runs/{run_id}/report.pdf")
def report(run_id: int) -> Response:
    run = db.get_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    project = project_or_404(run["project_id"])
    tests = {t.id: t.model_dump() for t in db.list_tests(project["id"])}
    pdf = build_pdf(project, run, tests, get_settings().artifacts_dir / f"run_{run_id}")
    return Response(
        pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="websentinel-run-{run_id}.pdf"'}
    )


class DemoVersion(BaseModel):
    version: int


@app.get("/api/demo/version")
def get_demo_version() -> dict:
    return {"version": demo_site.state["version"]}


@app.put("/api/demo/version")
def set_demo_version(body: DemoVersion) -> dict:
    if body.version not in (1, 2):
        raise HTTPException(400, "Version must be 1 or 2")
    demo_site.state["version"] = body.version
    return {"version": body.version}


_dist = get_settings().frontend_dist
if _dist.is_dir():
    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        if path.startswith(("api/", "demo/")):
            raise HTTPException(404, "Not found")
        file = _dist / path
        return FileResponse(file if path and file.is_file() else _dist / "index.html")
