import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SAFE_PATH = re.compile(r"^[A-Za-z0-9/_.~%@:+,=-]*$")
STATUSES = (301, 302, 307, 308)
# FormWeb's own model files: they describe how the site was built, a host has no use for them, and they
# can be large. Prepared host folders leave them out unless the person asks to keep them.
MODEL_FILES = ("site.formweb.json", "asset-access.json")


@dataclass
class PreparedInput:
    """One build as the adapters see it: the build record, publish.json and the unpacked site.zip."""

    build: dict
    publish: dict
    publish_bytes: bytes
    zip_path: Path
    root: Path
    names: list[str]
    slug: str
    excluded: list[str] = field(default_factory=list)

    def has(self, name: str) -> bool:
        return name in self.names

    def read(self, name: str) -> bytes:
        return (self.root / name).read_bytes()

    @property
    def site_name(self) -> str:
        site = self.publish.get("site") if isinstance(self.publish.get("site"), dict) else {}
        return str(site.get("name") or self.slug)

    @property
    def has_404(self) -> bool:
        # FormWeb exports a page at /404 as 404/index.html; copy_site also writes it as the 404.html hosts look for.
        return "404.html" in self.names or "404/index.html" in self.names

    @property
    def fallback_404(self) -> bool:
        return "404.html" not in self.names and "404/index.html" in self.names

    @property
    def redirects(self) -> list[dict]:
        rows = self.publish.get("redirects")
        out = []
        for row in rows if isinstance(rows, list) else []:
            if isinstance(row, dict) and isinstance(row.get("from"), str) and isinstance(row.get("to"), str):
                status = row.get("status") if row.get("status") in STATUSES else 301
                out.append({"from": row["from"], "to": row["to"], "status": status})
        return out

    @property
    def headers(self) -> list[dict]:
        rows = self.publish.get("headers")
        out = []
        for row in rows if isinstance(rows, list) else []:
            values = row.get("values") if isinstance(row, dict) else None
            if isinstance(row, dict) and isinstance(row.get("for"), str) and isinstance(values, dict):
                out.append({"for": row["for"], "values": {str(k): str(v) for k, v in sorted(values.items())}})
        return out

    @property
    def route_paths(self) -> list[str]:
        rows = self.publish.get("routes")
        out = []
        for row in rows if isinstance(rows, list) else []:
            if isinstance(row, dict) and isinstance(row.get("path"), str):
                out.append(normalize_route(row["path"]))
        return sorted(set(out))


@dataclass
class PreparedResult:
    commands: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def command(self, label: str, run: str, cwd: str = ".") -> None:
        self.commands.append({"label": label, "run": run, "cwd": cwd})


def normalize_route(path: str) -> str:
    raw = path.strip().lstrip("/")
    if raw == "" or raw == "index.html":
        return "/"
    if raw.endswith("/index.html"):
        return "/" + raw[: -len("index.html")]
    return "/" + raw


def is_splat(row: dict) -> bool:
    return row["from"].endswith("*")


def ordered_redirects(inp: PreparedInput) -> list[dict]:
    """Exact rules first, splat rules after, each group in publish order, as the preview host matches them."""
    rows = inp.redirects
    return [r for r in rows if not is_splat(r)] + [r for r in rows if is_splat(r)]


def simple_header_groups(inp: PreparedInput) -> list[tuple[str, dict]]:
    return [(row["for"], row["values"]) for row in inp.headers]


def copy_site(inp: PreparedInput, dest: Path) -> None:
    for name in inp.names:
        target = dest / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(inp.root / name, target)
    if "404.html" not in inp.names and "404/index.html" in inp.names:
        page = (inp.root / "404/index.html").read_bytes()
        (dest / "404.html").write_bytes(re.sub(rb'((?:href|src|poster|action)=")\.\./', rb"\1/", page))


def put(out: Path, rel: str, data: Any) -> None:
    target = out / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        data = data.replace("\r\n", "\n").encode("utf-8")
    target.write_bytes(data)


def netlify_style(inp: PreparedInput, result: PreparedResult, with_404: bool) -> tuple[str, str]:
    """Text of _redirects and _headers; the two hosts share one syntax."""
    lines = []
    for row in ordered_redirects(inp):
        if re.search(r"\s", row["from"]) or re.search(r"\s", row["to"]):
            result.warnings.append(f"Skipped the redirect {row['from']!r} because it contains whitespace.")
            continue
        lines.append(f"{row['from']} {row['to']} {row['status']}")
    if with_404 and inp.has_404:
        lines.append("/* /404.html 404")
    redirects = "\n".join(lines) + "\n" if lines else "# No redirects.\n"
    blocks = []
    for pattern, values in simple_header_groups(inp):
        blocks.append(pattern + "\n" + "".join(f"  {k}: {v}\n" for k, v in sorted(values.items())))
    headers = "\n".join(blocks) if blocks else "# No custom headers.\n"
    return redirects, headers
