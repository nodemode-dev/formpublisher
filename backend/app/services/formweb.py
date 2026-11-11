import os
import tempfile
import time
from pathlib import Path

import httpx2

from app.services import intake, settings
from app.services.codes import default_code

PROBE_TIMEOUT = 2.0
READ_TIMEOUT = 120.0


class FormwebError(Exception):
    def __init__(self, message: str, status: int = 502, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code or default_code(status)


def base_url() -> str:
    return str(settings.value("formwebUrl", "")).rstrip("/")


def _client(timeout: float) -> httpx2.Client:
    return httpx2.Client(timeout=timeout, follow_redirects=False, trust_env=False, headers={"User-Agent": "formpublisher-engine"})


def status() -> dict:
    url = base_url()
    started = time.monotonic()
    try:
        with _client(PROBE_TIMEOUT) as client:
            res = client.get(f"{url}/api/health")
        latency = round((time.monotonic() - started) * 1000)
        if res.status_code != 200:
            return {"reachable": False, "url": url, "error": f"FormWeb answered {res.status_code}", "latencyMs": latency}
        try:
            health = res.json()
        except ValueError:
            health = None
        return {"reachable": True, "url": url, "health": health, "latencyMs": latency}
    except httpx2.HTTPError as exc:
        return {"reachable": False, "url": url, "error": f"{type(exc).__name__}: {exc}" or "unreachable"}


def publications() -> dict:
    url = base_url()
    try:
        with _client(READ_TIMEOUT) as client:
            res = client.get(f"{url}/api/publications")
    except httpx2.HTTPError as exc:
        raise FormwebError(f"FormWeb is not reachable at {url} ({type(exc).__name__})", 502, "formweb-unreachable") from exc
    if res.status_code != 200:
        raise FormwebError(f"FormWeb answered {res.status_code} for its publications", 502, "formweb-refused")
    try:
        data = res.json()
    except ValueError as exc:
        raise FormwebError("FormWeb returned a publications list that is not JSON") from exc
    return data if isinstance(data, dict) else {"publications": data}


def download_export() -> tuple[Path, str]:
    url = base_url()
    handle, name = tempfile.mkstemp(prefix="formpublisher-formweb-", suffix=".zip")
    target = Path(name)
    total = 0
    try:
        with os.fdopen(handle, "wb") as out, _client(READ_TIMEOUT) as client:
            with client.stream("GET", f"{url}/api/export") as res:
                if res.status_code != 200:
                    raise FormwebError(f"FormWeb answered {res.status_code} for its export", 502, "formweb-refused")
                for chunk in res.iter_bytes(1024 * 1024):
                    total += len(chunk)
                    if total > intake.MAX_ZIP_BYTES:
                        raise FormwebError("FormWeb's export is larger than 512 MiB", 413)
                    out.write(chunk)
    except httpx2.HTTPError as exc:
        target.unlink(missing_ok=True)
        raise FormwebError(f"FormWeb is not reachable at {url} ({type(exc).__name__})", 502, "formweb-unreachable") from exc
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return target, url


def import_current(name: str | None = None) -> dict:
    archive, url = download_export()
    try:
        return intake.import_formweb_zip(archive, url, name)
    finally:
        archive.unlink(missing_ok=True)
