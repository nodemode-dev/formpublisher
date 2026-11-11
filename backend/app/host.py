import asyncio
import contextlib
import logging
import socket
from pathlib import Path
from typing import Awaitable, Callable

import uvicorn

from app.services import host as rules
from app.services import paths

log = logging.getLogger("formpublisher.host")


class HostServer(uvicorn.Server):
    @contextlib.contextmanager
    def capture_signals(self):
        yield


class HostApp:
    def __init__(self, get: Callable[[], rules.Serving | None], port: Callable[[], int], probe_route: bool) -> None:
        self.get = get
        self.port = port
        self.probe_route = probe_route

    async def __call__(self, scope, receive, send):
        kind = scope["type"]
        if kind == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    await send({"type": "lifespan.startup.complete"})
                else:
                    await send({"type": "lifespan.shutdown.complete"})
                    return
        if kind == "websocket":
            await receive()
            await send({"type": "websocket.close", "code": 1008})
            return
        if kind != "http":
            return
        method = scope["method"]
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
        port = self.port()
        if headers.get("host", "") not in (f"127.0.0.1:{port}", f"localhost:{port}"):
            await rules.plain(send, method, 421, "This host accepts exact loopback hostnames only.")
            return
        if method not in ("GET", "HEAD"):
            await rules.plain(send, method, 405, "Method not allowed.", "none", [(b"allow", b"GET, HEAD")])
            return
        started = False

        async def tracked(message):
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await rules.respond(scope, tracked, self.get(), self.probe_route)
        except Exception:
            log.exception("host request failed")
            if not started:
                await rules.plain(send, method, 500, "Internal error.")


app = HostApp(rules.current, paths.host_port, True)


async def _run(server: uvicorn.Server, sockets: list[socket.socket] | None) -> None:
    try:
        await server.serve(sockets=sockets)
    except (SystemExit, Exception) as exc:
        log.error("site host stopped: %r", exc)


async def _stop(server: uvicorn.Server, task: asyncio.Task) -> None:
    server.should_exit = True
    try:
        await asyncio.wait_for(asyncio.shield(task), 5)
    except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
        server.force_exit = True
        task.cancel()


async def start() -> tuple[uvicorn.Server, asyncio.Task]:
    wanted = paths.host_port()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(("127.0.0.1", wanted))
    except OSError:
        sock.close()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        log.warning("site host port %s is in use; this engine serves previews on port %s", wanted, sock.getsockname()[1])
    paths.set_host_port(sock.getsockname()[1])
    config = uvicorn.Config(app, log_level="warning", lifespan="off", access_log=False)
    server = HostServer(config)
    server.bound_socket = sock
    return server, asyncio.create_task(_run(server, [sock]))


async def stop(server: uvicorn.Server, task: asyncio.Task) -> None:
    await _stop(server, task)
    sock = getattr(server, "bound_socket", None)
    if sock is not None:
        sock.close()


async def serve_revision(root: Path) -> tuple[str, Callable[[], Awaitable[None]]]:
    folder = Path(root).resolve()
    if not folder.is_dir():
        raise ValueError("the revision folder is missing")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    serving = rules.Serving(folder, None, None, False, "auto", "auto", "none", 0)
    site = HostApp(lambda: serving, lambda: port, False)
    config = uvicorn.Config(site, log_level="warning", lifespan="off", access_log=False)
    server = HostServer(config)
    task = asyncio.create_task(_run(server, [sock]))
    for _ in range(250):
        if server.started or task.done():
            break
        await asyncio.sleep(0.02)
    if not server.started:
        server.should_exit = True
        sock.close()
        raise RuntimeError("the preview host did not start")

    async def close() -> None:
        await _stop(server, task)
        sock.close()

    return f"http://127.0.0.1:{port}", close
