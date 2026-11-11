import base64
import hashlib
import json
import os
import re
import subprocess
import tempfile
import threading
import zipfile
import zlib
from pathlib import Path, PurePosixPath
from typing import Any

from app.services import paths

FORMAT = "com.nodemode.formweb"
MAX_ENVELOPE_BYTES = 128 * 1024 * 1024
MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
MAX_PROJECT_JSON_BYTES = 64 * 1024 * 1024
MAX_ASSETS = 500
SIZE_LIMITS = {"mp4": 64 * 1024 * 1024, "webm": 64 * 1024 * 1024, "woff2": 4 * 1024 * 1024, "svg": 2 * 1024 * 1024}
DEFAULT_ASSET_LIMIT = 8 * 1024 * 1024
CHUNK = 1024 * 1024
REQUEST_SECONDS = 120
MISSING = "Opening .fweb projects needs formweb-core. Run ./setup/install_compiler."
ASSET_NAME = re.compile(r"^[0-9a-f]{64}\.(png|jpg|gif|webp|svg|mp4|webm|woff2)$")
ASSET_REF = re.compile(r"/api/assets/([0-9a-f]{64}\.(?:png|jpg|gif|webp|svg|mp4|webm|woff2))")
MIME_TYPES = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
    "svg": "image/svg+xml",
    "mp4": "video/mp4",
    "webm": "video/webm",
    "woff2": "font/woff2",
}
LICENSE_KEYS = ("source", "title", "creator", "copyright", "license", "licenseUrl", "usage", "sourceUrl", "attribution")
HEAD_RE = re.compile(rb'"format"\s*:\s*"com\.nodemode\.formweb"')


class CompileError(Exception):
    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


def binary_name() -> str:
    return "formweb-core.exe" if os.name == "nt" else "formweb-core"


def core_binary() -> Path | None:
    env = os.environ.get("FORMPUBLISHER_FORMWEB_CORE", "").strip()
    candidates = [Path(env).expanduser()] if env else []
    candidates.append(paths.backend_dir() / "bin" / binary_name())
    candidates.append(paths.resource_dir() / "bin" / binary_name())
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None


def read_project_json(archive: zipfile.ZipFile) -> dict:
    infos = archive.infolist()
    if not infos or infos[0].filename != "project.json":
        raise CompileError("the .fweb archive must start with project.json")
    if infos[0].file_size > MAX_PROJECT_JSON_BYTES:
        raise CompileError("the .fweb archive project.json is larger than 64 MiB", 413)
    with archive.open(infos[0]) as stream:
        raw = stream.read(MAX_PROJECT_JSON_BYTES + 1)
    if len(raw) > MAX_PROJECT_JSON_BYTES:
        raise CompileError("the .fweb archive project.json is larger than 64 MiB", 413)
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise CompileError("the .fweb archive project.json is not valid JSON") from exc
    if not isinstance(data, dict) or data.get("format") != FORMAT or data.get("version") != 2:
        raise CompileError("the .fweb archive project.json is not a FormWeb version 2 project")
    if not isinstance(data.get("site"), dict):
        raise CompileError("the .fweb archive has no site")
    return data


def is_archive_project(path: Path) -> bool:
    """True when the file is a zip whose first member is a FormWeb version 2 project.json."""
    try:
        with zipfile.ZipFile(path) as archive:
            read_project_json(archive)
        return True
    except (CompileError, zipfile.BadZipFile, zlib.error, EOFError, NotImplementedError, RuntimeError, OSError):
        return False


def looks_like_fweb(path: Path) -> bool:
    try:
        if zipfile.is_zipfile(path):
            return is_archive_project(path)
        with open(path, "rb") as handle:
            head = handle.read(4096)
    except OSError:
        return False
    return bool(HEAD_RE.search(head))


def read_envelope(path: Path) -> dict:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise CompileError(f"cannot read {path.name}: {exc.strerror}") from exc
    if size > MAX_ENVELOPE_BYTES:
        raise CompileError("the .fweb file is larger than 128 MiB", 413)
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise CompileError("that .fweb file is not valid JSON") from exc
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise CompileError("that file is not a FormWeb project (format com.nodemode.formweb)")
    if not isinstance(data.get("site"), dict):
        raise CompileError("the .fweb file has no site")
    return data


