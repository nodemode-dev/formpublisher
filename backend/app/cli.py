import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from app import __version__
from app.services import formweb, intake, paths, settings


class OpError(Exception):
    def __init__(self, message: str, code: int = 1) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


def _detail(payload: bytes, status: int) -> str:
    try:
        body = json.loads(payload)
    except ValueError:
        body = None
    if isinstance(body, dict) and isinstance(body.get("detail"), str):
        return body["detail"]
    return f"the engine answered {status}"


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
            raise OpError(f"no FormPublisher engine is answering at {self.explicit}", 3)
        self.url = ""

    def describe(self) -> dict:
        self.connect()
        if self.url:
            return {"mode": "http", "url": self.url}
        return {"mode": "in-process", "url": None}

    def call(self, method: str, path: str, body: Any = None) -> Any:
        status, payload = self._request(method, path, body)
        if status >= 400:
            raise OpError(_detail(payload, status), 3 if status >= 500 else 1)
        return json.loads(payload) if payload else None

    def _local(self, fn, *args):
        try:
            return fn(*args)
        except (intake.IntakeError, formweb.FormwebError) as exc:
            raise OpError(exc.message) from exc
        except ValueError as exc:
            raise OpError(str(exc)) from exc

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

    def import_formweb(self) -> dict:
        self.connect()
        if self.url:
            return self.call("POST", "/api/formweb/import-current", {})
        return self._local(formweb.import_current)

    def routes(self, site_id: str) -> dict:
        self.connect()
        if self.url:
            return self.call("GET", f"/api/sites/{urllib.parse.quote(site_id, safe='')}/routes")
        return self._local(intake.site_routes, site_id)


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
    return f"imported {data['name']}  id {data['id']}  revision {data['revision']}  {_plural(data['routes'], 'route')}  redirects {data.get('redirects', {}).get('count', 0)}"


def say_routes(data: dict) -> str:
    lines = [f"{data['id']}  revision {data['revision']}  {_plural(data['count'], 'route')} (from {data['source']})"]
    for r in data["routes"]:
        extra = f"  [{r['locale']}]" if r.get("locale") else ""
        lines.append(f"{r['path']:<40} {r.get('page') or ''}{extra}")
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
    imp = sub.add_parser("import", parents=[common], help="import a FormWeb export zip or publication folder")
    imp.add_argument("path")
    imp.add_argument("--name", help="site name, overriding site.formweb.json")
    sub.add_parser("import-formweb", parents=[common], help="download the current FormWeb export and import it")
    rt = sub.add_parser("routes", parents=[common], help="list the routes of a site")
    rt.add_argument("id")
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
            data, say = client.import_formweb(), say_import
        else:
            data, say = client.routes(args.id), say_routes
    except OpError as exc:
        print(f"formpublisher: {exc.message}", file=sys.stderr)
        return exc.code
    print(json.dumps(data, indent=2) if args.json else say(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
