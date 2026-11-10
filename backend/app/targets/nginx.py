import re
import shutil
import socket
import subprocess
import tempfile
from pathlib import Path

from app.targets._common import SAFE_PATH, PreparedInput, PreparedResult, copy_site, is_splat, ordered_redirects, put

ID = "nginx"
NAME = "nginx"
DESCRIPTION = "A server block with try_files, redirects, headers and gzip, plus a docker run line."
LOCAL_TOOL = "sh nginx-check.sh"

CHECK_SCRIPT = """#!/bin/sh
set -u
command -v nginx >/dev/null 2>&1 || { echo "nginx-check.sh: nginx was not found on this machine." >&2; exit 127; }
here=$(cd "$(dirname "$0")" && pwd) || exit 1
scratch=$(mktemp -d "${TMPDIR:-/tmp}/formpublisher-nginx.XXXXXX") || exit 1
trap 'rm -rf "$scratch"' EXIT
trap 'exit 1' HUP INT TERM
mkdir "$scratch/conf" || exit 1
cp "$here/nginx-test.conf" "$scratch/conf/nginx-test.conf" || exit 1
SCRATCH="$scratch" awk '/^[[:space:]]*listen[[:space:]]/ { n++; sub(/listen[[:space:]][^;]*;/, "listen unix:" ENVIRON["SCRATCH"] "/l" n ".sock;") } { print }' "$here/formpublisher.conf" > "$scratch/conf/formpublisher.conf" || exit 1
cd "$scratch" || exit 1
nginx -t -p "$scratch/" -e "$scratch/error.log" -c "$scratch/conf/nginx-test.conf" > "$scratch/out.txt" 2>&1
status=$?
sed "s|$scratch/conf|$here|g" "$scratch/out.txt" >&2
exit "$status"
"""

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
pid nginx.pid;
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


CHECK_SECONDS = 20
CHECK_OUTPUT_LIMIT = 2048


def _trim(text: str) -> str:
    text = "\n".join(line.rstrip() for line in text.strip().splitlines() if line.strip())
    raw = text.encode("utf-8")
    return text if len(raw) <= CHECK_OUTPUT_LIMIT else raw[:CHECK_OUTPUT_LIMIT].decode("utf-8", "ignore")


def _local_listens(text: str, scratch: Path) -> str:
    count = [0]

    def swap(found: re.Match) -> str:
        count[0] += 1
        return f"{found.group(1)}listen unix:{scratch / ('l' + str(count[0]) + '.sock')};"

    return re.sub(r"^([ \t]*)listen[ \t][^;\n]*;", swap, text, flags=re.M)


LISTEN_RX = re.compile(r"^([ \t]*)listen[ \t]+[^\s;]+([^;\n]*);", re.M)


def _free_ports(count: int) -> list[int] | None:
    held = []
    ports = []
    try:
        for _ in range(count):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            held.append(sock)
            sock.bind(("127.0.0.1", 0))
            ports.append(sock.getsockname()[1])
    except OSError:
        return None
    finally:
        for sock in held:
            sock.close()
    return ports


def _loopback_listens(text: str, ports: list[int]) -> str:
    count = [0]

    def swap(found: re.Match) -> str:
        port = ports[count[0]]
        count[0] += 1
        return f"{found.group(1)}listen 127.0.0.1:{port}{found.group(2)};"

    return LISTEN_RX.sub(swap, text)


def _run_nginx(exe: str, scratch: Path, confdir: Path, folder: Path) -> tuple[bool, str]:
    run = subprocess.run(
        [exe, "-t", "-p", str(scratch) + "/", "-e", str(scratch / "error.log"), "-c", str(confdir / "nginx-test.conf")],
        capture_output=True,
        text=True,
        errors="replace",
        timeout=CHECK_SECONDS,
        stdin=subprocess.DEVNULL,
        cwd=scratch,
    )
    printed = run.stderr + ("\n" + run.stdout if run.stdout.strip() else "")
    tagged = [line for line in printed.splitlines() if line.startswith("nginx:")]
    printed = "\n".join(tagged) if tagged else printed
    return run.returncode == 0, _trim(printed.replace(str(confdir), str(folder)))


