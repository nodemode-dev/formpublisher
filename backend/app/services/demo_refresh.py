import shutil
import tempfile
import threading
from pathlib import Path

from app.services import intake, package, paths, revisions

_lock = threading.Lock()
_zip_tables: dict[tuple[str, int, int], frozenset] = {}


def _zip_table(archive: Path) -> frozenset:
    info = archive.stat()
    key = (str(archive), info.st_mtime_ns, info.st_size)
    with _lock:
        hit = _zip_tables.get(key)
    if hit is not None:
        return hit
    work = Path(tempfile.mkdtemp(prefix=".demo-", dir=paths.sites_dir()))
    try:
        intake.safe_unzip(archive, work)
        root = intake._content_root(work)
        table = frozenset((rel, package.sha256_file(path)) for rel, path in package.collect(root))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    with _lock:
        _zip_tables[key] = table
    return table


def _revision_table(site_id: str, revision: str) -> frozenset:
    root = intake.revision_root(site_id, revision)
    return frozenset((rel, row["sha256"]) for rel, row in revisions._table(site_id, root).items())


def _touched(site_id: str) -> bool:
    for folder in (paths.builds_dir() / site_id, paths.prepared_dir() / site_id):
        if folder.is_dir() and any(not child.name.startswith(".") for child in folder.iterdir()):
            return True
    return False


def refresh(found: dict, archive: Path, key: str, stem: str) -> dict | None:
    site_id = str(found.get("id", ""))
    history = [r for r in (found.get("revisions") or []) if isinstance(r, str)]
    if not intake.ID_RE.match(site_id) or not history or not archive.is_file() or _touched(site_id):
        return None
    try:
        bundled = _zip_table(archive)
        if any(_revision_table(site_id, revision) == bundled for revision in history):
            return None
    except (intake.IntakeError, OSError):
        return None
    source = found.get("source") if isinstance(found.get("source"), dict) else {"kind": "demo", "key": key}
    return intake.import_zip_file(archive, "demo", source, key, None, stem, site_id=site_id)
