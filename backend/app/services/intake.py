import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
import threading
import zipfile
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services import compile as compiler
from app.services import paths, trash
from app.services.bus import bus
from app.services.codes import default_code

MAX_FILES = 20_000
MAX_ENTRIES = 40_000
MAX_BYTES = 1024 * 1024 * 1024
MAX_ZIP_BYTES = 512 * 1024 * 1024
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,100}$")
ROUTE_KEYS = ("path", "page", "locale", "item", "stylesheet")
MARKERS = ("routes.json", "index.html", "site.formweb.json")
_lock = threading.RLock()


class IntakeError(ValueError):
    def __init__(self, message: str, status: int = 400, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code or getattr(type(self), "code", None) or default_code(status)


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")[:48].strip("-")
    return slug or "site"


def make_id(name: str, source_key: str) -> str:
    digest = hashlib.sha1(f"{name}\n{source_key}".encode("utf-8")).hexdigest()[:6]
    return f"{slugify(name)}-{digest}"


def _clean_member(raw: str) -> str:
    name = raw.replace("\\", "/")
    if not name or "\x00" in name or name.startswith("/") or re.match(r"^[A-Za-z]:", name):
        raise IntakeError(f"the zip holds an unsafe path: {raw!r}")
    parts = [p for p in name.split("/") if p not in ("", ".")]
    if not parts or any(p == ".." for p in parts):
        raise IntakeError(f"the zip holds an unsafe path: {raw!r}")
    return "/".join(parts)


def safe_unzip(archive: Path, dest: Path) -> None:
    try:
        size = archive.stat().st_size
    except OSError as exc:
        raise IntakeError(f"cannot read {archive}: {exc.strerror}") from exc
    if size > MAX_ZIP_BYTES:
        raise IntakeError("the zip is larger than 512 MiB", 413)
    try:
        zf = zipfile.ZipFile(archive)
    except (zipfile.BadZipFile, OSError) as exc:
        raise IntakeError("that file is not a valid zip") from exc
    with zf:
        infos = zf.infolist()
        if len(infos) > MAX_ENTRIES:
            raise IntakeError(f"the zip has more than {MAX_ENTRIES} entries", 413)
        plan: list[tuple[zipfile.ZipInfo, str]] = []
        seen: set[str] = set()
        declared = 0
        for info in infos:
            rel = _clean_member(info.filename)
            if rel.startswith("__MACOSX/") or rel == "__MACOSX":
                continue
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise IntakeError(f"the zip holds a symbolic link: {info.filename!r}")
            if info.is_dir():
                continue
            if info.flag_bits & 0x1:
                raise IntakeError("the zip is encrypted")
            key = rel.lower()
            if key in seen:
                raise IntakeError(f"the zip holds a duplicate path: {rel!r}")
            seen.add(key)
            declared += info.file_size
            plan.append((info, rel))
        if len(plan) > MAX_FILES:
            raise IntakeError(f"the zip has more than {MAX_FILES} files", 413)
        if declared > MAX_BYTES:
            raise IntakeError("the zip expands to more than 1 GiB", 413)
        root = dest.resolve()
        total = 0
        for info, rel in plan:
            target = (root / rel).resolve()
            if root not in target.parents:
                raise IntakeError(f"the zip holds an unsafe path: {rel!r}")
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as src, open(target, "wb") as out:
                    while True:
                        chunk = src.read(1024 * 1024)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > MAX_BYTES:
                            raise IntakeError("the zip expands to more than 1 GiB", 413)
                        out.write(chunk)
            except (zipfile.BadZipFile, RuntimeError, NotImplementedError, zlib.error, OSError) as exc:
                raise IntakeError(f"cannot read {rel!r} from the zip: {getattr(exc, 'strerror', None) or exc}") from exc


def copy_folder(source: Path, dest: Path) -> int:
    root = source.resolve()
    files: list[tuple[Path, str]] = []
    total = 0
    skipped = 0
    for current, dirs, names in os.walk(root, followlinks=False):
        here = Path(current)
        kept = []
        for d in dirs:
            if (here / d).is_symlink():
                skipped += 1
                continue
            if d == ".git":
                continue
            kept.append(d)
        dirs[:] = kept
        for n in names:
            p = here / n
            if p.is_symlink() or not p.is_file():
                skipped += 1
                continue
            total += p.stat().st_size
            files.append((p, p.relative_to(root).as_posix()))
            if len(files) > MAX_FILES:
                raise IntakeError(f"the folder has more than {MAX_FILES} files", 413)
            if total > MAX_BYTES:
                raise IntakeError("the folder holds more than 1 GiB", 413)
    for p, rel in files:
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, target)
    return skipped


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


