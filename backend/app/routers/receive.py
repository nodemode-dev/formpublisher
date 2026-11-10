import os
import tempfile
from pathlib import Path
from urllib.parse import unquote

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from app.services import inbox, intake

router = APIRouter(prefix="/api/receive", tags=["receive"])
LOOPBACK = {"127.0.0.1", "::1", "::ffff:127.0.0.1", "localhost"}
ZIP_TYPES = {"application/zip", "application/x-zip-compressed", "application/octet-stream"}


def _clean(value: str | None, limit: int) -> str | None:
    text = unquote(value or "").strip()
    return text[:limit] if text else None


async def _spool(request: Request) -> Path:
    handle, name = tempfile.mkstemp(prefix="formpublisher-receive-", suffix=".zip")
    target = Path(name)
    total = 0
    try:
        with os.fdopen(handle, "wb") as out:
            async for chunk in request.stream():
                total += len(chunk)
                if total > intake.MAX_ZIP_BYTES:
                    raise intake.IntakeError("the zip is larger than 512 MiB", 413)
                out.write(chunk)
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    if total == 0:
        target.unlink(missing_ok=True)
        raise intake.IntakeError("the body is empty; send the site-export.zip bytes")
    return target


@router.post("/formweb")
async def receive_formweb(request: Request):
    client = request.client.host if request.client else ""
    if client not in LOOPBACK:
        return JSONResponse({"detail": "Only this computer may send a site here."}, status_code=403)
    kind = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if kind not in ZIP_TYPES:
        raise intake.IntakeError("send the site-export.zip as application/zip", 415)
    project = _clean(request.headers.get("x-formweb-project"), 200)
    name = _clean(request.headers.get("x-formweb-site-name"), 120)
    archive = await _spool(request)
    try:
        return await run_in_threadpool(inbox.receive_zip, archive, project, name)
    finally:
        archive.unlink(missing_ok=True)


@router.get("/status")
def status():
    return inbox.status()
