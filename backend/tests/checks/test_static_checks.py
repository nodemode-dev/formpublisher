import json

import pytest

from checks_site import ORIGIN, found, make_site, page_html, run, sitemap, site  # noqa: F401


def write_index(site, **kw):
    (site / "index.html").write_text(page_html("/", **kw), encoding="utf-8")


def only(problems, code):
    rows = found(problems, code)
    assert len(rows) == 1, [(p["code"], p["message"]) for p in problems]
    return rows[0]


def test_clean_site_has_no_findings(site):
    assert run(site) == []


def test_internal_link_to_missing_page_is_link_broken_error(site):
    write_index(site, body='<h1>Welcome</h1><a href="/missing-page">Gone</a>')
    p = only(run(site), "link.broken")
    assert (p["severity"], p["file"], p["route"], p["tier"]) == ("error", "index.html", "/", "static")
    assert p["url"] == "/missing-page"
    assert p["line"] == page_html("/", body='<h1>Welcome</h1><a href="/missing-page">Gone</a>').split("\n").index('<h1>Welcome</h1><a href="/missing-page">Gone</a>') + 1


def test_internal_link_to_existing_page_without_extension_passes(site):
    write_index(site, body='<h1>Welcome</h1><a href="/about">About</a>')
    assert run(site) == []


def test_link_covered_by_a_redirect_is_not_broken(site):
    (site / "redirects.json").write_text(json.dumps([{"from": "/old", "to": "/about", "status": 301}]), encoding="utf-8")
    write_index(site, body='<h1>Welcome</h1><a href="/old">Old</a>')
    assert run(site) == []


def test_fragment_without_matching_id_is_link_anchor_warning(site):
    write_index(site, body='<h1>Welcome</h1><a href="/about#nobody">About</a>')
    p = only(run(site), "link.anchor")
    assert (p["severity"], p["file"]) == ("warning", "index.html")


def test_fragment_with_matching_id_passes(site):
    write_index(site, body='<h1>Welcome</h1><a href="/about#team">About</a>')
    assert run(site) == []


@pytest.mark.parametrize("body", [
    '<h1>Welcome</h1><img src="/gone.png" alt="x" width="4" height="4">',
    '<h1>Welcome</h1><img src="/favicon.ico" srcset="/gone.png 2x" alt="x" width="4" height="4">',
    '<h1>Welcome</h1><video poster="/gone.png"></video>',
    '<h1>Welcome</h1><div style="background: url(/gone.png)">x</div>',
])
def test_reference_to_missing_file_is_asset_missing_error(site, body):
    write_index(site, body=body)
    p = only(run(site), "asset.missing")
    assert (p["severity"], p["file"], p["url"]) == ("error", "index.html", "/gone.png")


def test_missing_stylesheet_and_css_import_are_asset_missing(site):
    write_index(site, head='<link rel="stylesheet" href="/gone.css"><style>@import "/also-gone.css";</style>')
    rows = found(run(site), "asset.missing")
    assert sorted(p["url"] for p in rows) == ["/also-gone.css", "/gone.css"]
    assert {p["severity"] for p in rows} == {"error"}


def test_existing_image_reference_passes(site):
    (site / "pic.png").write_bytes(b"\x89PNG")
    write_index(site, body='<h1>Welcome</h1><img src="/pic.png" alt="A picture" width="4" height="4">')
    assert run(site) == []


def test_redirect_loop_is_an_error(site):
    (site / "redirects.json").write_text(json.dumps([{"from": "/a", "to": "/b", "status": 301}, {"from": "/b", "to": "/a", "status": 301}]), encoding="utf-8")
    rows = found(run(site), "redirect.loop")
    assert rows and {p["severity"] for p in rows} == {"error"}


def test_redirect_chain_is_a_warning(site):
    (site / "redirects.json").write_text(json.dumps([{"from": "/a", "to": "/b", "status": 301}, {"from": "/b", "to": "/about", "status": 301}]), encoding="utf-8")
    problems = run(site)
    p = only(problems, "redirect.chain")
    assert p["severity"] == "warning"
    assert found(problems, "redirect.loop") == []


def test_redirect_to_nothing_is_redirect_target_error(site):
    (site / "redirects.json").write_text(json.dumps([{"from": "/a", "to": "/nowhere", "status": 301}]), encoding="utf-8")
    p = only(run(site), "redirect.target")
    assert p["severity"] == "error"


def test_single_redirect_to_a_page_passes(site):
    (site / "redirects.json").write_text(json.dumps([{"from": "/a", "to": "/about", "status": 301}]), encoding="utf-8")
    assert run(site) == []


