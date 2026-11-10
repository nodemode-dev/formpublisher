import os
import shutil
import subprocess
import sys
import tempfile
import threading
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from app import targets
from app.services import intake, package, paths
from app.services.bus import bus
from app.targets._common import PreparedInput, PreparedResult

_lock = threading.RLock()


def _error(message: str, status: int = 400) -> intake.IntakeError:
    return intake.IntakeError(message, status)


def _target(target_id: str):
    module = targets.get(target_id) if isinstance(target_id, str) else None
    if module is None:
        raise _error(f"unknown target: {target_id!r}", 404)
    return module


def list_targets() -> dict:
    rows = targets.describe()
    return {"targets": rows, "count": len(rows)}


def _hash(path: Path) -> str:
    return package.sha256_file(path)


def _walk(folder: Path) -> list[dict]:
    rows = []
    base = folder.resolve()
    for current, dirs, names in os.walk(base, followlinks=False):
        dirs.sort()
        for n in sorted(names):
            path = Path(current) / n
            rows.append({"path": path.relative_to(base).as_posix(), "size": path.stat().st_size, "sha256": _hash(path)})
    rows.sort(key=lambda r: r["path"].encode("utf-8"))
    return rows


def _unpack(archive: Path, dest: Path) -> list[str]:
    names = []
    root = dest.resolve()
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            rel = intake._clean_member(info.filename)
            target = (root / rel).resolve()
            if root not in target.parents:
                raise _error(f"the package holds an unsafe path: {rel!r}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out, 1024 * 1024)
            names.append(rel)
    return sorted(names, key=lambda n: n.encode("utf-8"))


def _load(build_id: str, work: Path) -> PreparedInput:
    record = package.get_build(build_id)
    publish = record.get("publish")
    if not isinstance(publish, dict):
        raise _error("the build has no publish.json", 409)
    archive = package.zip_path(build_id)
    expected = (publish.get("package") or {}).get("sha256")
    if expected and _hash(archive) != expected:
        raise _error("site.zip no longer matches publish.json; build it again", 409)
    folder = archive.parent
    raw = (folder / "publish.json").read_bytes()
    root = work / "unpacked"
    root.mkdir()
    names = _unpack(archive, root)
    build = {k: v for k, v in record.items() if k not in ("publish", "signature")}
    return PreparedInput(build=build, publish=publish, publish_bytes=raw, zip_path=archive, root=root, names=names, slug=record["site"])


def _build_folder(module, inp: PreparedInput, out: Path) -> PreparedResult:
    out.mkdir(parents=True)
    result = module.prepare(inp, out)
    if not isinstance(result, PreparedResult):
        raise _error(f"target {module.ID} returned an invalid result", 500)
    return result


def _site_dir(site: str, build_id: str) -> Path:
    return paths.prepared_dir() / site / build_id


def _meta_file(site: str, build_id: str, target_id: str) -> Path:
    return _site_dir(site, build_id) / f".{target_id}.json"


def _read_meta(path: Path):
    return package._read_json(path)


def prepare(build_id: str, target_ids: list[str] | None) -> dict:
    ids = list(target_ids) if target_ids else list(targets.registry())
    if not all(isinstance(t, str) for t in ids):
        raise _error("targets must be a list of target ids")
    ids = list(dict.fromkeys(ids))
    modules = [_target(t) for t in ids]
    record = package.get_build(build_id)
    site = record["site"]
    results: dict[str, dict] = {}
    with _lock:
        work = Path(tempfile.mkdtemp(prefix=".prepare-", dir=paths.prepared_dir()))
        try:
            inp = _load(build_id, work)
            for module in modules:
                staged = work / "out" / module.ID
                result = _build_folder(module, inp, staged)
                files = _walk(staged)
                folder = _site_dir(site, build_id) / module.ID
                folder.parent.mkdir(parents=True, exist_ok=True)
                if folder.exists():
                    shutil.rmtree(folder)
                os.replace(staged, folder)
                meta = {
                    "target": module.ID,
                    "name": getattr(module, "NAME", module.ID),
                    "folder": str(folder),
                    "files": files,
                    "commands": result.commands,
                    "notes": result.notes,
                    "warnings": result.warnings,
                    "preparedAt": intake.now_iso(),
                }
                package._write_text(_meta_file(site, build_id, module.ID), package.dumps(meta))
                results[module.ID] = {k: meta[k] for k in ("name", "folder", "files", "commands", "notes", "warnings", "preparedAt")}
        finally:
            shutil.rmtree(work, ignore_errors=True)
    for target_id, row in results.items():
        bus.emit("publish.prepared", build=build_id, site=site, target=target_id, folder=row["folder"], files=len(row["files"]))
    return {"build": build_id, "results": results}


def prepared(build_id: str) -> dict:
    record = package.get_build(build_id)
    site = record["site"]
    results: dict[str, dict] = {}
    folder = _site_dir(site, build_id)
    for module_id in targets.registry():
        meta = _read_meta(_meta_file(site, build_id, module_id))
        if isinstance(meta, dict) and (folder / module_id).is_dir():
            results[module_id] = {k: meta.get(k) for k in ("name", "folder", "files", "commands", "notes", "warnings", "preparedAt")}
    return {"build": build_id, "site": site, "results": results}


def _prepared_folder(build_id: str, target_id: str) -> tuple[str, Path]:
    _target(target_id)
    record = package.get_build(build_id)
    folder = _site_dir(record["site"], build_id) / target_id
    if not folder.is_dir():
        raise _error("nothing is prepared for that build and target", 404)
    return record["site"], folder


def _desktop() -> bool:
    if sys.platform in ("darwin", "win32"):
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")) and shutil.which("xdg-open") is not None


def reveal(build_id: str, target_id: str) -> dict:
    _site, folder = _prepared_folder(build_id, target_id)
    opened = False
    if _desktop():
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", str(folder)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif sys.platform == "win32":
                os.startfile(str(folder))  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", str(folder)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            opened = True
        except OSError:
            opened = False
    return {"build": build_id, "target": target_id, "path": str(folder), "opened": opened}


def verify(build_id: str, target_id: str) -> dict:
    module = _target(target_id)
    site, folder = _prepared_folder(build_id, target_id)
    problems: list[dict] = []
    current = {row["path"]: row for row in _walk(folder)}
    with _lock:
        work = Path(tempfile.mkdtemp(prefix=".verify-", dir=paths.prepared_dir()))
        try:
            inp = _load(build_id, work)
            expected_zip = (inp.publish.get("package") or {}).get("sha256")
            if target_id == "static-zip":
                got = current.get("site.zip", {}).get("sha256")
                if got != expected_zip:
                    problems.append({"path": "site.zip", "problem": "hash differs from publish.json", "source": "publish.json"})
            else:
                for row in inp.publish.get("files") or []:
                    path = f"site/{row.get('path')}"
                    found = current.get(path)
                    if found is None:
                        problems.append({"path": path, "problem": "missing", "source": "publish.json"})
                    elif found["sha256"] != row.get("sha256"):
                        problems.append({"path": path, "problem": "hash differs from publish.json", "source": "publish.json"})
            staged = work / "fresh"
            _build_folder(module, inp, staged)
            fresh = {row["path"]: row for row in _walk(staged)}
        finally:
            shutil.rmtree(work, ignore_errors=True)
    for path in sorted(set(fresh) | set(current)):
        if path not in current:
            problems.append({"path": path, "problem": "missing", "source": "prepare"})
        elif path not in fresh:
            problems.append({"path": path, "problem": "extra file", "source": "prepare"})
        elif fresh[path]["sha256"] != current[path]["sha256"]:
            problems.append({"path": path, "problem": "differs from a fresh prepare", "source": "prepare"})
    seen = set()
    unique = []
    for p in problems:
        key = (p["path"], p["problem"])
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return {"build": build_id, "target": target_id, "folder": str(folder), "ok": not unique, "checked": len(current), "problems": unique}


def remove(build_id: str, target_id: str) -> dict:
    site, folder = _prepared_folder(build_id, target_id)
    with _lock:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        base = f"prepared-{site}-{build_id}-{target_id}-{stamp}"
        target = paths.trash_dir() / base
        counter = 2
        while target.exists():
            target = paths.trash_dir() / f"{base}-{counter}"
            counter += 1
        shutil.move(str(folder), str(target))
        _meta_file(site, build_id, target_id).unlink(missing_ok=True)
    bus.emit("publish.removed", build=build_id, site=site, target=target_id)
    return {"build": build_id, "target": target_id, "removed": True, "trash": str(target)}
