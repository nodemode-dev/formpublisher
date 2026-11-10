import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile

from app.services import intake

router = APIRouter(prefix="/api/sites", tags=["sites"])


def _spool(upload: UploadFile) -> Path:
    handle, name = tempfile.mkstemp(prefix="formpublisher-upload-", suffix=".zip")
    target = Path(name)
    total = 0
    try:
        with os.fdopen(handle, "wb") as out:
            upload.file.seek(0)
            while True:
                chunk = upload.file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > intake.MAX_ZIP_BYTES:
                    raise intake.IntakeError("the zip is larger than 512 MiB", 413)
                out.write(chunk)
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return target


def _import_upload(upload: UploadFile, name: str | None) -> dict:
    archive = _spool(upload)
    try:
        return intake.import_upload(archive, upload.filename or "upload.zip", name)
    finally:
        archive.unlink(missing_ok=True)


@router.get("")
def list_sites():
    sites = intake.list_sites()
    return {"sites": sites, "count": len(sites)}


@router.post("/import")
async def import_site(request: Request):
    kind = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if kind == "multipart/form-data":
        form = await request.form()
        upload = next((v for v in form.values() if isinstance(v, UploadFile)), None)
        if upload is None:
            raise intake.IntakeError("send the zip as a multipart file field")
        name = form.get("name")
        try:
            return await run_in_threadpool(_import_upload, upload, name if isinstance(name, str) else None)
        finally:
            await form.close()
    if kind == "application/json":
        try:
            body = await request.json()
        except ValueError as exc:
            raise intake.IntakeError("the body is not valid JSON") from exc
        if not isinstance(body, dict):
            raise intake.IntakeError("the body must be an object with a path")
        name = body.get("name")
        return await run_in_threadpool(intake.import_path, body.get("path"), name if isinstance(name, str) else None)
    raise intake.IntakeError("send a multipart zip upload or JSON with a path", 415)


@router.get("/{site_id}")
def get_site(site_id: str):
    return intake.get_site(site_id)


@router.get("/{site_id}/routes")
def site_routes(site_id: str, revision: str | None = None):
    return intake.site_routes(site_id, revision)


@router.delete("/{site_id}")
def remove_site(site_id: str):
    return intake.remove_site(site_id)
