import hashlib
import html
import ipaddress
import json
import os
import posixpath
import re
import threading
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

from app.services import host, intake, paths

TIERS = ("static", "live", "deep")
SEVERITIES = ("error", "warning", "info")
MAX_LIVE = 1000
KIB = 1024
MIB = 1024 * 1024
TEXT_EXT = {".html", ".htm", ".css", ".js", ".mjs"}
MEDIA_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif", ".svg", ".ico", ".mp4", ".webm", ".mp3", ".wav", ".woff", ".woff2", ".ttf", ".otf"}
RES_RELS = {
    "stylesheet", "icon", "shortcut", "apple-touch-icon", "apple-touch-icon-precomposed",
    "mask-icon", "preload", "modulepreload", "prefetch", "manifest",
}
SKIP_SCHEME = re.compile(r"^(?!https?:)[a-zA-Z][a-zA-Z0-9+.\-]*:")
CSS_URL = re.compile(r"""url\(\s*(['"]?)(.*?)\1\s*\)""", re.I | re.S)
CSS_IMPORT = re.compile(r"""@import\s+(['"])(.*?)\1""", re.I)
CSS_COMMENT = re.compile(r"/\*.*?\*/", re.S)
JS_EXTERNAL = re.compile(r"""(?:\bfetch|\bimport|\bnew\s+URL)\s*\(\s*(["'`])(https?://[^"'`\s]+)\1""")
SITEMAP_LOC = re.compile(r"<loc>\s*(.*?)\s*</loc>", re.I | re.S)
FORMS_PATH = "/api/forms/"
FORMS_FIX = "See Forms in the hosting guide (Host it yourself, Forms)."
WEB3FORMS = "https://api.web3forms.com/submit"
UNSENT_TYPES = {"submit", "button", "reset", "image"}
ANALYTICS_FIX = "See Analytics and search engines in the hosting guide (Host it yourself, Analytics and search engines)."
ANALYTICS_SRC = (
    ("Cloudflare Web Analytics", ("static.cloudflareinsights.com",), re.compile(r"^/beacon\.min\.js$")),
    ("Plausible", ("plausible.io",), re.compile(r"^/js/(?:pa-[^/]+|script[^/]*)\.js$")),
    ("Fathom", ("cdn.usefathom.com",), re.compile(r"^/script\.js$")),
    ("GoatCounter", ("gc.zgo.at",), re.compile(r"^/count\.js$")),
    ("Simple Analytics", ("scripts.simpleanalyticscdn.com",), re.compile(r"^/latest\.js$")),
    ("Google Analytics", ("www.googletagmanager.com", "googletagmanager.com"), re.compile(r"^/(?:gtag/js|gtm\.js)$")),
)
GOOGLE_INLINE = re.compile(r"googletagmanager\.com/(?:gtag/js|gtm\.js)")
VERCEL_STUB = re.compile(r"\bwindow\.va\s*=")
VOID ={"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
OG_REQUIRED = ("og:title", "og:type", "og:image", "og:url")
HREFLANG = re.compile(r"^(x-default|[a-z]{2}(-[a-z]{4})?(-[a-z]{2})?)$", re.I)
UNLABELED_TYPES = {"hidden", "submit", "button", "reset"}
_lock = threading.RLock()
_live: dict[tuple[str, str], dict[str, dict]] = {}


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def checks_dir(site: str, revision: str) -> Path:
    if not isinstance(site, str) or not intake.ID_RE.match(site):
        raise intake.IntakeError("site not found", 404, "site-missing")
    if not isinstance(revision, str) or not re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$", revision):
        raise intake.IntakeError("revision not found", 404, "revision-missing")
    folder = paths.sub("checks") / site / revision
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def route_hash(route: str) -> str:
    return hashlib.sha1(route.encode("utf-8")).hexdigest()


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def parse_rules(root: Path) -> list[dict]:
    data = _read_json(root / "redirects.json")
    rows = data.get("redirects", data) if isinstance(data, dict) else data
    if isinstance(rows, dict):
        rows = [
            {"from": src, "to": dst.get("to"), "status": dst.get("status", 301)} if isinstance(dst, dict) else {"from": src, "to": dst, "status": 301}
            for src, dst in rows.items()
        ]
    out = []
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, dict):
            continue
        src = row.get("from", row.get("source"))
        dst = row.get("to", row.get("target"))
        status = row.get("status", 301)
        if not isinstance(src, str) or not isinstance(dst, str) or status not in (200, 301, 302, 307, 308):
            continue
        src = src if src.startswith("/") else "/" + src
        splat = src.endswith("*")
        out.append({"from": src, "to": dst, "status": status, "splat": splat, "prefix": src[:-1] if splat else None})
    return out


def _norm(path: str) -> str:
    return path.rstrip("/") or "/"


class SiteIndex:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.files: dict[str, int] = {}
        for current, dirs, names in os.walk(self.root, followlinks=False):
            dirs[:] = [d for d in dirs if not (Path(current) / d).is_symlink()]
            for name in names:
                full = Path(current) / name
                if full.is_symlink():
                    continue
                try:
                    size = full.stat().st_size
                except OSError:
                    continue
                self.files[full.relative_to(self.root).as_posix()] = size
        self.rules = parse_rules(self.root)
        self.base = host.base_path(self.root)

    def local(self, path: str) -> str:
        inner = host.within(self.base, path if path.startswith("/") else "/" + path)
        return path if inner is None else inner

    def lookup(self, path: str) -> str | None:
        return self.find(path) or self.find(self.local(path))

    def find(self, path: str) -> str | None:
        rel = "/".join(s for s in path.split("/") if s)
        if path.endswith("/") or not rel:
            candidates = [f"{rel}/index.html" if rel else "index.html"]
        else:
            candidates = [rel, f"{rel}/index.html", f"{rel}.html"]
        for candidate in candidates:
            if candidate in self.files:
                return candidate
        return None

    def match(self, path: str) -> tuple[dict, str] | None:
        for rule in self.rules:
            if rule["splat"]:
                if path.startswith(rule["prefix"]):
                    return rule, rule["to"].replace(":splat", path[len(rule["prefix"]):])
            elif _norm(path) == _norm(rule["from"]):
                return rule, rule["to"]
        return None

    def resolve(self, raw: str) -> tuple[str, str | None, int | None]:
        path = unquote(raw or "/")
        if "\x00" in path or "\\" in path:
            return "none", None, None
        if not path.startswith("/"):
            path = "/" + path
        if ".." in path.split("/"):
            return "none", None, None
        hit = self.lookup(path)
        if hit:
            return "file", hit, 200
        found = self.match(path)
        if found is None:
            return "none", None, None
        rule, target = found
        if rule["status"] == 200:
            inner = self.lookup(unquote(urlsplit(target).path) or "/")
            return ("file", inner, 200) if inner else ("none", None, None)
        return "redirect", target, rule["status"]


class Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lang: str | None = None
        self.title: str | None = None
        self.description: str | None = None
        self.noindex = False
        self.canonical: str | None = None
        self.base: str | None = None
        self.ids: set[str] = set()
        self.links: list[tuple[str, int]] = []
        self.assets: list[dict] = []
        self.images: list[tuple[int, dict]] = []
        self.forms: list[tuple[int, dict]] = []
        self.form_fields: list[list[tuple[int, str, dict]]] = []
        self.in_form = False
        self.scripts: list[tuple[int, dict]] = []
        self.inline_js: list[str] = []
        self.script_buf: list[str] | None = None
        self.headings: list[tuple[int, int]] = []
        self.styles: list[tuple[int, str]] = []
        self.title_buf: list[str] | None = None
        self.style_buf: list[str] | None = None
        self.style_line = 0
        self.svg = 0
        self.canonicals: list[str] = []
        self.og: dict[str, str] = {}
        self.icon = False
        self.alternates: list[tuple[str, str, int]] = []
        self.jsonld: list[tuple[int, str]] = []
        self.jsonld_buf: list[str] | None = None
        self.jsonld_line = 0
        self.hidden = 0
        self.hidden_tag: str | None = None
        self.anchor: dict | None = None
        self.unnamed_links: list[tuple[int, str]] = []
        self.label_depth = 0
        self.label_for: set[str] = set()
        self.controls: list[tuple[int, str, dict, bool]] = []

    def _close_anchor(self) -> None:
        if self.anchor is not None and not self.anchor["named"]:
            self.unnamed_links.append((self.anchor["line"], self.anchor["href"]))
        self.anchor = None

    def _asset(self, tag: str, attr: str, url: str | None, line: int) -> None:
        if url and url.strip():
            self.assets.append({"tag": tag, "attr": attr, "url": url.strip(), "line": line})

    def handle_starttag(self, tag, attrs):
        line = self.getpos()[0]
        a = {k: (v if v is not None else "") for k, v in attrs}
        if self.hidden_tag:
            if tag == self.hidden_tag:
                self.hidden += 1
        elif tag not in VOID and ("hidden" in a or a.get("aria-hidden", "").strip().lower() == "true"):
            self.hidden_tag = tag
            self.hidden = 1
        if "id" in a and a["id"]:
            self.ids.add(a["id"])
        if tag == "a" and a.get("name"):
            self.ids.add(a["name"])
        if a.get("style"):
            self.styles.append((line, a["style"]))
        if tag == "svg":
            self.svg += 1
        elif tag == "html":
            if self.lang is None:
                self.lang = a.get("lang", "")
        elif tag == "base":
            if self.base is None and a.get("href"):
                self.base = a["href"]
        elif tag == "title":
            if not self.svg and self.title is None and self.title_buf is None:
                self.title_buf = []
        elif tag == "style":
            self.style_buf = []
            self.style_line = line
        elif tag == "meta":
            name = a.get("name", "").lower()
            if name == "description" and self.description is None:
                self.description = a.get("content", "")
            elif name == "robots" and "noindex" in a.get("content", "").lower():
                self.noindex = True
            prop = a.get("property", "").strip().lower()
            if prop.startswith("og:") and prop not in self.og:
                self.og[prop] = a.get("content", "").strip()
        elif tag == "link":
            rels = set(a.get("rel", "").lower().split())
            if "canonical" in rels and a.get("href"):
                self.canonical = a["href"]
            if "canonical" in rels:
                self.canonicals.append(a.get("href", "").strip())
            if "icon" in rels and a.get("href", "").strip():
                self.icon = True
            if "alternate" in rels and "hreflang" in a:
                self.alternates.append((a["hreflang"].strip(), a.get("href", "").strip(), line))
            if rels & RES_RELS:
                self._asset("link", "href", a.get("href"), line)
        elif tag == "a":
            if a.get("href", "").strip():
                self.links.append((a["href"].strip(), line))
                self._close_anchor()
                if not self.hidden:
                    named = any(a.get(k, "").strip() for k in ("aria-label", "aria-labelledby", "title"))
                    self.anchor = {"line": line, "href": a["href"].strip(), "named": named}
        elif tag == "img":
            self.images.append((line, a))
            if self.anchor is not None and not self.hidden and a.get("alt", "").strip():
                self.anchor["named"] = True
            self._asset("img", "src", a.get("src"), line)
            self._srcset(tag, a.get("srcset"), line)
        elif tag == "source":
            self._asset(tag, "src", a.get("src"), line)
            self._srcset(tag, a.get("srcset"), line)
        elif tag in ("video", "audio"):
            self._asset(tag, "src", a.get("src"), line)
            self._asset(tag, "poster", a.get("poster"), line)
        elif tag in ("script", "track", "iframe", "embed"):
            self._asset(tag, "src", a.get("src"), line)
            if tag == "script" and a.get("type", "").strip().lower() == "application/ld+json":
                self.jsonld_buf = []
                self.jsonld_line = line
            elif tag == "script":
                self.scripts.append((line, a))
                if not a.get("src", "").strip():
                    self.script_buf = []
        elif tag in ("input", "select", "textarea"):
            kind = a.get("type", "").strip().lower() if tag == "input" else tag
            if self.in_form and self.form_fields:
                self.form_fields[-1].append((line, tag, a))
            if kind == "image":
                self._asset(tag, "src", a.get("src"), line)
            if not self.hidden and kind not in UNLABELED_TYPES and not (kind == "image" and a.get("alt", "").strip()):
                self.controls.append((line, tag, a, self.label_depth > 0))
        elif tag == "label":
            self.label_depth += 1
            if a.get("for", "").strip():
                self.label_for.add(a["for"].strip())
        elif tag == "form":
            self.forms.append((line, a))
            self.form_fields.append([])
            self.in_form = True
        elif len(tag) == 2 and tag[0] == "h" and tag[1] in "123456":
            self.headings.append((int(tag[1]), line))

    def _srcset(self, tag: str, value: str | None, line: int) -> None:
        if not value:
            return
        for part in value.split(","):
            pieces = part.strip().split()
            if pieces:
                self._asset(tag, "srcset", pieces[0], line)

    def handle_endtag(self, tag):
        if self.hidden_tag and tag == self.hidden_tag:
            self.hidden -= 1
            if not self.hidden:
                self.hidden_tag = None
        if tag == "svg" and self.svg:
            self.svg -= 1
        elif tag == "title" and self.title_buf is not None:
            self.title = "".join(self.title_buf).strip()
            self.title_buf = None
        elif tag == "style" and self.style_buf is not None:
            self.styles.append((self.style_line, "".join(self.style_buf)))
            self.style_buf = None
        elif tag == "script" and self.jsonld_buf is not None:
            self.jsonld.append((self.jsonld_line, "".join(self.jsonld_buf)))
            self.jsonld_buf = None
        elif tag == "script" and self.script_buf is not None:
            self.inline_js.append("".join(self.script_buf))
            self.script_buf = None
        elif tag == "form":
            self.in_form = False
        elif tag == "a":
            self._close_anchor()
        elif tag == "label" and self.label_depth:
            self.label_depth -= 1

    def handle_data(self, data):
        if self.title_buf is not None:
            self.title_buf.append(data)
        elif self.style_buf is not None:
            self.style_buf.append(data)
        elif self.jsonld_buf is not None:
            self.jsonld_buf.append(data)
        elif self.script_buf is not None:
            self.script_buf.append(data)
        elif self.anchor is not None and not self.hidden and data.strip():
            self.anchor["named"] = True


