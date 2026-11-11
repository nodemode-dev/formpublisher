import logging
import threading
import uuid

from app.services import checks, intake, package, settings
from app.services.bus import bus

log = logging.getLogger("formpublisher")
_lock = threading.Lock()


def wanted() -> dict:
    current = settings.get()
    return {"check": current.get("receive.autoCheck") is True, "build": current.get("receive.autoBuild") is True}


def run(record: dict) -> dict:
    """Run the enabled steps for a site that has just arrived; the same events as the manual actions."""
    site = record["id"]
    revision = record["revision"]
    plan = wanted()
    result: dict = {"site": site, "revision": revision, "check": None, "build": None, "error": None}
    with _lock:
        try:
            if plan["check"]:
                root = intake.revision_root(site, revision)
                problems = checks.run_static(root)
                checks.store_tier(site, revision, "static", {"problems": problems})
                summary = checks.summarize(site, revision)
                bus.emit("checks.done", run=uuid.uuid4().hex[:12], site=site, revision=revision, summary=summary, auto=True)
                result["check"] = {"errors": summary["errors"], "warnings": summary["warnings"], "infos": summary["infos"]}
            if plan["build"]:
                made = package.build(site, revision)
                result["build"] = {"id": made["id"], "created": made.get("created", True), "files": made.get("files")}
        except Exception as exc:
            log.exception("receive pipeline failed for %s", site)
            result["error"] = f"{type(exc).__name__}: {exc}"
    bus.emit("receive.pipeline", **result)
    return result


def after_receive(record: dict) -> None:
    """Start the pipeline on its own thread, so the receive answer never waits for it."""
    plan = wanted()
    if not (plan["check"] or plan["build"]):
        return
    threading.Thread(target=run, args=(record,), name="formpublisher-receive-pipeline", daemon=True).start()
