from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from app.services import formweb

router = APIRouter(prefix="/api/formweb", tags=["formweb"])


def _failure(exc: formweb.FormwebError) -> JSONResponse:
    return JSONResponse({"detail": exc.message}, status_code=exc.status)


@router.get("/status")
async def status():
    return await run_in_threadpool(formweb.status)


@router.get("/publications")
async def publications():
    try:
        return await run_in_threadpool(formweb.publications)
    except formweb.FormwebError as exc:
        return _failure(exc)


@router.post("/import-current")
async def import_current(body: dict | None = Body(default=None)):
    name = (body or {}).get("name")
    try:
        return await run_in_threadpool(formweb.import_current, name if isinstance(name, str) else None)
    except formweb.FormwebError as exc:
        return _failure(exc)
