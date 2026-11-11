import html
import re
from pathlib import Path

from app.targets._common import PreparedInput, PreparedResult, copy_site, is_splat, ordered_redirects, put

ID = "github-pages"
NAME = "GitHub Pages"
DESCRIPTION = "A gh-pages branch or an Actions workflow, with a 404 page and meta-refresh redirects."
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

NOTE = """Redirects on GitHub Pages

GitHub Pages has no server redirects. Each redirect below became a small page with a
meta refresh and a canonical link, written into site/ at the old address. Browsers and
search engines follow them, but the status is a plain 200, not the 301 or 302 in publish.json.

{rows}
"""


def _stub_path(source: str) -> str:
    path = source.split("?")[0].split("#")[0].strip("/")
    last = path.rsplit("/", 1)[-1]
    if "." in last:
        return path
    return f"{path}/index.html" if path else "index.html"


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
        put(out, "site/404.html", MINIMAL_404)
        result.notes.append("The site has no 404.html, so a minimal one was added.")
    listed = []
    for row in ordered_redirects(inp):
        if is_splat(row):
            result.warnings.append(f"The splat redirect {row['from']} cannot be represented on GitHub Pages and was skipped.")
            continue
        if not re.match(r"^/[^\s]*$", row["from"]) or row["from"] == "/":
            result.warnings.append(f"The redirect {row['from']!r} cannot be written as a page and was skipped.")
            continue
        rel = _stub_path(row["from"])
        if rel in inp.names or (site / rel).exists():
            result.warnings.append(f"The redirect {row['from']} was skipped because the site already has a page at {rel}.")
            continue
        put(out, f"site/{rel}", STUB.format(to=html.escape(row["to"], quote=True)))
        listed.append(f"{row['from']} -> {row['to']} ({row['status']}) as site/{rel}")
    if listed:
        put(out, "redirects/README.txt", NOTE.format(rows="\n".join(listed)))
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
