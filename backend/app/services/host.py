import asyncio
import json
import mimetypes
import re
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

THROTTLES = {"none": (0.0, 0), "fast": (0.04, 1500 * 1024), "slow": (0.15, 200 * 1024)}
THEMES = ("auto", "dark", "light")
MOTIONS = ("auto", "reduce")
THROTTLE_CHUNK = 16 * 1024
FREE_CHUNK = 64 * 1024
PROBE_ROUTE = "/__fp/probe.js"
BASE_HEADERS = [
    (b"cache-control", b"no-store"),
    (b"x-content-type-options", b"nosniff"),
    (b"referrer-policy", b"strict-origin-when-cross-origin"),
]
MIME = {
    ".html": "text/html",
    ".css": "text/css",
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".json": "application/json",
    ".webmanifest": "application/manifest+json",
    ".xml": "application/xml",
    ".txt": "text/plain",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".avif": "image/avif",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
    ".woff": "font/woff",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".pdf": "application/pdf",
}
CHARSET_EXT = (".html", ".css", ".js", ".mjs", ".json", ".webmanifest", ".xml", ".txt", ".svg")
HEAD_RE = re.compile(rb"<head(?=[\s>/])[^>]*>", re.I)
HTML_RE = re.compile(rb"<html(?=[\s>/])[^>]*>", re.I)
DOCTYPE_RE = re.compile(rb"<!doctype[^>]*>", re.I)
RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")
REDIRECT_STATUSES = (200, 301, 302, 307, 308)
LOCATION_SAFE = "/:?&=#%@+,;~!$'()*[]-._"
SITEMAP_LINE = re.compile(r"^\s*sitemap\s*:\s*(\S+)", re.I | re.M)
_redirect_cache: dict[str, tuple[int, list]] = {}
_state: dict = {"mount": None, "generation": 0}


@dataclass(frozen=True)
class Serving:
    root: Path
    site: str | None
    revision: str | None
    probe: bool
    theme: str
    motion: str
    throttle: str
    generation: int
    base: str = ""


def mount(root: Path, site: str | None, revision: str | None, probe: bool, theme: str, motion: str, throttle: str) -> Serving:
    if theme not in THEMES:
        raise ValueError("theme must be auto, dark or light")
    if motion not in MOTIONS:
        raise ValueError("motion must be auto or reduce")
    if throttle not in THROTTLES:
        raise ValueError("throttle must be none, fast or slow")
    if not root.is_dir():
        raise ValueError("the revision folder is missing")
    _state["generation"] += 1
    current = Serving(root.resolve(), site, revision, bool(probe), theme, motion, throttle, _state["generation"], base_path(root))
    _state["mount"] = current
    return current


def unmount() -> bool:
    had = _state["mount"] is not None
    _state["mount"] = None
    return had


def current() -> Serving | None:
    return _state["mount"]


def generation() -> int:
    return _state["generation"]


def probe_path() -> Path:
    return Path(__file__).resolve().parents[1] / "static" / "probe.js"


def content_type(path: Path) -> str:
    ext = path.suffix.lower()
    kind = MIME.get(ext)
    if kind is None:
        kind = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        return f"{kind}; charset=utf-8" if kind.startswith("text/") else kind
    return f"{kind}; charset=utf-8" if ext in CHARSET_EXT else kind


def split_request(scope) -> tuple[str, str] | None:
    raw = scope.get("raw_path")
    text = raw.decode("latin-1") if raw else quote(scope.get("path", "/"))
    text = text.partition("?")[0]
    decoded = unquote(text, errors="replace")
    if not decoded.startswith("/") or "\x00" in decoded or "\\" in decoded:
        return None
    if any(part == ".." for part in decoded.split("/")):
        return None
    return decoded, scope.get("query_string", b"").decode("latin-1")


def inside(root: Path, candidate: Path) -> Path | None:
    try:
        real = candidate.resolve()
    except (OSError, RuntimeError):
        return None
    if real != root and root not in real.parents:
        return None
    return real if real.is_file() else None


def lookup(root: Path, decoded: str) -> Path | None:
    segments = [part for part in decoded.split("/") if part and part != "."]
    if not segments:
        names = [root / "index.html"]
    else:
        rel = root.joinpath(*segments)
        if decoded.endswith("/"):
            names = [rel / "index.html"]
        else:
            names = [rel, rel / "index.html", rel.with_name(rel.name + ".html")]
    for name in names:
        found = inside(root, name)
        if found is not None:
            return found
    return None


