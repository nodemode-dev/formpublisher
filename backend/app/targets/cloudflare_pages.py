from pathlib import Path

from app.targets._common import PreparedInput, PreparedResult, copy_site, is_splat, netlify_style, put

ID = "cloudflare-pages"
NAME = "Cloudflare Pages"
DESCRIPTION = "Wrangler deploy with _redirects and _headers in Cloudflare's syntax."
LOCAL_TOOL = "npx wrangler pages dev site"

STATIC_LIMIT = 2000
DYNAMIC_LIMIT = 100


def prepare(inp: PreparedInput, out: Path) -> PreparedResult:
    result = PreparedResult()
    copy_site(inp, out / "site")
    redirects, headers = netlify_style(inp, result, with_404=False)
    put(out, "site/_redirects", redirects)
    put(out, "site/_headers", headers)
    rows = inp.redirects
    splats = sum(1 for r in rows if is_splat(r))
    statics = len(rows) - splats
    if statics > STATIC_LIMIT:
        result.warnings.append(f"{statics} static redirects exceed Cloudflare Pages' limit of {STATIC_LIMIT}; the extra rules will be ignored.")
    if splats > DYNAMIC_LIMIT:
        result.warnings.append(f"{splats} splat redirects exceed Cloudflare Pages' limit of {DYNAMIC_LIMIT} dynamic rules.")
    result.command("Deploy", f"npx wrangler pages deploy site --project-name {inp.slug}")
    result.command("Run it locally", "npx wrangler pages dev site")
    result.notes.append(f"Cloudflare allows {STATIC_LIMIT} static and {DYNAMIC_LIMIT} dynamic redirect rules in _redirects.")
    result.notes.append("No 404 rule is written: Pages serves 404.html on its own when the file exists.")
    if inp.fallback_404:
        result.notes.append("This export has 404/index.html and no 404.html, so it was copied to 404.html as the 404 page.")
    if not inp.has_404:
        result.warnings.append("The site has no 404.html, so Cloudflare Pages treats it as a single-page app and serves index.html with status 200 for unknown paths. Add a 404 page in FormWeb.")
    return result
