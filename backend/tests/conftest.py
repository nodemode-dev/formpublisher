import asyncio
import json
import os
import sys
import zipfile
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
DEMO = REPO / "demo"
sys.path.insert(0, str(BACKEND))


def core_path() -> Path | None:
    env = os.environ.get("FORMPUBLISHER_FORMWEB_CORE", "").strip()
    name = "formweb-core.exe" if os.name == "nt" else "formweb-core"
    for candidate in ([Path(env)] if env else []) + [BACKEND / "bin" / name, REPO / "vendor" / "formweb-native" / "target" / "release" / name]:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None


def system_path() -> str:
    if os.name == "nt":
        return str(Path(os.environ.get("SystemRoot") or "C:\\Windows") / "System32")
    return "/usr/bin:/bin"


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    core_env = os.environ.get("FORMPUBLISHER_FORMWEB_CORE", "").strip()
    if core_env:
        monkeypatch.setenv("FORMPUBLISHER_FORMWEB_CORE", str(Path(core_env).expanduser().resolve()))
    user = tmp_path / "user"
    user.mkdir()
    for name in ("HOME", "USERPROFILE"):
        monkeypatch.setenv(name, str(user))
    monkeypatch.setenv("PATH", system_path())
    monkeypatch.setenv("PYTHON_KEYRING_BACKEND", "keyring.backends.fail.Keyring")
    for name in ("CODEX_HOME", "CLAUDE_CONFIG_DIR", "CURSOR_CONFIG_DIR", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME", "APPDATA", "LOCALAPPDATA"):
        monkeypatch.setenv(name, str(user / name.lower()))
    for name in ("FORMMCP_BIN", "FORMPUBLISHER_LAUNCHER", "APPIMAGE"):
        monkeypatch.delenv(name, raising=False)
    folder = tmp_path / "home"
    monkeypatch.setenv("FORMPUBLISHER_HOME", str(folder))
    monkeypatch.setenv("FORMPUBLISHER_PORT", "18299")
    monkeypatch.setenv("FORMPUBLISHER_FORMWEB_URL", "http://127.0.0.1:18298")
    monkeypatch.delenv("FORMPUBLISHER_URL", raising=False)
    from app.services import paths

    paths.ensure_layout()
    return folder


@pytest.fixture
def client():
    from app.cli import Client

    return Client(in_process=True)


@pytest.fixture
def core(monkeypatch):
    found = core_path()
    if found is None:
        if os.environ.get("FORMPUBLISHER_REQUIRE_CORE") == "1":
            pytest.fail("formweb-core is not built; run ./setup/install_compiler")
        pytest.skip("formweb-core is not built; run ./setup/install_compiler")
    monkeypatch.setenv("FORMPUBLISHER_FORMWEB_CORE", str(found))
    return found


def starter_site(core: Path, name: str = "Test starter") -> dict:
    from app.services.compile import Session

    with Session(core) as session:
        return session.call("new", {"name": name})["site"]


def write_fweb(path: Path, site: dict, version: int) -> Path:
    envelope = {"format": "com.nodemode.formweb", "version": version, "site": site, "assets": []}
    if version == 1:
        path.write_text(json.dumps(envelope), encoding="utf-8")
    else:
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("project.json", json.dumps(envelope))
    return path


def broken_site(tmp_path: Path) -> Path:
    folder = tmp_path / "broken"
    with zipfile.ZipFile(DEMO / "sites" / "lowlight.zip") as archive:
        archive.extractall(folder)
    page = folder / "index.html"
    page.write_text(page.read_text(encoding="utf-8").replace("</body>", '<a href="/no-such-page/">gone</a></body>', 1), encoding="utf-8")
    return folder


async def asgi_call(app, method: str, path: str, body: bytes = b"", headers: dict | None = None, client_host: str = "127.0.0.1") -> tuple[int, dict, bytes]:
    from app.services import paths

    sent = {"done": False}
    raw_headers = [(b"host", f"127.0.0.1:{paths.port()}".encode())]
    raw_headers += [(k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in (headers or {}).items()]
    if body:
        raw_headers.append((b"content-length", str(len(body)).encode()))
    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": method, "scheme": "http",
        "path": path, "raw_path": path.encode(), "query_string": b"", "headers": raw_headers,
        "client": (client_host, 50123), "server": ("127.0.0.1", paths.port()), "root_path": "",
    }

    async def receive():
        if sent["done"]:
            await asyncio.sleep(3600)
        sent["done"] = True
        return {"type": "http.request", "body": body, "more_body": False}

    status, out_headers, chunks = 0, {}, []

    async def send(message):
        nonlocal status, out_headers
        if message["type"] == "http.response.start":
            status = message["status"]
            out_headers = {k.decode("latin-1"): v.decode("latin-1") for k, v in message.get("headers", [])}
        elif message["type"] == "http.response.body":
            chunks.append(message.get("body", b""))

    await app(scope, receive, send)
    return status, out_headers, b"".join(chunks)
