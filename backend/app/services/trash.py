import json
import os
import re
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path

from app.services import paths
from app.services.bus import bus

SUFFIX = ".trash.json"
KINDS = ("site", "build", "key", "prepared")
ROOTS = {"site": "sites", "build": "builds", "key": "keys", "prepared": "prepared"}
PREFIXES = (("build-", "build"), ("key-", "key"), ("prepared-", "prepared"))
STAMP_RE = re.compile(r"-\d{8}T\d{6}Z(?:-\d+)?$")
BUILD_ID_RE = re.compile(r"^[0-9a-f]{12}$")
SITE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,100}$")
_lock = threading.RLock()


def _error(message: str, status: int = 400):
    from app.services.intake import IntakeError

    return IntakeError(message, status)


def _origin_unknown():
    from app.services.intake import IntakeError

    class OriginUnknown(IntakeError):
        code = "origin-unknown"

    return OriginUnknown(
        "This entry was moved before the trash kept its origin and its name cannot be read, so say where it goes (a place inside its own folder) to restore it.",
        409,
    )


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def rel(path: Path) -> str:
    """Return a path relative to the data folder, with forward slashes, for use as a trash origin."""
    return Path(os.path.abspath(path)).relative_to(os.path.abspath(paths.home())).as_posix()


def _size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.lstat(os.path.join(root, name)).st_size
            except OSError:
                continue
    return total


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _base_name(path: Path, kind: str) -> str:
    stamp = _stamp()
    if kind == "build":
        return f"build-{path.parent.name}-{path.name}-{stamp}"
    if kind == "key":
        return f"key-{path.stem}-{stamp}"
    if kind == "prepared":
        return f"prepared-{path.parent.parent.name}-{path.parent.name}-{path.name}-{stamp}"
    return f"{path.name}-{stamp}"


