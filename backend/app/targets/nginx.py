import re
from pathlib import Path

from app.targets._common import SAFE_PATH, PreparedInput, PreparedResult, copy_site, is_splat, ordered_redirects, put

ID = "nginx"
NAME = "nginx"
DESCRIPTION = "A server block with try_files, redirects, headers and gzip, plus a docker run line."
LOCAL_TOOL = "nginx -t -c nginx-test.conf"

GZIP_TYPES = "text/plain text/css text/xml text/javascript application/javascript application/json application/xml application/manifest+json image/svg+xml"
TYPES = """        text/html html htm;
        text/css css;
        text/xml xml;
        text/plain txt;
        application/javascript js mjs;
        application/json json;
        application/manifest+json webmanifest;
        image/svg+xml svg;
        image/png png;
        image/jpeg jpg jpeg;
        image/webp webp;
        image/avif avif;
        image/gif gif;
        image/x-icon ico;
        font/woff2 woff2;
        font/woff woff;"""

TEST_CONF = """# FormPublisher: a wrapper so nginx -t can check formpublisher.conf on its own.
daemon off;
pid /tmp/formpublisher-nginx/nginx.pid;
error_log /dev/stderr info;

events {{
    worker_connections 64;
}}

http {{
    access_log off;
    default_type application/octet-stream;
    types {{
{types}
    }}
    include formpublisher.conf;
}}
"""


def _header_lines(values: dict, indent: str) -> list[str]:
    return [f'{indent}add_header {k} "{v.replace(chr(34), chr(92) + chr(34))}" always;' for k, v in sorted(values.items())]


def _cut_rx(text: str) -> str:
    return re.sub(r"([.+?^$(){}|\\\[\]])", r"\\\1", text)


def prepare(inp: PreparedInput, out: Path) -> PreparedResult:
    result = PreparedResult()
    copy_site(inp, out / "site")
    lines = [
        f"# FormPublisher nginx server block for {inp.site_name.replace(chr(10), ' ')}",
        "# Copy site/ to the root below, or change root to where you put it.",
        "server {",
        "    listen 80;",
        "    listen [::]:80;",
        "    server_name _;",
        "    root /usr/share/nginx/html;",
        "    index index.html;",
        "    charset utf-8;",
        "    absolute_redirect off;",
        "",
        "    gzip on;",
        "    gzip_vary on;",
        "    gzip_min_length 256;",
        f"    gzip_types {GZIP_TYPES};",
        "",
    ]
    if inp.has_404:
        lines += ["    error_page 404 /404.html;", ""]
    global_headers: dict = {}
    scoped: list[tuple[str, dict]] = []
    for row in inp.headers:
        if row["for"] in ("/*", "*", "/"):
            global_headers.update(row["values"])
        elif row["for"].endswith("/*") and SAFE_PATH.match(row["for"][:-1]):
            scoped.append((row["for"][:-1], row["values"]))
        else:
            result.warnings.append(f"The header rule for {row['for']} cannot be written as an nginx location and was skipped.")
    lines += _header_lines(global_headers, "    ")
    if global_headers:
        lines.append("")
    for row in ordered_redirects(inp):
        src, dst = row["from"], row["to"]
        src_ok = bool(SAFE_PATH.match(src.replace("*", "")))
        dst_ok = bool(SAFE_PATH.match(dst.replace(":splat", ""))) or bool(re.match(r"^https?://[^\s;{}\"'$]+$", dst))
        if not (src_ok and dst_ok):
            result.warnings.append(f"Skipped the redirect {src!r} because it holds characters nginx needs quoted.")
            continue
        if is_splat(row):
            prefix = src[:-1]
            target = dst.replace(":splat", "$1")
            lines.append(f"    location ~ ^{_cut_rx(prefix)}(.*)$ {{ return {row['status']} {target}; }}")
        else:
            plain = src.rstrip("/") or "/"
            lines.append(f"    location = {plain} {{ return {row['status']} {dst}; }}")
            if plain != "/":
                lines.append(f"    location = {plain}/ {{ return {row['status']} {dst}; }}")
    lines.append("")
    for prefix, values in scoped:
        merged = {**global_headers, **values}
        lines.append(f"    location {prefix} {{")
        lines += _header_lines(merged, "        ")
        lines.append("        try_files $uri $uri/ $uri.html =404;")
        lines.append("    }")
        lines.append("")
    lines += ["    location / {", "        try_files $uri $uri/ $uri.html =404;", "    }", "}"]
    put(out, "formpublisher.conf", "\n".join(lines) + "\n")
    put(out, "nginx-test.conf", TEST_CONF.format(types=TYPES))
    result.command("Prepare a scratch folder for the check", "mkdir -p /tmp/formpublisher-nginx")
    result.command("Check the config", 'nginx -t -p /tmp/formpublisher-nginx/ -c "$PWD/nginx-test.conf"')
    result.command(
        "Run it in Docker",
        'docker run --rm -p 8080:80 -v "$PWD/site:/usr/share/nginx/html:ro" -v "$PWD/formpublisher.conf:/etc/nginx/conf.d/default.conf:ro" nginx:stable',
    )
    result.notes.append("formpublisher.conf is one server block for conf.d; nginx-test.conf wraps it so nginx -t can parse it alone.")
    result.notes.append("Unknown paths return 404 through try_files" + (" and show the site's 404.html." if inp.has_404 else "; the site has no 404.html, so nginx shows its own page."))
    if inp.fallback_404:
        result.notes.append("This export has 404/index.html and no 404.html, so it was copied to 404.html as the 404 page.")
    result.notes.append("absolute_redirect is off so redirects keep working behind a port mapping or a proxy.")
    return result