def test_route_absent_from_sitemap_is_sitemap_missing_warning(site):
    (site / "sitemap.xml").write_text(sitemap(["/about"]), encoding="utf-8")
    p = only(run(site), "sitemap.missing")
    assert (p["severity"], p["route"]) == ("warning", "/")


def test_noindex_route_absent_from_sitemap_is_not_reported(site):
    (site / "sitemap.xml").write_text(sitemap(["/about"]), encoding="utf-8")
    write_index(site, head='<meta name="robots" content="noindex">')
    assert found(run(site), "sitemap.missing") == []


def test_sitemap_url_without_a_page_is_sitemap_extra_warning(site):
    (site / "sitemap.xml").write_text(sitemap(["/", "/about", "/ghost"]), encoding="utf-8")
    p = only(run(site), "sitemap.extra")
    assert p["severity"] == "warning"
    assert "/ghost" in p["message"]


@pytest.mark.parametrize("text", ["User-agent: *\nAllow: /\n", f"User-agent: *\nAllow: /\nSitemap: {ORIGIN}/map.xml\n"])
def test_robots_without_a_proper_sitemap_line_is_robots_sitemap_warning(site, text):
    (site / "robots.txt").write_text(text, encoding="utf-8")
    p = only(run(site), "robots.sitemap")
    assert (p["severity"], p["file"]) == ("warning", "robots.txt")


def test_robots_disallowing_everything_is_robots_blocks_warning(site):
    (site / "robots.txt").write_text(f"User-agent: *\nDisallow: /\nSitemap: {ORIGIN}/sitemap.xml\n", encoding="utf-8")
    p = only(run(site), "robots.blocks")
    assert (p["severity"], p["file"]) == ("warning", "robots.txt")


def test_robots_disallowing_one_folder_passes(site):
    (site / "robots.txt").write_text(f"User-agent: *\nDisallow: /private/\nSitemap: {ORIGIN}/sitemap.xml\n", encoding="utf-8")
    assert run(site) == []


@pytest.mark.parametrize("title", [None, ""])
def test_missing_title_is_meta_title_error(site, title):
    write_index(site, title=title)
    p = only(run(site), "meta.title")
    assert (p["severity"], p["file"], p["route"]) == ("error", "index.html", "/")


def test_title_of_61_characters_is_meta_title_warning(site):
    write_index(site, title="t" * 61)
    p = only(run(site), "meta.title")
    assert p["severity"] == "warning"
    assert "61" in p["message"]


def test_title_of_60_characters_passes(site):
    write_index(site, title="t" * 60)
    assert run(site) == []


def test_missing_description_is_meta_description_warning(site):
    write_index(site, description=None)
    p = only(run(site), "meta.description")
    assert (p["severity"], p["file"]) == ("warning", "index.html")


def test_description_of_161_characters_is_a_warning_and_160_passes(site):
    write_index(site, description="d" * 161)
    assert only(run(site), "meta.description")["severity"] == "warning"
    write_index(site, description="d" * 160)
    assert run(site) == []


def test_html_without_lang_is_meta_lang_warning(site):
    write_index(site, lang="")
    p = only(run(site), "meta.lang")
    assert (p["severity"], p["file"]) == ("warning", "index.html")


def test_image_without_alt_is_img_alt_warning(site):
    (site / "pic.png").write_bytes(b"\x89PNG")
    write_index(site, body='<h1>Welcome</h1><img src="/pic.png" width="4" height="4">')
    p = only(run(site), "img.alt")
    assert (p["severity"], p["file"], p["url"]) == ("warning", "index.html", "/pic.png")


def test_image_with_empty_alt_passes(site):
    (site / "pic.png").write_bytes(b"\x89PNG")
    write_index(site, body='<h1>Welcome</h1><img src="/pic.png" alt="" width="4" height="4">')
    assert run(site) == []


def test_image_without_width_and_height_is_img_size_warning(site):
    (site / "pic.png").write_bytes(b"\x89PNG")
    write_index(site, body='<h1>Welcome</h1><img src="/pic.png" alt="x">')
    p = only(run(site), "img.size")
    assert (p["severity"], p["file"]) == ("warning", "index.html")


def test_image_with_inline_aspect_ratio_passes(site):
    (site / "pic.png").write_bytes(b"\x89PNG")
    write_index(site, body='<h1>Welcome</h1><img src="/pic.png" alt="x" style="aspect-ratio: 1 / 1">')
    assert run(site) == []


