import ipaddress
import json
import os
import re
import secrets
import socket
import ssl
import threading
import time
import zipfile
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.parse import quote, urljoin, urlsplit

import httpx2
from cryptography import x509

from app import __version__
from app.services import intake, package, paths
from app.services.bus import bus
from app.targets._common import MODEL_FILES

GUIDE_PART = {
    "static-zip": "static-zip",
    "netlify": "netlify",
    "cloudflare-pages": "cloudflare-pages",
    "vercel": "vercel",
    "github-pages": "github-pages",
    "nginx": "nginx-on-your-own-server",
}
START = "before-you-start"
UPDATING = "updating-the-site-later"
DOMAIN, HTTPS, FOLDER = "Your domain", "HTTPS", "The folder"
TOPIC = {
    "live.dns": DOMAIN,
    "live.www": DOMAIN,
    "live.tls": HTTPS,
    "live.cert-expiry": HTTPS,
    "live.http": HTTPS,
    "live.redirect": FOLDER,
    "live.404": FOLDER,
}
CODES = ("live.dns", "live.tls", "live.cert-expiry", "live.www", "live.http", "live.redirect", "live.404", "live.build")
WARN_DAYS = 7
MAX_REDIRECTS = 50
MAX_FILES = 3
MAX_FILE_BYTES = 8 * 1024 * 1024
DEADLINE_SECONDS = 120
TIMEOUT = httpx2.Timeout(10.0, connect=6.0)
LABEL = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)$")
CANONICAL = re.compile(r"<link\b[^>]*>", re.I)
ATTR = re.compile(r"""([a-zA-Z-]+)\s*=\s*("([^"]*)"|'([^']*)'|([^\s>]+))""")
PERMANENT = (301, 308)
TEMPORARY = (302, 303, 307)
PREFERRED = ("robots.txt", "sitemap.xml")
COMPARABLE = (".css", ".js", ".txt", ".xml", ".json", ".svg", ".webmanifest", ".ico")
SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}
_lock = threading.Lock()


class AddressError(intake.IntakeError):
    pass


def _bad(message: str) -> AddressError:
    return AddressError(message, 400, "address-invalid")


def normalise(address: object) -> str:
    if not isinstance(address, str) or not address.strip():
        raise _bad("Give the site's public address, for example example.com.")
    raw = address.strip()
    shape = "The address must be a domain name or an https address with no path, for example example.com."
    if any(c.isspace() for c in raw) or "\\" in raw:
        raise _bad(shape)
    if "://" not in raw:
        raw = "https://" + raw
    try:
        parts = urlsplit(raw)
        port = parts.port
    except ValueError as exc:
        raise _bad(shape) from exc
    if parts.scheme.lower() not in ("https", "http") or parts.username or parts.password or "@" in parts.netloc:
        raise _bad(shape)
    if parts.path not in ("", "/") or parts.query or parts.fragment:
        raise _bad(shape)
    if port is not None and port != 443:
        raise _bad(shape)
    host = (parts.hostname or "").rstrip(".")
    if not host:
        raise _bad(shape)
    try:
        ipaddress.ip_address(host.strip("[]"))
        is_ip = True
    except ValueError:
        is_ip = False
    if is_ip:
        raise _bad("The address must name a public domain, not an IP address or a local name.")
    try:
        host = host.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise _bad(shape) from exc
    labels = host.split(".")
    if len(labels) < 2 or len(host) > 253 or not all(LABEL.match(label) for label in labels) or labels[-1].isdigit():
        raise _bad("The address must name a public domain, not an IP address or a local name.")
    if labels[-1] in ("localhost", "local", "internal", "lan", "home", "localdomain"):
        raise _bad("The address must name a public domain, not an IP address or a local name.")
    return host


def names_of(host: str) -> tuple[str, str]:
    bare = host[4:] if host.startswith("www.") and host.count(".") >= 2 else host
    return bare, "www." + bare


def folder() -> Path:
    return paths.home() / "live"


def stored_file(site_id: str) -> Path:
    return folder() / f"{site_id}.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _latest_build(site_id: str) -> str | None:
    rows = [b for b in package.list_builds() if b.get("site") == site_id and isinstance(b.get("id"), str)]
    return rows[0]["id"] if rows else None