def decode_assets(envelope: dict) -> tuple[dict[str, bytes], dict[str, dict]]:
    items = envelope.get("assets", [])
    if not isinstance(items, list) or len(items) > MAX_ASSETS:
        raise CompileError(f"the .fweb assets must be a list of at most {MAX_ASSETS} items")
    blobs: dict[str, bytes] = {}
    licences: dict[str, dict] = {}
    for item in items:
        name = item.get("id") if isinstance(item, dict) else None
        if not isinstance(name, str) or not ASSET_NAME.fullmatch(name) or item.get("encoding") != "base64" or not isinstance(item.get("content"), str):
            raise CompileError("a .fweb image entry is invalid")
        try:
            data = base64.b64decode(item["content"], validate=True)
        except (ValueError, TypeError) as exc:
            raise CompileError(f"the .fweb image {name} is not valid base64") from exc
        if hashlib.sha256(data).hexdigest() != name.split(".")[0]:
            raise CompileError(f"the .fweb image {name} does not match its digest")
        blobs[name] = data
        if isinstance(item.get("license"), dict):
            licences[name] = item["license"]
    return blobs, licences


class ArchiveAssets:
    """The assets of a version 2 archive, validated up front and copied out one at a time."""

    def __init__(self, path: Path, names: set[str]) -> None:
        self.path = path
        self.names = names

    def __contains__(self, name: object) -> bool:
        return name in self.names

    def copy(self, name: str, target: Path) -> None:
        if name not in self.names:
            raise CompileError(f"the .fweb archive does not carry {name}")
        digest = hashlib.sha256()
        try:
            with zipfile.ZipFile(self.path) as archive, archive.open("assets/" + name) as stream, open(target, "wb") as out:
                while chunk := stream.read(CHUNK):
                    digest.update(chunk)
                    out.write(chunk)
        except (zipfile.BadZipFile, zlib.error, EOFError, NotImplementedError, RuntimeError, KeyError) as exc:
            raise CompileError("the .fweb archive is not a valid, readable zip file") from exc
        if digest.hexdigest() != name.split(".")[0]:
            raise CompileError(f"the .fweb image {name} does not match its digest")


def read_archive(path: Path) -> tuple[dict, ArchiveAssets, dict[str, dict]]:
    """Validate a version 2 .fweb zip on disk and return its project.json, its assets and their licences."""
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise CompileError(f"cannot read {path.name}: {exc.strerror}") from exc
    if size > MAX_ARCHIVE_BYTES:
        raise CompileError("the .fweb file is larger than 512 MiB", 413)
    try:
        with zipfile.ZipFile(path) as archive:
            envelope = read_project_json(archive)
            listed = envelope.get("assets", [])
            if not isinstance(listed, list) or len(listed) > MAX_ASSETS:
                raise CompileError(f"the .fweb assets must be a list of at most {MAX_ASSETS} items")
            ids: list[str] = []
            licences: dict[str, dict] = {}
            for entry in listed:
                name = entry.get("id") if isinstance(entry, dict) else None
                if not isinstance(name, str) or not ASSET_NAME.fullmatch(name) or not isinstance(entry.get("mime"), str) or ("name" in entry and not isinstance(entry["name"], str)):
                    raise CompileError("a .fweb image entry is invalid")
                if entry["mime"] != MIME_TYPES[name.rsplit(".", 1)[1]]:
                    raise CompileError(f"the .fweb image {name} has the wrong media type")
                ids.append(name)
                if isinstance(entry.get("license"), dict):
                    licences[name] = entry["license"]
            if len(set(ids)) != len(ids):
                raise CompileError("the .fweb archive lists an asset more than once")
            members = archive.infolist()[1:]
            member_names = [info.filename for info in members]
            if len(set(member_names)) != len(member_names):
                raise CompileError("the .fweb archive contains duplicate entries")
            for member in member_names:
                if not member.startswith("assets/") or member[7:] not in ids:
                    raise CompileError(f"the .fweb archive contains an entry that project.json does not list: {member[:80]}")
            if len(member_names) != len(ids):
                raise CompileError("the .fweb archive is missing a listed asset")
            for info in members:
                name = info.filename[7:]
                limit = SIZE_LIMITS.get(name.rsplit(".", 1)[1], DEFAULT_ASSET_LIMIT)
                if info.file_size > limit:
                    raise CompileError(f"the .fweb image {name} is too large", 413)
                digest, counted = hashlib.sha256(), 0
                with archive.open(info) as stream:
                    while chunk := stream.read(CHUNK):
                        counted += len(chunk)
                        if counted > limit:
                            raise CompileError(f"the .fweb image {name} is too large", 413)
                        digest.update(chunk)
                if digest.hexdigest() != name.split(".")[0]:
                    raise CompileError(f"the .fweb image {name} does not match its digest")
    except (zipfile.BadZipFile, zlib.error, EOFError, NotImplementedError, RuntimeError, OSError) as exc:
        raise CompileError("the .fweb archive is not a valid, readable zip file") from exc
    return envelope, ArchiveAssets(path, set(ids)), licences