@pytest.mark.parametrize("body", ["<p>No heading</p>", "<h1>One</h1><h1>Two</h1>"])
def test_zero_or_two_h1_is_heading_h1_warning(site, body):
    write_index(site, body=body)
    p = only(run(site), "heading.h1")
    assert (p["severity"], p["file"]) == ("warning", "index.html")


def test_skipped_heading_level_is_heading_order_info(site):
    write_index(site, body="<h1>One</h1><h3>Three</h3>")
    p = only(run(site), "heading.order")
    assert (p["severity"], p["file"]) == ("info", "index.html")


def test_headings_in_order_pass(site):
    write_index(site, body="<h1>One</h1><h2>Two</h2><h3>Three</h3><h2>Two again</h2>")
    assert run(site) == []


def test_script_from_another_host_is_external_request_warning(site):
    write_index(site, head='<script src="https://cdn.other.test/lib.js"></script>')
    p = only(run(site), "external.request")
    assert (p["severity"], p["file"], p["url"]) == ("warning", "index.html", "https://cdn.other.test/lib.js")


def test_same_external_url_on_two_pages_gives_one_warning_naming_the_count(site):
    tag = '<img src="https://cdn.other.test/a.png" alt="x" width="4" height="4">'
    write_index(site, body="<h1>Welcome</h1>" + tag)
    (site / "about.html").write_text(page_html("/about", title="About us", body="<h1>About</h1>" + tag), encoding="utf-8")
    p = only(run(site), "external.request")
    assert p["severity"] == "warning"
    assert "2 references" in p["message"]


def test_plain_link_to_another_site_is_not_an_external_request(site):
    write_index(site, body='<h1>Welcome</h1><a href="https://other.test/">Other</a>')
    assert run(site) == []


def test_fetch_of_another_host_in_a_js_file_is_external_request(site):
    (site / "app.js").write_text('fetch("https://api.other.test/data");\n', encoding="utf-8")
    write_index(site, head='<script src="/app.js"></script>')
    p = only(run(site), "external.request")
    assert (p["severity"], p["url"]) == ("warning", "https://api.other.test/data")


FIELD = '<label>Name <input name="name"></label><button>Send</button>'


@pytest.mark.parametrize("action", ["http://127.0.0.1:8240/api/forms/s/f", "http://localhost/send", "http://printer.local/x", "http://intranet/x", "http://192.168.1.4/x", "http://169.254.1.1/x", "http://0.0.0.0/x"])
def test_form_posting_to_a_local_address_is_forms_local_address_error(site, action):
    write_index(site, body=f'<h1>Welcome</h1><form method="post" action="{action}">{FIELD}</form>')
    p = only(run(site), "forms.local-address")
    assert (p["severity"], p["file"]) == ("error", "index.html")
    assert action in p["message"]
    assert "Forms" in p["fix"]


def test_get_form_to_a_local_address_is_also_an_error(site):
    write_index(site, body=f'<h1>Welcome</h1><form method="get" action="http://localhost/q">{FIELD}</form>')
    assert only(run(site), "forms.local-address")["severity"] == "error"


@pytest.mark.parametrize("attrs", ['method="post"', 'method="POST" action=""', 'method="Post" action="#"', 'method="post" action="/send"', 'method="get" action="/api/forms/site/contact"', 'method="post" action="https://forms.other.test/f" netlify'])
def test_form_that_cannot_send_is_forms_no_endpoint_error(site, attrs):
    write_index(site, body=f"<h1>Welcome</h1><form {attrs}>{FIELD}</form>")
    p = only(run(site), "forms.no-endpoint")
    assert (p["severity"], p["file"]) == ("error", "index.html")


def test_form_posting_to_a_form_service_passes(site):
    write_index(site, body=f'<h1>Welcome</h1><form method="post" action="https://forms.other.test/f/abc">{FIELD}</form>')
    assert run(site) == []


def test_named_netlify_form_passes(site):
    write_index(site, body=f'<h1>Welcome</h1><form name="contact" method="post" data-netlify="true">{FIELD}</form>')
    assert found(run(site), "forms.no-endpoint") == []


def test_web3forms_form_without_access_key_is_forms_access_key_error(site):
    write_index(site, body=f'<h1>Welcome</h1><form method="post" action="https://api.web3forms.com/submit">{FIELD}</form>')
    p = only(run(site), "forms.access-key")
    assert (p["severity"], p["file"]) == ("error", "index.html")


def test_web3forms_form_with_access_key_passes(site):
    write_index(site, body=f'<h1>Welcome</h1><form method="post" action="https://api.web3forms.com/submit"><input type="hidden" name="access_key" value="k1">{FIELD}</form>')
    assert run(site) == []