def move(path: Path, kind: str, label: str, origin: str, payload: dict | None = None) -> Path:
    """Move a folder or file into the trash under a unique entry name and write its metadata file.

    A key is a file: the trash entry is a folder holding the key and entry.json (the key's row, passed as payload).
    For other kinds the payload is kept in the metadata file so a restore can rebuild what the move removed.
    """
    if kind not in KINDS:
        raise _error(f"unknown trash kind: {kind!r}")
    with _lock:
        folder = paths.trash_dir()
        base = _base_name(path, kind)
        target = folder / base
        counter = 2
        while target.exists() or (folder / (target.name + SUFFIX)).exists():
            target = folder / f"{base}-{counter}"
            counter += 1
        if kind == "key":
            target.mkdir(parents=True)
            if path.is_file():
                shutil.move(str(path), str(target / path.name))
                os.chmod(target / path.name, 0o600)
            (target / "entry.json").write_text(json.dumps(payload or {}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        else:
            shutil.move(str(path), str(target))
        record = {"kind": kind, "label": label, "origin": origin, "moved": _iso(datetime.now(timezone.utc)), "size": _size(target)}
        if kind == "prepared" and payload is not None:
            record["payload"] = payload
        (folder / (target.name + SUFFIX)).write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    bus.emit("trash.changed", action="moved", kind=kind, entry=target.name)
    return target


def _entries() -> dict[str, Path]:
    found = {}
    for item in paths.trash_dir().iterdir():
        if item.name.endswith(SUFFIX) or item.name.startswith("."):
            continue
        found[item.name] = item
    return found


def _meta(entry: Path) -> dict | None:
    side = entry.with_name(entry.name + SUFFIX)
    try:
        data = json.loads(side.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get("kind") in KINDS else None


def _row(entry: Path) -> dict:
    meta = _meta(entry)
    if meta is not None:
        return {
            "entry": entry.name,
            "kind": meta["kind"],
            "label": meta.get("label") if isinstance(meta.get("label"), str) else entry.name,
            "origin": meta.get("origin") if isinstance(meta.get("origin"), str) else None,
            "originInferred": False,
            "moved": meta.get("moved") if isinstance(meta.get("moved"), str) else _iso(datetime.fromtimestamp(entry.stat().st_mtime, timezone.utc)),
            "size": meta.get("size") if isinstance(meta.get("size"), int) else _size(entry),
        }
    kind = _legacy_kind(entry)
    origin = _infer_origin(entry, kind)
    return {
        "entry": entry.name,
        "kind": kind,
        "label": entry.name,
        "origin": origin,
        "originInferred": origin is not None,
        "moved": _iso(datetime.fromtimestamp(entry.stat().st_mtime, timezone.utc)),
        "size": _size(entry),
    }


def _read_json(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _legacy_kind(entry: Path) -> str:
    if entry.is_dir() and (entry / "site.json").is_file():
        return "site"
    return next((k for prefix, k in PREFIXES if entry.name.startswith(prefix)), "site")


def _infer_origin(entry: Path, kind: str) -> str | None:
    """Work out where a trash entry made before 0.1.4 came from, from its contents and its name, or return None."""
    if kind == "site":
        record = _read_json(entry / "site.json") if entry.is_dir() else None
        site_id = record.get("id") if record else None
        if isinstance(site_id, str) and SITE_ID_RE.match(site_id):
            return f"sites/{site_id}"
        return None
    if kind == "key":
        record = _read_json(entry / "entry.json") if entry.is_dir() else None
        key_id = record.get("id") if record else None
        if isinstance(key_id, str) and re.match(r"^[0-9a-f]{16}$", key_id):
            return f"keys/{key_id}.pem"
        return None
    stem = STAMP_RE.sub("", entry.name, count=1)
    if stem == entry.name:
        return None
    if kind == "build":
        match = re.match(r"^build-(.+)-([0-9a-f]{12})$", stem)
        if match and SITE_ID_RE.match(match.group(1)):
            return f"builds/{match.group(1)}/{match.group(2)}"
        return None
    if not stem.startswith("prepared-"):
        return None
    body = stem[len("prepared-"):]
    from app import targets

    for target_id in sorted(targets.registry(), key=len, reverse=True):
        if not body.endswith("-" + target_id):
            continue
        match = re.match(r"^(.+)-([0-9a-f]{12})$", body[: -len(target_id) - 1])
        if match and SITE_ID_RE.match(match.group(1)):
            return f"prepared/{match.group(1)}/{match.group(2)}/{target_id}"
    return None


def list_entries() -> dict:
    """List trash entries newest first; entries from before metadata existed get their kind from the name."""
    with _lock:
        rows = [_row(item) for item in _entries().values()]
    rows.sort(key=lambda r: (r["moved"], r["entry"]), reverse=True)
    return {"entries": rows, "count": len(rows), "size": sum(r["size"] for r in rows)}


def _find(entry: str) -> Path:
    found = _entries().get(entry) if isinstance(entry, str) else None
    if found is None:
        raise _error("trash entry not found", 404)
    return found


def _free_destination(row: dict, origin: str | None = None) -> tuple[Path, str]:
    chosen = row["origin"]
    given = False
    if not chosen:
        if origin is None:
            raise _origin_unknown()
        if not isinstance(origin, str) or not origin.strip() or "\x00" in origin:
            raise _error("origin must be a path inside the data folder, such as sites/my-site")
        chosen = origin.strip()
        given = True
    base = Path(os.path.abspath(paths.home()))
    dest = Path(os.path.abspath(base / chosen))
    root = base / ROOTS[row["kind"]]
    if dest == root or root not in dest.parents:
        what = "The origin you gave" if given else "The recorded origin"
        raise _error(f"{what} is not a valid place for this kind of entry; it has to sit inside {ROOTS[row['kind']]}/.", 409)
    if row["kind"] == "key" and dest.parent != root:
        raise _error(f"A key goes straight inside {ROOTS['key']}/, as <key id>.pem.", 409)
    if dest.exists() or dest.is_symlink():
        raise _error(f"Something already exists at {dest.relative_to(base).as_posix()}; remove or rename it first.", 409)
    return dest, dest.relative_to(base).as_posix()


def _restore_key(entry: Path, row: dict, dest: Path) -> dict:
    from app.services import keys

    try:
        key_row = json.loads((entry / "entry.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        key_row = None
    if not isinstance(key_row, dict) or not isinstance(key_row.get("id"), str):
        raise _error("The key record in this entry is missing or damaged.", 409)
    if (entry / dest.name).name != f"{key_row['id']}.pem" or not (entry / dest.name).is_file():
        raise _error("The key file is missing from this entry.", 409)
    with keys._lock:
        if any(r.get("id") == key_row["id"] for r in keys._load()):
            raise _error("A key with this id already exists.", 409)
        shutil.move(str(entry / dest.name), str(dest))
        os.chmod(dest, 0o600)
        keys._save(keys._load() + [key_row])
    shutil.rmtree(entry, ignore_errors=True)
    bus.emit("keys.created", id=key_row["id"], name=key_row.get("name"), restored=True)
    return {"id": key_row["id"], "name": key_row.get("name")}


def _reprepare(entry_name: str, row: dict, dest: Path, origin: str) -> dict:
    from app.services import package, publish

    parts = Path(origin).parts
    if len(parts) != 4 or not BUILD_ID_RE.match(parts[2]) or not SITE_ID_RE.match(parts[1]):
        raise _error("A prepared folder goes at prepared/<site>/<build id>/<target>.", 409)
    site, build_id, target_id = parts[1], parts[2], parts[3]
    try:
        record = package.get_build(build_id)
    except Exception as exc:
        if getattr(exc, "status", None) == 404:
            raise _error(f"Build {build_id} is no longer here, so {target_id} cannot be prepared again from it. Restore the build from the trash first if it is there.", 409)
        raise
    if record.get("site") != site:
        raise _error(f"Build {build_id} belongs to a different site than {site}, so this entry cannot be prepared again from it.", 409)
    try:
        publish.prepare(build_id, [target_id])
    except Exception as exc:
        if getattr(exc, "status", None) == 404:
            raise _error(f"Target {target_id} is not available any more, so it cannot be prepared again.", 409)
        raise
    with _lock:
        entry = _entries().get(entry_name)
        if entry is not None:
            _destroy(entry)
    bus.emit("trash.changed", action="restored", kind="prepared", entry=entry_name)
    return {"entry": entry_name, "kind": "prepared", "restored": True, "origin": origin, "reprepared": True, "build": build_id, "target": target_id}


def restore(entry_name: str, origin: str | None = None) -> dict:
    """Move an entry back to where it came from, or raise 409 saying why it cannot go.

    An entry whose origin is neither recorded nor inferable from its name and contents needs origin, a path relative
    to the data folder inside the entry's own kind of folder; without one the answer is 409 with code origin-unknown.
    A prepared folder moved before 0.1.4 has no hidden record, so it is prepared again from its build.
    """
    with _lock:
        entry = _find(entry_name)
        row = _row(entry)
        dest, used = _free_destination(row, origin)
        row["origin"] = used
        kind = row["kind"]
        if kind == "prepared" and _meta(entry) is None:
            legacy = True
        else:
            legacy = False
    if legacy:
        return _reprepare(entry_name, row, dest, used)
    with _lock:
        entry = _find(entry_name)
        info: dict = {}
        if kind == "key":
            info = _restore_key(entry, row, dest)
        else:
            payload = (_meta(entry) or {}).get("payload")
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(entry), str(dest))
            if kind == "prepared" and isinstance(payload, dict):
                (dest.parent / f".{dest.name}.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        entry.with_name(entry.name + SUFFIX).unlink(missing_ok=True)
    _announce_restored(kind, dest, row)
    bus.emit("trash.changed", action="restored", kind=kind, entry=entry_name)
    return {"entry": entry_name, "kind": kind, "restored": True, "origin": row["origin"], **info}


def _announce_restored(kind: str, dest: Path, row: dict) -> None:
    if kind == "site":
        bus.emit("site.imported", id=dest.name, name=row["label"], restored=True)
    elif kind == "build":
        bus.emit("builds.created", id=dest.name, site=dest.parent.name, restored=True)
    elif kind == "prepared":
        bus.emit("publish.prepared", build=dest.parent.name, site=dest.parent.parent.name, target=dest.name, restored=True)


def _destroy(entry: Path) -> None:
    if entry.is_dir() and not entry.is_symlink():
        shutil.rmtree(entry)
    else:
        entry.unlink()
    entry.with_name(entry.name + SUFFIX).unlink(missing_ok=True)


def delete(entry_name: str) -> dict:
    """Delete one entry for good."""
    with _lock:
        entry = _find(entry_name)
        _destroy(entry)
    bus.emit("trash.changed", action="deleted", entry=entry_name)
    return {"entry": entry_name, "deleted": True}


def empty() -> dict:
    """Delete every entry for good, and any metadata file left without its entry."""
    with _lock:
        entries = list(_entries().values())
        for item in entries:
            _destroy(item)
        for item in paths.trash_dir().iterdir():
            if item.name.endswith(SUFFIX):
                item.unlink(missing_ok=True)
    bus.emit("trash.changed", action="emptied")
    return {"deleted": len(entries), "emptied": True}
