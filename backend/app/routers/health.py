from fastapi import APIRouter, Request

from app import __version__
from app.services import paths
from app.services.bus import bus

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health(request: Request):
    state = request.app.state
    return {
        "ok": True,
        "app": "formpublisher",
        "version": __version__,
        "api": "1",
        "home": str(paths.home()),
        "frozen": paths.frozen(),
        "routers": getattr(state, "routers", []),
        "routerErrors": getattr(state, "router_errors", {}),
        "liveClients": bus.clients(),
        "frontend": bool(paths.frontend_dist()),
        "hostPort": paths.host_port(),
    }
