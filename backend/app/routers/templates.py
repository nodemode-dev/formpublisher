from fastapi import APIRouter, Request
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool

from app.services import intake, templates

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("")
def kept():
    return templates.kept()


@router.post("/fetch")
async def fetch():
    return await run_in_threadpool(templates.fetch)


@router.get("/preview")
async def preview(id: str):
    data, kind = await run_in_threadpool(templates.preview, id)
    return Response(data, media_type=kind, headers={"Cache-Control": "no-cache"})


@router.post("/start")
async def start(request: Request):
    try:
        body = await request.json()
    except ValueError as exc:
        raise intake.IntakeError("the body is not valid JSON") from exc
    if not isinstance(body, dict):
        raise intake.IntakeError("the body must be an object")
    item, folder, name = body.get("template"), body.get("folder"), body.get("name")
    if not isinstance(item, str) or not item or not isinstance(folder, str) or not folder:
        raise intake.IntakeError("template and folder are required")
    if name is not None and not isinstance(name, str):
        raise intake.IntakeError("name must be text")
    return await run_in_threadpool(templates.start, item, folder, name)