def test_unnamed_field_in_a_posting_form_is_forms_field_name_warning(site):
    write_index(site, body='<h1>Welcome</h1><form method="post" action="https://forms.other.test/f"><label>Name <input></label><button>Send</button></form>')
    p = only(run(site), "forms.field-name")
    assert (p["severity"], p["file"]) == ("warning", "index.html")


def test_disabled_unnamed_field_is_skipped(site):
    write_index(site, body='<h1>Welcome</h1><form method="post" action="https://forms.other.test/f"><label>Name <input disabled></label><button>Send</button></form>')
    assert found(run(site), "forms.field-name") == []


def two_route_site(tmp_path, snippet):
    site = make_site(tmp_path / "two", head=snippet)
    (site / "about.html").unlink()
    (site / "about").mkdir()
    (site / "about" / "index.html").write_text(page_html("/about/", title="About us", body="<h1>About</h1>"), encoding="utf-8")
    (site / "sitemap.xml").write_text(sitemap(["/", "/about/"]), encoding="utf-8")
    return site


def test_analytics_on_one_page_only_is_analytics_partial_warning_naming_the_other(tmp_path):
    site = two_route_site(tmp_path, '<script defer data-domain="example.org" src="https://plausible.io/js/script.js"></script>')
    problems = run(site)
    p = only(problems, "analytics.partial")
    assert p["severity"] == "warning"
    assert "Plausible" in p["message"] and "/about/" in p["message"]
    assert found(problems, "external.request") == []


def test_analytics_on_every_page_passes(tmp_path):
    snippet = '<script defer src="https://plausible.io/js/script.js"></script>'
    site = two_route_site(tmp_path, snippet)
    (site / "about" / "index.html").write_text(page_html("/about/", title="About us", body="<h1>About</h1>", head=snippet), encoding="utf-8")
    assert run(site) == []


def test_google_tag_gives_one_analytics_cookies_info(site):
    write_index(site, head='<script async src="https://www.googletagmanager.com/gtag/js?id=G-1"></script>')
    p = only(run(site), "analytics.cookies")
    assert p["severity"] == "info"
    assert "_ga" in p["message"]


@pytest.mark.parametrize("name,size,severity", [("big.js", 1024 * 1024 + 1, "warning"), ("big.css", 5 * 1024 * 1024 + 1, "error"), ("film.mp4", 20 * 1024 * 1024 + 1, "warning")])
def test_oversized_file_is_budget_file_with_the_stated_severity(site, name, size, severity):
    with open(site / name, "wb") as handle:
        handle.truncate(size)
    p = only(run(site), "budget.file")
    assert (p["severity"], p["file"]) == (severity, name)


@pytest.mark.parametrize("name,size", [("ok.js", 1024 * 1024), ("film.mp4", 20 * 1024 * 1024), ("photo.png", 6 * 1024 * 1024)])
def test_file_at_or_under_its_budget_passes(site, name, size):
    with open(site / name, "wb") as handle:
        handle.truncate(size)
    assert run(site) == []


def test_page_with_css_and_js_over_500_kib_is_budget_page_warning(site):
    (site / "a.css").write_bytes(b" " * (300 * 1024))
    (site / "a.js").write_bytes(b" " * (300 * 1024))
    write_index(site, head='<link rel="stylesheet" href="/a.css"><script src="/a.js"></script>')
    p = only(run(site), "budget.page")
    assert (p["severity"], p["route"], p["file"]) == ("warning", "/", "index.html")


def test_page_with_css_and_js_under_500_kib_passes(site):
    (site / "a.css").write_bytes(b" " * (200 * 1024))
    (site / "a.js").write_bytes(b" " * (200 * 1024))
    write_index(site, head='<link rel="stylesheet" href="/a.css"><script src="/a.js"></script>')
    assert run(site) == []


@pytest.mark.parametrize("head,canonical", [("", False), (f'<link rel="canonical" href="{ORIGIN}/other">', True), ('<link rel="canonical" href="/">', False)])
def test_missing_doubled_or_relative_canonical_is_seo_canonical_warning(site, head, canonical):
    write_index(site, head=head, canonical=canonical)
    p = only(run(site), "seo.canonical")
    assert (p["severity"], p["file"]) == ("warning", "index.html")


def test_missing_open_graph_tags_are_one_seo_og_info_naming_them(site):
    write_index(site, og=False, head='<meta property="og:title" content="T">')
    p = only(run(site), "seo.og")
    assert (p["severity"], p["file"]) == ("info", "index.html")
    assert "og:title" not in p["message"]
    for name in ("og:type", "og:image", "og:url"):
        assert name in p["message"]


