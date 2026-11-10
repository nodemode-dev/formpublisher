from fastapi import APIRouter
from pydantic import BaseModel

from app.services import host, intake, paths
from app.services.bus import bus

router = APIRouter(prefix="/api/host", tags=["host"])


class MountBody(BaseModel):
    site: str
    revision: str | None = None
    probe: bool = False
    theme: str = "auto"
    motion: str = "auto"
    throttle: str = "none"


def _describe(serving: host.Serving | None) -> dict:
    origin = paths.host_origin()
    if serving is None:
        return {"mounted": False, "generation": host.generation(), "origin": origin, "url": None}
    return {
        "mounted": True,
        "site": serving.site,
        "revision": serving.revision,
        "probe": serving.probe,
        "theme": serving.theme,
        "motion": serving.motion,
        "throttle": serving.throttle,
        "generation": serving.generation,
        "origin": origin,
        "url": f"{origin}/",
    }


@router.post("/mount")
def mount_site(body: MountBody):
    root = intake.revision_root(body.site, body.revision)
    serving = host.mount(root, body.site, root.name, body.probe, body.theme, body.motion, body.throttle)
    bus.emit("host", mounted=True, site=body.site, revision=root.name, generation=serving.generation)
    return {"url": f"{paths.host_origin()}/", "generation": serving.generation, "origin": paths.host_origin()}


@router.get("")
def get_host():
    return _describe(host.current())


@router.delete("/mount")
def unmount_site():
    host.unmount()
    bus.emit("host", mounted=False, generation=host.generation())
    return _describe(None)
