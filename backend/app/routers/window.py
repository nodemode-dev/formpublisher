from fastapi import APIRouter, HTTPException, Request

from app.services import window_key

router = APIRouter(prefix="/api/window", tags=["window"])


@router.post("/key")
def claim_key(request: Request) -> dict:
    key = window_key.claim(request.headers.get("origin"))
    if key is None:
        raise HTTPException(404, "Not Found")
    return {"key": key}


@router.post("/check")
def check_key() -> dict:
    return {"ok": True}