def css_refs(text: str) -> list[tuple[str, int]]:
    cleaned = CSS_COMMENT.sub(lambda m: "\n" * m.group().count("\n"), text)
    out = []
    for pattern in (CSS_URL, CSS_IMPORT):
        for m in pattern.finditer(cleaned):
            url = m.group(2).strip()
            if url:
                out.append((url, cleaned.count("\n", 0, m.start()) + 1))
    return out


def _route_key(path: str) -> str:
    value = unquote(path or "/")
    for tail in ("/index.html", "/index.htm"):
        if value.endswith(tail):
            value = value[: -len(tail)] + "/"
    if value.endswith(".html"):
        value = value[:-5]
    return _norm(value if value.startswith("/") else "/" + value)


def local_host(host: str) -> bool:
    host = (host or "").lower()
    if host == "localhost" or host.endswith((".localhost", ".local")) or ("." not in host and ":" not in host):
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    address = getattr(address, "ipv4_mapped", None) or address
    return address.is_loopback or address.is_private or address.is_link_local or address.is_unspecified


def analytics_src(src: str) -> str | None:
    parts = urlsplit("http:" + src if src.startswith("//") else src)
    host = (parts.hostname or "").lower()
    for name, hosts, path in ANALYTICS_SRC:
        if host in hosts and path.match(parts.path):
            return name
    return None


def analytics_of(page: Page) -> set[str]:
    found = set()
    for _line, attrs in page.scripts:
        src = attrs.get("src", "").strip()
        if not src:
            continue
        parts = urlsplit("http:" + src if src.startswith("//") else src)
        name = analytics_src(src)
        if name:
            found.add(name)
        if parts.path.endswith("/script.js") and attrs.get("data-website-id", "").strip():
            found.add("Umami")
        if parts.path == "/_vercel/insights/script.js":
            found.add("Vercel Web Analytics")
    for text in page.inline_js:
        if GOOGLE_INLINE.search(text):
            found.add("Google Analytics")
        if VERCEL_STUB.search(text):
            found.add("Vercel Web Analytics")
    return found


