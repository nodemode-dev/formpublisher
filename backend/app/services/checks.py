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
        self.headings: list[tuple[int, int]] = []
        self.styles: list[tuple[int, str]] = []
        self.title_buf: list[str] | None = None
        self.style_buf: list[str] | None = None
        self.style_line = 0
        self.svg = 0

    def _asset(self, tag: str, attr: str, url: str | None, line: int) -> None:
        if url and url.strip():
            self.assets.append({"tag": tag, "attr": attr, "url": url.strip(), "line": line})

    def handle_starttag(self, tag, attrs):
        line = self.getpos()[0]
        a = {k: (v if v is not None else "") for k, v in attrs}
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
        elif tag == "link":
            rels = set(a.get("rel", "").lower().split())
            if "canonical" in rels and a.get("href"):
                self.canonical = a["href"]
            if rels & RES_RELS:
                self._asset("link", "href", a.get("href"), line)
        elif tag == "a":
            if a.get("href", "").strip():
                self.links.append((a["href"].strip(), line))
        elif tag == "img":
            self.images.append((line, a))
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
        elif tag == "input" and a.get("type", "").lower() == "image":
            self._asset(tag, "src", a.get("src"), line)
        elif tag == "form":
            self.forms.append((line, a))
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
        if tag == "svg" and self.svg:
            self.svg -= 1
        elif tag == "title" and self.title_buf is not None:
            self.title = "".join(self.title_buf).strip()
            self.title_buf = None
        elif tag == "style" and self.style_buf is not None:
            self.styles.append((self.style_line, "".join(self.style_buf)))
            self.style_buf = None

    def handle_data(self, data):
        if self.title_buf is not None:
            self.title_buf.append(data)
        elif self.style_buf is not None:
            self.style_buf.append(data)


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


class Runner:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.index = SiteIndex(root)
        self.problems: list[dict] = []
        self.seen: dict[str, int] = {}
        self.pages: dict[str, Page | None] = {}
        self.route_file: dict[str, str] = {}
        self.file_route: dict[str, str] = {}
        self.own_hosts: set[str] = {"localhost", "127.0.0.1"}

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
        self.add(
            "external.request", "warning", route,
            f"The page loads {url} from another host.",
            "Copy the file into the site and link to the local copy.",
            file=rel, line=ref.get("line"), selector=ref.get("selector"), url=url, key=url,
        )

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

    def check_forms(self, rel: str, route: str, page: Page) -> None:
        for line, attrs in page.forms:
            action = attrs.get("action", "").strip()
            target = self.target_path(rel, page, action) if action and not action.startswith("#") else None
            if target is None or target[0] == "self":
                continue
            if target[0] == "int":
                if not self.index.local(target[1]).startswith(FORMS_PATH):
                    continue
            elif not local_host(urlsplit("http:" + action if action.startswith("//") else action).hostname or ""):
                continue
            self.add(
                "forms.local-address", "warning", route,
                f"The form on {route} sends to {action}, which will not answer once the site is published, so the form will not send.",
                "In FormWeb, give the form a scripted reply (Motion > Script, trigger Submit), or point its action at a form service on the web.",
                file=rel, line=line, selector=f'form[action="{action}"]', url=action, key=action,
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
        self.check_redirects()
        self.check_seo(routes)
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
    for tier in ("static", "deep"):
        block = stored.get(tier)
        if isinstance(block, dict):
            ran.append(tier)
            problems.extend(p for p in block.get("problems", []) if isinstance(p, dict))
            if tier == "deep" and isinstance(block.get("thumbs"), dict):
                for route, name in block["thumbs"].items():
                    thumbs[route] = f"/api/checks/{site}/{revision}/thumbs/{name}.png"
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
    }


def summarize(site: str, revision: str) -> dict:
    return report(site, revision)["summary"]


def thumb_path(site: str, revision: str, name: str) -> Path | None:
    if not re.match(r"^[0-9a-f]{40}$", name or ""):
        return None
    target = checks_dir(site, revision) / "thumbs" / f"{name}.png"
    return target if target.is_file() else None
