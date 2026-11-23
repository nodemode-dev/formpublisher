import json
from html.parser import HTMLParser
from pathlib import Path

import pytest

from .support import ALL, EXACT, HOSTS, PAGES, REDIRECTS, SPLAT, api, made, make_site, out, prepared, tree  # noqa: F401

APP_HEADERS = {
    "/*": {"X-Content-Type-Options": "nosniff", "Referrer-Policy": "strict-origin-when-cross-origin"},
    "/assets/*": {"Cache-Control": "public, max-age=3600"},
}


def redirect_rules(text: str) -> list[tuple]:
    rules = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        assert len(parts) == 3, line
        assert parts[0].startswith("/")
        rules.append((parts[0], parts[1], int(parts[2])))
    return rules


def header_rules(text: str) -> dict:
    rules: dict = {}
    current = None
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[0] in " \t":
            assert current is not None, "a header line came before any path"
            name, sep, value = line.strip().partition(":")
            assert sep == ":" and name and " " not in name
            rules[current][name] = value.strip()
        else:
            current = line.strip()
            assert current.startswith("/")
            rules[current] = {}
    return rules


def as_rule(row: dict) -> tuple:
    return (row["from"], row["to"], row["status"])


class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def tags_of(data: bytes) -> list:
    reader = Tags()
    reader.feed(data.decode("utf-8"))
    return reader.tags


def other_site(tmp_path, client, api, pages, redirects, targets=ALL, name="other", include_model=False):
    folder = make_site(tmp_path / name, redirects=redirects, pages=pages)
    site = client.import_path(str(folder))
    build = client.build(site["id"])
    answer = api.post("/api/publish/prepare", {"build": build["id"], "targets": targets, "includeModel": include_model})
    assert answer.status_code == 200, answer.text
    return {"site": site["id"], "build": build["id"], "results": answer.json()["results"]}


@pytest.mark.parametrize("target", HOSTS)
def test_host_site_folder_holds_every_hand_made_file_byte_for_byte(prepared, target):
    got = tree(out(prepared, target) / "site")
    for rel, data in PAGES.items():
        if target == "github-pages" and rel == "404.html":
            continue
        assert got[rel] == data


def test_netlify_redirects_list_exact_rules_then_splat_rules_then_the_404_rule(prepared):
    rules = redirect_rules((out(prepared, "netlify") / "site/_redirects").read_text(encoding="utf-8"))
    assert rules == [as_rule(r) for r in EXACT] + [as_rule(r) for r in SPLAT] + [("/*", "/404.html", 404)]


def test_cloudflare_redirects_hold_the_same_rules_without_a_404_rule(prepared):
    rules = redirect_rules((out(prepared, "cloudflare-pages") / "site/_redirects").read_text(encoding="utf-8"))
    assert rules == [as_rule(r) for r in EXACT] + [as_rule(r) for r in SPLAT]


@pytest.mark.parametrize("target", ["netlify", "cloudflare-pages"])
def test_headers_file_groups_indented_header_lines_under_each_path(prepared, target):
    rules = header_rules((out(prepared, target) / "site/_headers").read_text(encoding="utf-8"))
    assert rules == APP_HEADERS


@pytest.mark.parametrize("target", ["netlify", "cloudflare-pages"])
def test_headers_file_agrees_with_the_headers_in_publish_json(prepared, target):
    manifest = json.loads((out(prepared, "static-zip") / "publish.json").read_bytes())
    rules = header_rules((out(prepared, target) / "site/_headers").read_text(encoding="utf-8"))
    assert rules == {row["for"]: row["values"] for row in manifest["headers"]}


def test_vercel_json_is_json_with_clean_urls_and_trailing_slash_for_folder_routes(prepared):
    config = json.loads((out(prepared, "vercel") / "site/vercel.json").read_text(encoding="utf-8"))
    assert config["cleanUrls"] is True
    assert config["trailingSlash"] is True
    assert set(config) <= {"cleanUrls", "trailingSlash", "redirects", "headers"}


def test_vercel_json_writes_each_redirect_with_source_destination_and_status_code(prepared):
    config = json.loads((out(prepared, "vercel") / "site/vercel.json").read_text(encoding="utf-8"))
    assert config["redirects"] == [
        {"source": "/old", "destination": "/about/", "statusCode": 301},
        {"source": "/team", "destination": "/about/", "statusCode": 308},
        {"source": "/blog/:path*", "destination": "/news/:path*", "statusCode": 302},
    ]


def test_vercel_json_headers_use_key_value_pairs_and_a_regex_source(prepared):
    config = json.loads((out(prepared, "vercel") / "site/vercel.json").read_text(encoding="utf-8"))
    got = {row["source"]: {h["key"]: h["value"] for h in row["headers"]} for row in config["headers"]}
    assert got == {"/(.*)": APP_HEADERS["/*"], "/assets/(.*)": APP_HEADERS["/assets/*"]}
    for row in config["headers"]:
        assert all(set(h) == {"key", "value"} for h in row["headers"])


