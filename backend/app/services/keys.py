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
SERVICE = "FormPublisher signing key"
STORE_SILENT = "The system password store did not answer; unlock it and try again."
_lock = threading.RLock()


def _store():
    try:
        import keyring
        from keyring.backends import fail, null

        kr = keyring.get_keyring()
    except Exception:
        return None
    if isinstance(kr, (fail.Keyring, null.Keyring)) or getattr(kr, "priority", 1) <= 0:
        return None
    return kr


def _error(message: str, status: int = 400, code: str | None = None) -> intake.IntakeError:
    return intake.IntakeError(message, status, code)


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


def _kept(row: dict) -> str:
    if "secret" not in row:
        return "file" if isinstance(row.get("id"), str) and _pem_path(row["id"]).is_file() else "none"
    return row["secret"] if row["secret"] in ("store", "file") else "none"


def _public_view(row: dict) -> dict:
    kept = _kept(row)
    return {**{k: row.get(k) for k in ("id", "name", "fingerprint", "created", "encrypted")}, "secret": kept, "canSign": kept != "none"}


def _public_row(row: dict) -> dict:
    return {**{k: row.get(k) for k in ("id", "name", "fingerprint", "created", "publicKey")}, "encrypted": False, "secret": None}


def known_signer(raw: bytes) -> dict | None:
    for row in _load():
        try:
            mine = base64.b64decode(str(row.get("publicKey", "")), validate=True)
        except (ValueError, TypeError):
            continue
        if mine == raw:
            return row
    return None


def signer_verdict(raw: bytes | None, valid: bool, reason: str | None = None) -> dict:
    fingerprint = fingerprint_of(raw) if raw is not None else None
    row = known_signer(raw) if raw is not None else None
    known = row is not None
    signer = None if fingerprint is None else {"fingerprint": fingerprint, "id": row.get("id") if row else None, "name": row.get("name") if row else None}
    if not valid:
        message = reason or "The signature is not valid."
    elif known:
        message = f"Verified with your key {row.get('name') or row.get('id')}."
    else:
        message = "Signed by a key you do not have."
    out = {"valid": valid, "known": known, "trusted": valid and known, "signer": signer, "key": fingerprint, "message": message}
    if not valid:
        out["reason"] = message
    return out


def _row(key_id: str) -> dict:
    if not isinstance(key_id, str) or not KEY_ID_RE.match(key_id):
        raise _error("key not found", 404, "key-missing")
    for row in _load():
        if row.get("id") == key_id:
            return row
    raise _error("key not found", 404, "key-missing")


def _pem_path(key_id: str) -> Path:
    return paths.keys_dir() / f"{key_id}.pem"


def _write_private_file(key_id: str, pem: bytes) -> None:
    target = _pem_path(key_id)
    tmp = target.with_name(target.name + ".tmp")
    tmp.unlink(missing_ok=True)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(pem)
    os.chmod(tmp, 0o600)
    os.replace(tmp, target)


def _store_put(kr, key_id: str, pem: bytes) -> bool:
    text = pem.decode("ascii")
    try:
        kr.set_password(SERVICE, key_id, text)
        return kr.get_password(SERVICE, key_id) == text
    except Exception:
        return False


def _keep_secret(key_id: str, pem: bytes) -> str:
    kr = _store()
    if kr is not None and _store_put(kr, key_id, pem):
        return "store"
    _write_private_file(key_id, pem)
    return "file"


def _set_secret(key_id: str, kept: str) -> None:
    rows = _load()
    for row in rows:
        if row.get("id") == key_id:
            row["secret"] = kept
    _save(rows)


def _read_secret(row: dict) -> bytes:
    key_id = row["id"]
    pem = _pem_path(key_id)
    if _kept(row) == "store":
        kr = _store()
        value, answered = None, False
        if kr is not None:
            try:
                value, answered = kr.get_password(SERVICE, key_id), True
            except Exception:
                value = None
        if value:
            return value.encode("ascii")
        if pem.is_file():
            _set_secret(key_id, "file")
            return pem.read_bytes()
        if not answered:
            raise _error(STORE_SILENT, 409, "store-unavailable")
        raise _error("The system password store has no private key for this key.", 404, "key-missing")
    if ("secret" in row and row["secret"] is None) or not pem.is_file():
        raise _error("This key can verify but not sign: it has no private key here.", 409, "key-public")
    data = pem.read_bytes()
    kr = _store()
    if kr is not None and _store_put(kr, key_id, data):
        _set_secret(key_id, "store")
        pem.unlink(missing_ok=True)
    elif row.get("secret") != "file":
        os.chmod(pem, 0o600)
        _set_secret(key_id, "file")
    return data


