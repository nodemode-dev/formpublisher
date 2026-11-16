import re
import threading
from pathlib import Path

from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from app.services import demo_refresh, intake, paths

router = APIRouter(prefix="/api/demo", tags=["demo"])

_lock = threading.Lock()
DEMO_KEY ="demo:northwind-notes"
DEMO_SOURCE = "Bundled sample site"
DEMO_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,40}")


def _existing(key: str) -> dict | None:
    for record in intake.list_sites():
        source = record.get("source")
        if isinstance(source, dict) and source.get("kind") == "demo" and source.get("key") == key:
            return record
    return None


def _open(key: str, archive: Path, stem: str, missing: str) -> dict:
    with _lock:
        found = _existing(key)
        if found is not None:
            updated = demo_refresh.refresh(found, archive, key, stem)
            return {"site": updated or found, "created": False, "updated": updated is not None}
        if not archive.is_file():
            raise intake.IntakeError(missing, 404)
        record = intake.import_zip_file(archive, "demo", {"kind": "demo", "key": key, "path": DEMO_SOURCE}, key, None, stem)
        return {"site": record, "created": True}


def _open_sample() -> dict:
    return _open(DEMO_KEY, paths.resource_dir() / "demo" / "sample-site.zip", "northwind-notes", "the bundled sample site is missing from this install")


def _open_bundled(demo_id: str) -> dict:
    if not DEMO_ID.fullmatch(demo_id):
        raise intake.IntakeError("that is not a demo id", 404)
    return _open(f"demo:{demo_id}", paths.resource_dir() / "demo" / "sites" / f"{demo_id}.zip", demo_id, "that demo is missing from this install")


@router.post("/sample")
async def open_sample():
    return await run_in_threadpool(_open_sample)


@router.post("/open/{demo_id}")
async def open_bundled(demo_id: str):
    return await run_in_threadpool(_open_bundled, demo_id)