def site_name_from(root: Path) -> str | None:
    data = _read_json(root / "site.formweb.json")
    if not isinstance(data, dict):
        return None
    site = data.get("site") if isinstance(data.get("site"), dict) else {}
    for candidate in (data.get("name"), site.get("name"), data.get("title"), site.get("title")):
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()[:120]
    return None


def routes_of(root: Path) -> tuple[str, list[dict]]:
    data = _read_json(root / "routes.json")
    rows = data.get("routes") if isinstance(data, dict) else data
    if isinstance(rows, list):
        out = []
        for row in rows:
            if isinstance(row, dict) and isinstance(row.get("path"), str):
                out.append({key: row.get(key) for key in ROUTE_KEYS})
        return "routes.json", out
    out = []
    base = root.resolve()
    for current, dirs, names in os.walk(base, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        if "index.html" in names:
            rel = Path(current).relative_to(base).as_posix()
            page = "index.html" if rel == "." else f"{rel}/index.html"
            path = "/" if rel == "." else f"/{rel}/"
            out.append({"path": path, "page": page, "locale": None, "item": None, "stylesheet": None})
    out.sort(key=lambda r: r["path"])
    return "walk", out


def redirects_of(root: Path) -> dict:
    target = root / "redirects.json"
    if not target.is_file():
        return {"present": False, "count": 0}
    data = _read_json(target)
    rows = data.get("redirects", data) if isinstance(data, dict) else data
    if isinstance(rows, dict):
        rows = [
            {"from": src, "to": dst.get("to"), "status": dst.get("status", 301)} if isinstance(dst, dict) else {"from": src, "to": dst, "status": 301}
            for src, dst in rows.items()
        ]
    if not isinstance(rows, list):
        return {"present": True, "count": 0, "invalid": 1, "error": "redirects.json is not a list or an object"}
    mapping: dict[str, str] = {}
    by_status: dict[str, int] = {}
    external = 0
    invalid = 0
    for row in rows:
        src = row.get("from", row.get("source")) if isinstance(row, dict) else None
        dst = row.get("to", row.get("target")) if isinstance(row, dict) else None
        status = row.get("status", 301) if isinstance(row, dict) else None
        if not isinstance(src, str) or not isinstance(dst, str) or status not in (301, 302, 307, 308):
            invalid += 1
            continue
        by_status[str(status)] = by_status.get(str(status), 0) + 1
        if dst.startswith(("http://", "https://")):
            external += 1
        mapping[src.rstrip("/") or "/"] = dst.rstrip("/") or "/"
    loops = 0
    for start in mapping:
        seen = {start}
        step = mapping.get(start)
        while step is not None:
            if step in seen:
                loops += 1
                break
            seen.add(step)
            step = mapping.get(step)
    return {"present": True, "count": sum(by_status.values()), "byStatus": by_status, "external": external, "invalid": invalid, "loops": loops}


def _tree_stats(root: Path) -> tuple[int, int]:
    files = 0
    size = 0
    for current, _dirs, names in os.walk(root, followlinks=False):
        for n in names:
            files += 1
            try:
                size += (Path(current) / n).stat().st_size
            except OSError:
                pass
    return files, size


def _content_root(staging: Path) -> Path:
    if any((staging / m).exists() for m in MARKERS):
        return staging
    children = [c for c in staging.iterdir() if c.name != "__MACOSX"]
    if len(children) == 1 and children[0].is_dir() and not children[0].is_symlink():
        return children[0]
    return staging


def _write_json(target: Path, data: dict) -> None:
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, target)


