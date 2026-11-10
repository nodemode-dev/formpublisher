import threading

from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from app.services import intake, paths

router = APIRouter(prefix="/api/demo", tags=["demo"])

_lock = threading.Lock()
DEMO_KEY ="demo:northwind-notes"
DEMO_SOURCE = "Bundled sample site"


def _existing() -> dict | None:
    for record in intake.list_sites():
        source = record.get("source")
        if isinstance(source, dict) and source.get("kind") == "demo" and source.get("key") == DEMO_KEY:
            return record
    return None


def _open_sample() -> dict:
    with _lock:
        found = _existing()
        if found is not None:
            return {"site": found, "created": False}
        archive = paths.resource_dir() / "demo" / "sample-site.zip"
        if not archive.is_file():
            raise intake.IntakeError("the bundled sample site is missing from this install", 404)
        record = intake.import_zip_file(archive, "demo", {"kind": "demo", "key": DEMO_KEY, "path": DEMO_SOURCE}, DEMO_KEY, None, "northwind-notes")
        return {"site": record, "created": True}


@router.post("/sample")
async def open_sample():
    return await run_in_threadpool(_open_sample)
