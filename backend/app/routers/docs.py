import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response

from app.services import paths

router = APIRouter(prefix="/api/docs", tags=["docs"])

IMAGE_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*\.webp$")


def docs_dir():
    return (paths.resource_dir() / "docs").resolve()


@router.get("/manual")
def manual():
    target = docs_dir() / "MANUAL.md"
    if not target.is_file():
        raise HTTPException(404, "The manual is not bundled with this engine.")
    return Response(target.read_text(encoding="utf-8"), media_type="text/markdown; charset=utf-8", headers={"Cache-Control": "no-cache"})


@router.get("/images/{name}")
def image(name: str):
    root = (docs_dir() / "images").resolve()
    target = (root / name).resolve()
    if not IMAGE_NAME.match(name) or target.parent != root or not target.is_file():
        raise HTTPException(404, "The manual has no such image.")
    return FileResponse(target, media_type="image/webp", headers={"Cache-Control": "no-cache"})