def _finish(staging: Path, kind: str, source: dict, source_key: str, stem: str, name: str | None, skipped: int = 0, site_id: str | None = None, revision_name: str | None = None) -> dict:
    try:
        root = _content_root(staging)
        _, rows = routes_of(root)
        if not rows:
            raise IntakeError("no site found: the source has no routes.json and no index.html", 400, "not-a-site")
        title = (name or "").strip() or site_name_from(root) or stem
        sid = site_id or project_site(title, source_key)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        files, size = _tree_stats(root)
        redirects = redirects_of(root)
        with _lock:
            folder = paths.sites_dir() / sid
            folder.mkdir(parents=True, exist_ok=True)
            base = revision_name or stamp
            revision = base
            counter = 2
            while (folder / revision).exists():
                revision = f"{base}-{counter}"
                counter += 1
            os.replace(root, folder / revision)
            previous = _read_json(folder / "site.json")
            history = previous.get("revisions", []) if isinstance(previous, dict) else []
            history = [r for r in history if isinstance(r, str)] + [revision]
            record = {
                "id": sid,
                "name": title,
                "source": source,
                "revisions": history,
                "revision": revision,
                "routes": len(rows),
                "bytes": size,
                "files": files,
                "skipped": skipped,
                "redirects": redirects,
                "sitemap": (folder / revision / "sitemap.xml").is_file(),
                "robots": (folder / revision / "robots.txt").is_file(),
                "createdAt": previous.get("createdAt", now_iso()) if isinstance(previous, dict) else now_iso(),
                "importedAt": now_iso(),
            }
            _write_json(folder / "site.json", record)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    bus.emit("site.imported", id=sid, name=title, revision=revision, routes=len(rows), kind=kind)
    return record


def project_site(title: str, source_key: str) -> str:
    sid = make_id(title, source_key)
    if not source_key.startswith("formweb:receive:") or source_key == "formweb:receive:formweb" or (paths.sites_dir() / sid / "site.json").is_file():
        return sid
    for record in list_sites():
        source = record.get("source")
        if isinstance(source, dict) and f"{source.get('kind')}:{source.get('url')}" == source_key and ID_RE.match(str(record.get("id", ""))):
            return str(record["id"])
    return _address_site(title) or sid


def _address_site(title: str) -> str | None:
    wanted = title.strip().casefold()
    found = []
    for record in list_sites():
        source = record.get("source")
        if not isinstance(source, dict) or source.get("kind") != "formweb":
            continue
        url = source.get("url")
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            continue
        if str(record.get("name", "")).strip().casefold() == wanted and ID_RE.match(str(record.get("id", ""))):
            found.append(str(record["id"]))
    return found[0] if len(found) == 1 else None


def _staging() -> Path:
    return Path(tempfile.mkdtemp(prefix=".staging-", dir=paths.sites_dir()))


def import_zip_file(archive: Path, kind: str, source: dict, source_key: str, name: str | None = None, stem: str | None = None, site_id: str | None = None) -> dict:
    staging = _staging()
    try:
        safe_unzip(archive, staging)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return _finish(staging, kind, source, source_key, stem or "site", name, site_id=site_id)


def is_fweb(path: Path, filename: str | None = None) -> bool:
    if (filename or path.name).lower().endswith(".fweb"):
        return True
    return compiler.looks_like_fweb(path)


def import_fweb_file(envelope: Path, source: dict, source_key: str, name: str | None = None, stem: str | None = None) -> dict:
    staging = _staging()
    try:
        try:
            details = compiler.compile_fweb(envelope, staging)
        except compiler.CompileError as exc:
            raise IntakeError(exc.message, exc.status, exc.code) from exc
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    source = {**source, "engine": details.get("engine"), "locale": details.get("locale"), "assets": details.get("assets")}
    return _finish(staging, "fweb", source, source_key, stem or "site", name or details.get("name"))