def base_path(root: Path) -> str:
    """The folder the site is addressed under on its own host ("/shop/"), read from the Sitemap line of its robots.txt; "" at the root."""
    try:
        text = (root / "robots.txt").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    for address in SITEMAP_LINE.findall(text):
        parts = urlsplit(address)
        path = unquote(parts.path)
        if parts.scheme in ("http", "https") and parts.netloc and path.endswith("/sitemap.xml") and ".." not in path.split("/"):
            base = path[: -len("sitemap.xml")]
            return "" if base == "/" else base
    return ""


def within(base: str, decoded: str) -> str | None:
    if not base:
        return None
    if decoded.startswith(base):
        return "/" + decoded[len(base):]
    return "/" if decoded + "/" == base else None


def load_redirects(root: Path) -> list[tuple[str, str, int]]:
    target = root / "redirects.json"
    try:
        stamp = target.stat().st_mtime_ns
    except OSError:
        return []
    cached = _redirect_cache.get(str(root))
    if cached is not None and cached[0] == stamp:
        return cached[1]
    try:
        data = json.loads(target.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        data = None
    rows = data.get("redirects", data) if isinstance(data, dict) else data
    if isinstance(rows, dict):
        rows = [
            {"from": src, "to": dst.get("to"), "status": dst.get("status", 301)} if isinstance(dst, dict) else {"from": src, "to": dst, "status": 301}
            for src, dst in rows.items()
        ]
    out: list[tuple[str, str, int]] = []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            src = row.get("from", row.get("source"))
            dst = row.get("to", row.get("target"))
            status = row.get("status", 301)
            if isinstance(src, str) and isinstance(dst, str) and status in REDIRECT_STATUSES:
                out.append((src if src.endswith("*") else (src.rstrip("/") or "/"), dst, status))
    _redirect_cache[str(root)] = (stamp, out)
    return out


def match_redirect(root: Path, decoded: str) -> tuple[str, int] | None:
    rows = load_redirects(root)
    if not rows:
        return None
    plain = decoded.rstrip("/") or "/"
    for src, dst, status in rows:
        if src == plain and not src.endswith("*"):
            return dst, status
    for src, dst, status in rows:
        if not src.endswith("*"):
            continue
        prefix = src[:-1]
        if decoded.startswith(prefix):
            splat = decoded[len(prefix):]
        elif plain + "/" == prefix:
            splat = ""
        else:
            continue
        return dst.replace(":splat", splat), status
    return None


def inject(data: bytes, serving: Serving) -> bytes:
    tag = f'<script src="{PROBE_ROUTE}?theme={serving.theme}&motion={serving.motion}&gen={serving.generation}"></script>'.encode()
    pos = 0
    for pattern in (HEAD_RE, HTML_RE, DOCTYPE_RE):
        found = pattern.search(data)
        if found:
            pos = found.end()
            break
    else:
        if data.startswith(b"\xef\xbb\xbf"):
            pos = 3
    return data[:pos] + tag + data[pos:]


def parse_range(header: str | None, size: int):
    if not header:
        return None
    match = RANGE_RE.match(header.strip())
    if not match:
        return None
    first, last = match.groups()
    if not first and not last:
        return None
    if not first:
        count = int(last)
        if count == 0 or size == 0:
            return "bad"
        return max(size - count, 0), size - 1
    start = int(first)
    if start >= size:
        return "bad"
    end = min(int(last), size - 1) if last else size - 1
    if end < start:
        return None
    return start, end


async def deliver(send, method: str, status: int, headers: list, source, start: int, length: int, throttle: str) -> None:
    latency, bandwidth = THROTTLES[throttle]
    if latency:
        await asyncio.sleep(latency)
    await send({"type": "http.response.start", "status": status, "headers": BASE_HEADERS + headers})
    if method == "HEAD" or length <= 0:
        await send({"type": "http.response.body", "body": b""})
        return
    step = THROTTLE_CHUNK if bandwidth else FREE_CHUNK
    handle = None if isinstance(source, bytes) else open(source, "rb")
    began = time.monotonic()
    sent = 0
    try:
        if handle is not None:
            handle.seek(start)
        while sent < length:
            size = min(step, length - sent)
            chunk = source[start + sent:start + sent + size] if handle is None else handle.read(size)
            if not chunk:
                break
            if bandwidth:
                wait = (sent + len(chunk)) / bandwidth - (time.monotonic() - began)
                if wait > 0:
                    await asyncio.sleep(wait)
            sent += len(chunk)
            await send({"type": "http.response.body", "body": chunk, "more_body": sent < length})
        if sent < length:
            await send({"type": "http.response.body", "body": b""})
    finally:
        if handle is not None:
            handle.close()


async def plain(send, method: str, status: int, text: str, throttle: str = "none", extra: list | None = None) -> None:
    body = text.encode("utf-8")
    headers = [(b"content-type", b"text/plain; charset=utf-8"), (b"content-length", str(len(body)).encode())] + (extra or [])
    await deliver(send, method, status, headers, body, 0, len(body), throttle)


async def serve_file(send, method: str, request_headers: dict, serving: Serving, path: Path, status: int = 200) -> None:
    kind = content_type(path)
    if kind.startswith("text/html") and serving.probe:
        source = inject(path.read_bytes(), serving)
        size = len(source)
    else:
        source = path
        size = path.stat().st_size
    headers = [(b"content-type", kind.encode())]
    start, length = 0, size
    if status == 200:
        headers.append((b"accept-ranges", b"bytes"))
        wanted = parse_range(request_headers.get("range"), size)
        if wanted == "bad":
            await plain(send, method, 416, "Range not satisfiable", serving.throttle, [(b"content-range", f"bytes */{size}".encode())])
            return
        if wanted is not None:
            start, end = wanted
            length = end - start + 1
            status = 206
            headers.append((b"content-range", f"bytes {start}-{end}/{size}".encode()))
    headers.append((b"content-length", str(length).encode()))
    await deliver(send, method, status, headers, source, start, length, serving.throttle)


async def serve_missing(send, method: str, request_headers: dict, serving: Serving) -> None:
    page = inside(serving.root, serving.root / "404.html")
    if page is not None:
        await serve_file(send, method, request_headers, serving, page, 404)
        return
    page = inside(serving.root, serving.root / "404" / "index.html")
    if page is not None:
        source = re.sub(rb'((?:href|src|poster|action)=")\.\./', rb"\1/", page.read_bytes())
        if serving.probe:
            source = inject(source, serving)
        headers = [(b"content-type", b"text/html; charset=utf-8"), (b"content-length", str(len(source)).encode())]
        await deliver(send, method, 404, headers, source, 0, len(source), serving.throttle)
        return
    await plain(send, method, 404, "Not found", serving.throttle)


async def serve_probe(send, method: str) -> None:
    try:
        body = probe_path().read_bytes()
    except OSError:
        await plain(send, method, 404, "Not found")
        return
    headers = [(b"content-type", b"text/javascript; charset=utf-8"), (b"content-length", str(len(body)).encode())]
    await deliver(send, method, 200, headers, body, 0, len(body), "none")


async def respond(scope, send, serving: Serving | None, probe_route: bool) -> None:
    method = scope["method"]
    parsed = split_request(scope)
    if parsed is None:
        await plain(send, method, 400, "Bad request")
        return
    decoded, query = parsed
    if probe_route and (decoded == PROBE_ROUTE or decoded.startswith("/__fp/")):
        if decoded == PROBE_ROUTE:
            await serve_probe(send, method)
        else:
            await plain(send, method, 404, "Not found")
        return
    if serving is None:
        await plain(send, method, 503, "No site is mounted. Open a site in FormPublisher to preview it here.")
        return
    request_headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
    found = lookup(serving.root, decoded)
    if found is None:
        inner = within(serving.base, decoded)
        found = lookup(serving.root, inner) if inner is not None else None
    if found is not None:
        await serve_file(send, method, request_headers, serving, found)
        return
    hit = match_redirect(serving.root, decoded)
    if hit is not None:
        target, status = hit
        if status == 200:
            local = None if target.startswith(("http://", "https://")) else lookup(serving.root, unquote(target.partition("?")[0]))
            if local is not None:
                await serve_file(send, method, request_headers, serving, local)
                return
        else:
            where = target if (not query or "?" in target) else f"{target}?{query}"
            await plain(send, method, status, "", serving.throttle, [(b"location", quote(where, safe=LOCATION_SAFE).encode("latin-1"))])
            return
    await serve_missing(send, method, request_headers, serving)
