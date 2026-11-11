import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app.services import fpub, intake, keys, package

router = APIRouter(prefix="/api/builds", tags=["builds"])


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


@router.get("")
def list_builds():
    rows = package.list_builds()
    return {"builds": rows, "count": len(rows)}


@router.post("")
async def create_build(request: Request):
    body = await _body(request)
    site = body.get("site")
    revision = body.get("revision")
    if not isinstance(site, str) or not site:
        raise intake.IntakeError("site is required")
    return package.build(site, revision if isinstance(revision, str) and revision else None)


@router.get("/{a}/compare/{b}")
def compare(a: str, b: str):
    return package.compare(a, b)


@router.get("/{build_id}")
def get_build(build_id: str):
    return package.get_build(build_id)


@router.get("/{build_id}/download")
def download(build_id: str):
    target = package.zip_path(build_id)
    return FileResponse(target, media_type="application/zip", filename="site.zip")


@router.get("/{build_id}/fpub")
def fpub_file(build_id: str):
    handle, name = tempfile.mkstemp(prefix="formpublisher-fpub-", suffix=".fpub")
    os.close(handle)
    target = Path(name)
    try:
        made = fpub.write_file(build_id, target)
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return FileResponse(target, media_type="application/octet-stream", filename=f"{made['site']}-{build_id}.fpub", background=BackgroundTask(target.unlink, missing_ok=True))


@router.post("/{build_id}/reproduce")
def reproduce(build_id: str):
    return package.reproduce(build_id)


@router.post("/{build_id}/sign")
async def sign(build_id: str, request: Request):
    body = await _body(request)
    key = body.get("key")
    passphrase = body.get("passphrase")
    if not isinstance(key, str) or not key:
        raise intake.IntakeError("key is required")
    return keys.sign_build(build_id, key, passphrase if isinstance(passphrase, str) and passphrase else None)


@router.post("/{build_id}/verify")
def verify(build_id: str):
    return keys.verify_build(build_id)


@router.delete("/{build_id}")
def remove(build_id: str):
    return package.remove_build(build_id)