def _forget_secret(row: dict) -> None:
    key_id = row["id"]
    kr = _store()
    if kr is not None:
        try:
            if kr.get_password(SERVICE, key_id) is not None:
                kr.delete_password(SERVICE, key_id)
        except Exception as exc:
            if _kept(row) == "store":
                raise _error(STORE_SILENT, 409, "store-unavailable") from exc
    elif _kept(row) == "store":
        raise _error(STORE_SILENT, 409, "store-unavailable")
    _pem_path(key_id).unlink(missing_ok=True)


def adopt_private(row: dict, pem: bytes) -> dict:
    with _lock:
        kept = _keep_secret(row["id"], pem)
        stored = {**row, "secret": kept}
        _save([r for r in _load() if r.get("id") != row["id"]] + [stored])
    return stored


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
        row["secret"] = _keep_secret(key_id, pem)
        _save([r for r in _load() if r.get("id") != key_id] + [row])
    bus.emit("keys.created", id=key_id, name=row["name"])
    return _public_view(row)


def list_keys() -> list[dict]:
    return [_public_view(r) for r in _load()]


def public_key(key_id: str) -> dict:
    row = _row(key_id)
    return {"id": row["id"], "fingerprint": row["fingerprint"], "publicKey": row["publicKey"]}


MIN_EXPORT_PASSPHRASE = 8
MAX_PEM = 16 * 1024


def export_pem(key_id: str, passphrase: str, current: str | None = None) -> bytes:
    if not isinstance(passphrase, str) or len(passphrase) < MIN_EXPORT_PASSPHRASE:
        raise _error(f"Choose a passphrase of at least {MIN_EXPORT_PASSPHRASE} characters for the exported key.", 400, "passphrase-short")
    if current is not None and not isinstance(current, str):
        raise _error("passphrase must be text")
    row = _row(key_id)
    if _kept(row) == "none":
        raise _error("This key can verify but not sign: it has no private key here.", 409, "key-public")
    private = _unlock(row, current or None)
    return private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.BestAvailableEncryption(passphrase.encode("utf-8")))


def write_export(target: Path, pem: bytes, force: bool = False) -> Path:
    if target.is_dir():
        raise _error("That path is a folder; give a file name ending in .pem.", 400, "place-invalid")
    if not target.parent.is_dir():
        raise _error("The folder for the exported key does not exist.", 400, "place-invalid")
    if target.exists() and not force:
        raise _error("A file already exists at that path.", 409, "place-taken")
    tmp = target.with_name(f".{target.name}.{os.getpid()}.part")
    tmp.unlink(missing_ok=True)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(pem)
        os.chmod(tmp, 0o600)
        if force:
            os.replace(tmp, target)
        else:
            os.link(tmp, target)
            tmp.unlink()
    except FileExistsError as exc:
        tmp.unlink(missing_ok=True)
        raise _error("A file already exists at that path.", 409, "place-taken") from exc
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return target


def export_to(key_id: str, path: str, passphrase: str, current: str | None = None, force: bool = False) -> dict:
    if not isinstance(path, str) or not path.strip() or "\x00" in path:
        raise _error("Give the full path of the file to write, ending in .pem.", 400, "place-invalid")
    target = Path(path.strip()).expanduser()
    if not target.is_absolute() or target.suffix.lower() != ".pem":
        raise _error("Give the full path of the file to write, ending in .pem.", 400, "place-invalid")
    pem = export_pem(key_id, passphrase, current)
    written = write_export(target, pem, bool(force))
    bus.emit("keys.exported", id=key_id)
    return {"id": key_id, "file": str(written), "encrypted": True}


