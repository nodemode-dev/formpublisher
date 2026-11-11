from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool

from app.services import intake, publish

router = APIRouter(tags=["publish"])


async def _body(request: Request) -> dict:
    raw = await request.body()
    if not raw.strip():
        return {}
    try:
        body = await request.json()
    except ValueError as exc:
        raise intake.IntakeError("the body is not valid JSON") from exc
    if not isinstance(body, dict):
        raise intake.IntakeError("the body must be an object")
    return body


@router.get("/api/targets")
def list_targets():
    return publish.list_targets()


@router.post("/api/publish/prepare")
async def prepare(request: Request):
    body = await _body(request)
    build = body.get("build")
    ids = body.get("targets")
    if not isinstance(build, str) or not build:
        raise intake.IntakeError("build is required")
    if ids is not None and not isinstance(ids, list):
        raise intake.IntakeError("targets must be a list of target ids")
    return await run_in_threadpool(publish.prepare, build, ids)


@router.get("/api/publish/{build_id}")
def prepared(build_id: str):
    return publish.prepared(build_id)


@router.post("/api/publish/{build_id}/{target_id}/reveal")
def reveal(build_id: str, target_id: str):
    return publish.reveal(build_id, target_id)


@router.post("/api/publish/{build_id}/{target_id}/verify")
async def verify(build_id: str, target_id: str):
    return await run_in_threadpool(publish.verify, build_id, target_id)


@router.delete("/api/publish/{build_id}/{target_id}")
def remove(build_id: str, target_id: str):
    return publish.remove(build_id, target_id)
