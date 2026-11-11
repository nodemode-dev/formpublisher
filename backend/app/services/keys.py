import base64
import hashlib
import json
import os
import re
import secrets
import threading
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from app.services import intake, package, paths, trash
from app.services.bus import bus

KEY_ID_RE = re.compile(r"^[0-9a-f]{16}$")
WRONG_PASSPHRASE = "The passphrase does not unlock this key."
_lock = threading.RLock()


def _error(message: str, status: int = 400) -> intake.IntakeError:
    return intake.IntakeError(message, status)


def _index_file() -> Path:
    return paths.keys_dir() / "index.json"


def _load() -> list[dict]:
    data = package._read_json(_index_file())
    return [row for row in data if isinstance(row, dict)] if isinstance(data, list) else []


def _save(rows: list[dict]) -> None:
    package._write_text(_index_file(), package.dumps(rows))


def _raw_public(public: Ed25519PublicKey) -> bytes:
    return public.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def fingerprint_of(raw: bytes) -> str:
    return "SHA256:" + base64.b64encode(hashlib.sha256(raw).digest()).decode("ascii").rstrip("=")


def _public_view(row: dict) -> dict:
    return {k: row.get(k) for k in ("id", "name", "fingerprint", "created", "encrypted")}


def _row(key_id: str) -> dict:
    if not isinstance(key_id, str) or not KEY_ID_RE.match(key_id):
        raise _error("key not found", 404)
    for row in _load():
        if row.get("id") == key_id:
            return row
    raise _error("key not found", 404)


def _pem_path(key_id: str) -> Path:
    return paths.keys_dir() / f"{key_id}.pem"


def create_key(name: str, passphrase: str | None = None) -> dict:
    label = name.strip() if isinstance(name, str) else ""
    if not label:
        raise _error("name is required")
    if passphrase is not None and not isinstance(passphrase, str):
        raise _error("passphrase must be text")
    private = Ed25519PrivateKey.generate()
    raw = _raw_public(private.public_key())
    digest = hashlib.sha256(raw).hexdigest()
    key_id = digest[:16]
    encryption = serialization.BestAvailableEncryption(passphrase.encode("utf-8")) if passphrase else serialization.NoEncryption()
    pem = private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, encryption)
    row = {
        "id": key_id,
        "name": label[:120],
        "fingerprint": fingerprint_of(raw),
        "created": intake.now_iso(),
        "encrypted": bool(passphrase),
        "publicKey": base64.b64encode(raw).decode("ascii"),
    }
    with _lock:
        target = _pem_path(key_id)
        tmp = target.with_name(target.name + ".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(pem)
        os.chmod(tmp, 0o600)
        os.replace(tmp, target)
        _save([r for r in _load() if r.get("id") != key_id] + [row])
    bus.emit("keys.created", id=key_id, name=row["name"])
    return _public_view(row)


def list_keys() -> list[dict]:
    return [_public_view(r) for r in _load()]


def public_key(key_id: str) -> dict:
    row = _row(key_id)
    return {"id": row["id"], "fingerprint": row["fingerprint"], "publicKey": row["publicKey"]}


def remove_key(key_id: str) -> dict:
    with _lock:
        row = _row(key_id)
        pem = _pem_path(key_id)
        target = trash.move(pem, "key", row.get("name") or key_id, trash.rel(pem), row)
        _save([r for r in _load() if r.get("id") != key_id])
    bus.emit("keys.removed", id=key_id)
    return {"id": key_id, "removed": True, "trash": str(target)}


def _unlock(row: dict, passphrase: str | None) -> Ed25519PrivateKey:
    pem = _pem_path(row["id"])
    if not pem.is_file():
        raise _error("the private key file is missing", 404)
    data = pem.read_bytes()
    if row.get("encrypted") and not passphrase:
        raise _error("This key needs a passphrase.")
    secret = passphrase.encode("utf-8") if row.get("encrypted") and passphrase else None
    try:
        loaded = serialization.load_pem_private_key(data, password=secret)
    except (ValueError, TypeError) as exc:
        raise _error(WRONG_PASSPHRASE) from exc
    if not isinstance(loaded, Ed25519PrivateKey):
        raise _error("the key is not an Ed25519 key")
    return loaded


def sign_build(build_id: str, key_id: str, passphrase: str | None = None) -> dict:
    row = _row(key_id)
    archive = package.zip_path(build_id)
    private = _unlock(row, passphrase)
    raw = _raw_public(private.public_key())
    payload = {
        "algorithm": "ed25519",
        "key": fingerprint_of(raw),
        "publicKey": base64.b64encode(raw).decode("ascii"),
        "signature": base64.b64encode(private.sign(archive.read_bytes())).decode("ascii"),
    }
    package._write_text(archive.with_name("site.zip.sig"), package.dumps(payload))
    package.mark_signed(build_id, True)
    bus.emit("builds.signed", id=build_id, key=payload["key"])
    return {"id": build_id, "signed": True, "key": payload["key"], "keyId": row["id"]}


def verify_build(build_id: str) -> dict:
    archive = package.zip_path(build_id)
    sig_file = archive.with_name("site.zip.sig")
    if not sig_file.is_file():
        return {"valid": False, "key": None, "reason": "This build is not signed."}
    data = package._read_json(sig_file)
    if not isinstance(data, dict):
        return {"valid": False, "key": None, "reason": "The signature file is not readable."}
    key = data.get("key") if isinstance(data.get("key"), str) else None
    try:
        raw = base64.b64decode(str(data.get("publicKey", "")), validate=True)
        signature = base64.b64decode(str(data.get("signature", "")), validate=True)
        public = Ed25519PublicKey.from_public_bytes(raw)
    except (ValueError, TypeError):
        return {"valid": False, "key": key, "reason": "The signature file is malformed."}
    if data.get("algorithm") != "ed25519":
        return {"valid": False, "key": key, "reason": "The signature algorithm is not supported."}
    if key != fingerprint_of(raw):
        return {"valid": False, "key": key, "reason": "The key fingerprint does not match the public key."}
    try:
        public.verify(signature, archive.read_bytes())
    except InvalidSignature:
        return {"valid": False, "key": key, "reason": "The package does not match its signature."}
    return {"valid": True, "key": key}
