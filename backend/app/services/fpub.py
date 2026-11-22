import base64
import hashlib
import json
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from app.services import intake, keys, package, paths
from app.services.bus import bus

FORMAT = "formpublisher-package"
VERSION = 1
ENTRIES = ("fpub.json", "publish.json", "site.zip")
SIG_ENTRY = "site.zip.sig"
LIMITS = {"fpub.json": 1024 * 1024, "publish.json": 32 * 1024 * 1024, "site.zip": intake.MAX_ZIP_BYTES, SIG_ENTRY: 64 * 1024}
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
REVISION_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z(-[0-9]{1,3})?$")
SOURCE_BACK = {"formweb-export": "zip", "folder": "folder", "fweb": "fweb"}


def _error(message: str, status: int = 400, code: str = "fpub-invalid") -> intake.IntakeError:
    return intake.IntakeError(message, status, code)


def is_fpub(path: Path, filename: str | None = None) -> bool:
    """True when the name ends in .fpub or the file is a zip whose first entry is fpub.json."""
    if (filename or path.name).lower().endswith(".fpub"):
        return True
    try:
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
    except (zipfile.BadZipFile, OSError):
        return False
    return bool(names) and names[0] == "fpub.json"


def _check_signature(raw: bytes, archive: Path) -> dict:
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError):
        data = None
    if not isinstance(data, dict):
        raise _error("the signature is not valid: the signature file is not readable", 400, "fpub-signature")
    if data.get("algorithm") != "ed25519":
        raise _error("the signature is not valid: the signature algorithm is not supported", 400, "fpub-signature")
    try:
        public_raw = base64.b64decode(str(data.get("publicKey", "")), validate=True)
        signature = base64.b64decode(str(data.get("signature", "")), validate=True)
        public = Ed25519PublicKey.from_public_bytes(public_raw)
    except (ValueError, TypeError):
        raise _error("the signature is not valid: the signature file is malformed", 400, "fpub-signature") from None
    fingerprint = keys.fingerprint_of(public_raw)
    if data.get("key") != fingerprint:
        raise _error("the signature is not valid: the key fingerprint does not match the public key", 400, "fpub-signature")
    try:
        public.verify(signature, archive.read_bytes())
    except InvalidSignature:
        raise _error("the signature is not valid: the package does not match its signature", 400, "fpub-signature") from None
    return {
        "keyId": hashlib.sha256(public_raw).hexdigest()[:16],
        "fingerprint": fingerprint,
        "publicKey": base64.b64encode(public_raw).decode("ascii"),
    }