def load_project(path: Path) -> tuple[dict, Any, dict[str, dict]]:
    """Read a version 1 JSON .fweb or a version 2 zip .fweb; the assets are bytes (1) or an ArchiveAssets (2)."""
    if zipfile.is_zipfile(path):
        return read_archive(path)
    envelope = read_envelope(path)
    blobs, licences = decode_assets(envelope)
    return envelope, blobs, licences


def safe_path(value: Any) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise CompileError("the engine returned an invalid export path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in (".", "..", "") for part in value.split("/")) or ":" in value:
        raise CompileError(f"the engine returned an unsafe export path: {value!r}")
    return path


class Session:
    def __init__(self, binary: Path) -> None:
        self.binary = binary
        self.process: subprocess.Popen | None = None
        self.errors: Any = None
        self.counter = 0
        self.expired = False

    def __enter__(self) -> "Session":
        self.errors = tempfile.TemporaryFile()
        try:
            self.process = subprocess.Popen(
                [str(self.binary)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=self.errors,
                cwd=str(paths.home()),
            )
        except OSError as exc:
            self.errors.close()
            raise CompileError(f"formweb-core could not start: {exc.strerror or exc}", 500) from exc
        return self

    def __exit__(self, *_exc: object) -> None:
        process = self.process
        if process is not None:
            for stream in (process.stdin,):
                try:
                    if stream:
                        stream.close()
                except OSError:
                    pass
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            if process.stdout:
                process.stdout.close()
        if self.errors is not None:
            self.errors.close()

    def tail(self) -> str:
        try:
            self.errors.seek(0)
            return self.errors.read()[-400:].decode("utf-8", "replace").strip()
        except (OSError, ValueError):
            return ""

    def call(self, method: str, params: dict) -> Any:
        process = self.process
        if process is None or process.poll() is not None or process.stdin is None or process.stdout is None:
            raise CompileError("formweb-core stopped unexpectedly", 500)
        self.counter += 1
        request = json.dumps({"id": self.counter, "method": method, "params": params}, separators=(",", ":"))
        self.expired = False

        def expire() -> None:
            self.expired = True
            process.kill()

        timer = threading.Timer(REQUEST_SECONDS, expire)
        timer.start()
        try:
            process.stdin.write(request.encode("utf-8") + b"\n")
            process.stdin.flush()
            line = process.stdout.readline()
        except OSError as exc:
            if self.expired:
                raise CompileError(f"formweb-core did not answer {method} in {REQUEST_SECONDS} seconds", 504) from exc
            raise CompileError(f"formweb-core stopped during {method}", 500) from exc
        finally:
            timer.cancel()
        if self.expired:
            raise CompileError(f"formweb-core did not answer {method} in {REQUEST_SECONDS} seconds", 504)
        if not line:
            detail = self.tail()
            raise CompileError(f"formweb-core stopped during {method}" + (f": {detail}" if detail else ""), 500)
        try:
            reply = json.loads(line)
        except ValueError as exc:
            raise CompileError("formweb-core sent an unreadable reply", 500) from exc
        if not isinstance(reply, dict) or reply.get("id") != self.counter:
            raise CompileError("formweb-core answered out of order", 500)
        if not reply.get("ok"):
            raise CompileError(str(reply.get("error") or "formweb-core could not export this project"))
        return reply.get("result")


def bundle(files: list[dict], blobs: dict[str, bytes], licences: dict[str, dict]) -> list[dict]:
    originals = {item["path"]: item for item in files}
    access: dict = {"schemaVersion": 1, "assets": {}}
    access_file = originals.get("asset-access.json")
    if access_file:
        try:
            parsed = json.loads(access_file["content"])
            if isinstance(parsed, dict):
                access = parsed
        except (ValueError, TypeError):
            pass
    ownership = access.setdefault("assets", {})
    if not isinstance(ownership, dict):
        ownership = access["assets"] = {}
    route_file = originals.get("routes.json")
    try:
        manifest = json.loads(route_file["content"]) if route_file else []
    except (ValueError, TypeError):
        manifest = []
    rows = manifest.get("routes", []) if isinstance(manifest, dict) else manifest
    file_pages: dict[str, set] = {}
    for route in rows if isinstance(rows, list) else []:
        if not isinstance(route, dict):
            continue
        for key in (route.get("path"), route.get("stylesheet")):
            if key and route.get("page"):
                file_pages.setdefault(key, set()).add(route["page"])
    for key, pages in ownership.items():
        file_pages.setdefault(key, set()).update(pages)
    names: set[str] = set()
    out = []
    for original in files:
        if original["path"] == "asset-access.json":
            continue
        item = dict(original)
        if item.get("encoding") != "base64" and isinstance(item.get("content"), str):
            prefix = "../" * (len(PurePosixPath(item["path"]).parts) - 1)
            for name in ASSET_REF.findall(item["content"]):
                names.add(name)
                target = "assets/" + name
                owners = set(ownership.get(target, [])) | file_pages.get(item["path"], set())
                ownership[target] = sorted(owners)
                item["content"] = item["content"].replace("/api/assets/" + name, prefix + target)
        out.append(item)
    credits = []
    for name in sorted(names):
        if name not in blobs:
            raise CompileError(f"the project uses the image {name} but the .fweb file does not carry it")
        if isinstance(blobs, ArchiveAssets):
            out.append({"path": "assets/" + name, "blob": name})
        else:
            out.append({"path": "assets/" + name, "content": base64.b64encode(blobs[name]).decode(), "encoding": "base64"})
        if licences.get(name):
            credits.append((name, licences[name]))
    if credits:
        lines = ["Credits for images in this site", ""]
        for name, licence in credits:
            lines.append(f"assets/{name}")
            lines.extend(f"  {key}: {str(licence[key])[:500]}" for key in LICENSE_KEYS if licence.get(key))
            lines.append("")
        out.append({"path": "CREDITS.txt", "content": "\n".join(lines)})
    out.append({"path": "asset-access.json", "content": json.dumps(access, sort_keys=True)})
    return out


def write_files(files: list[dict], dest: Path, blobs: Any = None) -> int:
    root = dest.resolve()
    root.mkdir(parents=True, exist_ok=True)
    count = 0
    for item in files:
        rel = safe_path(item.get("path"))
        target = (root / rel).resolve()
        if root not in target.parents:
            raise CompileError(f"the engine returned an unsafe export path: {item.get('path')!r}")
        if isinstance(blobs, ArchiveAssets) and isinstance(item.get("blob"), str):
            target.parent.mkdir(parents=True, exist_ok=True)
            blobs.copy(item["blob"], target)
            count += 1
            continue
        content = item.get("content")
        if not isinstance(content, str):
            raise CompileError(f"the engine returned no content for {item.get('path')!r}")
        if item.get("encoding") == "base64":
            try:
                data = base64.b64decode(content, validate=True)
            except (ValueError, TypeError) as exc:
                raise CompileError(f"the engine returned invalid base64 for {item.get('path')!r}") from exc
        else:
            data = content.encode("utf-8")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        count += 1
    return count


def compile_fweb(envelope_path: Path, dest: Path) -> dict:
    binary = core_binary()
    if binary is None:
        raise CompileError(MISSING, 422)
    envelope, blobs, licences = load_project(envelope_path)
    site = envelope["site"]
    locale = site.get("defaultLocale") if isinstance(site.get("defaultLocale"), str) and site.get("defaultLocale") else "en"
    settings = site.get("settings") if isinstance(site.get("settings"), dict) else {}
    base = settings.get("baseUrl") if isinstance(settings.get("baseUrl"), str) and settings.get("baseUrl") else "https://example.com"
    with Session(binary) as session:
        hello = session.call("hello", {})
        session.call("load", {"site": site})
        result = session.call("export", {"locale": locale, "baseUrl": base, "formsEndpoint": "", "all": True})
    if not isinstance(result, dict) or not isinstance(result.get("files"), list):
        raise CompileError("formweb-core returned no files")
    for item in result["files"]:
        if not isinstance(item, dict):
            raise CompileError("formweb-core returned an invalid file entry")
        safe_path(item.get("path"))
    bundled = bundle(result["files"], blobs, licences)
    count = write_files(bundled, dest, blobs)
    name = site.get("name") if isinstance(site.get("name"), str) and site.get("name").strip() else None
    return {
        "name": name,
        "engine": hello.get("version") if isinstance(hello, dict) else None,
        "schemaVersion": hello.get("schemaVersion") if isinstance(hello, dict) else None,
        "locale": locale,
        "files": count,
        "assets": sum(1 for item in bundled if item["path"].startswith("assets/") and (item.get("encoding") == "base64" or "blob" in item)),
        "warnings": [str(w) for w in result.get("warnings", [])][:20] if isinstance(result.get("warnings"), list) else [],
    }
