import json
import os
import sys
from datetime import datetime, timezone
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
        # The engine serves the built window itself, so its own origin is allowed on whatever port it runs.
        own = (f"http://127.0.0.1:{port()}", f"http://localhost:{port()}")
        return list(dict.fromkeys((*DEFAULT_ORIGINS, *own)))
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


def inbox_dir() -> Path:
    return sub("inbox")


def settings_file() -> Path:
    return home() / "settings.json"


def engine_file() -> Path:
    """Where the running engine announces itself: engine.json in the data folder."""
    return home() / "engine.json"


def write_engine_file(version: str) -> None:
    """Write engine.json atomically with the port this engine serves on, its pid, version and start time."""
    record = {
        "app": "formpublisher",
        "port": port(),
        "pid": os.getpid(),
        "version": version,
        "started": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    target = engine_file()
    temp = target.with_name(f"engine.json.{os.getpid()}.tmp")
    temp.write_text(json.dumps(record), encoding="utf-8")
    os.replace(temp, target)


def remove_engine_file() -> None:
    """Remove engine.json only when it still names this process."""
    target = engine_file()
    try:
        record = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if isinstance(record, dict) and record.get("pid") == os.getpid():
        target.unlink(missing_ok=True)


def ensure_layout() -> None:
    for make in (sites_dir, builds_dir, keys_dir, prepared_dir, trash_dir, inbox_dir):
        make()


def frontend_dist() -> Path | None:
    env = os.environ.get("FORMPUBLISHER_DIST", "").strip()
    candidates = [Path(env).expanduser()] if env else []
    candidates += [resource_dir() / "frontend_dist", repo_root() / "frontend" / "dist"]
    for candidate in candidates:
        if (candidate / "index.html").is_file():
            return candidate
    return None
