import json
from pathlib import Path

import pytest

ALL = ["static-zip", "netlify", "cloudflare-pages", "vercel", "github-pages", "nginx"]
HOSTS = ALL[1:]

PAGES = {
    "index.html": b'<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><title>Home</title><link rel="stylesheet" href="assets/app.css"></head><body><h1>Home</h1><a href="about/">About</a></body></html>\n',
    "about/index.html": b'<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><title>About</title><link rel="stylesheet" href="../assets/app.css"></head><body><h1>About</h1><a href="../">Home</a></body></html>\n',
    "404.html": b'<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><title>Missing</title></head><body><h1>Missing</h1><a href="/">Home</a></body></html>\n',
    "assets/app.css": b"body{margin:0;font-family:sans-serif}\n",
    "assets/dot.bin": bytes(range(256)),
}
REDIRECTS = [
    {"from": "/old", "to": "/about/", "status": 301},
    {"from": "/blog/*", "to": "/news/:splat", "status": 302},
    {"from": "/team", "to": "/about/", "status": 308},
]
EXACT = [r for r in REDIRECTS if not r["from"].endswith("*")]
SPLAT = [r for r in REDIRECTS if r["from"].endswith("*")]


def make_site(folder: Path, redirects=REDIRECTS, pages=PAGES) -> Path:
    for rel, data in pages.items():
        path = folder / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    if redirects is not None:
        (folder / "redirects.json").write_text(json.dumps({"redirects": redirects}), encoding="utf-8")
    return folder


class Api:
    def __init__(self):
        from fastapi.testclient import TestClient

        from app.main import app
        from app.services import paths, window_key

        self.app = app
        self.key = window_key.LOCAL_KEY
        self.header = window_key.HEADER
        self.http = TestClient(app, base_url=f"http://127.0.0.1:{paths.port()}")

    def get(self, path):
        return self.http.get(path)

    def post(self, path, body=None, keyed=True, raw=None):
        headers = {self.header: self.key} if keyed else {}
        if raw is not None:
            return self.http.post(path, content=raw, headers={**headers, "content-type": "application/json"})
        return self.http.post(path, json=body, headers=headers)

    def delete(self, path, keyed=True):
        return self.http.delete(path, headers={self.header: self.key} if keyed else {})


@pytest.fixture
def api():
    return Api()


@pytest.fixture
def made(tmp_path, client):
    folder = make_site(tmp_path / "handmade")
    site = client.import_path(str(folder))
    build = client.build(site["id"])
    return {"folder": folder, "site": site["id"], "build": build["id"]}


@pytest.fixture
def prepared(api, made):
    answer = api.post("/api/publish/prepare", {"build": made["build"], "targets": ALL})
    assert answer.status_code == 200, answer.text
    return {**made, "results": answer.json()["results"]}


def out(prepared, target: str) -> Path:
    return Path(prepared["results"][target]["folder"])


def tree(folder: Path) -> dict:
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in sorted(folder.rglob("*")) if p.is_file()}


def nginx_tokens(text: str) -> list[str]:
    tokens, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c.isspace():
            i += 1
        elif c == "#":
            while i < n and text[i] != "\n":
                i += 1
        elif c in "{};":
            tokens.append(c)
            i += 1
        elif c in "\"'":
            j = i + 1
            buf = []
            while True:
                if j >= n:
                    raise ValueError("unterminated quoted string")
                if text[j] == "\\" and j + 1 < n:
                    buf.append(text[j + 1])
                    j += 2
                    continue
                if text[j] == c:
                    break
                buf.append(text[j])
                j += 1
            tokens.append("\x00" + "".join(buf))
            i = j + 1
        else:
            j = i
            depth = 0
            while j < n and not text[j].isspace():
                if text[j] == "$" and j + 1 < n and text[j + 1] == "{":
                    depth += 1
                    j += 2
                    continue
                if text[j] == "}" and depth:
                    depth -= 1
                    j += 1
                    continue
                if text[j] in "{};":
                    break
                j += 1
            tokens.append(text[i:j])
            i = j
    return tokens


def nginx_parse(text: str) -> list:
    tokens = nginx_tokens(text)
    pos = 0

    def block(top: bool) -> list:
        nonlocal pos
        rows = []
        words: list[str] = []
        while pos < len(tokens):
            t = tokens[pos]
            pos += 1
            if t == ";":
                if not words:
                    raise ValueError("empty directive")
                rows.append((words, None))
                words = []
            elif t == "{":
                if not words:
                    raise ValueError("block without a name")
                rows.append((words, block(False)))
                words = []
            elif t == "}":
                if words:
                    raise ValueError("directive not ended by ; before }")
                if top:
                    raise ValueError("unexpected }")
                return rows
            else:
                words.append(t[1:] if t.startswith("\x00") else t)
        if words:
            raise ValueError("directive not ended by ;")
        if not top:
            raise ValueError("missing }")
        return rows

    return block(True)


def directives(rows: list, name: str) -> list:
    return [(words[1:], body) for words, body in rows if words[0] == name]


def other_site(tmp_path, client, api, pages, redirects, targets=ALL, name="other", include_model=False):
    folder = make_site(tmp_path / name, redirects=redirects, pages=pages)
    site = client.import_path(str(folder))
    build = client.build(site["id"])
    answer = api.post("/api/publish/prepare", {"build": build["id"], "targets": targets, "includeModel": include_model})
    assert answer.status_code == 200, answer.text
    return {"folder": folder, "site": site["id"], "build": build["id"], "results": answer.json()["results"]}


def server_block(text: str) -> list:
    servers = directives(nginx_parse(text), "server")
    assert len(servers) == 1
    return servers[0][1]


def resolve(server: list, path: str, query: str = "") -> tuple | None:
    import re

    exact = [body for args, body in directives(server, "location") if args[0] == "=" and args[1] == path]
    chosen = exact[0] if exact else None
    if chosen is None:
        for args, body in directives(server, "location"):
            if args[0] == "~" and re.match(args[1], path):
                chosen = body
                match = re.match(args[1], path)
                break
    else:
        match = None
    if chosen is None:
        return None
    for words, _ in chosen:
        if words[0] == "return":
            target = words[2]
            if match is not None:
                target = target.replace("$1", match.group(1))
            target = target.replace("$is_args$args", ("?" + query) if query else "")
            return int(words[1]), target
    return None


def standin_nginx(folder: Path, log: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    log.mkdir(parents=True, exist_ok=True)
    script = folder / "nginx"
    script.write_text(
        """#!/bin/sh
if [ "$1" = "-v" ]; then echo "nginx version: nginx/1.99.0" >&2; exit 0; fi
conf=""
while [ $# -gt 0 ]; do
  if [ "$1" = "-c" ]; then conf="$2"; fi
  shift
done
n=$(ls "$STANDIN_LOG" | wc -l)
cp "$(dirname "$conf")/formpublisher.conf" "$STANDIN_LOG/pass$n.conf"
case "${STANDIN_MODE:-ok}" in
  fail) echo 'nginx: [emerg] unknown directive "bogus" in '"$(dirname "$conf")"'/formpublisher.conf:3' >&2; echo "nginx: configuration file $conf test failed" >&2; exit 1 ;;
  busy) if [ "$n" -ge 1 ] && [ "$n" -le "${STANDIN_BUSY:-2}" ]; then echo "nginx: [emerg] bind() to 127.0.0.1:1 failed (98: Address already in use)" >&2; exit 1; fi ;;
esac
echo "nginx: the configuration file $conf syntax is ok" >&2
echo "nginx: configuration file $conf test is successful" >&2
exit 0
""",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script
