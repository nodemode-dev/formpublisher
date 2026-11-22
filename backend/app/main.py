import asyncio
import importlib
import logging
import pkgutil
import traceback
from contextlib import asynccontextmanager

from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import __version__, routers
from app import host as site_host
from app.services import enginelog, paths, window_key
from app.services.bus import bus
from app.services.codes import default_code
from app.services.compile import CompileError
from app.services.formweb import FormwebError
from app.services.intake import IntakeError

log = logging.getLogger("formpublisher")
CORE = ("health", "settings", "sites", "live")
MAX_BODY = 600 * 1024 * 1024


class LocalAccess:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            return await self.app(scope, receive, send)
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
        port = paths.port()
        hosts = {f"localhost:{port}", f"127.0.0.1:{port}", f"[::1]:{port}"}
        origin = headers.get("origin")
        problem = None
        if headers.get("host", "") not in hosts:
            problem = (421, "This service accepts exact loopback hostnames only.")
        elif origin is not None and origin.rstrip("/") not in paths.origins():
            problem = (403, "Origin is not allowed.")
        elif origin is None and headers.get("sec-fetch-site", "").strip().lower() == "cross-site":
            problem = (403, "Cross-site requests are not allowed.")
        elif scope["type"] == "http":
            length = headers.get("content-length", "")
            if length and (not length.isdecimal() or int(length) > MAX_BODY):
                problem = (413, "Request body exceeds the configured size limit.")
        if problem is not None:
            if scope["type"] == "websocket":
                await receive()
                return await send({"type": "websocket.close", "code": 1008})
            return await JSONResponse({"detail": problem[1], "code": default_code(problem[0])}, status_code=problem[0])(scope, receive, send)

        async def guarded_send(message):
            if message["type"] == "http.response.start":
                message["headers"] = list(message.get("headers", [])) + [
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer"),
                ]
            await send(message)

        return await self.app(scope, receive, guarded_send)


@asynccontextmanager
async def lifespan(app: FastAPI):
    bus.attach(asyncio.get_running_loop())
    paths.ensure_layout()
    from app.services import deep, inbox

    deep.attach(asyncio.get_running_loop())
    host_server, host_task = await site_host.start()
    inbox.start()
    paths.write_engine_file(__version__)
    window_key.write_key_file()
    try:
        yield
    finally:
        window_key.remove_key_file()
        paths.remove_engine_file()
        inbox.stop()
        deep.attach(None)
        await site_host.stop(host_server, host_task)


app = FastAPI(title="FormPublisher", version=__version__, lifespan=lifespan)
app.add_middleware(window_key.WindowKeyGuard)
app.add_middleware(
    CORSMiddleware,
    allow_origins=paths.origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LocalAccess)


@app.exception_handler(IntakeError)
async def intake_error(_request: Request, exc: IntakeError):
    return JSONResponse({"detail": exc.message, "code": exc.code}, status_code=exc.status)


@app.exception_handler(FormwebError)
async def formweb_error(_request: Request, exc: FormwebError):
    return JSONResponse({"detail": exc.message, "code": exc.code}, status_code=exc.status)


@app.exception_handler(CompileError)
async def compile_error(_request: Request, exc: CompileError):
    return JSONResponse({"detail": exc.message, "code": exc.code}, status_code=exc.status)


@app.exception_handler(ValueError)
async def value_error(_request: Request, exc: ValueError):
    return JSONResponse({"detail": str(exc), "code": "invalid"}, status_code=400)


@app.exception_handler(StarletteHTTPException)
async def http_error(_request: Request, exc: StarletteHTTPException):
    detail = exc.detail if isinstance(exc.detail, str) and exc.detail else HTTPStatus(exc.status_code).phrase
    return JSONResponse({"detail": detail, "code": default_code(exc.status_code)}, status_code=exc.status_code, headers=getattr(exc, "headers", None))


@app.exception_handler(RequestValidationError)
async def validation_error(_request: Request, exc: RequestValidationError):
    parts = []
    for item in exc.errors():
        where = ".".join(str(p) for p in item.get("loc", ()) if p not in ("body", "query", "path"))
        parts.append(f"{where}: {item.get('msg', 'is invalid')}" if where else str(item.get("msg", "the request is invalid")))
    return JSONResponse({"detail": "; ".join(parts) or "the request is invalid", "code": "invalid"}, status_code=422)


@app.exception_handler(Exception)
async def internal_error(_request: Request, exc: Exception):
    log.error("unhandled error\n%s", "".join(traceback.format_exception(exc)))
    kept = enginelog.attached()
    where = f"its log, {kept}" if kept else "the terminal that started it"
    return JSONResponse({"detail": f"The engine hit an unexpected problem; see {where}.", "code": "internal", "log": str(kept) if kept else None}, status_code=500)


def include_routers(target: FastAPI) -> None:
    names = [m.name for m in pkgutil.iter_modules(routers.__path__) if not m.name.startswith("_")]
    ordered = [n for n in CORE if n in names] + sorted(n for n in names if n not in CORE)
    loaded: list[str] = []
    errors: dict[str, str] = {}
    for name in ordered:
        try:
            module = importlib.import_module(f"app.routers.{name}")
        except Exception as exc:
            errors[name] = f"{type(exc).__name__}: {exc}"
            log.error("router %s failed to import\n%s", name, traceback.format_exc())
            continue
        router = getattr(module, "router", None)
        if router is None:
            continue
        target.include_router(router)
        loaded.append(name)
    target.state.routers = loaded
    target.state.router_errors = errors


include_routers(app)


@app.get("/{rel:path}", include_in_schema=False)
def frontend(rel: str):
    if rel == "api" or rel.startswith("api/"):
        return JSONResponse({"detail": "Not Found", "code": "not-found"}, status_code=404)
    dist = paths.frontend_dist()
    if dist is None:
        return JSONResponse({"detail": "The frontend is not built. Run npm run build in frontend/, or set FORMPUBLISHER_DIST.", "code": "unavailable"}, status_code=503)
    root = dist.resolve()
    target = (root / rel).resolve() if rel else root / "index.html"
    if rel and root in target.parents and target.is_file():
        cache = "public, max-age=31536000, immutable" if rel.startswith("assets/") else "no-cache"
        return FileResponse(target, headers={"Cache-Control": cache})
    index = root / "index.html"
    return FileResponse(index, headers={"Cache-Control": "no-cache", "Content-Security-Policy": window_key.content_policy(index)})
