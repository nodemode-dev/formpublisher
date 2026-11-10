import hashlib
import json
import os
import re
import shutil
import tempfile
import threading
import zipfile
from pathlib import Path
from typing import Any

from app import __version__
from app.services import intake, paths, trash
from app.services.bus import bus

ID_RE = re.compile(r"^[0-9a-f]{12}$")
SOURCE_KINDS = {"formweb": "formweb-export", "zip": "formweb-export", "folder": "folder", "fweb": "fweb"}
HEADERS = [
    {"for": "/*", "values": {"X-Content-Type-Options": "nosniff", "Referrer-Policy": "strict-origin-when-cross-origin"}},
    {"for": "/assets/*", "values": {"Cache-Control": "public, max-age=3600"}},
]
_lock = threading.RLock()


def _error(message: str, status: int = 400) -> intake.IntakeError:
    return intake.IntakeError(message, status)


def dumps(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _write_text(target: Path, text: str) -> None:
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, target)


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _own_record(name: str) -> bool:
    return name.startswith(".fp")


def collect(root: Path) -> list[tuple[str, Path]]:
    base = root.resolve()
    found: list[tuple[str, Path]] = []
    for current, dirs, names in os.walk(base, followlinks=False):
        here = Path(current)
        dirs[:] = [d for d in dirs if not _own_record(d) and not (here / d).is_symlink()]
        for n in names:
            path = here / n
            if _own_record(n) or path.is_symlink() or not path.is_file():
                continue
            found.append((path.relative_to(base).as_posix(), path))
    found.sort(key=lambda row: row[0].encode("utf-8"))
    return found


def write_zip(files: list[tuple[str, Path]], target: Path) -> None:
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for rel, path in files:
            info = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            info.extra = b""
            info.comment = b""
            with open(path, "rb") as src, zf.open(info, "w", force_zip64=False) as out:
                shutil.copyfileobj(src, out, 1024 * 1024)


def _file_rows(files: list[tuple[str, Path]]) -> list[dict]:
    return [{"path": rel, "sha256": sha256_file(path), "size": path.stat().st_size} for rel, path in files]


def _redirect_rows(root: Path) -> list[dict]:
    data = intake._read_json(root / "redirects.json")
    rows = data.get("redirects", data) if isinstance(data, dict) else data
    if isinstance(rows, dict):
        rows = [
            {"from": src, "to": dst.get("to"), "status": dst.get("status", 301)} if isinstance(dst, dict) else {"from": src, "to": dst, "status": 301}
            for src, dst in rows.items()
        ]
    out = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        src = row.get("from", row.get("source"))
        dst = row.get("to", row.get("target"))
        status = row.get("status", 301)
        if isinstance(src, str) and isinstance(dst, str) and status in (301, 302, 307, 308):
            out.append({"from": src, "to": dst, "status": status})
    return out


def _check_summary(site_id: str, revision: str) -> dict:
    data = _read_json(paths.home() / "checks" / site_id / revision / "results.json")
    counts = {"error": 0, "warning": 0, "info": 0}
    tiers = []
    for tier in ("static", "deep"):
        block = data.get(tier) if isinstance(data, dict) else None
        if not isinstance(block, dict) or not isinstance(block.get("problems"), list):
            continue
        tiers.append(tier)
        for problem in block["problems"]:
            severity = problem.get("severity") if isinstance(problem, dict) else None
            if severity in counts:
                counts[severity] += 1
    return {"errors": counts["error"], "warnings": counts["warning"], "infos": counts["info"], "tiers": tiers}


def _source_block(record: dict, root: Path) -> dict:
    source = record.get("source") if isinstance(record.get("source"), dict) else {}
    block: dict[str, Any] = {"kind": SOURCE_KINDS.get(str(source.get("kind")), "folder")}
    manifest = intake._read_json(root / "site.formweb.json")
    if isinstance(manifest, dict):
        for key in ("formwebVersion", "generatorVersion", "version"):
            if isinstance(manifest.get(key), str) and manifest[key].strip():
                block["formwebVersion"] = manifest[key].strip()
                break
    if "formwebVersion" not in block and isinstance(source.get("engine"), str) and source["engine"].strip():
        block["formwebVersion"] = source["engine"].strip()
    return block


def _assemble(site_id: str, revision: str | None, work: Path) -> dict:
    root = intake.revision_root(site_id, revision)
    record = intake._read_json(root.parent / "site.json") or {}
    files = collect(root)
    if not files:
        raise _error("the revision has no files to package")
    archive = work / "site.zip"
    write_zip(files, archive)
    digest = sha256_file(archive)
    size = archive.stat().st_size
    rows = _file_rows(files)
    _, routes = intake.routes_of(root)
    publish = {
        "format": "formpublisher-site",
        "version": 1,
        "site": {"id": site_id, "name": record.get("name") or site_id, "revision": root.name, "source": _source_block(record, root)},
        "package": {"file": "site.zip", "sha256": digest, "size": size},
        "files": rows,
        "routes": routes,
        "redirects": _redirect_rows(root),
        "headers": HEADERS,
        "checks": _check_summary(site_id, root.name),
        "builtWith": f"FormPublisher {__version__}",
    }
    return {"site": site_id, "revision": root.name, "sha256": digest, "size": size, "files": len(rows), "publish": publish}