def check(folder: Path) -> dict:
    """Run nginx -t on a prepared folder's nginx-test.conf, from a copy in a fresh scratch folder, in two passes.

    nginx -t opens every listen socket, so the first pass swaps each listen for a unix socket inside the scratch folder: no port is bound, no network is used and a normal user can run it. The prefix, pid, temp paths and error log all sit under the scratch folder and there is no user directive.

    When that passes and free loopback TCP ports can be had, the second pass keeps every listen line's parameters and points its address and port at 127.0.0.1 and a free port, so the listen lines themselves are parsed. A failure there fails the check; a bind trouble or no free port skips the pass.

    Returns {"ran", "ok", "version", "output", "listen"}; "listen" is {"ran", "ok", "output"}. When nginx is not on PATH, or the folder has no nginx-test.conf, "ran" is false and "ok" is None.
    """
    exe = shutil.which("nginx")
    conf = Path(folder) / "nginx-test.conf"
    if exe is None or not conf.is_file():
        return {"ran": False, "ok": None, "version": "", "output": ""}
    version = ""
    scratch = Path(tempfile.mkdtemp(prefix="formpublisher-nginx-"))
    try:
        try:
            probe = subprocess.run([exe, "-v"], capture_output=True, text=True, timeout=CHECK_SECONDS, stdin=subprocess.DEVNULL, cwd=scratch)
            found = re.search(r"nginx/(\S+)", probe.stderr + probe.stdout)
            version = found.group(1) if found else ""
        except (OSError, subprocess.SubprocessError):
            version = ""
        confdir = scratch / "conf"
        confdir.mkdir()
        shutil.copyfile(conf, confdir / "nginx-test.conf")
        site_conf = Path(folder) / "formpublisher.conf"
        site_text = site_conf.read_text(encoding="utf-8", errors="replace") if site_conf.is_file() else None
        if site_text is not None:
            (confdir / "formpublisher.conf").write_text(_local_listens(site_text, scratch), encoding="utf-8")
        skipped = {"ran": False, "ok": None, "output": ""}
        try:
            ok, output = _run_nginx(exe, scratch, confdir, Path(folder))
        except subprocess.TimeoutExpired:
            return {"ran": True, "ok": False, "version": version, "output": f"nginx -t did not finish within {CHECK_SECONDS} seconds.", "listen": skipped}
        except OSError as exc:
            return {"ran": False, "ok": None, "version": version, "output": _trim(str(exc)), "listen": skipped}
        if not ok or site_text is None:
            return {"ran": True, "ok": ok, "version": version, "output": output, "listen": skipped}
        wanted = len(LISTEN_RX.findall(site_text))
        ports = _free_ports(wanted) if wanted else None
        if ports is None:
            return {"ran": True, "ok": True, "version": version, "output": output, "listen": skipped}
        (confdir / "formpublisher.conf").write_text(_loopback_listens(site_text, ports), encoding="utf-8")
        try:
            listen_ok, listen_output = _run_nginx(exe, scratch, confdir, Path(folder))
        except (subprocess.SubprocessError, OSError):
            return {"ran": True, "ok": True, "version": version, "output": output, "listen": skipped}
        if not listen_ok and "Address already in use" in listen_output:
            return {"ran": True, "ok": True, "version": version, "output": output, "listen": skipped}
        if not listen_ok:
            return {"ran": True, "ok": False, "version": version, "output": listen_output, "listen": {"ran": True, "ok": False, "output": listen_output}}
        return {"ran": True, "ok": True, "version": version, "output": output, "listen": {"ran": True, "ok": True, "output": listen_output}}
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def message_of(report: dict) -> str:
    """The first line nginx printed that names the failure, without the leading nginx: tag."""
    lines = [line for line in str(report.get("output") or "").splitlines() if line.strip()]
    for line in lines:
        if "[emerg]" in line or "[alert]" in line or "[crit]" in line:
            return re.sub(r"^nginx:\s*", "", line).strip()
    return re.sub(r"^nginx:\s*", "", lines[0]).strip() if lines else "nginx -t failed"


def annotate(result: PreparedResult, folder: Path) -> None:
    """Add the nginx -t outcome for a freshly prepared folder as a note or a warning."""
    report = check(folder)
    if not report["ran"]:
        result.notes.append("nginx -t runs where nginx is installed; nginx was not found on this machine, so the config was not checked here.")
    elif report["ok"]:
        with_version = f"The config passed nginx -t with nginx {report['version']}" if report["version"] else "The config passed nginx -t"
        listen = report.get("listen") or {}
        result.notes.append(with_version + (", and so did its listen lines on a loopback port." if listen.get("ran") else "; its listen lines were not checked on a loopback port because none was free."))
    else:
        result.warnings.append(f"nginx -t failed: {message_of(report)}")


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
        keep = "" if "?" in dst else "$is_args$args"
        if is_splat(row):
            prefix = src[:-1]
            target = dst.replace(":splat", "$1")
            lines.append(f"    location ~ ^{_cut_rx(prefix)}(.*)$ {{ return {row['status']} {target}{keep}; }}")
        else:
            plain = src.rstrip("/") or "/"
            lines.append(f"    location = {plain} {{ return {row['status']} {dst}{keep}; }}")
            if plain != "/":
                lines.append(f"    location = {plain}/ {{ return {row['status']} {dst}{keep}; }}")
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
    put(out, "nginx-check.sh", CHECK_SCRIPT, 0o755)
    result.command("Check the config", "sh nginx-check.sh")
    result.command(
        "Run it in Docker",
        'docker run --rm -p 8080:80 -v "$PWD/site:/usr/share/nginx/html:ro" -v "$PWD/formpublisher.conf:/etc/nginx/conf.d/default.conf:ro" nginx:stable',
    )
    result.notes.append("formpublisher.conf is one server block for conf.d; nginx-test.conf wraps it so nginx -t can parse it alone.")
    result.notes.append("nginx-check.sh runs nginx -t on a scratch copy with unix sockets instead of ports, so it needs no root and no IPv6 and changes nothing in this folder.")
    result.notes.append("Unknown paths return 404 through try_files" + (" and show the site's 404.html." if inp.has_404 else "; the site has no 404.html, so nginx shows its own page."))
    if inp.fallback_404:
        result.notes.append("This export has 404/index.html and no 404.html, so it was copied to 404.html as the 404 page.")
    result.notes.append("absolute_redirect is off so redirects keep working behind a port mapping or a proxy.")
    return result
