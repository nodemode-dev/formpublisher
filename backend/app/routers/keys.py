from fastapi import APIRouter, Request

from app.services import intake, keys

router = APIRouter(prefix="/api/keys", tags=["keys"])


async def _body(request: Request) -> dict:
    try:
        body = await request.json()
    except ValueError as exc:
        raise intake.IntakeError("the body is not valid JSON") from exc
    if not isinstance(body, dict):
        raise intake.IntakeError("the body must be an object")
    return body


@router.get("")
def list_keys():
    rows = keys.list_keys()
    return {"keys": rows, "count": len(rows)}


@router.post("")
async def create_key(request: Request):
    body = await _body(request)
    passphrase = body.get("passphrase")
    return keys.create_key(body.get("name"), passphrase if isinstance(passphrase, str) and passphrase else None)


@router.get("/{key_id}/public")
def public_key(key_id: str):
    return keys.public_key(key_id)


@router.delete("/{key_id}")
def remove_key(key_id: str):
    return keys.remove_key(key_id)
