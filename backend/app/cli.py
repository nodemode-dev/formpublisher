import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from app import __version__
from app.services.codes import default_code
from app.services import checks, formweb, fpub, intake, keys, package, paths, settings

DEEP_WAIT_SECONDS = 900


class OpError(Exception):
    def __init__(self, message: str, code: int = 1, error_code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.error_code = error_code or "invalid"

    def label(self) -> str:
        """Return the message with its error code in front, as error [code]: detail."""
        return f"error [{self.error_code}]: {self.message}"


def _detail(payload: bytes, status: int) -> str:
    try:
        body = json.loads(payload)
    except ValueError:
        body = None
    if isinstance(body, dict) and isinstance(body.get("detail"), str):
        return body["detail"]
    return f"the engine answered {status}"


def _error_code(payload: bytes, status: int) -> str:
    try:
        body = json.loads(payload)
    except ValueError:
        body = None
    if isinstance(body, dict) and isinstance(body.get("code"), str) and body["code"]:
        return body["code"]
    return default_code(status)


class Client:
    def __init__(self, url: str | None = None, in_process: bool = False) -> None:
        self.explicit = (url or os.environ.get("FORMPUBLISHER_URL") or "").rstrip("/")
        self.in_process = in_process
        self.url = ""
        self.resolved = False
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def _request(self, method: str, path: str, body: Any = None, timeout: float = 300) -> tuple[int, bytes]:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Accept": "application/json", "User-Agent": f"formpublisher-cli/{__version__}"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(f"{self.url}{path}", data=data, method=method, headers=headers)
        try:
            with self.opener.open(req, timeout=timeout) as res:
                return res.status, res.read()
        except urllib.error.HTTPError as err:
            return err.code, err.read()

    def connect(self) -> None:
        if self.resolved:
            return
        self.resolved = True
        if self.in_process:
            return
        base = self.explicit or f"http://127.0.0.1:{paths.port()}"
        self.url = base
        try:
            status, payload = self._request("GET", "/api/health", timeout=1.5)
            info = json.loads(payload) if status == 200 else None
        except (OSError, ValueError):
            info = None
        if isinstance(info, dict) and info.get("app") == "formpublisher":
            return
        if self.explicit:
            raise OpError(f"no FormPublisher engine is answering at {self.explicit}", 3, "engine-unreachable")
        self.url = ""

    def describe(self) -> dict:
        self.connect()
        if self.url:
            return {"mode": "http", "url": self.url}
        return {"mode": "in-process", "url": None}

    def call(self, method: str, path: str, body: Any = None) -> Any:
        status, payload = self._request(method, path, body)
        if status >= 400:
            raise OpError(_detail(payload, status), 3 if status >= 500 else 1, _error_code(payload, status))
        return json.loads(payload) if payload else None

    def _local(self, fn, *args):
        try:
            return fn(*args)
        except (intake.IntakeError, formweb.FormwebError) as exc:
            raise OpError(exc.message, 1, exc.code) from exc
        except ValueError as exc:
            raise OpError(str(exc), 1, "invalid") from exc

    def status(self) -> dict:
        self.connect()
        if self.url:
            health = self.call("GET", "/api/health")
            sites = self.call("GET", "/api/sites")["count"]
            web = self.call("GET", "/api/formweb/status")
        else:
            health = {"ok": True, "app": "formpublisher", "version": __version__, "api": "1", "home": str(paths.home()), "frozen": paths.frozen()}
            sites = len(intake.list_sites())
            web = formweb.status()
        return {"engine": self.describe(), "health": health, "sites": sites, "formweb": web, "settings": settings.get() if not self.url else self.call("GET", "/api/settings")}

    def sites(self) -> dict:
        self.connect()
        if self.url:
            return self.call("GET", "/api/sites")
        rows = intake.list_sites()
        return {"sites": rows, "count": len(rows)}

    def import_path(self, path: str, name: str | None = None) -> dict:
        self.connect()
        absolute = str(Path(path).expanduser().resolve())
        if self.url:
            return self.call("POST", "/api/sites/import", {"path": absolute, "name": name})
        return self._local(intake.import_path, absolute, name)

    def import_formweb(self, project: str | None = None) -> dict:
        self.connect()
        if self.url:
            return self.call("POST", "/api/formweb/import-current", {"project": project} if project else {})
        return self._local(formweb.import_project, project)

    def formweb_projects(self) -> dict:
        self.connect()
        if self.url:
            return self.call("GET", "/api/formweb/projects")
        return self._local(formweb.projects)

    def routes(self, site_id: str) -> dict:
        self.connect()
        if self.url:
            return self.call("GET", f"/api/sites/{urllib.parse.quote(site_id, safe='')}/routes")
        return self._local(intake.site_routes, site_id)

    def revisions(self, site_id: str) -> dict:
        self.connect()
        if self.url:
            return self.call("GET", f"/api/sites/{urllib.parse.quote(site_id, safe='')}/revisions")
        from app.services import revisions

        return self._local(revisions.list_revisions, site_id)

    def diff(self, site_id: str, left: str | None = None, right: str | None = None) -> dict:
        self.connect()
        if self.url:
            query = urllib.parse.urlencode({k: v for k, v in (("from", left), ("to", right)) if v})
            return self.call("GET", f"/api/sites/{urllib.parse.quote(site_id, safe='')}/diff" + (f"?{query}" if query else ""))
        from app.services import revisions

        return self._local(revisions.diff, site_id, left, right)

    def _revision(self, site_id: str, revision: str | None) -> str:
        if revision:
            return revision
        record = self.call("GET", f"/api/sites/{_q(site_id)}")
        return record.get("revision") or (record.get("revisions") or [""])[-1]

    def check(self, site_id: str, deep: bool = False, widths: list[int] | None = None, revision: str | None = None) -> dict:
        self.connect()
        if self.url:
            body: dict[str, Any] = {"site": site_id, "tiers": ["static", "deep"] if deep else ["static"]}
            if revision:
                body["revision"] = revision
            if widths:
                body["widths"] = widths
            self.call("POST", "/api/checks/run", body)
            chosen = self._revision(site_id, revision)
            deadline = time.monotonic() + DEEP_WAIT_SECONDS
            while True:
                report = self.call("GET", f"/api/checks/{_q(site_id)}/{_q(chosen)}")
                if not report.get("running") or time.monotonic() > deadline:
                    break
                time.sleep(1)
            report.pop("running", None)
            return {"site": site_id, "revision": chosen, **report}
        from app.routers import checks as route

        def run_local() -> str:
            root = intake.revision_root(site_id, revision)
            route._static(site_id, root.name, root)
            if deep:
                route._deep("cli", site_id, root.name, root, route._widths(widths), "auto")
            return root.name

        chosen = self._local(run_local)
        return {"site": site_id, "revision": chosen, **checks.report(site_id, chosen)}

    def get_checks(self, site_id: str, revision: str | None = None) -> dict:
        self.connect()
        if self.url:
            chosen = self._revision(site_id, revision)
            report = self.call("GET", f"/api/checks/{_q(site_id)}/{_q(chosen)}")
            report.pop("running", None)
            return {"site": site_id, "revision": chosen, **report}
        chosen = self._local(lambda: intake.revision_root(site_id, revision).name)
        return {"site": site_id, "revision": chosen, **checks.report(site_id, chosen)}

    def build(self, site_id: str, revision: str | None = None) -> dict:
        self.connect()
        if self.url:
            return self.call("POST", "/api/builds", {"site": site_id, "revision": revision})
        return self._local(package.build, site_id, revision)

    def builds(self) -> dict:
        self.connect()
        if self.url:
            return self.call("GET", "/api/builds")
        rows = package.list_builds()
        return {"builds": rows, "count": len(rows)}

    def save_fpub(self, build_id: str, out: str | None = None, force: bool = False) -> dict:
        self.connect()
        record = self.call("GET", f"/api/builds/{_q(build_id)}") if self.url else self._local(package.get_build, build_id)
        target = Path(out).expanduser().resolve() if out else (Path.cwd() / f"{record['site']}-{build_id}.fpub")
        if target.suffix.lower() != ".fpub":
            raise OpError("the file name must end in .fpub")
        if target.is_dir():
            raise OpError(f"{target} is a folder")
        if target.exists() and not force:
            raise OpError(f"{target} already exists; use --force to replace it")
        if not target.parent.is_dir():
            raise OpError(f"the folder {target.parent} does not exist")
        if not self.url:
            return self._local(fpub.write_file, build_id, target)
        part = target.with_name(target.name + ".part")
        try:
            req = urllib.request.Request(f"{self.url}/api/builds/{_q(build_id)}/fpub", headers={"User-Agent": f"formpublisher-cli/{__version__}"})
            try:
                with self.opener.open(req, timeout=600) as res, open(part, "wb") as out_file:
                    while True:
                        chunk = res.read(1024 * 1024)
                        if not chunk:
                            break
                        out_file.write(chunk)
            except urllib.error.HTTPError as err:
                body = err.read()
                raise OpError(_detail(body, err.code), 3 if err.code >= 500 else 1, _error_code(body, err.code)) from err
            os.replace(part, target)
        except OSError as exc:
            raise OpError(f"cannot write {target}: {exc.strerror or exc}") from exc
        finally:
            part.unlink(missing_ok=True)
        return {"build": build_id, "site": record["site"], "file": str(target), "size": target.stat().st_size, "sha256": package.sha256_file(target)}

    def keys(self) -> dict:
        self.connect()
        if self.url:
            return self.call("GET", "/api/keys")
        rows = keys.list_keys()
        return {"keys": rows, "count": len(rows)}

    def create_key(self, name: str, passphrase: str | None = None) -> dict:
        self.connect()
        if self.url:
            return self.call("POST", "/api/keys", {"name": name, "passphrase": passphrase})
        return self._local(keys.create_key, name, passphrase)

    def sign(self, build_id: str, key: str | None = None, passphrase: str | None = None) -> dict:
        self.connect()
        if not key:
            rows = self.keys()["keys"]
            if not rows:
                raise OpError("there is no signing key yet; create one with: keys --create NAME")
            if len(rows) > 1:
                raise OpError("several keys exist; name one with --key (" + ", ".join(f"{r['id']} {r.get('name', '')}" for r in rows) + ")")
            key = rows[0]["id"]
        if self.url:
            return self.call("POST", f"/api/builds/{_q(build_id)}/sign", {"key": key, "passphrase": passphrase})
        return self._local(keys.sign_build, build_id, key, passphrase)

    def verify(self, build_id: str) -> dict:
        self.connect()
        if self.url:
            return self.call("POST", f"/api/builds/{_q(build_id)}/verify", {})
        return self._local(keys.verify_build, build_id)

    def targets(self) -> dict:
        self.connect()
        if self.url:
            return self.call("GET", "/api/targets")
        from app.services import publish

        return self._local(publish.list_targets)

    def prepare(self, build_id: str, target_ids: list[str], include_model: bool = False) -> dict:
        self.connect()
        if not target_ids:
            raise OpError("name at least one target (see targets)")
        if self.url:
            return self.call("POST", "/api/publish/prepare", {"build": build_id, "targets": target_ids, "includeModel": include_model})
        from app.services import publish

        return self._local(publish.prepare, build_id, target_ids, include_model)

    def prepared(self, build_id: str) -> dict:
        self.connect()
        if self.url:
            return self.call("GET", f"/api/publish/{_q(build_id)}")
        from app.services import publish

        return self._local(publish.prepared, build_id)

    def trash(self) -> dict:
        self.connect()
        if self.url:
            return self.call("GET", "/api/trash")
        from app.services import trash

        return self._local(trash.list_entries)

    def trash_restore(self, entry: str, origin: str | None = None, passphrase: str | None = None) -> dict:
        self.connect()
        if self.url:
            body = {k: v for k, v in (("origin", origin), ("passphrase", passphrase)) if v}
            return self.call("POST", f"/api/trash/{_q(entry)}/restore", body or None)
        from app.services import trash

        return self._local(trash.restore, entry, origin, passphrase)

    def trash_delete(self, entry: str) -> dict:
        self.connect()
        if self.url:
            return self.call("DELETE", f"/api/trash/{_q(entry)}")
        from app.services import trash

        return self._local(trash.delete, entry)

    def trash_empty(self) -> dict:
        self.connect()
        if self.url:
            return self.call("DELETE", "/api/trash")
        from app.services import trash

        return self._local(trash.empty)

    def receive_status(self) -> dict:
        self.connect()
        if self.url:
            return self.call("GET", "/api/receive/status")
        from app.services import inbox

        return self._local(inbox.status)


def _q(value: str) -> str:
    return urllib.parse.quote(value, safe="")


def _widths(raw: str | None) -> list[int] | None:
    if not raw:
        return None
    try:
        return [int(part) for part in raw.split(",") if part.strip()]
    except ValueError as exc:
        raise OpError("--widths takes whole numbers separated by commas, for example 390,1440") from exc


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def say_status(data: dict) -> str:
    health = data["health"]
    web = data["formweb"]
    engine = data["engine"]
    where = engine["url"] if engine["mode"] == "http" else "in-process (no engine is running on this port)"
    lines = [
        f"FormPublisher {health.get('version')}  api {health.get('api')}",
        f"engine    {where}",
        f"home      {health.get('home')}",
        f"sites     {data['sites']}",
        f"formweb   {web.get('url')}  " + ("reachable" if web.get("reachable") else f"not reachable ({web.get('error', 'unknown')})"),
    ]
    return "\n".join(lines)


def say_sites(data: dict) -> str:
    rows = data["sites"]
    if not rows:
        return "no sites yet; import one with: import <path> or import-formweb"
    lines = []
    for r in rows:
        lines.append(f"{r['id']:<36} {_plural(r.get('routes', 0), 'route'):<12} {r.get('importedAt', '')}  {r.get('name', '')}")
    return "\n".join(lines)


def say_import(data: dict) -> str:
    line = f"imported {data['name']}  id {data['id']}  revision {data['revision']}  {_plural(data['routes'], 'route')}  redirects {data.get('redirects', {}).get('count', 0)}"
    built = data.get("build")
    if not isinstance(built, dict):
        return line
    sig = built.get("signature")
    state = "not signed" if not sig else f"signature valid, key {sig.get('key')}" + ("" if sig.get("known") else " (not one of your keys)")
    moved = f" (was {built['originalId']})" if built.get("remapped") else ""
    return f"{line}\nbuild {built['id']}{moved}  {state}"


def say_formweb_projects(data: dict) -> str:
    lines = []
    for row in data.get("projects", []):
        state = "open" if row.get("open") else "saved"
        if row.get("open") and not row.get("saved"):
            state = "open, not saved"
        lines.append(f"{row.get('id') or '-':<40} {state:<16} {row.get('updatedAt') or '':<22} {row.get('name') or ''}")
    return "\n".join(lines) or "FormWeb has no projects"


def say_fpub(data: dict) -> str:
    return f"saved build {data['build']} as {data['file']}  {data['size']} bytes  sha256 {data['sha256']}"


def say_routes(data: dict) -> str:
    lines = [f"{data['id']}  revision {data['revision']}  {_plural(data['count'], 'route')} (from {data['source']})"]
    for r in data["routes"]:
        extra = f"  [{r['locale']}]" if r.get("locale") else ""
        lines.append(f"{r['path']:<40} {r.get('page') or ''}{extra}")
    return "\n".join(lines)


def say_revisions(data: dict) -> str:
    lines = [f"{data['id']}  {_plural(data['count'], 'revision')}, newest first"]
    for r in data["revisions"]:
        ch = r.get("changes")
        delta = f"+{ch['added']} -{ch['removed']} ~{ch['changed']}" if ch else "first"
        lines.append(f"{r['revision']:<22} {_plural(r['files'], 'file'):<10} {r['bytes']:>9} bytes  {_plural(r['routes'], 'route'):<10} {delta}" + ("  latest" if r.get("latest") else ""))
    return "\n".join(lines)


def say_diff(data: dict) -> str:
    s = data["summary"]
    lines = [f"{data['id']}  {data['from']} -> {data['to']}  +{s['added']} -{s['removed']} ~{s['changed']} ={s['same']}  {s['bytesFrom']} -> {s['bytesTo']} bytes" + ("  identical" if s["identical"] else "")]
    for row in data["added"]:
        lines.append(f"added    {row['path']}  {row['size']} bytes  {row['sha256'][:12]}")
    for row in data["removed"]:
        lines.append(f"removed  {row['path']}  {row['size']} bytes  {row['sha256'][:12]}")
    for row in data["changed"]:
        lines.append(f"changed  {row['path']}  {row['from']['size']} -> {row['to']['size']} bytes  {row['from']['sha256'][:12]} -> {row['to']['sha256'][:12]}")
    routes = data["routes"]
    lines.append(f"routes   {routes['from']} -> {routes['to']}")
    for path in routes["added"]:
        lines.append(f"  added route    {path}")
    for path in routes["removed"]:
        lines.append(f"  removed route  {path}")
    return "\n".join(lines)


def say_check(data: dict) -> str:
    summary = data["summary"]
    ran = ", ".join(summary.get("ran", [])) or "nothing yet"
    lines = [f"{data['site']}  revision {data['revision']}  checked: {ran}  {_plural(summary['errors'], 'error')}, {_plural(summary['warnings'], 'warning')}, {_plural(summary['infos'], 'note')}"]
    for p in data["problems"]:
        lines.append(f"{p.get('severity', ''):<8} {p.get('route', ''):<28} {p.get('code', '')}  {p.get('message', '')}")
        if p.get("fix"):
            lines.append(f"{'':<8} fix: {p['fix']}")
    return "\n".join(lines)


def say_build(data: dict) -> str:
    return f"build {data['id']}  site {data['site']}  revision {data['revision']}  {_plural(data['files'], 'file')}  {data['size']} bytes  " + ("signed" if data.get("signed") else "not signed") + ("" if data.get("created", True) else "  (already built, same bytes)")


def say_builds(data: dict) -> str:
    if not data["builds"]:
        return "no builds yet; make one with: build SITE-ID"
    return "\n".join(f"{b['id']:<14} {b['site']:<30} {_plural(b.get('files', 0), 'file'):<10} {b.get('size', 0):>9} bytes  {'signed' if b.get('signed') else 'unsigned':<8} {b.get('created', '')}" for b in data["builds"])


def say_keys(data: dict) -> str:
    if not data["keys"]:
        return "no keys yet; create one with: keys --create NAME"
    return "\n".join(f"{k['id']:<14} {k.get('name', ''):<24} {k.get('fingerprint', '')}" + ("  passphrase" if k.get("encrypted") else "") for k in data["keys"])


def say_key(data: dict) -> str:
    return f"created key {data['id']}  {data.get('name', '')}  {data.get('fingerprint', '')}"


def say_sign(data: dict) -> str:
    return f"signed build {data['id']} with key {data['keyId']}  {data['key']}"


def say_verify(data: dict) -> str:
    if data.get("valid"):
        return f"valid  signed by {data.get('key')}"
    return f"not valid: {data.get('reason', 'unknown')}"


def say_targets(data: dict) -> str:
    return "\n".join(f"{t['id']:<18} {t['name']:<18} {t.get('description', '')}" + (f"  [local: {t['localTool']}]" if t.get("localTool") else "") for t in data["targets"])


def say_prepared(data: dict) -> str:
    results = data["results"]
    if not results:
        return f"nothing is prepared for build {data['build']} yet; run: prepare {data['build']} --target T"
    lines = [f"build {data['build']}  {_plural(len(results), 'target')} prepared"]
    for target, row in results.items():
        lines.append("")
        lines.append(f"{target}  {row.get('folder', '')}  {_plural(len(row.get('files') or []), 'file')}")
        for cmd in row.get("commands") or []:
            where = f"  (in {cmd['cwd']})" if cmd.get("cwd") else ""
            lines.append(f"  {cmd.get('label', '')}: {cmd.get('run', '')}{where}")
        if row.get("leftOut"):
            lines.append(f"  left out: {', '.join(row['leftOut'])} (use --include-model to keep them)")
        for note in row.get("notes") or []:
            lines.append(f"  note: {note}")
        for warning in row.get("warnings") or []:
            lines.append(f"  warning: {warning}")
    return "\n".join(lines)


def say_prepare(data: dict) -> str:
    return say_prepared({"build": data["build"], "results": data["results"]})


def say_trash(data: dict) -> str:
    if not data["entries"]:
        return "the trash is empty"
    return "\n".join(f"{e['entry']:<52} {e['kind']:<9} {e['label'][:30]:<30} {e['size']:>10} bytes  {e['moved']}" + (f"  -> {e['origin']}" + (" (inferred)" if e.get("originInferred") else "") if e.get("origin") else "  (origin unknown: restore with --to PATH)") for e in data["entries"])


def say_trash_restore(data: dict) -> str:
    if data.get("reprepared"):
        return f"prepared {data['target']} again from build {data['build']} and removed {data['entry']} from the trash"
    return f"restored {data['kind']} {data['entry']} to {data['origin']}"


def say_trash_delete(data: dict) -> str:
    return f"deleted {data['entry']} for good"


def say_trash_empty(data: dict) -> str:
    return f"emptied the trash, {data['deleted']} deleted for good"


def say_receive(data: dict) -> str:
    lines = [
        f"endpoint  {data.get('endpoint')}",
        f"inbox     {data.get('inbox')}  " + ("watching" if data.get("watching") else "not watching") + f", {data.get('pending', 0)} waiting",
    ]
    rows = data.get("receipts") or []
    lines.append("no receipts yet" if not rows else "last receipts:")
    for r in rows:
        lines.append("  " + "  ".join(f"{k} {v}" for k, v in r.items() if v not in (None, "")))
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="print the raw JSON result")
    common.add_argument("--engine", help="engine URL (default: the engine on the configured port, else in-process)")
    common.add_argument("--in-process", action="store_true", help="never contact a running engine")
    parser = argparse.ArgumentParser(prog="formpublisher_engine.py cli", description="FormPublisher command line, over the same services as the engine.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", parents=[common], help="engine, data folder, site count and FormWeb reachability")
    sub.add_parser("sites", parents=[common], help="list imported sites")
    imp = sub.add_parser("import", parents=[common], help="import a FormWeb export zip, .fweb project, .fpub package or publication folder")
    imp.add_argument("path")
    imp.add_argument("--name", help="site name, overriding site.formweb.json")
    ifw = sub.add_parser("import-formweb", parents=[common], help="download the current FormWeb export (or a saved project with --project) and import it")
    ifw.add_argument("--project", metavar="ID", help="a saved FormWeb project id from formweb-projects (default: the site open in FormWeb)")
    sub.add_parser("formweb-projects", parents=[common], help="list the running FormWeb's saved projects, the open one first")
    rt = sub.add_parser("routes", parents=[common], help="list the routes of a site")
    rt.add_argument("id")
    rv = sub.add_parser("revisions", parents=[common], help="list the revisions of a site, newest first, with what changed from the one before")
    rv.add_argument("id")
    df = sub.add_parser("diff", parents=[common], help="show the added, removed and changed files and routes between two revisions of a site")
    df.add_argument("id")
    df.add_argument("--from", dest="left", metavar="R", help="older revision (default: the one before --to)")
    df.add_argument("--to", dest="right", metavar="R", help="newer revision (default: the latest)")
    ck = sub.add_parser("check", parents=[common], help="run the static checks on a site (add --deep for the browser run) and print the problems")
    ck.add_argument("id")
    ck.add_argument("--revision", help="revision to check (default: the latest)")
    ck.add_argument("--deep", action="store_true", help="also run the deep tier in the installed Chrome (needs Playwright)")
    ck.add_argument("--widths", help="comma separated viewport widths for the deep tier (default 1440,390)")
    ck.add_argument("--last", action="store_true", help="print the stored results without running anything")
    bd = sub.add_parser("build", parents=[common], help="build the deterministic site.zip and publish.json for a site")
    bd.add_argument("id")
    bd.add_argument("--revision", help="revision to build (default: the latest)")
    sub.add_parser("builds", parents=[common], help="list builds, newest first")
    fp = sub.add_parser("fpub", parents=[common], help="save a build as a .fpub package (the same bytes every time)")
    fp.add_argument("build")
    fp.add_argument("--out", metavar="FILE", help="where to write it (default: SITE-BUILD.fpub in the current folder)")
    fp.add_argument("--force", action="store_true", help="replace the file when it exists")
    sg = sub.add_parser("sign", parents=[common], help="sign a build with an Ed25519 key")
    sg.add_argument("build")
    sg.add_argument("--key", help="key id (default: the only key, when there is exactly one)")
    sg.add_argument("--passphrase", help="the key's passphrase, when it has one")
    vf = sub.add_parser("verify", parents=[common], help="verify a build's signature; exits 1 when it is not valid")
    vf.add_argument("build")
    ky = sub.add_parser("keys", parents=[common], help="list signing keys; --create NAME makes a new Ed25519 key")
    ky.add_argument("--create", metavar="NAME", help="create a key with this name")
    ky.add_argument("--passphrase", help="encrypt the new key with this passphrase")
    sub.add_parser("targets", parents=[common], help="list the host targets a build can be prepared for")
    pp = sub.add_parser("prepare", parents=[common], help="prepare a folder per target for a build, with the exact commands to run")
    pp.add_argument("build")
    pp.add_argument("--target", action="append", required=True, metavar="T", help="target id; repeat for several (see targets)")
    pp.add_argument("--include-model", action="store_true", help="keep FormWeb's model files (site.formweb.json, asset-access.json) in the host folders; they are left out by default")
    pd = sub.add_parser("prepared", parents=[common], help="list what is prepared for a build")
    pd.add_argument("build")
    tr = sub.add_parser("trash", parents=[common], help="list the trash; trash restore ENTRY, trash delete ENTRY and trash empty --yes act on it")
    tr_sub = tr.add_subparsers(dest="trash_command")
    trr = tr_sub.add_parser("restore", parents=[common], help="move an entry back to where it came from")
    trr.add_argument("entry")
    trr.add_argument("--to", metavar="PATH", help="where it goes, relative to the data folder (for example sites/my-site), for an entry whose origin is not known")
    trr.add_argument("--passphrase-stdin", action="store_true", help="read the passphrase of an encrypted key from standard input (one line), for a key whose record has to be rebuilt")
    trd = tr_sub.add_parser("delete", parents=[common], help="delete one entry for good")
    trd.add_argument("entry")
    tre = tr_sub.add_parser("empty", parents=[common], help="delete every entry for good")
    tre.add_argument("--yes", action="store_true", help="confirm that everything in the trash is deleted for good")
    sub.add_parser("receive-status", parents=[common], help="the receive endpoint, the inbox folder and the last receipts")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    client = Client(args.engine, args.in_process)
    try:
        if args.command == "status":
            data, say = client.status(), say_status
        elif args.command == "sites":
            data, say = client.sites(), say_sites
        elif args.command == "import":
            data, say = client.import_path(args.path, args.name), say_import
        elif args.command == "import-formweb":
            data, say = client.import_formweb(args.project), say_import
        elif args.command == "formweb-projects":
            data, say = client.formweb_projects(), say_formweb_projects
        elif args.command == "revisions":
            data, say = client.revisions(args.id), say_revisions
        elif args.command == "diff":
            data, say = client.diff(args.id, args.left, args.right), say_diff
        elif args.command == "routes":
            data, say = client.routes(args.id), say_routes
        elif args.command == "check":
            if args.last:
                data = client.get_checks(args.id, args.revision)
            else:
                data = client.check(args.id, args.deep, _widths(args.widths), args.revision)
            say = say_check
        elif args.command == "build":
            data, say = client.build(args.id, args.revision), say_build
        elif args.command == "builds":
            data, say = client.builds(), say_builds
        elif args.command == "fpub":
            data, say = client.save_fpub(args.build, args.out, args.force), say_fpub
        elif args.command == "sign":
            data, say = client.sign(args.build, args.key, args.passphrase), say_sign
        elif args.command == "verify":
            data, say = client.verify(args.build), say_verify
        elif args.command == "keys":
            if args.create:
                data, say = client.create_key(args.create, args.passphrase), say_key
            else:
                data, say = client.keys(), say_keys
        elif args.command == "targets":
            data, say = client.targets(), say_targets
        elif args.command == "prepare":
            data, say = client.prepare(args.build, args.target, args.include_model), say_prepare
        elif args.command == "prepared":
            data, say = client.prepared(args.build), say_prepared
        elif args.command == "trash":
            action = args.trash_command
            if action == "restore":
                secret = sys.stdin.readline().rstrip("\r\n") if args.passphrase_stdin else None
                data, say = client.trash_restore(args.entry, args.to, secret), say_trash_restore
            elif action == "delete":
                data, say = client.trash_delete(args.entry), say_trash_delete
            elif action == "empty":
                if not args.yes:
                    raise OpError("emptying the trash deletes everything in it for good; run again with --yes to confirm")
                data, say = client.trash_empty(), say_trash_empty
            else:
                data, say = client.trash(), say_trash
        else:
            data, say = client.receive_status(), say_receive
    except OpError as exc:
        print(exc.label(), file=sys.stderr)
        return exc.code
    try:
        print(json.dumps(data, indent=2) if args.json else say(data))
        sys.stdout.flush()
    except BrokenPipeError:
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
    return 1 if args.command == "verify" and not data.get("valid") else 0


if __name__ == "__main__":
    sys.exit(main())