def _find(build_id: str) -> Path:
    if not isinstance(build_id, str) or not ID_RE.match(build_id):
        raise _error("build not found", 404)
    for site in sorted(paths.builds_dir().iterdir()):
        folder = site / build_id
        if site.is_dir() and not site.name.startswith(".") and (folder / "build.json").is_file():
            return folder
    raise _error("build not found", 404)


def build(site_id: str, revision: str | None = None) -> dict:
    with _lock:
        intake.revision_root(site_id, revision)
        work = Path(tempfile.mkdtemp(prefix=".build-", dir=paths.builds_dir()))
        try:
            made = _assemble(site_id, revision, work)
            # The same bytes imported as two sites must not share a build id (builds live under builds/<site>/<id>).
            build_id = hashlib.sha256(f"{site_id}:{made['sha256']}".encode()).hexdigest()[:12]
            folder = paths.builds_dir() / site_id / build_id
            if (folder / "build.json").is_file():
                existing = get_build(build_id)
                return {**existing, "created": False}
            record = {
                "id": build_id,
                "site": site_id,
                "revision": made["revision"],
                "created": intake.now_iso(),
                "size": made["size"],
                "files": made["files"],
                "signed": False,
            }
            _write_text(work / "publish.json", dumps(made["publish"]))
            _write_text(work / "build.json", dumps(record))
            folder.parent.mkdir(parents=True, exist_ok=True)
            if folder.exists():
                shutil.rmtree(folder)
            os.replace(work, folder)
        finally:
            shutil.rmtree(work, ignore_errors=True)
    bus.emit("builds.created", id=build_id, site=site_id, revision=made["revision"], size=made["size"])
    return {**get_build(build_id), "created": True}


def get_build(build_id: str) -> dict:
    folder = _find(build_id)
    record = _read_json(folder / "build.json") or {}
    return {**record, "publish": _read_json(folder / "publish.json"), "signature": (folder / "site.zip.sig").is_file()}


def list_builds() -> list[dict]:
    out = []
    for site in paths.builds_dir().iterdir():
        if not site.is_dir() or site.name.startswith("."):
            continue
        for folder in site.iterdir():
            record = _read_json(folder / "build.json") if folder.is_dir() else None
            if isinstance(record, dict):
                out.append({**record, "signature": (folder / "site.zip.sig").is_file()})
    out.sort(key=lambda r: (str(r.get("created", "")), str(r.get("id", ""))), reverse=True)
    return out


def reproduce(build_id: str) -> dict:
    folder = _find(build_id)
    record = _read_json(folder / "build.json") or {}
    publish = _read_json(folder / "publish.json") or {}
    expected = (publish.get("package") or {}).get("sha256", "")
    work = Path(tempfile.mkdtemp(prefix=".repro-", dir=paths.builds_dir()))
    try:
        made = _assemble(record.get("site", ""), record.get("revision"), work)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return {"same": made["sha256"] == expected, "sha256": made["sha256"], "expected": expected}


def zip_path(build_id: str) -> Path:
    target = _find(build_id) / "site.zip"
    if not target.is_file():
        raise _error("the build has no site.zip", 404)
    return target


def compare(a: str, b: str) -> dict:
    left = {row["path"]: row for row in (get_build(a).get("publish") or {}).get("files", [])}
    right = {row["path"]: row for row in (get_build(b).get("publish") or {}).get("files", [])}
    added = sorted(set(right) - set(left))
    removed = sorted(set(left) - set(right))
    changed = []
    same = 0
    for path in sorted(set(left) & set(right)):
        if left[path]["sha256"] == right[path]["sha256"]:
            same += 1
        else:
            changed.append(
                {
                    "path": path,
                    "a": {"sha256": left[path]["sha256"], "size": left[path]["size"]},
                    "b": {"sha256": right[path]["sha256"], "size": right[path]["size"]},
                }
            )
    return {"a": a, "b": b, "added": added, "removed": removed, "changed": changed, "same": same}


def remove_build(build_id: str) -> dict:
    with _lock:
        folder = _find(build_id)
        target = trash.move(folder, "build", build_id, trash.rel(folder))
    bus.emit("builds.removed", id=build_id)
    return {"id": build_id, "removed": True, "trash": str(target)}


def mark_signed(build_id: str, signed: bool) -> None:
    folder = _find(build_id)
    record = _read_json(folder / "build.json")
    if isinstance(record, dict) and record.get("signed") != signed:
        record["signed"] = signed
        _write_text(folder / "build.json", dumps(record))
