import asyncio
import uuid
from typing import Literal

from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.services import checks, deep, intake
from app.services.bus import bus

router = APIRouter(prefix="/api/checks", tags=["checks"])
_running: dict[str, str] = {}
_tasks: set[asyncio.Task] = set()


class RunBody(BaseModel):
    site: str
    revision: str | None = None
    tiers: list[Literal["static", "deep"]] = Field(default_factory=lambda: ["static"], min_length=1, max_length=2)
    widths: list[int] | None = None
    motion: Literal["auto", "reduce"] = "auto"


class LiveBody(BaseModel):
    site: str
    revision: str
    problems: list[dict] = Field(default_factory=list, max_length=500)


def _widths(raw: list[int] | None) -> list[int]:
    values = []
    for item in raw or [1440, 390]:
        if not 200 <= item <= 4000:
            raise intake.IntakeError("widths must be between 200 and 4000")
        if item not in values:
            values.append(item)
    if not values or len(values) > 6:
        raise intake.IntakeError("send between 1 and 6 widths")
    return values


def _static(site: str, revision: str, root) -> list[dict]:
    problems = checks.run_static(root)
    checks.store_tier(site, revision, "static", {"problems": problems})
    return problems


def _deep(run: str, site: str, revision: str, root, widths: list[int], motion: str) -> None:
    rows = intake.routes_of(root)[1]
    routes: list[str] = []
    for row in rows:
        path = row.get("path")
        if isinstance(path, str):
            path = path if path.startswith("/") else "/" + path
            if path not in routes:
                routes.append(path)
    routes.sort()

    def progress(done: int, total: int, route: str, width: int) -> None:
        bus.emit("checks.progress", run=run, site=site, revision=revision, done=done, total=total, route=route, width=width)

    result = deep.execute(site, revision, root, routes, widths, motion, progress)
    checks.store_tier(
        site, revision, "deep",
        {k: result[k] for k in ("problems", "thumbs", "widths", "motion", "routes")},
    )


async def _background(run: str, site: str, revision: str, root, widths: list[int], motion: str) -> None:
    try:
        await run_in_threadpool(_deep, run, site, revision, root, widths, motion)
    except Exception:
        pass
    finally:
        _running.pop(site, None)
        bus.emit("checks.done", run=run, site=site, revision=revision, summary=checks.summarize(site, revision))


@router.post("/run")
async def run_checks(body: RunBody):
    root = intake.revision_root(body.site, body.revision)
    site, revision = body.site, root.name
    widths = _widths(body.widths)
    if site in _running:
        raise intake.IntakeError("a check is already running for this site", 409, "check-running")
    run = uuid.uuid4().hex[:12]
    _running[site] = run
    tiers = set(body.tiers)
    try:
        if "static" in tiers:
            await run_in_threadpool(_static, site, revision, root)
    except BaseException:
        _running.pop(site, None)
        raise
    if "deep" in tiers:
        task = asyncio.create_task(_background(run, site, revision, root, widths, body.motion))
        _tasks.add(task)
        task.add_done_callback(_tasks.discard)
    else:
        _running.pop(site, None)
        bus.emit("checks.done", run=run, site=site, revision=revision, summary=checks.summarize(site, revision))
    return {"run": run}


@router.post("/live")
def live_checks(body: LiveBody):
    root = intake.revision_root(body.site, body.revision)
    total = checks.merge_live(body.site, root.name, body.problems)
    return {"site": body.site, "revision": root.name, "count": total}


@router.get("/{site}/{revision}")
def get_checks(site: str, revision: str):
    root = intake.revision_root(site, revision)
    return {**checks.report(site, root.name), "running": _running.get(site)}


@router.get("/{site}/{revision}/thumbs/{name}.png")
def get_thumb(site: str, revision: str, name: str):
    root = intake.revision_root(site, revision)
    target = checks.thumb_path(site, root.name, name)
    if target is None:
        raise intake.IntakeError("thumbnail not found", 404)
    return FileResponse(target, media_type="image/png", headers={"Cache-Control": "no-cache"})
