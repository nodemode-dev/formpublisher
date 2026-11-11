import logging
import shutil
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from app.services import intake, package, paths
from app.services.bus import bus

log = logging.getLogger("formpublisher")
SUFFIXES = (".zip", ".fweb")
POLL_SECONDS = 5.0
SETTLE_SECONDS = 2.0
KEEP_RECEIPTS = 5
_lock = threading.RLock()
_stop = threading.Event()
_thread: threading.Thread | None = None


def _receipts_file() -> Path:
    return paths.home() / "receipts.json"


def receipts() -> list[dict]:
    data = package._read_json(_receipts_file())
    return [r for r in data if isinstance(r, dict)][:KEEP_RECEIPTS] if isinstance(data, list) else []


def _record(entry: dict) -> None:
    with _lock:
        rows = [entry] + receipts()
        package._write_text(_receipts_file(), package.dumps(rows[:KEEP_RECEIPTS]))


def endpoint() -> str:
    return f"http://127.0.0.1:{paths.port()}/api/receive/formweb"


def announce(record: dict, via: str, name: str | None) -> dict:
    """Log a successful import, tell the bus and return the receipt."""
    entry = {
        "at": intake.now_iso(),
        "via": via,
        "ok": True,
        "site": record["id"],
        "name": record.get("name"),
        "revision": record["revision"],
        "file": name,
    }
    _record(entry)
    bus.emit("sites.received", site=record["id"], name=record.get("name"), revision=record["revision"], via=via, file=name)
    return entry


def receive_zip(archive: Path, project: str | None, site_name: str | None) -> dict:
    url = f"receive:{project}" if project else "receive:formweb"
    record = intake.import_formweb_zip(archive, url, site_name)
    announce(record, "http", None)
    return {"site": record["id"], "revision": record["revision"], "opened": bus.clients() > 0}


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _park(path: Path, folder: str, reason: str | None) -> Path:
    base = paths.inbox_dir() / folder
    base.mkdir(parents=True, exist_ok=True)
    target = base / f"{_stamp()}-{path.name}"
    counter = 2
    while target.exists():
        target = base / f"{_stamp()}-{counter}-{path.name}"
        counter += 1
    shutil.move(str(path), str(target))
    if reason is not None:
        target.with_name(target.name + ".txt").write_text(reason + "\n", encoding="utf-8")
    return target


def process(path: Path) -> None:
    try:
        record = intake.import_upload(path, path.name, None)
    except intake.IntakeError as exc:
        _fail(path, exc.message)
        return
    except Exception as exc:
        log.exception("inbox import of %s failed", path.name)
        _fail(path, f"{type(exc).__name__}: {exc}")
        return
    _park(path, "imported", None)
    announce(record, "inbox", path.name)


def _fail(path: Path, reason: str) -> None:
    try:
        _park(path, "failed", reason)
    except OSError:
        log.exception("could not move %s to failed/", path.name)
    _record({"at": intake.now_iso(), "via": "inbox", "ok": False, "file": path.name, "error": reason})
    bus.emit("sites.receive_failed", file=path.name, error=reason)


def pending() -> list[Path]:
    try:
        found = [p for p in paths.inbox_dir().iterdir() if p.is_file() and p.suffix.lower() in SUFFIXES and not p.name.startswith(".")]
    except OSError:
        return []
    return sorted(found, key=lambda p: p.name)


def scan_once() -> int:
    handled = 0
    now = time.time()
    for path in pending():
        try:
            if now - path.stat().st_mtime < SETTLE_SECONDS:
                continue
        except OSError:
            continue
        process(path)
        handled += 1
    return handled


def _run() -> None:
    while not _stop.is_set():
        try:
            scan_once()
        except Exception:
            log.exception("inbox scan failed")
        _stop.wait(POLL_SECONDS)


def start() -> None:
    global _thread
    with _lock:
        if _thread is not None and _thread.is_alive():
            return
        _stop.clear()
        paths.inbox_dir()
        _thread = threading.Thread(target=_run, name="formpublisher-inbox", daemon=True)
        _thread.start()


def stop() -> None:
    global _thread
    _stop.set()
    thread = _thread
    if thread is not None:
        thread.join(timeout=3)
    _thread = None


def status() -> dict:
    return {
        "endpoint": endpoint(),
        "inbox": str(paths.inbox_dir()),
        "watching": _thread is not None and _thread.is_alive(),
        "pending": len(pending()),
        "intervalSeconds": POLL_SECONDS,
        "receipts": receipts(),
    }