def test_relative_og_image_is_seo_og_info(site):
    write_index(site, og=False, head=f'<meta property="og:title" content="T"><meta property="og:type" content="website"><meta property="og:image" content="/card.png"><meta property="og:url" content="{ORIGIN}/">')
    assert only(run(site), "seo.og")["severity"] == "info"


def test_invalid_json_ld_is_seo_jsonld_error_and_valid_passes(site):
    write_index(site, head='<script type="application/ld+json">{"@type": </script>')
    p = only(run(site), "seo.jsonld")
    assert (p["severity"], p["file"]) == ("error", "index.html")
    write_index(site, head='<script type="application/ld+json">{"@context": "https://schema.org", "@type": "WebSite"}</script>')
    assert run(site) == []


def test_bad_hreflang_value_is_seo_hreflang_warning(site):
    write_index(site, head=f'<link rel="alternate" hreflang="english" href="{ORIGIN}/">')
    rows = found(run(site), "seo.hreflang")
    assert rows and {p["severity"] for p in rows} == {"warning"} and {p["file"] for p in rows} == {"index.html"}


def test_missing_favicon_is_one_site_favicon_warning(site):
    (site / "favicon.ico").unlink()
    assert only(run(site), "site.favicon")["severity"] == "warning"


def test_icon_link_on_the_home_page_stands_in_for_favicon_ico(site):
    (site / "favicon.ico").unlink()
    (site / "icon.png").write_bytes(b"\x89PNG")
    write_index(site, head='<link rel="icon" href="/icon.png">')
    assert run(site) == []


def test_missing_404_page_is_one_site_404_warning(site):
    (site / "404.html").unlink()
    assert only(run(site), "site.404")["severity"] == "warning"


@pytest.mark.parametrize("body", ['<a href="/about"></a>', '<a href="/about"><img src="/favicon.ico" width="4" height="4" alt=""></a>'])
def test_link_without_a_name_is_a11y_link_name_warning(site, body):
    write_index(site, body="<h1>Welcome</h1>" + body)
    p = only(run(site), "a11y.link-name")
    assert (p["severity"], p["file"]) == ("warning", "index.html")


@pytest.mark.parametrize("body", ['<a href="/about" aria-label="About"></a>', '<a href="/about" title="About"></a>', '<a href="/about"><img src="/favicon.ico" width="4" height="4" alt="About"></a>', '<div hidden><a href="/about"></a></div>', '<div aria-hidden="true"><a href="/about"></a></div>'])
def test_link_named_another_way_or_hidden_passes(site, body):
    write_index(site, body="<h1>Welcome</h1>" + body)
    assert run(site) == []


@pytest.mark.parametrize("control", ['<input type="text" name="q">', '<select name="s"><option>a</option></select>', '<textarea name="t"></textarea>'])
def test_control_without_a_label_is_a11y_label_warning(site, control):
    write_index(site, body="<h1>Welcome</h1>" + control)
    p = only(run(site), "a11y.label")
    assert (p["severity"], p["file"]) == ("warning", "index.html")


@pytest.mark.parametrize("control", ['<label>Q <input name="q"></label>', '<label for="q">Q</label><input id="q" name="q">', '<input name="q" aria-label="Search">', '<input name="q" title="Search">', '<input type="hidden" name="h">', '<input type="submit" value="Go">', '<input type="image" src="/favicon.ico" alt="Go">', '<div hidden><input name="q"></div>'])
def test_labelled_or_exempt_control_passes(site, control):
    write_index(site, body="<h1>Welcome</h1>" + control)
    assert run(site) == []


def test_results_are_sorted_by_route_then_code_then_line(tmp_path):
    site = two_route_site(tmp_path, "")
    write_index(site, body='<p>x</p>\n<a href="/z1">a</a>\n<a href="/z2">b</a>', lang="")
    (site / "about" / "index.html").write_text(page_html("/about/", title=None, body="<h1>About</h1>"), encoding="utf-8")
    problems = run(site)
    keys = [(p["route"], p["code"], p.get("line") or 0) for p in problems]
    assert keys == sorted(keys)
    assert {p["code"] for p in problems} == {"link.broken", "heading.h1", "meta.lang", "meta.title"}


def test_same_site_checked_twice_gives_the_same_problem_ids(site):
    write_index(site, body='<h1>Welcome</h1><a href="/missing-page">Gone</a>', lang="")
    first = [p["id"] for p in run(site)]
    assert first == [p["id"] for p in run(site)]
    assert len(set(first)) == len(first) == 2
