import json
from pathlib import Path

from app.targets._common import PreparedInput, PreparedResult, copy_site, is_splat, ordered_redirects, put

ID = "vercel"
NAME = "Vercel"
DESCRIPTION = "CLI deploy with a vercel.json for clean URLs, redirects and headers."
LOCAL_TOOL = "npx vercel dev site"


def _source(pattern: str) -> str:
    if pattern.endswith("/*"):
        return pattern[:-2] + "/:path*"
    if pattern.endswith("*"):
        return pattern[:-1] + ":path*"
    return pattern


def _header_source(pattern: str) -> str:
    if pattern.endswith("*"):
        return pattern[:-1] + "(.*)"
    return pattern


def prepare(inp: PreparedInput, out: Path) -> PreparedResult:
    result = PreparedResult()
    copy_site(inp, out / "site")
    config: dict = {"cleanUrls": True}
    routes = [r for r in inp.route_paths if r != "/"]
    if routes and all(r.endswith("/") for r in routes):
        config["trailingSlash"] = True
    elif routes and not any(r.endswith("/") for r in routes):
        config["trailingSlash"] = False
    elif routes:
        result.warnings.append("The routes mix trailing-slash and file URLs, so trailingSlash is left unset and Vercel keeps each URL as written.")
    redirects = []
    for row in ordered_redirects(inp):
        splat = is_splat(row)
        redirects.append(
            {
                "source": _source(row["from"]),
                "destination": row["to"].replace(":splat", ":path*") if splat else row["to"],
                "statusCode": row["status"],
            }
        )
    if redirects:
        config["redirects"] = redirects
    headers = []
    for row in inp.headers:
        headers.append(
            {
                "source": _header_source(row["for"]),
                "headers": [{"key": k, "value": v} for k, v in sorted(row["values"].items())],
            }
        )
    if headers:
        config["headers"] = headers
    put(out, "site/vercel.json", json.dumps(config, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    result.command("Preview deploy", "npx vercel deploy site")
    result.command("Production deploy", "npx vercel deploy site --prod")
    result.command("Run it locally", "npx vercel dev site")
    result.notes.append("vercel.json sits inside site/ so the deploy picks it up; Vercel serves 404.html itself when the file exists.")
    if not inp.has_404:
        result.notes.append("The site has no 404.html, so Vercel shows its own not-found page.")
    return result
