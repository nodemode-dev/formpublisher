import html
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from app.targets._common import PreparedInput, PreparedResult, copy_site, is_splat, ordered_redirects, put

ID = "github-pages"
NAME = "GitHub Pages"
DESCRIPTION = "A gh-pages branch or an Actions workflow, with a 404 page that also follows folder redirects, and meta-refresh redirects."
LOCAL_TOOL = "python3 -m http.server -d site 8080"

MINIMAL_404 = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Page not found</title>
</head>
<body>
<h1>Page not found</h1>
<p><a href="/">Back to the home page</a></p>
</body>
</html>
"""

STUB = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Redirecting</title>
<link rel="canonical" href="{to}">
<meta http-equiv="refresh" content="0; url={to}">
<meta name="robots" content="noindex">
</head>
<body>
<p>This page moved to <a href="{to}">{to}</a>.</p>
</body>
</html>
"""

WORKFLOW = """name: Publish site to GitHub Pages

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: site
      - id: deployment
        uses: actions/deploy-pages@v4
"""

NOTE_HEAD = """Redirects on GitHub Pages

GitHub Pages has no server redirects.
"""

NOTE = """
Each redirect below became a small page with a meta refresh and a canonical link, written
into site/ at the old address. Browsers and search engines follow them, but the status is
a plain 200, not the 301 or 302 in publish.json.

{rows}
"""

SPLAT_NOTE = """
Each splat redirect below is a rule in a small script at the top of site/404.html. When a
visitor opens a path that is not a page, GitHub Pages answers with the 404 page, the script
sends the browser to the new address (keeping the query and the hash) and the longest
matching prefix wins. The browser follows them, but the status is the 404 page's 404, not
the 301 or 302 in publish.json. The script assumes the site lives under {base}.

{rows}
"""

SCRIPT = """<script>(function(){{var b={base},r={rules},p=location.pathname.replace(/\\/+$/,"")||"/",i,x,t;
if(b){{if(p.indexOf(b+"/")!==0)return;p=p.slice(b.length)}}
for(i=0;i<r.length;i++){{x=r[i][0];if(p.indexOf(x+"/")===0){{
t=r[i][1].split(":splat").join(p.slice(x.length+1).replace(/^[\\/\\\\]+/,""));
if(t!==location.pathname)location.replace(t+location.search+location.hash);return}}}}}})();</script>"""

HEAD_OPEN = re.compile(rb"<head(?:\s[^>]*)?>", re.I)
HTML_OPEN = re.compile(rb"<html(?:\s[^>]*)?>", re.I)
META_CHARSET = re.compile(rb"\s*<meta\s[^>]*charset[^>]*>", re.I)
LINK_TAG = re.compile(rb"<link\s[^>]*>", re.I)
CANONICAL_HREF = re.compile(rb"""href\s*=\s*["']([^"']*)["']""", re.I)


def _stub_path(source: str) -> str:
    path = source.split("?")[0].split("#")[0].strip("/")
    last = path.rsplit("/", 1)[-1]
    if "." in last:
        return path
    return f"{path}/index.html" if path else "index.html"


def _url_path(url: str) -> str | None:
    parts = urlsplit(url.strip())
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return None
    return parts.path.rstrip("/")


def _base_path(inp: PreparedInput, page: bytes) -> tuple[str, str]:
    """The path the site is served under and where it came from: the model's baseUrl, the 404 page's canonical link, or the root."""
    model = inp.root / "site.formweb.json"
    if model.is_file():
        try:
            settings = json.loads(model.read_text(encoding="utf-8")).get("settings")
            found = _url_path(settings["baseUrl"]) if isinstance(settings, dict) and isinstance(settings.get("baseUrl"), str) else None
        except (OSError, ValueError, AttributeError):
            found = None
        if found is not None:
            return found, "the site's base URL"
    for tag in LINK_TAG.findall(page):
        if re.search(rb"""rel\s*=\s*["']?canonical""", tag, re.I):
            href = CANONICAL_HREF.search(tag)
            found = _url_path(href.group(1).decode("utf-8", "replace")) if href else None
            if found is not None:
                return re.sub(r"/404(?:\.html|/index\.html)?$", "", found), "the canonical link of the 404 page"
    return "", "the default"


def _splat_rules(inp: PreparedInput, base: str, result: PreparedResult) -> list[list[str]]:
    found: dict[str, str] = {}
    for row in inp.redirects:
        if not is_splat(row):
            continue
        source, target = row["from"], row["to"]
        if not source.startswith("/") or not source.endswith("/*") or re.search(r"\s", source + target):
            result.warnings.append(f"The splat redirect {source!r} is not written as /path/* and was skipped.")
            continue
        if target.startswith(("https://", "http://")):
            full = target
        elif target.startswith("/"):
            full = base + target
        else:
            result.warnings.append(f"The splat redirect {source} was skipped because its target {target!r} is neither a path nor an http(s) address.")
            continue
        found[source[:-2].rstrip("/")] = full
    return sorted(([prefix, full] for prefix, full in found.items()), key=lambda rule: -len(rule[0]))


