import asyncio
import hashlib
import json
import os
import stat
import struct
import zipfile
from pathlib import Path

from conftest import asgi_call

SITE_PAGES = {
    "index.html": b"<!doctype html><html><body><h1>Home</h1></body></html>",
    "about/index.html": b"<!doctype html><html><body><h1>About</h1></body></html>",
    "css/site.css": b"body { color: #222; }\n",
}


def with_query(app, query: str):
    async def wrapped(scope, receive, send):
        await app({**scope, "query_string": query.encode()}, receive, send)

    return wrapped


def call(method: str, path: str, body=None, headers: dict | None = None, keyed: bool = True) -> tuple[int, dict]:
    from app.main import app
    from app.services import window_key

    sent = dict(headers or {})
    raw = b""
    if isinstance(body, (bytes, bytearray)):
        raw = bytes(body)
    elif body is not None:
        raw = json.dumps(body).encode("utf-8")
        sent.setdefault("content-type", "application/json")
    if keyed and method not in ("GET", "HEAD", "OPTIONS"):
        sent[window_key.HEADER] = window_key.LOCAL_KEY
    path, _, query = path.partition("?")
    status, _, payload = asyncio.run(asgi_call(with_query(app, query), method, path, raw, sent))
    try:
        data = json.loads(payload) if payload else None
    except ValueError:
        data = {"raw": payload}
    return status, data


def raw_get(path: str) -> tuple[int, dict, bytes]:
    from app.main import app

    return asyncio.run(asgi_call(app, "GET", path))


def write_zip(path: Path, files: dict, prefix: str = "") -> Path:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(prefix + name, data)
    return path


def zip_bytes(tmp_path: Path, files: dict, name: str = "site.zip") -> bytes:
    return write_zip(tmp_path / name, files).read_bytes()


def import_path(path: Path, name: str | None = None) -> tuple[int, dict]:
    body = {"path": str(path)}
    if name is not None:
        body["name"] = name
    return call("POST", "/api/sites/import", body)


def receive(data: bytes, project: str | None = None, name: str | None = None, kind: str = "application/zip") -> tuple[int, dict]:
    headers = {"content-type": kind}
    if project is not None:
        headers["x-formweb-project"] = project
    if name is not None:
        headers["x-formweb-site-name"] = name
    return call("POST", "/api/receive/formweb", data, headers, keyed=False)


def tree_digest(root: Path) -> dict:
    out = {}
    for current, _dirs, names in os.walk(root):
        for n in names:
            p = Path(current) / n
            out[p.relative_to(root).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def site_tree(site_id: str, revision: str) -> Path:
    from app.services import paths

    return paths.sites_dir() / site_id / revision


def symlink_zip(path: Path) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("index.html", SITE_PAGES["index.html"])
        info = zipfile.ZipInfo("link.html")
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, "/etc/passwd")
    return path


def encrypted_flag_zip(path: Path) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("index.html", SITE_PAGES["index.html"])
    data = bytearray(path.read_bytes())
    for signature, offset in ((b"PK\x03\x04", 6), (b"PK\x01\x02", 8)):
        at = data.find(signature)
        flags = struct.unpack_from("<H", data, at + offset)[0]
        struct.pack_into("<H", data, at + offset, flags | 0x1)
    path.write_bytes(bytes(data))
    return path


def inflated_size_zip(path: Path, declared: list[int]) -> Path:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_STORED) as archive:
        archive.writestr("index.html", SITE_PAGES["index.html"])
        for i in range(len(declared)):
            archive.writestr(f"big-{i}.bin", b"x")
    data = bytearray(path.read_bytes())
    at = 0
    sizes = iter([None] + declared)
    while True:
        at = data.find(b"PK\x01\x02", at)
        if at < 0:
            break
        size = next(sizes)
        if size is not None:
            struct.pack_into("<I", data, at + 24, size)
        at += 4
    path.write_bytes(bytes(data))
    return path


def multipart_upload(filename: str, payload: bytes, name: str | None = None) -> tuple[bytes, dict]:
    boundary = "xBOUNDARYx"
    parts = b""
    if name is not None:
        parts += f'--{boundary}\r\nContent-Disposition: form-data; name="name"\r\n\r\n{name}\r\n'.encode()
    parts += f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: application/zip\r\n\r\n'.encode()
    parts += payload + f"\r\n--{boundary}--\r\n".encode()
    return parts, {"content-type": f"multipart/form-data; boundary={boundary}"}
