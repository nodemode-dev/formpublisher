import asyncio
import base64
import hashlib
import json
import re
from pathlib import Path

from conftest import BACKEND, asgi_call

VERSION_FILE = BACKEND / "app" / "__init__.py"


def declared_version() -> str:
    text = VERSION_FILE.read_text(encoding="utf-8")
    return re.search(r"__version__\s*=\s*[\"']([^\"']+)[\"']", text).group(1)


def local_key() -> str:
    from app.services import window_key

    return window_key.LOCAL_KEY


def call(method: str, path: str, body=None, headers: dict | None = None, key: str | None = "local", raw: bytes | None = None):
    from app.main import app
    from app.services import window_key

    sent = dict(headers or {})
    if key == "local":
        sent[window_key.HEADER] = local_key()
    elif key is not None:
        sent[window_key.HEADER] = key
    data = raw if raw is not None else (json.dumps(body).encode("utf-8") if body is not None else b"")
    if data:
        sent.setdefault("content-type", "application/json")
    status, out_headers, payload = asyncio.run(asgi_call(app, method, path, data, sent))
    try:
        parsed = json.loads(payload) if payload else None
    except ValueError:
        parsed = None
    return status, out_headers, parsed, payload


def fingerprint(raw: bytes) -> str:
    return "SHA256:" + base64.b64encode(hashlib.sha256(raw).digest()).decode("ascii").rstrip("=")


def pem_body(pem: bytes) -> str:
    lines = pem.decode("ascii").strip().splitlines()
    return "".join(line for line in lines if not line.startswith("-----"))


def keys_folder(home: Path) -> Path:
    return home / "keys"


def host_call(method: str, path: str, headers: dict | None = None, host: str | None = None):
    from app.host import app as host_app
    from app.services import paths
    from conftest import asgi_call as raw_call

    sent = {"host": host or f"127.0.0.1:{paths.host_port()}"}
    sent.update(headers or {})
    return asyncio.run(raw_call(host_app, method, path, b"", sent))


class TempKeyring:
    priority = 5

    def __init__(self, folder: Path) -> None:
        import keyring.backend

        store = folder / "store.json"

        class Backend(keyring.backend.KeyringBackend):
            priority = 5

            def _all(self):
                return json.loads(store.read_text(encoding="utf-8")) if store.is_file() else {}

            def get_password(self, service, username):
                return self._all().get(f"{service}\n{username}")

            def set_password(self, service, username, password):
                data = self._all()
                data[f"{service}\n{username}"] = password
                store.write_text(json.dumps(data), encoding="utf-8")

            def delete_password(self, service, username):
                data = self._all()
                data.pop(f"{service}\n{username}", None)
                store.write_text(json.dumps(data), encoding="utf-8")

        self.store = store
        self.backend = Backend()

    def entries(self) -> dict:
        return json.loads(self.store.read_text(encoding="utf-8")) if self.store.is_file() else {}
