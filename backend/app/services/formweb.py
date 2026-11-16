import os
import tempfile
import time
from pathlib import Path
from urllib.parse import quote

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
    return _download("/api/export", ".zip", "export")


def _download(route: str, suffix: str, what: str) -> tuple[Path, str]:
    url = base_url()
    handle, name = tempfile.mkstemp(prefix="formpublisher-formweb-", suffix=suffix)
    target = Path(name)
    total = 0
    try:
        with os.fdopen(handle, "wb") as out, _client(READ_TIMEOUT) as client:
            with client.stream("GET", f"{url}{route}") as res:
                if res.status_code == 404 and what == "project":
                    raise FormwebError("FormWeb has no saved project with that id", 404, "project-missing")
                if res.status_code != 200:
                    raise FormwebError(f"FormWeb answered {res.status_code} for its {what}", 502, "formweb-refused")
                for chunk in res.iter_bytes(1024 * 1024):
                    total += len(chunk)
                    if total > intake.MAX_ZIP_BYTES:
                        raise FormwebError(f"FormWeb's {what} is larger than 512 MiB", 413)
                    out.write(chunk)
    except httpx2.HTTPError as exc:
        target.unlink(missing_ok=True)
        raise FormwebError(f"FormWeb is not reachable at {url} ({type(exc).__name__})", 502, "formweb-unreachable") from exc
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return target, url


def project_id() -> str | None:
    try:
        with _client(PROBE_TIMEOUT) as client:
            res = client.get(f"{base_url()}/api/access")
        data = res.json() if res.status_code == 200 else None
    except (httpx2.HTTPError, ValueError):
        return None
    value = data.get("projectId") if isinstance(data, dict) else None
    return value.strip()[:200] if isinstance(value, str) and value.strip() else None


def import_current(name: str | None = None) -> dict:
    project = project_id()
    archive, url = download_export()
    try:
        return intake.import_formweb_zip(archive, f"receive:{project}" if project else url, name)
    finally:
        archive.unlink(missing_ok=True)


def _clean_id(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()[:200]
    return text if text and "/" not in text and "\\" not in text and not text.startswith(".") else None


def projects() -> dict:
    url = base_url()
    try:
        with _client(READ_TIMEOUT) as client:
            res = client.get(f"{url}/api/projects")
    except httpx2.HTTPError as exc:
        raise FormwebError(f"FormWeb is not reachable at {url} ({type(exc).__name__})", 502, "formweb-unreachable") from exc
    if res.status_code not in (200, 404):
        raise FormwebError(f"FormWeb answered {res.status_code} for its projects", 502, "formweb-refused")
    try:
        data = res.json() if res.status_code == 200 else {}
    except ValueError as exc:
        raise FormwebError("FormWeb returned a projects list that is not JSON") from exc
    rows = data.get("projects") if isinstance(data, dict) else None
    saved = []
    for row in rows if isinstance(rows, list) else []:
        pid = _clean_id(row.get("id")) if isinstance(row, dict) else None
        if pid is None:
            continue
        name = row.get("name")
        updated = row.get("updatedAt")
        saved.append({"id": pid, "name": name.strip()[:160] if isinstance(name, str) and name.strip() else None, "updatedAt": updated if isinstance(updated, str) else None, "saved": True, "open": False})
    current = project_id()
    found = next((row for row in saved if row["id"] == current), None) if current else None
    first = {**found, "open": True} if found else {"id": current, "name": None, "updatedAt": None, "saved": False, "open": True}
    return {"url": url, "open": current, "projects": [first] + [row for row in saved if row is not found]}


def import_project(project: str | None, name: str | None = None) -> dict:
    if project is None or project == project_id():
        return import_current(name)
    pid = _clean_id(project)
    if pid is None:
        raise FormwebError("FormWeb has no saved project with that id", 404, "project-missing")
    envelope, _url = _download(f"/api/projects/{quote(pid, safe='')}/file", ".fweb", "project")
    try:
        return intake.import_fweb_file(envelope, {"kind": "formweb", "url": f"receive:{pid}"}, f"formweb:receive:{pid}", name, "formweb-project")
    finally:
        envelope.unlink(missing_ok=True)
