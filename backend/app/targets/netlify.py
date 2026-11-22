from pathlib import Path

from app.targets._common import PreparedInput, PreparedResult, copy_site, netlify_style, put

ID = "netlify"
NAME = "Netlify"
DESCRIPTION = "Drag-and-drop or CLI deploy with _redirects and _headers."
LOCAL_TOOL = "npx netlify-cli@27 dev --dir site"


def prepare(inp: PreparedInput, out: Path) -> PreparedResult:
    result = PreparedResult()
    copy_site(inp, out / "site")
    redirects, headers = netlify_style(inp, result, with_404=True)
    put(out, "site/_redirects", redirects)
    put(out, "site/_headers", headers)
    result.command("Draft deploy (preview URL)", "npx netlify-cli@27 deploy --dir site")
    result.command("Production deploy", "npx netlify-cli@27 deploy --dir site --prod")
    result.command("Run it locally", "npx netlify-cli@27 dev --dir site")
    result.notes.append("You can also drag the site folder onto app.netlify.com/drop.")
    result.notes.append("_redirects lists exact rules first, then splat rules; Netlify uses the first match.")
    if inp.has_404:
        result.notes.append("A final rule serves 404.html with status 404 for unknown paths.")
        if inp.fallback_404:
            result.notes.append("This export has 404/index.html and no 404.html, so it was copied to 404.html as the 404 page.")
    else:
        result.notes.append("The site has no 404.html, so Netlify shows its own not-found page.")
    return result