class Runner:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.index = SiteIndex(root)
        self.problems: list[dict] = []
        self.seen: dict[str, int] = {}
        self.pages: dict[str, Page | None] = {}
        self.route_file: dict[str, str] = {}
        self.file_route: dict[str, str] = {}
        self.route_locale: dict[str, str] = {}
        self.own_hosts: set[str] = {"localhost", "127.0.0.1"}
        self.remote: dict[str, list[tuple]] = {}

    def add(self, code, severity, route, message, fix, file=None, line=None, selector=None, url=None, key=None):
        short = route.lstrip("/") or "/"
        base = f"static:{code}:{short}:{line if line is not None else (key or '')}"
        count = self.seen.get(base, 0)
        self.seen[base] = count + 1
        item = {
            "id": base if count == 0 else f"{base}:{count + 1}",
            "tier": "static",
            "severity": severity,
            "code": code,
            "route": route,
            "message": message,
            "fix": fix,
        }
        if file is not None:
            item["file"] = file
        if line is not None:
            item["line"] = line
        if selector is not None:
            item["selector"] = selector
        if url is not None:
            item["url"] = url
        self.problems.append(item)

    def page(self, rel: str) -> Page | None:
        if rel not in self.pages:
            parsed: Page | None = None
            if self.index.files.get(rel, 0) <= 16 * MIB:
                parsed = Page()
                try:
                    parsed.feed(_read_text(self.root / rel))
                    parsed.close()
                except Exception:
                    pass
            self.pages[rel] = parsed
        return self.pages[rel]

    def html_files(self) -> list[str]:
        return sorted(r for r in self.index.files if r.lower().endswith((".html", ".htm")))

    def route_of(self, rel: str) -> str:
        return self.file_route.get(rel) or "/" + rel

    def is_own(self, host: str | None) -> bool:
        return bool(host) and host.lower() in self.own_hosts

    def collect_routes(self) -> list[str]:
        source, rows = intake.routes_of(self.root)
        routes = []
        for row in rows:
            path = row.get("path")
            if not isinstance(path, str):
                continue
            if not path.startswith("/"):
                path = "/" + path
            if path in self.route_file:
                continue
            kind, rel, _status = self.index.resolve(path)
            if kind != "file":
                page = row.get("page")
                rel = page.lstrip("/") if isinstance(page, str) and page.lstrip("/") in self.index.files else None
            if rel is None:
                continue
            self.route_file[path] = rel
            self.file_route.setdefault(rel, path)
            if isinstance(row.get("locale"), str) and row["locale"].strip():
                self.route_locale[path] = row["locale"].strip()
            routes.append(path)
        return sorted(routes)

    def collect_hosts(self) -> None:
        for rel in self.html_files():
            page = self.page(rel)
            if page is not None and page.canonical:
                host = urlsplit(page.canonical).hostname
                if host:
                    self.own_hosts.add(host.lower())
        if "sitemap.xml" in self.index.files:
            for loc in SITEMAP_LOC.findall(_read_text(self.root / "sitemap.xml")):
                host = urlsplit(html.unescape(loc)).hostname
                if host:
                    self.own_hosts.add(host.lower())

    def target_path(self, rel: str, page: Page | None, url: str) -> tuple[str, str, bool] | None:
        if url.startswith("//"):
            parts = urlsplit("http:" + url)
        elif SKIP_SCHEME.match(url):
            return None
        else:
            parts = urlsplit(url)
        if parts.scheme or url.startswith("//"):
            return ("ext", parts.hostname or "", False) if not self.is_own(parts.hostname) else ("own", parts.path or "/", True)
        base_dir = "/" + posixpath.dirname(rel) + "/" if posixpath.dirname(rel) else "/"
        if page is not None and page.base:
            base_parts = urlsplit(page.base)
            if not base_parts.scheme and not page.base.startswith("//"):
                base_dir = urljoin(base_dir, page.base.split("#")[0].split("?")[0])
        if not parts.path:
            return "self", "", False
        joined = urljoin("http://fp.invalid" + base_dir, parts.path)
        return "int", urlsplit(joined).path or "/", False

    def check_assets(self, rel: str, route: str, page: Page | None, refs: list[dict]) -> None:
        for ref in refs:
            url = ref["url"]
            if url.startswith("#") or SKIP_SCHEME.match(url):
                continue
            target = self.target_path(rel, page, url)
            if target is None:
                continue
            kind, value, _ = target
            if kind == "ext":
                self.external(rel, route, ref, url)
                continue
            if kind == "self":
                continue
            result = self.index.resolve(value)
            if result[0] == "none":
                self.add(
                    "asset.missing", "error", route,
                    f"The file {url} does not exist.",
                    "Add the file in FormWeb or correct the path.",
                    file=rel, line=ref.get("line"), selector=ref.get("selector"), url=url, key=url,
                )

    def external(self, rel: str, route: str, ref: dict, url: str) -> None:
        if ref.get("tag") == "script" and analytics_src(url):
            return
        self.remote.setdefault(url, []).append((route, rel, ref.get("line"), ref.get("selector")))

    def report_external(self) -> None:
        for url, refs in self.remote.items():
            refs = sorted(refs, key=lambda r: (r[0], r[2] or 0))
            route, rel, line, selector = refs[0]
            pages = sorted({r[0] for r in refs})
            if len(refs) == 1:
                message = f"The page loads {url} from another host."
            else:
                message = f"The site loads {url} from another host: {len(refs)} references on {', '.join(pages)}."
            self.add(
                "external.request", "warning", route, message,
                "Copy the file into the site and link to the local copy.",
                file=rel, line=line, selector=selector, url=url, key=url,
            )
            self.problems[-1]["count"] = len(refs)
            self.problems[-1]["pages"] = pages

    def check_html(self, rel: str) -> None:
        page = self.page(rel)
        if page is None:
            return
        route = self.route_of(rel)
        routed = rel in self.file_route
        for url, line in page.links:
            target = self.target_path(rel, page, url)
            if target is None or target[0] == "ext":
                continue
            kind, value, _ = target
            frag = ""
            if "#" in url:
                frag = unquote(url.split("#", 1)[1])
            selector = f'a[href="{url}"]'
            if kind == "self":
                dest = rel
            else:
                result = self.index.resolve(value)
                if result[0] == "none":
                    self.add(
                        "link.broken", "error", route,
                        f"The link to {url} has no page.",
                        "Remove the link or add the page in FormWeb.",
                        file=rel, line=line, selector=selector, url=url, key=url,
                    )
                    continue
                if result[0] != "file":
                    continue
                dest = result[1]
            if not frag or frag == "top" or frag.startswith(("/", "!")):
                continue
            if not dest.lower().endswith((".html", ".htm")):
                continue
            target_page = self.page(dest)
            if target_page is not None and frag not in target_page.ids:
                self.add(
                    "link.anchor", "warning", route,
                    f"The link to {url} points at #{frag}, which is not on that page.",
                    "Add an element with that id or correct the fragment.",
                    file=rel, line=line, selector=selector, url=url, key=url,
                )
        refs = []
        for asset in page.assets:
            asset = dict(asset)
            asset["selector"] = f'{asset["tag"]}[{asset["attr"]}="{asset["url"]}"]'
            refs.append(asset)
        for line, text in page.styles:
            for url, offset in css_refs(text):
                if url.startswith("data:"):
                    continue
                refs.append({"tag": "style", "attr": "url", "url": url, "line": line + offset - 1, "selector": None})
        self.check_assets(rel, route, page, refs)
        for line, attrs in page.images:
            src = attrs.get("src", "")
            selector = f'img[src="{src}"]' if src else "img"
            if "data-fw-poster" not in attrs and not (attrs.get("width", "").strip() and attrs.get("height", "").strip()) and "aspect-ratio" not in attrs.get("style", "").lower():
                self.add(
                    "img.size", "warning", route,
                    f"The image {src or '(no source)'} has no width and height.",
                    "Add width and height attributes so the page does not shift while it loads.",
                    file=rel, line=line, selector=selector, url=src or None, key=src,
                )
            if "alt" not in attrs:
                self.add(
                    "img.alt", "warning", route,
                    f"The image {src or '(no source)'} has no alt attribute.",
                    "Describe the image in alt text, or use an empty alt for decoration.",
                    file=rel, line=line, selector=selector, url=src or None, key=src,
                )
        self.check_a11y(rel, route, page)
        self.check_forms(rel, route, page)
        if not routed:
            return
        if page.title is None or not page.title:
            self.add(
                "meta.title", "error", route, "The page has no title.",
                "Add a title in the page settings.", file=rel,
            )
        elif len(page.title) > 60:
            self.add(
                "meta.title", "warning", route,
                f"The title is {len(page.title)} characters long.",
                "Shorten the title to 60 characters or fewer.", file=rel,
            )
        if page.description is None or not page.description.strip():
            self.add(
                "meta.description", "warning", route, "The page has no meta description.",
                "Add a description of up to 160 characters in the page settings.", file=rel,
            )
        elif len(page.description) > 160:
            self.add(
                "meta.description", "warning", route,
                f"The meta description is {len(page.description)} characters long.",
                "Shorten the description to 160 characters or fewer.", file=rel,
            )
        if not (page.lang or "").strip():
            self.add(
                "meta.lang", "warning", route, "The html element has no lang attribute.",
                "Set the page language so browsers and screen readers pick the right rules.", file=rel,
            )
        h1 = [h for h in page.headings if h[0] == 1]
        if len(h1) != 1:
            self.add(
                "heading.h1", "warning", route,
                "The page has no h1." if not h1 else f"The page has {len(h1)} h1 headings.",
                "Use exactly one h1 heading per page.", file=rel, line=h1[1][1] if len(h1) > 1 else None,
            )
        previous = 0
        for level, line in page.headings:
            if previous and level > previous + 1:
                self.add(
                    "heading.order", "info", route,
                    f"The heading level jumps from h{previous} to h{level}.",
                    "Use heading levels in order without skipping.", file=rel, line=line,
                )
            previous = level
        self.check_share(rel, route, page)

    def check_a11y(self, rel: str, route: str, page: Page) -> None:
        for line, href in page.unnamed_links:
            self.add(
                "a11y.link-name", "warning", route,
                f"The link to {href} has no text a screen reader can announce.",
                "Add link text, an aria-label, or alt text on the image inside the link.",
                file=rel, line=line, selector=f'a[href="{href}"]', url=href, key=href,
            )
        for line, tag, attrs, wrapped in page.controls:
            ident = attrs.get("id", "").strip()
            if wrapped or (ident and ident in page.label_for):
                continue
            if any(attrs.get(k, "").strip() for k in ("aria-label", "aria-labelledby", "title")):
                continue
            name = attrs.get("name", "").strip()
            kind = (attrs.get("type", "").strip().lower() or "text") if tag == "input" else tag
            what = f"{kind} field named {name}" if name else f"{kind} field"
            if name:
                selector = f'{tag}[name="{name}"]'
            elif ident:
                selector = f"#{ident}"
            else:
                selector = tag
            self.add(
                "a11y.label", "warning", route,
                f"The {what} has no label.",
                "Add a label linked to the field with for, or an aria-label, so screen readers can name it.",
                file=rel, line=line, selector=selector, key=name or ident,
            )

    def check_share(self, rel: str, route: str, page: Page) -> None:
        canonicals = [c for c in page.canonicals if c]
        if not canonicals and not page.noindex:
            self.add(
                "seo.canonical", "warning", route, "The page has no canonical link.",
                "Set the site address in FormWeb so each page names its canonical URL.", file=rel,
            )
        elif len(page.canonicals) > 1:
            self.add(
                "seo.canonical", "warning", route, f"The page has {len(page.canonicals)} canonical links.",
                "Keep one canonical link per page.", file=rel,
            )
        for href in canonicals[:1]:
            parts = urlsplit(href)
            if parts.scheme not in ("http", "https") or not parts.netloc:
                self.add(
                    "seo.canonical", "warning", route, f"The canonical link {href} is not an absolute URL.",
                    "Use the full address, starting with https://.", file=rel, url=href, key=href,
                )
        missing = [p for p in OG_REQUIRED if not page.og.get(p)]
        if missing:
            self.add(
                "seo.og", "info", route,
                f"The page has no {missing[0]} Open Graph tag." if len(missing) == 1 else f"The page has none of these Open Graph tags: {', '.join(missing)}.",
                "Add og:title, og:type, og:image and og:url so links to the page show a full preview.", file=rel,
            )
        image = page.og.get("og:image")
        if image:
            parts = urlsplit(image)
            if parts.scheme not in ("http", "https") or not parts.netloc:
                self.add(
                    "seo.og", "info", route, f"The og:image {image} is not an absolute URL.",
                    "Use the full address of the image, starting with https://.", file=rel, url=image, key=image,
                )
        for line, text in page.jsonld:
            try:
                json.loads(text)
            except ValueError as exc:
                self.add(
                    "seo.jsonld", "error", route,
                    f"The structured data block is not valid JSON: {getattr(exc, 'msg', str(exc))}.",
                    "Correct the JSON-LD in the page, or remove the block.", file=rel, line=line,
                )

    def own_file(self, href: str) -> str | None:
        parts = urlsplit(href)
        if parts.scheme not in ("http", "https") or not self.is_own(parts.hostname):
            return None
        kind, found, _status = self.index.resolve(self.index.local(parts.path or "/"))
        return found if kind == "file" else None

    def check_hreflang(self, routes: list[str]) -> None:
        lists: dict[str, dict[str, tuple[str, str]]] = {}
        for route in routes:
            rel = self.route_file[route]
            page = self.page(rel)
            if page is None:
                continue
            lists[rel] = {}
            for lang, href, _line in page.alternates:
                found = self.own_file(href)
                if found is not None and found not in lists[rel]:
                    lists[rel][found] = (lang, href)
        for route in routes:
            rel = self.route_file[route]
            page = self.page(rel)
            if page is None or rel not in lists:
                continue
            for lang, href, line in page.alternates:
                if not HREFLANG.match(lang):
                    self.add(
                        "seo.hreflang", "warning", route,
                        f"The hreflang value {lang or '(empty)'} is not a language code or language-region code.",
                        "Use an ISO 639-1 language code with an optional ISO 3166-1 region, such as en or en-GB, or x-default.",
                        file=rel, line=line, url=href or None, key=lang,
                    )
                parts = urlsplit(href)
                if parts.scheme not in ("http", "https") or not parts.netloc:
                    self.add(
                        "seo.hreflang", "warning", route,
                        f"The hreflang link for {lang or '(empty)'} points at {href or '(nothing)'}, which is not a full address.",
                        "Use the full address of each version, starting with https://.",
                        file=rel, line=line, url=href or None, key=href,
                    )
            if page.alternates:
                own = lists[rel].get(rel)
                if own is None and page.canonical not in {h for _l, h, _n in page.alternates}:
                    self.add(
                        "seo.hreflang", "warning", route,
                        "The page's hreflang links do not list the page itself.",
                        "Add an hreflang link for this page's own language that points at its own address.",
                        file=rel,
                    )
                locale = self.route_locale.get(route)
                if own is not None and locale and own[0].lower() != "x-default":
                    if own[0].split("-")[0].lower() != locale.replace("_", "-").split("-")[0].lower():
                        self.add(
                            "seo.hreflang", "warning", route,
                            f"The page lists itself as {own[0]}, but the route's locale is {locale}.",
                            "Make the page's own hreflang value match its locale.",
                            file=rel, url=own[1], key=own[1],
                        )
            for other in sorted(lists):
                if other == rel or rel not in lists[other] or other in lists[rel]:
                    continue
                lang, _href = lists[other][rel]
                back = self.route_of(other)
                self.add(
                    "seo.hreflang", "warning", route,
                    f"The page at {back} lists this page as its {lang} version, but this page has no hreflang link back to {back}.",
                    "List every language version on each version, this page included, so the links go both ways.",
                    file=rel, url=back, key=back,
                )

    def check_site(self, routes: list[str]) -> None:
        if not routes:
            return
        home = self.index.lookup("/")
        page = self.page(home) if home else None
        if not (page is not None and page.icon) and "favicon.ico" not in self.index.files:
            self.add(
                "site.favicon", "warning", "/", "The site has no favicon.",
                "Add a site icon in FormWeb, or put favicon.ico at the root of the site.", file=home,
            )
        if "404.html" not in self.index.files and "404/index.html" not in self.index.files:
            self.add(
                "site.404", "warning", "/", "The site has no 404 page.",
                "Add a page at /404 in FormWeb so hosts show it for addresses that do not exist.",
            )

    def check_analytics(self, routes: list[str]) -> None:
        files = sorted({self.route_file[r] for r in routes} if routes else self.html_files(), key=self.route_of)
        found: dict[str, list[str]] = {}
        counted = []
        for rel in files:
            page = self.page(rel)
            if page is None:
                continue
            for name in analytics_of(page):
                found.setdefault(name, []).append(rel)
            if not page.noindex and rel not in ("404.html", "404/index.html"):
                counted.append(rel)
        for name in sorted(found):
            lacking = [rel for rel in counted if rel not in found[name]]
            if lacking:
                missing = [self.route_of(rel) for rel in lacking]
                shown = ", ".join(missing[:5]) + (f" and {len(missing) - 5} more" if len(missing) > 5 else "")
                self.add(
                    "analytics.partial", "warning", missing[0],
                    f"{name} is on {len(counted) - len(missing)} of {len(counted)} pages; it is missing from {shown}.",
                    "Add the same snippet to the site's head in FormWeb so it is on every page. " + ANALYTICS_FIX,
                    file=lacking[0], key=name,
                )
            if name == "Google Analytics":
                self.add(
                    "analytics.cookies", "info", self.route_of(found[name][0]),
                    "The site loads the Google tag from googletagmanager.com. Google Analytics sets cookies (_ga) in visitors' browsers.",
                    ANALYTICS_FIX, file=found[name][0], key=name,
                )

    def form_problem(self, rel: str, route: str, page: Page, action: str, posts: bool) -> tuple[str, str] | None:
        nothing = "so it will send nothing once the site is on a static host."
        if not action or action.startswith("#"):
            if not posts:
                return None
            return "forms.no-endpoint", f"The form on {route} posts to {action or 'no address'} ({'it has no action' if not action else 'the page itself'}), {nothing}"
        target = self.target_path(rel, page, action)
        if target is None:
            return None
        if target[0] == "ext" or target[0] == "own":
            host = urlsplit("http:" + action if action.startswith("//") else action).hostname or ""
            if local_host(host):
                return "forms.local-address", f"The form on {route} sends to {action}, which will not answer once the site is published, so the form will not send."
            if target[0] == "ext":
                return None
        path = self.index.local(target[1]) if target[0] != "self" else ""
        if path.startswith(FORMS_PATH):
            return "forms.no-endpoint", f"The form on {route} sends to {action}, FormWeb's own form route, {nothing}"
        if not posts:
            return None
        return "forms.no-endpoint", f"The form on {route} posts to {action}, an address on the site itself, {nothing}"

    def check_forms(self, rel: str, route: str, page: Page) -> None:
        for index, (line, attrs) in enumerate(page.forms):
            fields = page.form_fields[index] if index < len(page.form_fields) else []
            action = attrs.get("action", "").strip()
            name = attrs.get("name", "").strip()
            posts = attrs.get("method", "").strip().lower() == "post"
            netlify = "netlify" in attrs or attrs.get("data-netlify", "").strip().lower() == "true"
            selector = f'form[action="{action}"]' if action else (f'form[name="{name}"]' if name else "form")
            found = None if netlify else self.form_problem(rel, route, page, action, posts)
            if netlify and not name:
                found = "forms.no-endpoint", f"The form on {route} has Netlify's form attribute but no name, and Netlify needs a name for each form, so it will send nothing once the site is on a static host."
            if found is not None:
                self.add(found[0], "error", route, found[1], FORMS_FIX, file=rel, line=line, selector=selector, url=action or None, key=action or name)
                continue
            if not (posts or netlify):
                continue
            if action.lower().rstrip("/") == WEB3FORMS and not any(
                tag == "input" and a.get("name", "").strip() == "access_key" and a.get("value", "").strip() for _l, tag, a in fields
            ):
                self.add(
                    "forms.access-key", "error", route,
                    f"The form on {route} posts to Web3Forms but has no hidden access_key field with a value, so Web3Forms cannot deliver it.",
                    FORMS_FIX, file=rel, line=line, selector=selector, url=action, key=action,
                )
                continue
            for field_line, tag, a in fields:
                kind = (a.get("type", "").strip().lower() or "text") if tag == "input" else tag
                if kind in UNSENT_TYPES or a.get("name", "").strip() or "disabled" in a:
                    continue
                ident = a.get("id", "").strip()
                self.add(
                    "forms.field-name", "warning", route,
                    f"A field ({kind}) in the form on {route} has no name, so its value is not sent.",
                    "Give the field a name in FormWeb. " + FORMS_FIX,
                    file=rel, line=field_line, selector=f"#{ident}" if ident else tag, key=ident or kind,
                )

    def check_css(self, rel: str) -> None:
        text = _read_text(self.root / rel)
        route = "/" + rel
        refs = []
        for url, line in css_refs(text):
            if url.startswith("data:"):
                continue
            refs.append({"tag": "css", "attr": "url", "url": url, "line": line, "selector": None})
        self.check_assets(rel, route, None, refs)

    def check_js(self, rel: str) -> None:
        text = _read_text(self.root / rel)
        for m in JS_EXTERNAL.finditer(text):
            host = urlsplit(m.group(2)).hostname
            if self.is_own(host):
                continue
            self.external(rel, "/" + rel, {"line": text.count("\n", 0, m.start()) + 1, "selector": None}, m.group(2))

    def check_redirects(self) -> None:
        for rule in self.index.rules:
            src = rule["from"]
            target = rule["to"]
            if rule["splat"] or SKIP_SCHEME.match(target) or target.startswith(("http://", "https://", "//")):
                continue
            tpath = _norm(unquote(urlsplit(target).path) or "/")
            seen = [_norm(src)]
            current = tpath
            looped = False
            while True:
                if current in seen:
                    looped = True
                    break
                seen.append(current)
                kind, value, _status = self.index.resolve(current)
                if kind != "redirect":
                    break
                if SKIP_SCHEME.match(value) or value.startswith(("http://", "https://", "//")):
                    break
                current = _norm(unquote(urlsplit(value).path) or "/")
            if looped:
                self.add(
                    "redirect.loop", "error", src,
                    f"The redirect from {src} loops back to {current}.",
                    "Change one redirect so the chain ends at a page.",
                    file="redirects.json", url=target, key=target,
                )
                continue
            kind, _value, _status = self.index.resolve(tpath)
            if kind == "none":
                self.add(
                    "redirect.target", "error", src,
                    f"The redirect from {src} goes to {target}, which has no page.",
                    "Point the redirect at a page that exists.",
                    file="redirects.json", url=target, key=target,
                )
            elif kind == "redirect":
                self.add(
                    "redirect.chain", "warning", src,
                    f"The redirect from {src} goes to {target}, which is redirected again.",
                    "Point the redirect straight at the final page.",
                    file="redirects.json", url=target, key=target,
                )

    def check_seo(self, routes: list[str]) -> None:
        sitemap_present = "sitemap.xml" in self.index.files
        if sitemap_present:
            locs = [html.unescape(x) for x in SITEMAP_LOC.findall(_read_text(self.root / "sitemap.xml"))]
            listed = {_route_key(self.index.local(urlsplit(loc).path or "/")) for loc in locs}
            for route in routes:
                page = self.page(self.route_file[route])
                if page is not None and page.noindex:
                    continue
                if _route_key(route) not in listed:
                    self.add(
                        "sitemap.missing", "warning", route, "The route is not listed in sitemap.xml.",
                        "Add the page to the sitemap, or mark it noindex.", file="sitemap.xml",
                    )
            for loc in locs:
                path = urlsplit(loc).path or "/"
                if self.index.resolve(path)[0] == "none":
                    self.add(
                        "sitemap.extra", "warning", path, f"The sitemap lists {loc}, which has no page.",
                        "Remove the entry from sitemap.xml or add the page.",
                        file="sitemap.xml", url=loc, key=loc,
                    )
        elif routes:
            self.add(
                "sitemap.missing", "warning", "/", "The site has no sitemap.xml.",
                "Generate a sitemap so search engines find every page.", file="sitemap.xml",
            )
        if "robots.txt" in self.index.files:
            lines = [ln.split("#", 1)[0].strip() for ln in _read_text(self.root / "robots.txt").splitlines()]
            sitemaps = [ln.split(":", 1)[1].strip() for ln in lines if ln.lower().startswith("sitemap:")]
            if not sitemaps or not any(s.rstrip("/").endswith("/sitemap.xml") for s in sitemaps):
                self.add(
                    "robots.sitemap", "warning", "/robots.txt",
                    "robots.txt has no Sitemap line ending in /sitemap.xml.",
                    "Add a Sitemap: line with the full address of sitemap.xml.", file="robots.txt",
                )
            agents: list[str] = []
            collecting = False
            blocked = False
            for ln in lines:
                lower = ln.lower()
                if lower.startswith("user-agent:"):
                    if collecting:
                        agents.append(ln.split(":", 1)[1].strip())
                    else:
                        agents = [ln.split(":", 1)[1].strip()]
                        collecting = True
                elif lower.startswith("disallow:"):
                    collecting = False
                    if "*" in agents and ln.split(":", 1)[1].strip() == "/":
                        blocked = True
                elif ln:
                    collecting = False
            if blocked:
                self.add(
                    "robots.blocks", "warning", "/robots.txt", "robots.txt blocks every crawler from the whole site.",
                    "Remove the Disallow: / line under User-agent: * unless the site should stay hidden.",
                    file="robots.txt",
                )

    def check_budgets(self, routes: list[str]) -> None:
        for rel in sorted(self.index.files):
            size = self.index.files[rel]
            ext = posixpath.splitext(rel)[1].lower()
            mib = size / MIB
            if ext in TEXT_EXT:
                if size > 5 * MIB:
                    severity = "error"
                elif size > MIB:
                    severity = "warning"
                else:
                    continue
                self.add(
                    "budget.file", severity, "/" + rel, f"{rel} is {mib:.1f} MiB.",
                    "Split or minify the file so it stays under 1 MiB.", file=rel,
                )
            elif ext in MEDIA_EXT and size > 20 * MIB:
                self.add(
                    "budget.file", "warning", "/" + rel, f"{rel} is {mib:.1f} MiB.",
                    "Compress the file or host it elsewhere so it stays under 20 MiB.", file=rel,
                )
        for route in routes:
            rel = self.route_file[route]
            page = self.page(rel)
            if page is None:
                continue
            total = self.index.files.get(rel, 0)
            counted: set[str] = set()
            for asset in page.assets:
                if asset["tag"] not in ("script", "link"):
                    continue
                target = self.target_path(rel, page, asset["url"])
                if target is None or target[0] not in ("int", "own"):
                    continue
                kind, found, _ = self.index.resolve(target[1])
                if kind != "file" or found in counted:
                    continue
                if posixpath.splitext(found)[1].lower() not in (".css", ".js", ".mjs"):
                    continue
                counted.add(found)
                total += self.index.files.get(found, 0)
            if total > 500 * KIB:
                self.add(
                    "budget.page", "warning", route,
                    f"The page, its CSS and its scripts total {total // KIB} KiB.",
                    "Trim the page or split large scripts and styles to stay under 500 KiB.", file=rel,
                )

    def run(self) -> list[dict]:
        routes = self.collect_routes()
        self.collect_hosts()
        for rel in self.html_files():
            self.check_html(rel)
        for rel in sorted(self.index.files):
            ext = posixpath.splitext(rel)[1].lower()
            if ext == ".css":
                self.check_css(rel)
            elif ext in (".js", ".mjs"):
                self.check_js(rel)
        self.report_external()
        self.check_redirects()
        self.check_seo(routes)
        self.check_hreflang(routes)
        self.check_site(routes)
        self.check_analytics(routes)
        self.check_budgets(routes)
        self.problems.sort(key=lambda p: (p["route"], p["code"], p.get("line") or 0, p["id"]))
        return self.problems


