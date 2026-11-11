import json
import os
import re
import threading
from typing import Any

from app.services import paths
from app.services.bus import bus

KEYS = ("theme", "language", "density", "formwebUrl", "checks.chromePath")
LOOPBACK_URL = re.compile(r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d{1,5})?/?$")
_lock = threading.Lock()


def defaults() -> dict[str, Any]:
    return {
        "theme": "dark",
        "language": "en",
        "density": "comfortable",
        "formwebUrl": paths.formweb_url_default(),
    }


def _read() -> dict:
    try:
        data = json.loads(paths.settings_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in data.items() if k in KEYS} if isinstance(data, dict) else {}


def _write(data: dict) -> None:
    target = paths.settings_file()
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, target)


def _check(key: str, value: Any) -> Any:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    value = value.strip()
    if key == "formwebUrl":
        if not LOOPBACK_URL.match(value):
            raise ValueError("formwebUrl must be an http(s) loopback address such as http://127.0.0.1:8240")
        return value.rstrip("/")
    if key == "checks.chromePath":
        if len(value) > 1024 or "\x00" in value or not os.path.isabs(value):
            raise ValueError("checks.chromePath must be the absolute path of a Chrome executable")
        return value
    if len(value) > 64:
        raise ValueError(f"{key} is too long")
    return value


def get() -> dict:
    with _lock:
        return {**defaults(), **_read()}


def value(key: str, default: Any = None) -> Any:
    return get().get(key, default)


def update(patch: dict) -> dict:
    if not isinstance(patch, dict):
        raise ValueError("settings must be an object")
    unknown = sorted(k for k in patch if k not in KEYS)
    if unknown:
        raise ValueError(f"unknown settings: {', '.join(unknown)}")
    with _lock:
        stored = _read()
        for key, item in patch.items():
            if item is None:
                stored.pop(key, None)
            else:
                stored[key] = _check(key, item)
        _write(stored)
        merged = {**defaults(), **stored}
    bus.emit("settings.changed", settings=merged)
    return merged
