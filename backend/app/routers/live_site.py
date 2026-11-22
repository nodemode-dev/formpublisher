from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool

from app.services import intake, live_site

router = APIRouter(tags=["live-site"])


@router.get("/api/live/{site_id}")
def stored(site_id: str):
    return live_site.stored(site_id)


@router.post("/api/live/{site_id}")
async def check(site_id: str, request: Request):
    try:
        body = await request.json()
    except ValueError as exc:
        raise intake.IntakeError("the body is not valid JSON") from exc
    if not isinstance(body, dict):
        raise intake.IntakeError("the body must be an object")
    address, build, target = body.get("address"), body.get("build"), body.get("target")
    if not isinstance(address, str) or not address.strip():
        raise intake.IntakeError("address is required")
    if build is not None and (not isinstance(build, str) or not build):
        raise intake.IntakeError("build must be a build id")
    if target is not None and (not isinstance(target, str) or not target):
        raise intake.IntakeError("target must be a target id")
    return await run_in_threadpool(live_site.run, site_id, address, build, target)