def run_static(root: Path) -> list[dict]:
    return Runner(root).run()


def _results_file(site: str, revision: str) -> Path:
    return checks_dir(site, revision) / "results.json"


def load_results(site: str, revision: str) -> dict:
    data = _read_json(_results_file(site, revision))
    return data if isinstance(data, dict) else {}


def store_tier(site: str, revision: str, tier: str, payload: dict) -> None:
    with _lock:
        target = _results_file(site, revision)
        data = load_results(site, revision)
        data[tier] = {"ranAt": now_iso(), **payload}
        tmp = target.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(tmp, target)


def _clip(value, limit: int) -> str:
    return str(value)[:limit]


def merge_live(site: str, revision: str, problems: list) -> int:
    checks_dir(site, revision)
    if not isinstance(problems, list):
        raise ValueError("problems must be a list")
    with _lock:
        bucket = _live.setdefault((site, revision), {})
        for row in problems:
            if not isinstance(row, dict):
                continue
            ident = row.get("id")
            severity = row.get("severity")
            if not isinstance(ident, str) or not ident or severity not in SEVERITIES:
                continue
            if ident not in bucket and len(bucket) >= MAX_LIVE:
                continue
            item = {
                "id": _clip(ident, 300),
                "tier": "live",
                "severity": severity,
                "code": _clip(row.get("code", "live.event"), 80),
                "route": _clip(row.get("route", "/"), 500),
                "message": _clip(row.get("message", ""), 1000),
                "fix": _clip(row.get("fix", ""), 500),
            }
            for key in ("file", "selector", "url"):
                if isinstance(row.get(key), str):
                    item[key] = _clip(row[key], 500)
            if isinstance(row.get("line"), int) and not isinstance(row.get("line"), bool):
                item["line"] = row["line"]
            bucket[item["id"]] = item
        return len(bucket)