def _prepared_target(site_id: str, build_id: str | None) -> str | None:
    if not build_id:
        return None
    base = paths.prepared_dir() / site_id / build_id
    try:
        found = sorted(p.name for p in base.iterdir() if p.is_dir() and p.name in GUIDE_PART)
    except OSError:
        return None
    if len(found) > 1:
        found = [name for name in found if name != "static-zip"]
    return found[0] if len(found) == 1 else None


def suggest(site_id: str, build_id: str | None = None) -> str | None:
    chosen = build_id or _latest_build(site_id)
    if not chosen:
        return None
    try:
        archive = package.zip_path(chosen)
        with zipfile.ZipFile(archive) as zf:
            text = zf.read("index.html")[:512 * 1024].decode("utf-8", "replace")
    except (intake.IntakeError, OSError, KeyError, zipfile.BadZipFile):
        return None
    for tag in CANONICAL.findall(text):
        attrs = {m.group(1).lower(): next(g for g in m.groups()[2:] if g is not None) for m in ATTR.finditer(tag)}
        if "canonical" not in attrs.get("rel", "").lower().split():
            continue
        try:
            return normalise(urlsplit(attrs.get("href", "")).hostname or "")
        except intake.IntakeError:
            return None
    return None


def stored(site_id: str) -> dict:
    intake._site_folder(site_id)
    last = package._read_json(stored_file(site_id))
    last = last if isinstance(last, dict) and isinstance(last.get("problems"), list) else None
    suggested = last.get("address") if last and isinstance(last.get("address"), str) else suggest(site_id)
    return {"site": site_id, "suggested": suggested, "last": last}


class Run:
    def __init__(self, target: str | None) -> None:
        self.target = target
        self.problems: list[dict] = []
        self.requests = 0

    def guide(self, code: str) -> tuple[str, str | None]:
        if code == "live.build":
            return UPDATING, None
        part = GUIDE_PART.get(self.target or "")
        if not part:
            return START, None
        return part, TOPIC.get(code)

    def add(self, code: str, severity: str, name: str | None, message: str, fix: str = "") -> None:
        part, topic = self.guide(code)
        self.problems.append({"code": code, "severity": severity, "name": name, "message": message, "fix": fix, "guide": part, "guideTopic": topic})


def _resolves(name: str) -> bool:
    try:
        return bool(socket.getaddrinfo(name, 443, type=socket.SOCK_STREAM))
    except (socket.gaierror, UnicodeError, OSError):
        return False


def _cause(exc: BaseException) -> BaseException | None:
    seen = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, (ssl.SSLError, ssl.CertificateError)):
            return current
        current = current.__cause__ or current.__context__
    return None


def _peek_certificate(name: str) -> x509.Certificate | None:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    try:
        with socket.create_connection((name, 443), timeout=6) as raw, context.wrap_socket(raw, server_hostname=name) as tls:
            der = tls.getpeercert(binary_form=True)
    except (OSError, ssl.SSLError):
        return None
    try:
        return x509.load_der_x509_certificate(der) if der else None
    except ValueError:
        return None


