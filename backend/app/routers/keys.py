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


def _text(body: dict, name: str) -> str | None:
    value = body.get(name)
    return value if isinstance(value, str) and value else None


@router.post("/import")
async def import_key(request: Request):
    body = await _body(request)
    return keys.import_pem(body.get("pem"), _text(body, "passphrase"), _text(body, "name"))


@router.post("/{key_id}/export")
async def export_key(key_id: str, request: Request):
    body = await _body(request)
    passphrase = body.get("passphrase")
    current = _text(body, "current")
    if body.get("path") is not None:
        return keys.export_to(key_id, body.get("path"), passphrase, current, body.get("force") is True)
    return {"id": key_id, "pem": keys.export_pem(key_id, passphrase, current).decode("ascii"), "encrypted": True}


@router.get("/{key_id}/public")
def public_key(key_id: str):
    return keys.public_key(key_id)


@router.delete("/{key_id}")
def remove_key(key_id: str):
    return keys.remove_key(key_id)