def rewritten(inp: PreparedInput) -> set[str]:
    """Files of the build this target changes on purpose, so verify compares them with a fresh prepare instead of publish.json."""
    return {"404.html"} if _splat_rules(inp, "", PreparedResult()) else set()


def _script_tag(base: str, rules: list[list[str]]) -> bytes:
    def literal(value) -> str:
        return json.dumps(value, ensure_ascii=True).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")

    return SCRIPT.format(base=literal(base), rules=literal(rules)).encode("ascii")


def _place_script(page: bytes, tag: bytes) -> bytes:
    """Put the script first in <head>, after a leading meta charset when there is one."""
    head = HEAD_OPEN.search(page)
    if head:
        at = head.end()
        charset = META_CHARSET.match(page, at)
        if charset:
            at = charset.end()
        return page[:at] + tag + page[at:]
    root = HTML_OPEN.search(page)
    if root:
        return page[: root.end()] + b"<head>" + tag + b"</head>" + page[root.end() :]
    return tag + page


def prepare(inp: PreparedInput, out: Path) -> PreparedResult:
    result = PreparedResult()
    site = out / "site"
    copy_site(inp, site)
    put(out, "site/.nojekyll", "")
    if inp.has_404:
        result.notes.append("The site's own 404.html is used for unknown paths.")
        if inp.fallback_404:
            result.notes.append("This export has 404/index.html and no 404.html, so it was copied to 404.html as the 404 page.")
    else:
        put(out, "site/404.html", MINIMAL_404.replace('<a href="/">', f'<a href="{html.escape(_base_path(inp, b"")[0], quote=True)}/">'))
        result.notes.append("The site has no 404.html, so a minimal one was added.")
    listed = []
    splats = []
    page_path = out / "site/404.html"
    base, base_source = _base_path(inp, page_path.read_bytes())
    rules = _splat_rules(inp, base, result)
    if rules:
        put(out, "site/404.html", _place_script(page_path.read_bytes(), _script_tag(base, rules)))
        shown = base or "/"
        result.notes.append(f"{len(rules)} splat redirect(s) are followed by a script at the top of site/404.html; it assumes the site is served under {shown} (from {base_source}).")
        splats = [f"{row['from']} -> {row['to']} (the 404 page redirects the browser)" for row in ordered_redirects(inp) if is_splat(row) and any(row["from"][:-2].rstrip("/") == rule[0] for rule in rules)]
    for row in ordered_redirects(inp):
        if is_splat(row):
            continue
        if not re.match(r"^/[^\s]*$", row["from"]) or row["from"] == "/":
            result.warnings.append(f"The redirect {row['from']!r} cannot be written as a page and was skipped.")
            continue
        rel = _stub_path(row["from"])
        if rel in inp.names or (site / rel).exists():
            result.warnings.append(f"The redirect {row['from']} was skipped because the site already has a page at {rel}.")
            continue
        to = base + row["to"] if row["to"].startswith("/") and not row["to"].startswith("//") else row["to"]
        put(out, f"site/{rel}", STUB.format(to=html.escape(to, quote=True)))
        listed.append(f"{row['from']} -> {to} ({row['status']}) as site/{rel}")
    if listed or splats:
        text = NOTE_HEAD
        if listed:
            text += NOTE.format(rows="\n".join(listed))
        if splats:
            text += SPLAT_NOTE.format(rows="\n".join(splats), base=base or "/")
        put(out, "redirects/README.txt", text)
    if listed:
        result.notes.append(f"{len(listed)} redirect(s) became meta-refresh pages; see redirects/README.txt.")
    for pattern, values in [(r["for"], r["values"]) for r in inp.headers]:
        result.warnings.append(f"GitHub Pages ignores custom headers, so {', '.join(sorted(values))} for {pattern} will not be sent.")
    put(out, ".github/workflows/pages.yml", WORKFLOW)
    result.command("Start a repository for the site", "git init -b gh-pages", "site")
    result.command("Stage the files", "git add -A", "site")
    result.command("Commit", 'git commit -m "Publish site"', "site")
    result.command("Add your repository", "git remote add origin git@github.com:OWNER/REPO.git", "site")
    result.command("Push the gh-pages branch", "git push -u origin gh-pages --force", "site")
    result.command("Look at it locally", "python3 -m http.server -d site 8080")
    result.notes.append("Then set Settings > Pages > Source to the gh-pages branch.")
    result.notes.append("Or copy .github/workflows/pages.yml into your repository (with the site/ folder) and set Pages > Source to GitHub Actions.")
    result.notes.append(".nojekyll stops GitHub from running Jekyll over the files.")
    return result
