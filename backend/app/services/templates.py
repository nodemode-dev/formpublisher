"""Templates to start a site from: the FormWeb items of the public formai-templates index, fetched only when asked.

The list is read from index.json only when the person (or a command naming it) asks for it, and kept in the data folder
with the time it was fetched. Only whole sites are offered as a start: the index's FormWeb demos, each a complete .fweb
project. A start downloads that one file, keeps it only when its size and SHA-256 match the index, opens it with the
vendored FormWeb core and writes it as a FormWeb project into a folder the person chose.
"""

import hashlib
import json
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

import httpx2

from app.services import compile as fweb_compile
from app.services import paths
from app.services.intake import IntakeError

DEFAULT_BASE = "https://raw.githubusercontent.com/nodemode-dev/formai-templates/main/"
APP = "formweb"
PREFIX = "apps/formweb/"
MAX_INDEX_BYTES = 4 * 1024 * 1024
MAX_ITEM_BYTES = 128 * 1024 * 1024
MAX_PREVIEW_BYTES = 2 * 1024 * 1024
TIMEOUT = 60.0
SHA = re.compile(r"^[0-9a-f]{64}$")
IDENT = re.compile(r"^[a-z0-9][a-z0-9._/-]{0,160}$")
PREVIEW_TYPES = {".webp": "image/webp", ".png": "image/png", ".jpg": "image/jpeg"}
SOURCE = "The list comes from the public formai-templates repository on GitHub. Nothing is fetched until you ask."


def base_url() -> str:
    raw = os.environ.get("FORMPUBLISHER_TEMPLATES_URL", "").strip() or DEFAULT_BASE
    return raw if raw.endswith("/") else raw + "/"


def folder() -> Path:
    return paths.home() / "templates"


def kept_file() -> Path:
    return folder() / "index.json"


def safe_index_path(value: object) -> str:
    """An index path: a relative POSIX path under apps/formweb/, with no '..', no backslash and nothing absolute."""
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value or value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        raise IntakeError("the template index names a path that is not allowed", 400, "template-path")
    parts = PurePosixPath(value).parts
    if ".." in parts or "." in parts or not value.startswith(PREFIX) or len(parts) < 3:
        raise IntakeError(f"the template index names a path outside {PREFIX}: {value[:120]}", 400, "template-path")
    return value


def _client() -> httpx2.Client:
    return httpx2.Client(timeout=TIMEOUT, follow_redirects=False, headers={"User-Agent": "formpublisher-engine"})


def _download(rel: str, limit: int) -> bytes:
    url = base_url() + rel
    try:
        with _client() as client, client.stream("GET", url) as res:
            if res.status_code != 200:
                raise IntakeError(f"the templates repository answered {res.status_code} for {rel}", 502, "upstream")
            chunks, total = [], 0
            for chunk in res.iter_bytes():
                total += len(chunk)
                if total > limit:
                    raise IntakeError(f"{rel} is larger than the index allows", 413, "too-large")
                chunks.append(chunk)
    except httpx2.HTTPError as exc:
        raise IntakeError(f"the templates repository could not be reached ({type(exc).__name__})", 502, "upstream") from exc
    return b"".join(chunks)


def _item(raw: dict, licence: str) -> dict | None:
    if not isinstance(raw, dict) or raw.get("kind") not in ("template", "demo"):
        return None
    ident, path, digest, size = raw.get("id"), raw.get("path"), raw.get("sha256"), raw.get("bytes")
    if not isinstance(ident, str) or not IDENT.match(ident) or not isinstance(digest, str) or not SHA.match(digest):
        return None
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0 or size > MAX_ITEM_BYTES:
        return None
    safe_index_path(path)
    preview = raw.get("preview")
    if preview is not None:
        safe_index_path(preview)
        if PurePosixPath(preview).suffix.lower() not in PREVIEW_TYPES:
            preview = None
    text = lambda key, limit: str(raw.get(key) or "")[:limit]
    return {
        "id": ident,
        "kind": raw["kind"],
        "name": text("name", 120) or ident.rsplit("/", 1)[-1],
        "description": text("description", 600),
        "path": path,
        "bytes": size,
        "sha256": digest,
        "licence": text("licence", 300) or licence,
        "credit": text("credit", 600),
        "preview": preview,
        "start": raw["kind"] == "demo" and path.endswith(".fweb"),
    }


def parse_index(data: object) -> dict:
    if not isinstance(data, dict) or data.get("format") != "formai-templates" or data.get("format_version") != 1 or not isinstance(data.get("apps"), list):
        raise IntakeError("the template index is not a formai-templates index of format version 1", 502, "template-index")
    app = next((a for a in data["apps"] if isinstance(a, dict) and a.get("id") == APP), None)
    if app is None or not isinstance(app.get("items"), list):
        raise IntakeError("the template index has no FormWeb items", 502, "template-index")
    licence = str(app.get("licence") or "")[:120]
    items = [it for it in (_item(raw, licence) for raw in app["items"]) if it is not None]
    return {
        "app": {"id": APP, "name": str(app.get("name") or "FormWeb")[:60], "version": str(app.get("version") or "")[:40], "licence": licence},
        "generated": str(data.get("generated") or "")[:40],
        "items": [it for it in items if it["start"]],
        "notStartable": sum(1 for it in items if not it["start"]),
    }