def test_vercel_json_omits_redirects_when_the_site_has_none(tmp_path, client, api):
    made_other = other_site(tmp_path, client, api, PAGES, None, ["vercel"])
    config = json.loads((out(made_other, "vercel") / "site/vercel.json").read_text(encoding="utf-8"))
    assert "redirects" not in config


def test_vercel_trailing_slash_is_false_when_routes_are_files(tmp_path, client, api):
    pages = {"index.html": PAGES["index.html"].replace(b"about/", b"about.html"), "about.html": PAGES["404.html"], "assets/app.css": PAGES["assets/app.css"], "routes.json": json.dumps({"routes": [{"path": "/", "page": "index.html"}, {"path": "/about.html", "page": "about.html"}]}).encode()}
    made_other = other_site(tmp_path, client, api, pages, None, ["vercel"])
    config = json.loads((out(made_other, "vercel") / "site/vercel.json").read_text(encoding="utf-8"))
    assert config["trailingSlash"] is False


def test_github_pages_nojekyll_is_an_empty_file(prepared):
    assert (out(prepared, "github-pages") / "site/.nojekyll").read_bytes() == b""


@pytest.mark.parametrize("row", EXACT, ids=[r["from"] for r in EXACT])
def test_github_pages_writes_a_meta_refresh_page_at_each_old_address(prepared, row):
    page = (out(prepared, "github-pages") / "site" / row["from"].strip("/") / "index.html").read_bytes()
    tags = tags_of(page)
    refresh = [a for t, a in tags if t == "meta" and (a.get("http-equiv") or "").lower() == "refresh"]
    canonical = [a for t, a in tags if t == "link" and a.get("rel") == "canonical"]
    assert [a["content"] for a in refresh] == [f"0; url={row['to']}"]
    assert [a["href"] for a in canonical] == [row["to"]]


def test_github_pages_404_page_is_the_site_page_plus_one_script_for_the_splat_rule(prepared):
    page = (out(prepared, "github-pages") / "site/404.html").read_bytes()
    start = page.index(b"<script>")
    end = page.index(b"</script>") + len(b"</script>")
    assert page[:start] + page[end:] == PAGES["404.html"]
    script = page[start:end].decode("ascii")
    assert json.dumps([["/blog", "/news/:splat"]], separators=(",", ":")) in script.replace(", ", ",")
    assert page[:start].endswith(b'<meta charset="utf-8">')


def test_github_pages_workflow_uploads_site_with_hidden_files_and_has_no_tabs(prepared):
    text = (out(prepared, "github-pages") / ".github/workflows/pages.yml").read_text(encoding="utf-8")
    assert "\t" not in text
    lines = [line.strip() for line in text.splitlines()]
    assert "path: site" in lines
    assert "include-hidden-files: true" in lines
    assert "pages: write" in lines and "id-token: write" in lines


def test_github_pages_warns_that_each_custom_header_group_will_not_be_sent(prepared):
    warnings = prepared["results"]["github-pages"]["warnings"]
    assert len(warnings) == len(APP_HEADERS)
    for pattern, values in APP_HEADERS.items():
        assert any(pattern in w and all(name in w for name in values) for w in warnings)


def test_github_pages_redirect_note_lists_every_redirect(prepared):
    text = (out(prepared, "github-pages") / "redirects/README.txt").read_text(encoding="utf-8")
    for row in REDIRECTS:
        assert row["from"] in text and row["to"] in text


def test_github_pages_commands_never_name_a_real_remote(prepared):
    runs = [c["run"] for c in prepared["results"]["github-pages"]["commands"]]
    assert "git remote add origin git@github.com:OWNER/REPO.git" in runs
    assert not any(run.startswith("gh ") for run in runs)


NO_404 = {k: v for k, v in PAGES.items() if k != "404.html"}


def test_site_without_404_gets_a_comment_only_redirects_file_on_netlify(tmp_path, client, api):
    made_other = other_site(tmp_path, client, api, NO_404, None, ["netlify"])
    text = (out(made_other, "netlify") / "site/_redirects").read_text(encoding="utf-8")
    assert redirect_rules(text) == []
    assert "The site has no 404.html, so Netlify shows its own not-found page." in made_other["results"]["netlify"]["notes"]


def test_site_without_404_gets_a_minimal_404_page_on_github_pages(tmp_path, client, api):
    made_other = other_site(tmp_path, client, api, NO_404, None, ["github-pages"])
    page = (out(made_other, "github-pages") / "site/404.html").read_bytes()
    tags = tags_of(page)
    assert ("a", {"href": "/"}) in tags
    assert "The site has no 404.html, so a minimal one was added." in made_other["results"]["github-pages"]["notes"]