def import_folder(folder: Path, name: str | None = None) -> dict:
    root = folder.resolve()
    staging = _staging()
    try:
        skipped = copy_folder(root, staging)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return _finish(staging, "folder", {"kind": "folder", "path": str(root)}, f"folder:{root}", root.name, name, skipped)


def import_path(raw: str, name: str | None = None) -> dict:
    if not isinstance(raw, str) or not raw.strip():
        raise IntakeError("path is required")
    target = Path(raw.strip()).expanduser()
    if not target.is_absolute():
        raise IntakeError("path must be absolute")
    if target.is_dir():
        return import_folder(target, name)
    if target.is_file():
        resolved = target.resolve()
        from app.services import fpub

        if fpub.is_fpub(resolved):
            return fpub.import_file(resolved, {"path": str(resolved)}, name)
        if is_fweb(resolved):
            return import_fweb_file(resolved, {"kind": "fweb", "path": str(resolved)}, f"fweb:{resolved}", name, resolved.stem)
        return import_zip_file(resolved, "zip", {"kind": "zip", "path": str(resolved)}, f"zip:{resolved}", name, resolved.stem)
    raise IntakeError(f"{raw} does not exist", 404, "path-missing")


def import_upload(archive: Path, filename: str, name: str | None = None) -> dict:
    label = Path(filename or "upload.zip").name
    from app.services import fpub

    if fpub.is_fpub(archive, label):
        return fpub.import_file(archive, {"path": label, "upload": True}, name)
    if is_fweb(archive, label):
        return import_fweb_file(archive, {"kind": "fweb", "path": label, "upload": True}, f"fweb-upload:{label}", name, Path(label).stem)
    return import_zip_file(archive, "zip", {"kind": "zip", "path": label, "upload": True}, f"upload:{label}", name, Path(label).stem)


def import_formweb_zip(archive: Path, url: str, name: str | None = None) -> dict:
    return import_zip_file(archive, "formweb", {"kind": "formweb", "url": url}, f"formweb:{url}", name, "formweb-export")


def _valid_id(site_id: str) -> str:
    if not isinstance(site_id, str) or not ID_RE.match(site_id):
        raise IntakeError("site not found", 404, "site-missing")
    return site_id


def _site_folder(site_id: str) -> Path:
    folder = paths.sites_dir() / _valid_id(site_id)
    if not (folder / "site.json").is_file():
        raise IntakeError("site not found", 404, "site-missing")
    return folder


def list_sites() -> list[dict]:
    out = []
    for folder in paths.sites_dir().iterdir():
        if folder.name.startswith(".") or not folder.is_dir():
            continue
        record = _read_json(folder / "site.json")
        if isinstance(record, dict):
            out.append(record)
    out.sort(key=lambda r: str(r.get("importedAt", "")), reverse=True)
    return out


def get_site(site_id: str) -> dict:
    folder = _site_folder(site_id)
    record = _read_json(folder / "site.json") or {}
    revision = record.get("revision") or (record.get("revisions") or [""])[-1]
    return {**record, "path": str(folder / revision)}


def revision_root(site_id: str, revision: str | None = None) -> Path:
    folder = _site_folder(site_id)
    record = _read_json(folder / "site.json") or {}
    chosen = revision or record.get("revision") or (record.get("revisions") or [""])[-1]
    if chosen not in (record.get("revisions") or []):
        raise IntakeError("revision not found", 404, "revision-missing")
    return folder / chosen


def site_routes(site_id: str, revision: str | None = None) -> dict:
    root = revision_root(site_id, revision)
    source, rows = routes_of(root)
    return {"id": site_id, "revision": root.name, "source": source, "count": len(rows), "routes": rows}


def remove_site(site_id: str) -> dict:
    with _lock:
        folder = _site_folder(site_id)
        record = _read_json(folder / "site.json") or {}
        name = record.get("name") if isinstance(record.get("name"), str) and record.get("name") else site_id
        target = trash.move(folder, "site", name, trash.rel(folder))
    bus.emit("site.removed", id=site_id)
    return {"id": site_id, "removed": True, "trash": str(target)}