def _write_atomic(target: Path, data: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix=".pending-", dir=target.parent)
    try:
        with os.fdopen(handle, "wb") as out:
            out.write(data)
        os.replace(name, target)
    except BaseException:
        Path(name).unlink(missing_ok=True)
        raise


def kept() -> dict:
    """The kept list without touching the network: fetched false until the person has asked for it once."""
    try:
        data = json.loads(kept_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"fetched": False, "source": SOURCE, "url": base_url() + "index.json", "items": [], "notStartable": 0}
    data.update({"fetched": True, "source": SOURCE, "url": base_url() + "index.json"})
    return data


def fetch() -> dict:
    """Read index.json from the templates repository now and keep its FormWeb part with the time it was fetched."""
    raw = _download("index.json", MAX_INDEX_BYTES)
    try:
        parsed = parse_index(json.loads(raw.decode("utf-8")))
    except (ValueError, UnicodeDecodeError) as exc:
        if isinstance(exc, IntakeError):
            raise
        raise IntakeError("the template index is not valid JSON", 502, "template-index") from exc
    parsed["fetchedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    _write_atomic(kept_file(), json.dumps(parsed, indent=2).encode("utf-8"))
    return kept()


def find(item_id: str) -> dict:
    listed = kept()
    if not listed["fetched"]:
        raise IntakeError("there is no kept template list yet; get the templates first", 409, "templates-not-fetched")
    for item in listed["items"]:
        if item["id"] == item_id:
            return item
    raise IntakeError(f"no template {item_id} that a site can start from is in the kept list", 404, "not-found")


def _verified(item: dict) -> Path:
    cached = folder() / "files" / f"{item['sha256']}{PurePosixPath(item['path']).suffix}"
    if cached.is_file() and hashlib.sha256(cached.read_bytes()).hexdigest() == item["sha256"]:
        return cached
    data = _download(safe_index_path(item["path"]), item["bytes"])
    if len(data) != item["bytes"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
        raise IntakeError(f"{item['name']} does not match the size and SHA-256 in the index, so nothing was kept", 502, "template-mismatch")
    _write_atomic(cached, data)
    return cached


def preview(item_id: str) -> tuple[bytes, str]:
    item = find(item_id)
    rel = item.get("preview")
    if not rel:
        raise IntakeError("this template has no preview", 404, "not-found")
    suffix = PurePosixPath(rel).suffix.lower()
    cached = folder() / "previews" / (hashlib.sha256(rel.encode()).hexdigest()[:32] + suffix)
    if not cached.is_file():
        _write_atomic(cached, _download(safe_index_path(rel), MAX_PREVIEW_BYTES))
    return cached.read_bytes(), PREVIEW_TYPES[suffix]


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60] or "site"


def start(item_id: str, dest: str, name: str | None = None) -> dict:
    """Make an editable FormWeb project from one template in the folder dest: download, compare, open with the core, write."""
    target_dir = Path(dest).expanduser()
    if not target_dir.is_absolute():
        raise IntakeError("the folder must be an absolute path", 400, "invalid")
    if not target_dir.is_dir():
        raise IntakeError(f"the folder {target_dir} does not exist", 404, "not-found")
    item = find(item_id)
    project = target_dir / f"{_slug(name or item['name'])}.fweb"
    if project.exists():
        raise IntakeError(f"{project.name} already exists in that folder; choose another folder or name", 409, "conflict")
    source = _verified(item)
    with tempfile.TemporaryDirectory(prefix="formpublisher-template-") as scratch:
        try:
            opened = fweb_compile.compile_fweb(source, Path(scratch) / "out")
        except fweb_compile.CompileError as exc:
            raise IntakeError(f"the FormWeb core could not open {item['name']}: {exc.message}", exc.status, exc.code) from exc
    try:
        with open(project, "xb") as out, open(source, "rb") as src:
            shutil.copyfileobj(src, out)
    except FileExistsError as exc:
        raise IntakeError(f"{project.name} already exists in that folder", 409, "conflict") from exc
    except OSError:
        project.unlink(missing_ok=True)
        raise
    return {
        "template": item["id"],
        "name": opened.get("name") or item["name"],
        "project": str(project),
        "bytes": item["bytes"],
        "sha256": item["sha256"],
        "files": opened.get("files"),
        "core": opened.get("engine"),
        "licence": item["licence"],
        "credit": item["credit"],
    }