def test_site_without_404_is_warned_about_single_page_app_mode_on_cloudflare(tmp_path, client, api):
    made_other = other_site(tmp_path, client, api, NO_404, None, ["cloudflare-pages"])
    warnings = made_other["results"]["cloudflare-pages"]["warnings"]
    assert len(warnings) == 1 and "single-page app" in warnings[0]
    assert not (out(made_other, "cloudflare-pages") / "site/404.html").exists()


@pytest.mark.parametrize("target", ["netlify", "cloudflare-pages", "vercel", "nginx"])
def test_404_folder_page_is_copied_to_404_html_with_parent_links_made_root_links(tmp_path, client, api, target):
    pages = dict(NO_404)
    pages["404/index.html"] = b'<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><title>Missing</title><link rel="stylesheet" href="../assets/app.css"></head><body><a href="../">Home</a></body></html>\n'
    made_other = other_site(tmp_path, client, api, pages, None, [target])
    site = out(made_other, target) / "site"
    assert (site / "404/index.html").read_bytes() == pages["404/index.html"]
    assert (site / "404.html").read_bytes() == pages["404/index.html"].replace(b'"../', b'"/')
    assert "This export has 404/index.html and no 404.html, so it was copied to 404.html as the 404 page." in made_other["results"][target]["notes"]


def test_redirect_with_a_space_is_skipped_with_a_warning_on_netlify(tmp_path, client, api):
    rows = [{"from": "/a b", "to": "/about/", "status": 301}, {"from": "/old", "to": "/about/", "status": 301}]
    made_other = other_site(tmp_path, client, api, PAGES, rows, ["netlify"])
    rules = redirect_rules((out(made_other, "netlify") / "site/_redirects").read_text(encoding="utf-8"))
    assert rules == [("/old", "/about/", 301), ("/*", "/404.html", 404)]
    assert made_other["results"]["netlify"]["warnings"] == ["Skipped the redirect '/a b' because it contains whitespace."]


def test_github_pages_skips_a_redirect_whose_address_is_already_a_page(tmp_path, client, api):
    rows = [{"from": "/about", "to": "/", "status": 301}]
    made_other = other_site(tmp_path, client, api, PAGES, rows, ["github-pages"])
    assert (out(made_other, "github-pages") / "site/about/index.html").read_bytes() == PAGES["about/index.html"]
    assert made_other["results"]["github-pages"]["warnings"][0] == "The redirect /about was skipped because the site already has a page at about/index.html."


def test_redirect_status_outside_301_302_307_308_is_not_published(tmp_path, client, api):
    rows = [{"from": "/gone", "to": "/about/", "status": 410}, {"from": "/old", "to": "/about/", "status": 307}]
    made_other = other_site(tmp_path, client, api, PAGES, rows, ["netlify"])
    rules = redirect_rules((out(made_other, "netlify") / "site/_redirects").read_text(encoding="utf-8"))
    assert rules == [("/old", "/about/", 307), ("/*", "/404.html", 404)]


def test_cloudflare_warns_past_one_hundred_splat_rules_and_still_writes_them(tmp_path, client, api):
    rows = [{"from": f"/s{i}/*", "to": f"/t{i}/:splat", "status": 301} for i in range(101)]
    made_other = other_site(tmp_path, client, api, PAGES, rows, ["cloudflare-pages"])
    rules = redirect_rules((out(made_other, "cloudflare-pages") / "site/_redirects").read_text(encoding="utf-8"))
    assert len(rules) == 101
    assert "101 splat redirects exceed Cloudflare Pages' limit of 100 dynamic rules." in made_other["results"]["cloudflare-pages"]["warnings"]


MODEL = json.dumps({"settings": {"baseUrl": "https://example.github.io/proj/"}}).encode()


@pytest.mark.parametrize("target", HOSTS)
def test_model_file_is_left_out_of_host_folders_and_named_in_left_out(tmp_path, client, api, target):
    made_other = other_site(tmp_path, client, api, {**PAGES, "site.formweb.json": MODEL}, None, [target])
    assert not (out(made_other, target) / "site/site.formweb.json").exists()
    assert made_other["results"][target]["leftOut"] == ["site.formweb.json"]


def test_include_model_keeps_the_model_file_byte_for_byte(tmp_path, client, api):
    made_other = other_site(tmp_path, client, api, {**PAGES, "site.formweb.json": MODEL}, None, ["netlify"], include_model=True)
    assert (out(made_other, "netlify") / "site/site.formweb.json").read_bytes() == MODEL
    assert made_other["results"]["netlify"]["leftOut"] == []
    assert made_other["results"]["netlify"]["includeModel"] is True


def test_github_pages_redirect_pages_point_under_the_base_path_of_the_base_url(tmp_path, client, api):
    rows = [{"from": "/old", "to": "/about/", "status": 301}]
    made_other = other_site(tmp_path, client, api, {**PAGES, "site.formweb.json": MODEL}, rows, ["github-pages"])
    tags = tags_of((out(made_other, "github-pages") / "site/old/index.html").read_bytes())
    assert ("link", {"rel": "canonical", "href": "/proj/about/"}) in tags