def _entry(zf: zipfile.ZipFile, name: str, source: Path | bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    info.extra = b""
    info.comment = b""
    with zf.open(info, "w", force_zip64=False) as out:
        if isinstance(source, bytes):
            out.write(source)
        else:
            with open(source, "rb") as src:
                shutil.copyfileobj(src, out, 1024 * 1024)


def write_file(build_id: str, target: Path) -> dict:
    """Write the build as a .fpub to target (same bytes every time) and return its file, size and sha256."""
    folder = package._find(build_id)
    record = package._read_json(folder / "build.json")
    publish = package._read_json(folder / "publish.json")
    archive = folder / "site.zip"
    if not isinstance(record, dict) or not isinstance(publish, dict) or not archive.is_file():
        raise _error("the build is damaged; build it again", 409, "build-damaged")
    digest = package.sha256_file(archive)
    size = archive.stat().st_size
    declared = publish.get("package") if isinstance(publish.get("package"), dict) else {}
    if declared.get("sha256") != digest or declared.get("size") != size:
        raise _error("site.zip no longer matches publish.json; build it again", 409, "build-damaged")
    sig_file = folder / SIG_ENTRY
    signature = None
    if sig_file.is_file():
        try:
            found = _check_signature(sig_file.read_bytes(), archive)
        except intake.IntakeError as exc:
            raise _error(f"the build's signature does not hold ({exc.message}); sign it again", 409, "build-damaged") from exc
        signature = {"file": SIG_ENTRY, **found}
    site_id = record.get("site")
    meta = {
        "format": FORMAT,
        "version": VERSION,
        "site": {"id": site_id, "name": (publish.get("site") or {}).get("name") or site_id},
        "build": build_id,
        "revision": record.get("revision"),
        "builtWith": publish.get("builtWith"),
        "createdAt": record.get("created"),
        "package": {"file": "site.zip", "sha256": digest, "size": size},
        "signature": signature,
    }
    text = json.dumps(meta, indent=2, ensure_ascii=False) + "\n"
    tmp = target.with_name(target.name + ".tmp")
    try:
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            _entry(zf, "fpub.json", text.encode("utf-8"))
            _entry(zf, "publish.json", folder / "publish.json")
            _entry(zf, "site.zip", archive)
            if signature:
                _entry(zf, SIG_ENTRY, sig_file)
        total = tmp.stat().st_size
        if total > intake.MAX_ZIP_BYTES:
            raise _error("the build is too large to save as a .fpub (over 512 MiB)", 413, "too-large")
        os.replace(tmp, target)
    finally:
        tmp.unlink(missing_ok=True)
    return {"build": build_id, "site": site_id, "file": str(target), "size": total, "sha256": package.sha256_file(target)}


def _text(value: Any, field: str, limit: int = 300) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise _error(f"fpub.json is missing a valid {field}")
    return value


def _read_meta(raw: bytes) -> dict:
    try:
        meta = json.loads(raw.decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError):
        raise _error("fpub.json is not valid JSON") from None
    if not isinstance(meta, dict) or meta.get("format") != FORMAT:
        raise _error("that file is not a FormPublisher package (format formpublisher-package)")
    version = meta.get("version")
    if isinstance(version, bool) or version != VERSION:
        raise _error(f"this .fpub is version {version}; this FormPublisher reads version {VERSION}")
    site = meta.get("site") if isinstance(meta.get("site"), dict) else {}
    site_id = site.get("id")
    if not isinstance(site_id, str) or not intake.ID_RE.match(site_id):
        raise _error("fpub.json is missing a valid site id")
    _text(site.get("name"), "site name", 120)
    if not isinstance(meta.get("build"), str) or not package.ID_RE.match(meta["build"]):
        raise _error("fpub.json is missing a valid build id")
    _text(meta.get("revision"), "revision", 100)
    _text(meta.get("createdAt"), "createdAt", 40)
    _text(meta.get("builtWith"), "builtWith", 120)
    pack = meta.get("package") if isinstance(meta.get("package"), dict) else {}
    if pack.get("file") != "site.zip" or not isinstance(pack.get("sha256"), str) or not SHA_RE.match(pack["sha256"]):
        raise _error("fpub.json is missing a valid package")
    if isinstance(pack.get("size"), bool) or not isinstance(pack.get("size"), int) or pack["size"] < 0:
        raise _error("fpub.json is missing a valid package")
    sig = meta.get("signature")
    if sig is not None:
        if not isinstance(sig, dict) or sig.get("file") != SIG_ENTRY:
            raise _error("fpub.json has an invalid signature record")
        for field in ("keyId", "fingerprint", "publicKey"):
            _text(sig.get(field), f"signature {field}", 200)
    return meta


def _unpack(archive: Path, work: Path) -> tuple[dict, bool]:
    try:
        size = archive.stat().st_size
    except OSError as exc:
        raise _error(f"cannot read {archive.name}: {exc.strerror}") from exc
    if size > intake.MAX_ZIP_BYTES:
        raise _error("the .fpub is larger than 512 MiB", 413, "too-large")
    try:
        zf = zipfile.ZipFile(archive)
    except (zipfile.BadZipFile, OSError):
        raise _error("that file is not a valid .fpub") from None
    with zf:
        infos = zf.infolist()
        for info in infos:
            intake._clean_member(info.filename)
        names = [info.filename for info in infos]
        if names != list(ENTRIES) and names != [*ENTRIES, SIG_ENTRY]:
            raise _error("the .fpub must hold exactly fpub.json, publish.json, site.zip and, when signed, site.zip.sig, in that order")
        for info in infos:
            if info.flag_bits & 0x1:
                raise _error("the .fpub is encrypted")
            if info.file_size > LIMITS[info.filename]:
                raise _error(f"{info.filename} in the .fpub is too large", 413, "too-large")
        for info in infos:
            limit = LIMITS[info.filename]
            written = 0
            try:
                with zf.open(info) as src, open(work / info.filename, "wb") as out:
                    while True:
                        chunk = src.read(1024 * 1024)
                        if not chunk:
                            break
                        written += len(chunk)
                        if written > limit:
                            raise _error(f"{info.filename} in the .fpub is too large", 413, "too-large")
                        out.write(chunk)
            except (zipfile.BadZipFile, RuntimeError, NotImplementedError, OSError, EOFError) as exc:
                raise _error(f"cannot read {info.filename} from the .fpub: {exc}") from exc
    meta = _read_meta((work / "fpub.json").read_bytes())
    return meta, len(names) == len(ENTRIES) + 1


def _free_id(build_id: str, site_id: str, digest: str) -> tuple[str, bool]:
    def taken(candidate: str) -> bool:
        try:
            package._find(candidate)
            return True
        except intake.IntakeError:
            return (paths.builds_dir() / site_id / candidate).exists()

    if not taken(build_id):
        return build_id, False
    while True:
        candidate = hashlib.sha256(f"{site_id}:{digest}:{os.urandom(8).hex()}".encode()).hexdigest()[:12]
        if not taken(candidate):
            return candidate, True


def import_file(archive: Path, source: dict | None = None, name: str | None = None) -> dict:
    """Check a .fpub, restore its build into the builds library and import its site.zip as a revision of its site."""
    work = Path(tempfile.mkdtemp(prefix=".fpub-", dir=paths.builds_dir()))
    try:
        meta, signed = _unpack(archive, work)
        pack = meta["package"]
        zip_file = work / "site.zip"
        digest = package.sha256_file(zip_file)
        if zip_file.stat().st_size != pack["size"]:
            raise _error("site.zip does not match the size recorded in fpub.json", 400, "fpub-tampered")
        if digest != pack["sha256"]:
            raise _error("site.zip does not match the checksum recorded in fpub.json", 400, "fpub-tampered")
        publish = package._read_json(work / "publish.json")
        if not isinstance(publish, dict) or publish.get("format") != "formpublisher-site":
            raise _error("publish.json is not a FormPublisher build manifest")
        inner = publish.get("package") if isinstance(publish.get("package"), dict) else {}
        if inner.get("sha256") != digest or inner.get("size") != pack["size"]:
            raise _error("publish.json does not match site.zip", 400, "fpub-tampered")
        site = meta["site"]
        if (publish.get("site") or {}).get("id") != site["id"]:
            raise _error("publish.json belongs to a different site than fpub.json", 400, "fpub-tampered")
        if (meta.get("signature") is not None) != signed:
            raise _error("fpub.json and the entries disagree about whether the package is signed", 400, "fpub-signature")
        verdict = None
        if signed:
            found = _check_signature((work / SIG_ENTRY).read_bytes(), zip_file)
            if any(found[k] != meta["signature"][k] for k in ("keyId", "fingerprint", "publicKey")):
                raise _error("the signature is not valid: it does not match the key recorded in fpub.json", 400, "fpub-signature")
            verdict = {**keys.signer_verdict(base64.b64decode(found["publicKey"]), True), "keyId": found["keyId"]}
        site_id = site["id"]
        revision = meta["revision"] if REVISION_RE.match(meta["revision"]) else None
        origin = (publish.get("site") or {}).get("source") if isinstance((publish.get("site") or {}).get("source"), dict) else {}
        record_source = {"kind": SOURCE_BACK.get(origin.get("kind"), "zip"), **(source or {}), "fpub": {"build": meta["build"], "revision": meta["revision"]}}
        if isinstance(origin.get("formwebVersion"), str):
            record_source["engine"] = origin["formwebVersion"]
        staging = intake._staging()
        try:
            intake.safe_unzip(zip_file, staging)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        site_folder = paths.sites_dir() / site_id
        prior = intake._read_json(site_folder / "site.json")
        record = intake._finish(staging, "fpub", record_source, f"fpub:{site_id}", site_id, (name or "").strip() or site["name"], site_id=site_id, revision_name=revision)
        try:
            with package._lock:
                final_id, remapped = _free_id(meta["build"], site_id, digest)
                row = {
                    "id": final_id,
                    "site": site_id,
                    "revision": record["revision"],
                    "created": meta["createdAt"],
                    "size": pack["size"],
                    "files": len(publish["files"]) if isinstance(publish.get("files"), list) else 0,
                    "signed": signed,
                    "imported": {"from": meta["build"], "remapped": remapped, "at": intake.now_iso(), "signature": verdict},
                }
                stage = work / "build"
                stage.mkdir()
                for item in ("publish.json", "site.zip") + ((SIG_ENTRY,) if signed else ()):
                    os.replace(work / item, stage / item)
                package._write_text(stage / "build.json", package.dumps(row))
                target = paths.builds_dir() / site_id / final_id
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(stage, target)
        except BaseException:
            shutil.rmtree(site_folder / record["revision"], ignore_errors=True)
            if prior is None:
                shutil.rmtree(site_folder, ignore_errors=True)
            else:
                intake._write_json(site_folder / "site.json", prior)
            raise
    finally:
        shutil.rmtree(work, ignore_errors=True)
    bus.emit("builds.created", id=final_id, site=site_id, revision=record["revision"], size=pack["size"])
    return {**record, "build": {"id": final_id, "originalId": meta["build"], "remapped": remapped, "signed": signed, "signature": verdict}}