def _day(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%d")


def _check_dates(run: Run, name: str, cert: x509.Certificate) -> None:
    ends = cert.not_valid_after_utc
    left = ends - datetime.now(timezone.utc)
    if left.total_seconds() <= 0:
        run.add("live.cert-expiry", "error", name, f"The certificate of {name} expired on {_day(ends)}.", "Renew it, or let your host renew it: hosts that issue certificates renew them on their own while DNS points at them.")
    elif left.days < WARN_DAYS:
        run.add("live.cert-expiry", "warning", name, f"The certificate of {name} expires on {_day(ends)}, in less than {WARN_DAYS} days.", "Check that renewal works at your host; a certificate is normally renewed well before its last week.")
    else:
        run.add("live.tls", "info", name, f"The certificate of {name} is valid until {_day(ends)}.")


def _tls_failure(run: Run, name: str, exc: BaseException) -> None:
    fix = f"Let your host issue a certificate for {name}: it does so once the domain is added to the site there and DNS points at it."
    if isinstance(exc, ssl.SSLCertVerificationError) and exc.verify_code == 10:
        cert = _peek_certificate(name)
        if cert is not None:
            run.add("live.cert-expiry", "error", name, f"The certificate of {name} expired on {_day(cert.not_valid_after_utc)}.", "Renew it, or let your host renew it: hosts that issue certificates renew them on their own while DNS points at them.")
        else:
            run.add("live.cert-expiry", "error", name, f"The certificate of {name} has expired.", "Renew it, or let your host renew it: hosts that issue certificates renew them on their own while DNS points at them.")
        return
    reason = exc.verify_message if isinstance(exc, ssl.SSLCertVerificationError) and exc.verify_message else (getattr(exc, "reason", None) or type(exc).__name__)
    run.add("live.tls", "error", name, f"The certificate of {name} is not valid: {str(reason).rstrip('.')}.", fix)


def _client() -> httpx2.Client:
    return httpx2.Client(
        timeout=TIMEOUT,
        follow_redirects=False,
        verify=httpx2.create_ssl_context(),
        headers={"User-Agent": f"formpublisher-live-check/{__version__}", "Accept": "*/*"},
        limits=httpx2.Limits(max_connections=4, max_keepalive_connections=4),
    )


def _get(run: Run, client: httpx2.Client, url: str, keep_body: bool = False) -> tuple[int, str, bytes | None, bytes | None]:
    run.requests += 1
    client.cookies.clear()
    with client.stream("GET", url) as res:
        der = None
        stream = res.extensions.get("network_stream")
        obj = stream.get_extra_info("ssl_object") if stream is not None else None
        if obj is not None:
            try:
                der = obj.getpeercert(True)
            except (TypeError, ValueError, ssl.SSLError):
                der = None
        body = None
        if keep_body and res.status_code == 200:
            chunks, total = [], 0
            for chunk in res.iter_bytes():
                total += len(chunk)
                if total > MAX_FILE_BYTES:
                    chunks = []
                    break
                chunks.append(chunk)
            body = b"".join(chunks) if chunks or total == 0 else None
        return res.status_code, res.headers.get("location", ""), body, der


def _failure(exc: Exception) -> str:
    return type(exc).__name__


def _probe_name(run: Run, client: httpx2.Client, name: str) -> dict:
    state = {"name": name, "resolves": _resolves(name), "home": None, "location": "", "reason": ""}
    if not state["resolves"]:
        return state
    try:
        status, location, _, der = _get(run, client, f"https://{name}/")
    except httpx2.HTTPError as exc:
        cause = _cause(exc)
        if cause is not None:
            _tls_failure(run, name, cause)
            state["reason"] = "tls"
        else:
            state["reason"] = _failure(exc)
        return state
    if der:
        try:
            _check_dates(run, name, x509.load_der_x509_certificate(der))
        except ValueError:
            pass
    state["home"], state["location"] = status, location
    return state


def _redirect_target(location: str, base: str) -> tuple[str, str, str]:
    joined = urlsplit(urljoin(base, location))
    return joined.scheme.lower(), (joined.hostname or "").lower(), joined.path or "/"


def _judge_home(run: Run, state: dict, other: str) -> bool:
    name = state["name"]
    status = state["home"]
    if status == 200:
        run.add("live.www", "info", name, f"{name} serves the home page.")
        return True
    if status is None:
        return False
    scheme, host, _ = _redirect_target(state["location"], f"https://{name}/")
    if status in PERMANENT and scheme == "https" and host in (other, name):
        run.add("live.www", "info", name, f"{name} redirects to {host}.")
        return True
    run.add("live.www", "warning", name, f"{name} answers {status} at / instead of the home page or a permanent redirect to {other}.", f"Add {name} to the site at your host as well, so that it redirects to {other}.")
    return False


def _http_check(run: Run, client: httpx2.Client, name: str) -> None:
    try:
        status, location, _, _ = _get(run, client, f"http://{name}/")
    except httpx2.HTTPError:
        run.add("live.http", "warning", name, f"http://{name}/ does not answer on port 80.", "Turn on the host's redirect from http to https (on GitHub Pages, Enforce HTTPS; on nginx, a server block on port 80 that redirects).")
        return
    if 300 <= status < 400 and urlsplit(urljoin(f"http://{name}/", location)).scheme.lower() == "https":
        run.add("live.http", "info", name, f"http://{name}/ redirects to https.")
        return
    run.add("live.http", "warning", name, f"http://{name}/ answers {status} instead of redirecting to https.", "Turn on the host's redirect from http to https (on GitHub Pages, Enforce HTTPS; on nginx, a server block on port 80 that redirects).")


def _family(status: int) -> str:
    return "permanent" if status in PERMANENT else "temporary" if status in TEMPORARY else "other"


def _check_redirects(run: Run, client: httpx2.Client, primary: str, rows: list[dict], deadline: float) -> None:
    usable = [r for r in rows if isinstance(r.get("from"), str) and r["from"].startswith("/") and "*" not in r["from"] and ":" not in r["from"] and isinstance(r.get("to"), str)]
    if not usable:
        return
    total, tested, failed = len(usable), 0, 0
    fix = "Deploy the whole prepared site folder again, with the redirect rules FormPublisher wrote for this host."
    base = f"https://{primary}/"
    for row in usable[:MAX_REDIRECTS]:
        if time.monotonic() > deadline:
            break
        src, dst, want = row["from"], row["to"], int(row.get("status") or 301)
        tested += 1
        try:
            status, location, _, _ = _get(run, client, urljoin(base, quote(src, safe="/%?=&")))
        except httpx2.HTTPError as exc:
            failed += 1
            run.add("live.redirect", "warning", primary, f"{src} did not answer: {_failure(exc)}.", fix)
            continue
        if status not in PERMANENT + TEMPORARY:
            failed += 1
            run.add("live.redirect", "warning", primary, f"{src} should redirect to {dst} with {want}, but answers {status}.", fix)
            continue
        _, got_host, got_path = _redirect_target(location, base)
        _, want_host, want_path = _redirect_target(dst, base)
        same_host = got_host == want_host or (want_host in names_of(primary) and got_host in names_of(primary))
        if not same_host or got_path.rstrip("/") != want_path.rstrip("/") or _family(status) != _family(want):
            failed += 1
            run.add("live.redirect", "warning", primary, f"{src} redirects to {location or '?'} with {status} instead of {dst} with {want}.", fix)
    if not failed:
        run.add("live.redirect", "info", primary, f"Redirects tested: {tested} of {total}. All hold.")


def _check_404(run: Run, client: httpx2.Client, primary: str) -> None:
    path = f"/formpublisher-live-check-{secrets.token_hex(4)}"
    fix = "Deploy the prepared site folder with its 404 rule, so that an unknown address gets 404.html with status 404."
    try:
        status, _, _, _ = _get(run, client, f"https://{primary}{path}")
    except httpx2.HTTPError as exc:
        run.add("live.404", "warning", primary, f"{path} did not answer: {_failure(exc)}.", fix)
        return
    if status == 404:
        run.add("live.404", "info", primary, "An address that does not exist gets 404.")
    elif status == 200:
        run.add("live.404", "warning", primary, f"An address that does not exist ({path}) answers 200 instead of 404 (a soft 404).", fix)
    else:
        run.add("live.404", "warning", primary, f"An address that does not exist ({path}) answers {status} instead of 404.", fix)


def _pick_files(rows: list[dict], left_out: tuple[str, ...]) -> list[dict]:
    files = [r for r in rows if isinstance(r, dict) and isinstance(r.get("path"), str) and isinstance(r.get("sha256"), str)]
    files = [r for r in files if r["path"] not in left_out and not r["path"].lower().endswith((".html", ".htm")) and not r["path"].startswith(".")]
    chosen = [r for name in PREFERRED for r in files if r["path"] == name]
    for suffix in COMPARABLE:
        for r in files:
            if len(chosen) >= MAX_FILES:
                break
            if r["path"].lower().endswith(suffix) and r not in chosen and r.get("size", 0) <= MAX_FILE_BYTES:
                chosen.append(r)
    return chosen[:MAX_FILES]


def _check_build(run: Run, client: httpx2.Client, primary: str, publish: dict, build_id: str, deadline: float) -> None:
    chosen =_pick_files(publish.get("files") or [], tuple(MODEL_FILES))
    fix = "Deploy this build again, with the guide's steps for updating the site."
    if not chosen:
        run.add("live.build", "info", primary, "The build has no files to compare besides its pages, which hosts may rewrite.")
        return
    differ = False
    for row in chosen:
        if time.monotonic() > deadline:
            break
        rel = row["path"]
        try:
            status, _, body, _ = _get(run, client, f"https://{primary}/" + quote(rel), keep_body=True)
        except httpx2.HTTPError as exc:
            differ = True
            run.add("live.build", "warning", primary, f"/{rel} did not answer: {_failure(exc)}.", fix)
            continue
        if status != 200 or body is None:
            differ = True
            run.add("live.build", "warning", primary, f"/{rel} is missing online (it answers {status}), so the site online is not build {build_id}.", fix)
        elif sha256(body).hexdigest() != row["sha256"]:
            differ = True
            run.add("live.build", "warning", primary, f"/{rel} online differs from build {build_id}, so the site online is not this build.", fix)
    if not differ:
        run.add("live.build", "info", primary, f"The files compared ({', '.join(r['path'] for r in chosen)}) match build {build_id}, so the site online is this build.")


def _summary(problems: list[dict]) -> dict:
    counts = {"error": 0, "warning": 0, "info": 0}
    for p in problems:
        counts[p["severity"]] = counts.get(p["severity"], 0) + 1
    return {"errors": counts["error"], "warnings": counts["warning"], "infos": counts["info"]}


def _write(site_id: str, result: dict) -> None:
    target = stored_file(site_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        temp = target.with_name(f".{target.name}.{os.getpid()}.{threading.get_ident()}.tmp")
        temp.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(temp, target)


def run(site_id: str, address: str, build_id: str | None = None, target: str | None = None) -> dict:
    intake._site_folder(site_id)
    host = normalise(address)
    if target is not None and target not in GUIDE_PART:
        raise intake.IntakeError(f"unknown target: {target!r}", 404, "target-unknown")
    publish = None
    if build_id:
        record = package.get_build(build_id)
        if record.get("site") != site_id:
            raise intake.IntakeError("that build belongs to another site", 400, "build-site")
        publish = record.get("publish") if isinstance(record.get("publish"), dict) else None
    else:
        build_id = _latest_build(site_id)
        if build_id:
            publish = package.get_build(build_id).get("publish")
            publish = publish if isinstance(publish, dict) else None
    target = target or _prepared_target(site_id, build_id)
    bare, www = names_of(host)
    run_state = Run(target)
    started = time.monotonic()
    deadline = started + DEADLINE_SECONDS
    with _client() as client:
        states = [_probe_name(run_state, client, bare), _probe_name(run_state, client, www)]
        if not any(s["resolves"] for s in states):
            run_state.add("live.dns", "error", bare, f"Neither {bare} nor {www} has a DNS record that answers.", "Add the domain to your site at the host, then add the DNS records it shows at your DNS provider. They can take up to a day to reach everyone.")
        for state, other in ((states[0], www), (states[1], bare)):
            name = state["name"]
            if not state["resolves"]:
                if any(s["resolves"] for s in states):
                    run_state.add("live.www", "warning", name, f"{name} has no DNS record that answers, so visitors who type it get nothing.", f"Add the DNS record your host gives for {name} (for www usually a CNAME), then wait for it to reach everyone.")
                continue
            if state["reason"] and state["reason"] != "tls":
                alone = not any(s["home"] is not None or s["reason"] == "tls" for s in states)
                run_state.add("live.www", "error" if alone else "warning", name, f"{name} does not answer on port 443: {state['reason']}.", f"Check that {name} points at your host and that the domain is added to the site there.")
                continue
            _judge_home(run_state, state, other)
            _http_check(run_state, client, name)
        primary = host if states[[bare, www].index(host)]["home"] == 200 else next((s["name"] for s in states if s["home"] == 200), None)
        if primary is None and any(s["home"] is not None for s in states):
            run_state.add("live.build", "error", None, "Neither name serves the home page, so the site does not seem to be deployed.", "Deploy the prepared folder with the steps in the guide, then check again.")
        if primary is not None:
            if publish:
                _check_redirects(run_state, client, primary, publish.get("redirects") or [], deadline)
            _check_404(run_state, client, primary)
            if publish and build_id:
                _check_build(run_state, client, primary, publish, build_id, deadline)
            else:
                run_state.add("live.build", "info", primary, "There is no build of this site to compare the site online with.")
    problems = sorted(run_state.problems, key=lambda p: (SEVERITY_ORDER.get(p["severity"], 3), CODES.index(p["code"]) if p["code"] in CODES else 99))
    summary = _summary(problems)
    result = {
        "site": site_id,
        "address": host,
        "names": [bare, www],
        "primary": primary,
        "build": build_id,
        "target": target,
        "checkedAt": _now(),
        "seconds": round(time.monotonic() - started, 2),
        "requests": run_state.requests,
        "ok": summary["errors"] == 0 and summary["warnings"] == 0,
        "summary": summary,
        "problems": problems,
    }
    _write(site_id, result)
    bus.emit("live.checked", site=site_id, ok=result["ok"], address=host)
    return result