def import_pem(text: str, passphrase: str | None = None, name: str | None = None) -> dict:
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_PEM:
        raise _error("That is not a PEM private key FormPublisher can read.", 400, "pem-invalid")
    if passphrase is not None and not isinstance(passphrase, str):
        raise _error("passphrase must be text")
    if name is not None and not isinstance(name, str):
        raise _error("name must be text")
    data = text.strip().encode("utf-8", "replace") + b"\n"
    encrypted = False
    try:
        private = serialization.load_pem_private_key(data, password=None)
    except TypeError:
        encrypted = True
        private = None
    except ValueError:
        raise _error("That is not a PEM private key FormPublisher can read.", 400, "pem-invalid") from None
    if encrypted:
        if not passphrase:
            raise _error("This key needs a passphrase.", 400, "passphrase-required")
        try:
            private = serialization.load_pem_private_key(data, password=passphrase.encode("utf-8"))
        except (ValueError, TypeError):
            raise _error(WRONG_PASSPHRASE, 400, "passphrase-wrong") from None
    if not isinstance(private, Ed25519PrivateKey):
        raise _error("the key is not an Ed25519 key", 400, "pem-invalid")
    raw = _raw_public(private.public_key())
    key_id = hashlib.sha256(raw).hexdigest()[:16]
    secure = serialization.BestAvailableEncryption(passphrase.encode("utf-8")) if encrypted else serialization.NoEncryption()
    pem = private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, secure)
    label = name.strip()[:120] if name and name.strip() else ""
    with _lock:
        prior = next((r for r in _load() if r.get("id") == key_id), None)
        if prior is not None and _kept(prior) != "none":
            raise _error("This key is already one of your signing keys.", 409, "key-exists")
        row = {
            "id": key_id,
            "name": label or (prior or {}).get("name") or f"Imported key {key_id}",
            "fingerprint": fingerprint_of(raw),
            "created": (prior or {}).get("created") or intake.now_iso(),
            "encrypted": encrypted,
            "publicKey": base64.b64encode(raw).decode("ascii"),
        }
        stored = adopt_private(row, pem)
    bus.emit("keys.created", id=key_id, name=stored["name"], imported=True, upgraded=prior is not None)
    return {**_public_view(stored), "upgraded": prior is not None}


def remove_key(key_id: str) -> dict:
    with _lock:
        row = _row(key_id)
        pem = _pem_path(key_id)
        _forget_secret(row)
        target = trash.move(pem, "key", row.get("name") or key_id, trash.rel(pem), _public_row(row))
        _save([r for r in _load() if r.get("id") != key_id])
    bus.emit("keys.removed", id=key_id)
    return {"id": key_id, "removed": True, "trash": str(target), "trashKeeps": "public"}


def _unlock(row: dict, passphrase: str | None) -> Ed25519PrivateKey:
    with _lock:
        data = _read_secret(row)
    if row.get("encrypted") and not passphrase:
        raise _error("This key needs a passphrase.", 400, "passphrase-required")
    secret = passphrase.encode("utf-8") if row.get("encrypted") and passphrase else None
    try:
        loaded = serialization.load_pem_private_key(data, password=secret)
    except (ValueError, TypeError) as exc:
        raise _error(WRONG_PASSPHRASE, 400, "passphrase-wrong") from exc
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
        return signer_verdict(None, False, "This build is not signed.")
    data = package._read_json(sig_file)
    if not isinstance(data, dict):
        return signer_verdict(None, False, "The signature file is not readable.")
    try:
        raw = base64.b64decode(str(data.get("publicKey", "")), validate=True)
        signature = base64.b64decode(str(data.get("signature", "")), validate=True)
        public = Ed25519PublicKey.from_public_bytes(raw)
    except (ValueError, TypeError):
        return signer_verdict(None, False, "The signature file is malformed.")
    if data.get("algorithm") != "ed25519":
        return signer_verdict(raw, False, "The signature algorithm is not supported.")
    if data.get("key") != fingerprint_of(raw):
        return signer_verdict(raw, False, "The key fingerprint does not match the public key.")
    try:
        public.verify(signature, archive.read_bytes())
    except InvalidSignature:
        return signer_verdict(raw, False, "The package does not match its signature.")
    return signer_verdict(raw, True)