def clear_live(site: str, revision: str) -> None:
    with _lock:
        _live.pop((site, revision), None)


def report(site: str, revision: str) -> dict:
    with _lock:
        stored = load_results(site, revision)
        live = list(_live.get((site, revision), {}).values())
    problems: list[dict] = []
    ran: list[str] = []
    thumbs: dict[str, str] = {}
    measures: list[dict] = []
    for tier in ("static", "deep"):
        block = stored.get(tier)
        if isinstance(block, dict):
            ran.append(tier)
            problems.extend(p for p in block.get("problems", []) if isinstance(p, dict))
            if tier == "deep" and isinstance(block.get("thumbs"), dict):
                for route, name in block["thumbs"].items():
                    thumbs[route] = f"/api/checks/{site}/{revision}/thumbs/{name}.png"
            if tier == "deep" and isinstance(block.get("measures"), list):
                measures = [m for m in block["measures"] if isinstance(m, dict)]
    if live:
        ran.append("live")
        problems.extend(live)
    counts = {tier: 0 for tier in TIERS}
    for p in problems:
        if p.get("tier") in counts:
            counts[p["tier"]] += 1
    return {
        "problems": problems,
        "summary": {
            "errors": sum(1 for p in problems if p.get("severity") == "error"),
            "warnings": sum(1 for p in problems if p.get("severity") == "warning"),
            "infos": sum(1 for p in problems if p.get("severity") == "info"),
            "tiers": counts,
            "ran": ran,
        },
        "thumbs": thumbs,
        "measures": measures,
        "inp": "not measured",
    }


def summarize(site: str, revision: str) -> dict:
    return report(site, revision)["summary"]


def thumb_path(site: str, revision: str, name: str) -> Path | None:
    if not re.match(r"^[0-9a-f]{40}$", name or ""):
        return None
    target = checks_dir(site, revision) / "thumbs" / f"{name}.png"
    return target if target.is_file() else None
