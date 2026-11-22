import base64
import hashlib
import hmac
import json
import os
import re
import secrets
from pathlib import Path

from app.services import paths

HEADER = "x-formpublisher-key"
DESKTOP_ENV = "FORMPUBLISHER_DESKTOP"
LINE = "formpublisher-window-key: "
KEY_FILE = "engine.key"
REFUSED = "Only the FormPublisher window, its command line or its MCP server can do this."
READS = ("GET", "HEAD", "OPTIONS")
OPEN = ("/api/receive/formweb", "/api/window/key")
WINDOW_KEY = secrets.token_urlsafe(32)
LOCAL_KEY = secrets.token_urlsafe(32)
INLINE_SCRIPT = re.compile(rb"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", re.DOTALL | re.IGNORECASE)

_policy: dict[str, tuple[float, str]] = {}


def desktop() -> bool:
    return os.environ.get(DESKTOP_ENV) == "1"


def announce() -> None:
    if desktop():
        print(f"{LINE}{WINDOW_KEY}", flush=True)


def _same(given: str, key: str) -> bool:
    return hmac.compare_digest(given.encode("utf-8"), key.encode("utf-8"))


def valid(value) -> bool:
    return isinstance(value, str) and bool(value) and (_same(value, WINDOW_KEY) or _same(value, LOCAL_KEY))


def is_open(path: str) -> bool:
    return path in OPEN


def claim(origin: str | None) -> str | None:
    if desktop() or not origin or origin.rstrip("/") not in paths.origins():
        return None
    return WINDOW_KEY


def key_file() -> Path:
    return paths.home() / KEY_FILE


def write_key_file() -> None:
    target = key_file()
    temp = target.with_name(f"{KEY_FILE}.{os.getpid()}.tmp")
    handle = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(handle, "w", encoding="utf-8") as out:
        json.dump({"pid": os.getpid(), "key": LOCAL_KEY}, out)
    os.replace(temp, target)


def remove_key_file() -> None:
    target = key_file()
    try:
        record = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if isinstance(record, dict) and record.get("pid") == os.getpid():
        target.unlink(missing_ok=True)


def read_key_file() -> str:
    try:
        record = json.loads(key_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    key = record.get("key") if isinstance(record, dict) else None
    return key if isinstance(key, str) else ""


def _script_hashes(index: Path) -> str:
    try:
        stamp = index.stat().st_mtime
        kept = _policy.get(str(index))
        if kept and kept[0] == stamp:
            return kept[1]
        found = INLINE_SCRIPT.findall(index.read_bytes())
    except OSError:
        return ""
    hashes = " ".join(f"'sha256-{base64.b64encode(hashlib.sha256(body).digest()).decode()}'" for body in found if body.strip())
    _policy[str(index)] = (stamp, hashes)
    return hashes


def content_policy(index: Path) -> str:
    port = paths.port()
    host = paths.host_port()
    frames = f"http://127.0.0.1:{host} http://localhost:{host}"
    scripts = " ".join(part for part in ("'self'", _script_hashes(index)) if part)
    return "; ".join(
        (
            "default-src 'self'",
            f"script-src {scripts}",
            "style-src 'self' 'unsafe-inline'",
            f"img-src 'self' data: blob: {frames}",
            "font-src 'self' data:",
            f"connect-src 'self' ws://127.0.0.1:{port} ws://localhost:{port} ipc: http://ipc.localhost",
            f"frame-src {frames}",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",
        )
    )


class WindowKeyGuard:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http" or scope.get("method") in READS or is_open(str(scope.get("path", ""))):
            await self.app(scope, receive, send)
            return
        given = next((v.decode("latin-1") for k, v in scope.get("headers", []) if k.decode("latin-1").lower() == HEADER), None)
        if valid(given):
            await self.app(scope, receive, send)
            return
        body = json.dumps({"detail": REFUSED, "code": "forbidden"}).encode("utf-8")
        await send({"type": "http.response.start", "status": 403, "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})
