import json

from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from app.services import trash
from app.services.intake import IntakeError

router = APIRouter(prefix="/api/trash", tags=["trash"])


@router.get("")
def list_trash():
    return trash.list_entries()


@router.delete("")
def empty_trash():
    return trash.empty()


@router.post("/{entry}/restore")
async def restore_entry(entry: str, request: Request):
    raw = await request.body()
    origin = None
    if raw.strip():
        try:
            body = json.loads(raw)
        except ValueError:
            return JSONResponse({"detail": "the body must be JSON, such as {\"origin\": \"sites/my-site\"}", "code": "invalid"}, status_code=400)
        if not isinstance(body, dict):
            return JSONResponse({"detail": "the body must be a JSON object", "code": "invalid"}, status_code=400)
        origin = body.get("origin")
        if origin is not None and not isinstance(origin, str):
            return JSONResponse({"detail": "origin must be text", "code": "invalid"}, status_code=400)
    try:
        return await run_in_threadpool(trash.restore, entry, origin)
    except IntakeError as exc:
        return JSONResponse({"code": exc.code, "detail": exc.message, "message": exc.message}, status_code=exc.status)


@router.delete("/{entry}")
def delete_entry(entry: str):
    return trash.delete(entry)
