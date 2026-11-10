import os
import sys
from pathlib import Path

DEFAULT_PORT = 8280
DEFAULT_HOST_PORT = 8281
DEFAULT_ORIGINS = (
    "http://localhost:5280",
    "http://127.0.0.1:5280",
    "http://localhost:5281",
    "http://127.0.0.1:5281",
    "http://127.0.0.1:8280",
    "http://localhost:8280",
    "tauri://localhost",
    "http://tauri.localhost",
)
DEFAULT_FORMWEB_URL = "http://127.0.0.1:8240"


def frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def backend_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def repo_root() -> Path:
    return backend_dir().parent


def resource_dir() -> Path:
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return repo_root()


def port() -> int:
    raw = os.environ.get("FORMPUBLISHER_PORT", "").strip()
    try:
        value = int(raw) if raw else DEFAULT_PORT
    except ValueError:
        return DEFAULT_PORT
    return value if 0 < value < 65536 else DEFAULT_PORT


def host_port() -> int:
    raw = os.environ.get("FORMPUBLISHER_HOST_PORT", "").strip()
    try:
        value = int(raw) if raw else DEFAULT_HOST_PORT
    except ValueError:
        return DEFAULT_HOST_PORT
    return value if 0 < value < 65536 else DEFAULT_HOST_PORT


def host_origin() -> str:
    return f"http://127.0.0.1:{host_port()}"


def origins() -> list[str]:
    raw = os.environ.get("FORMPUBLISHER_ORIGINS", "").strip()
    if not raw:
        return list(DEFAULT_ORIGINS)
    return [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]


def formweb_url_default() -> str:
    return (os.environ.get("FORMPUBLISHER_FORMWEB_URL", "").strip() or DEFAULT_FORMWEB_URL).rstrip("/")


def home() -> Path:
    env = os.environ.get("FORMPUBLISHER_HOME", "").strip()
    base = Path(env).expanduser() if env else Path.home() / "FormPublisher"
    base.mkdir(parents=True, exist_ok=True)
    return base


def sub(name: str) -> Path:
    folder = home() / name
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def sites_dir() -> Path:
    return sub("sites")


def builds_dir() -> Path:
    return sub("builds")


def keys_dir() -> Path:
    return sub("keys")


def prepared_dir() -> Path:
    return sub("prepared")


def trash_dir() -> Path:
    return sub("trash")


def settings_file() -> Path:
    return home() / "settings.json"


def ensure_layout() -> None:
    for make in (sites_dir, builds_dir, keys_dir, prepared_dir, trash_dir):
        make()


def frontend_dist() -> Path | None:
    env = os.environ.get("FORMPUBLISHER_DIST", "").strip()
    candidates = [Path(env).expanduser()] if env else []
    candidates += [resource_dir() / "frontend_dist", repo_root() / "frontend" / "dist"]
    for candidate in candidates:
        if (candidate / "index.html").is_file():
            return candidate
    return None
