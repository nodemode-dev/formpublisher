from pathlib import Path

import pytest

ORIGIN = "https://example.org"


def page_html(path, title="Home page", body="<h1>Welcome</h1><p>Text</p>", head="", description="A short description of the page.", lang=' lang="en"', canonical=True, og=True):
    parts = ["<!doctype html>", f"<html{lang}>", "<head>", '<meta charset="utf-8">']
    if title is not None:
        parts.append(f"<title>{title}</title>")
    if description is not None:
        parts.append(f'<meta name="description" content="{description}">')
    if canonical:
        parts.append(f'<link rel="canonical" href="{ORIGIN}{path}">')
    if og:
        parts.append(f'<meta property="og:title" content="T">')
        parts.append('<meta property="og:type" content="website">')
        parts.append(f'<meta property="og:image" content="{ORIGIN}/card.png">')
        parts.append(f'<meta property="og:url" content="{ORIGIN}{path}">')
    parts.append(head)
    parts += ["</head>", "<body>", body, "</body>", "</html>"]
    return "\n".join(parts) + "\n"


def sitemap(paths):
    rows = "".join(f"<url><loc>{ORIGIN}{p}</loc></url>" for p in paths)
    return f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{rows}</urlset>\n'


def make_site(root: Path, **index_kw) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "index.html").write_text(page_html("/", **index_kw), encoding="utf-8")
    (root / "about.html").write_text(page_html("/about", title="About us", body='<h1 id="team">About</h1><p><a href="/">Home</a></p>'), encoding="utf-8")
    (root / "404.html").write_text(page_html("/404", title="Not found", body="<h1>Not found</h1>", head='<meta name="robots" content="noindex">', canonical=False), encoding="utf-8")
    (root / "favicon.ico").write_bytes(b"\x00\x00\x01\x00")
    (root / "sitemap.xml").write_text(sitemap(["/", "/about"]), encoding="utf-8")
    (root / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {ORIGIN}/sitemap.xml\n", encoding="utf-8")
    return root


def run(root: Path) -> list[dict]:
    from app.services import checks

    return checks.run_static(root)


def found(problems, code):
    return [p for p in problems if p["code"] == code]


@pytest.fixture
def site(tmp_path):
    return make_site(tmp_path / "site")
