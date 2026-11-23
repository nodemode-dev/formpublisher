import json

import pytest

from .support import host_call


@pytest.fixture
def site(tmp_path):
    from app.services import host

    root = tmp_path / "site"
    (root / "about").mkdir(parents=True)
    (root / "index.html").write_text("<!doctype html><html><head><title>Home</title></head><body>home</body></html>", encoding="utf-8")
    (root / "about" / "index.html").write_text("<html><head></head><body>about</body></html>", encoding="utf-8")
    (root / "notes.txt").write_bytes(bytes(range(97, 123)))
    (root / "redirects.json").write_text(json.dumps({"redirects": [{"from": "/old", "to": "/about/", "status": 301}, {"from": "/blog/*", "to": "/posts/:splat", "status": 302}]}), encoding="utf-8")
    previous = host.current()
    yield root
    host.unmount()
    if previous is not None:
        host._state["mount"] = previous


def mount(root, **options):
    from app.services import host

    settings = {"probe": False, "theme": "auto", "motion": "auto", "throttle": "none"}
    settings.update(options)
    return host.mount(root, "demo", "r1", settings["probe"], settings["theme"], settings["motion"], settings["throttle"])


def test_host_with_nothing_mounted_says_so(site):
    from app.services import host

    host.unmount()
    status, _, body = host_call("GET", "/")
    assert status == 503
    assert body.decode() == "No site is mounted. Open a site in FormPublisher to preview it here."


def test_mounted_site_serves_its_index_page(site):
    mount(site)
    status, headers, body = host_call("GET", "/")
    assert status == 200
    assert body == (site / "index.html").read_bytes()
    assert headers["content-type"] == "text/html; charset=utf-8"
    assert headers["cache-control"] == "no-store"


def test_folder_route_without_a_slash_finds_its_index(site):
    mount(site)
    status, _, body = host_call("GET", "/about")
    assert status == 200 and b"about" in body


def test_byte_range_returns_exactly_the_asked_bytes(site):
    mount(site)
    status, headers, body = host_call("GET", "/notes.txt", {"range": "bytes=2-5"})
    assert status == 206
    assert body == b"cdef"
    assert headers["content-range"] == "bytes 2-5/26"


def test_suffix_range_returns_the_last_bytes(site):
    mount(site)
    status, _, body = host_call("GET", "/notes.txt", {"range": "bytes=-3"})
    assert status == 206 and body == b"xyz"


def test_range_past_the_end_is_not_satisfiable(site):
    mount(site)
    status, headers, _ = host_call("GET", "/notes.txt", {"range": "bytes=26-"})
    assert status == 416
    assert headers["content-range"] == "bytes */26"


def test_head_request_sends_headers_without_a_body(site):
    mount(site)
    status, headers, body = host_call("HEAD", "/notes.txt")
    assert status == 200 and body == b"" and headers["content-length"] == "26"


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE"])
def test_host_refuses_writes_and_names_the_allowed_methods(site, method):
    mount(site)
    status, headers, body = host_call(method, "/")
    assert status == 405
    assert headers["allow"] == "GET, HEAD"


def test_host_refuses_a_foreign_hostname(site):
    mount(site)
    status, _, body = host_call("GET", "/", host="evil.test")
    assert status == 421
    assert body.decode() == "This host accepts exact loopback hostnames only."


def test_path_climbing_out_of_the_site_is_refused(site):
    (site.parent / "secret.txt").write_text("hidden", encoding="utf-8")
    mount(site)
    status, _, body = host_call("GET", "/../secret.txt")
    assert status == 400 and b"hidden" not in body


def test_missing_page_answers_not_found(site):
    mount(site)
    status, _, body = host_call("GET", "/nowhere")
    assert status == 404 and body == b"Not found"


def test_site_404_page_is_served_with_a_404_status(site):
    (site / "404.html").write_text("<p>lost</p>", encoding="utf-8")
    mount(site)
    status, _, body = host_call("GET", "/nowhere")
    assert status == 404 and body == b"<p>lost</p>"


def test_redirect_file_sends_the_browser_on(site):
    mount(site)
    status, headers, _ = host_call("GET", "/old")
    assert status == 301 and headers["location"] == "/about/"
    status, headers, _ = host_call("GET", "/blog/first")
    assert status == 302 and headers["location"] == "/posts/first"


def test_probe_mount_injects_the_probe_script_right_after_head(site):
    served = mount(site, probe=True, theme="dark")
    status, _, body = host_call("GET", "/")
    tag = f'<script src="/__fp/probe.js?theme=dark&motion=auto&gen={served.generation}"></script>'.encode()
    assert body.count(tag) == 1
    assert body.index(tag) == body.index(b"<head>") + len(b"<head>")
    assert body.replace(tag, b"") == (site / "index.html").read_bytes()


@pytest.mark.parametrize("option,value,message", [("theme", "pink", "theme must be auto, dark or light"), ("motion", "fast", "motion must be auto or reduce"), ("throttle", "dialup", "throttle must be none, fast or slow")])
def test_mount_refuses_unknown_preview_options(site, option, value, message):
    with pytest.raises(ValueError) as caught:
        mount(site, **{option: value})
    assert str(caught.value) == message


def test_each_mount_raises_the_generation_and_the_host_route_reports_it(site):
    from .support import call

    first = mount(site)
    second = mount(site)
    assert second.generation == first.generation + 1
    status, _, data, _ = call("GET", "/api/host", key=None)
    assert status == 200
    assert data["mounted"] is True and data["generation"] == second.generation and data["site"] == "demo"


def test_unmount_route_needs_the_window_key_and_then_empties_the_host(site):
    from .support import call

    mount(site)
    assert call("DELETE", "/api/host/mount", key=None)[0] == 403
    assert call("GET", "/api/host", key=None)[2]["mounted"] is True
    status, _, data, _ = call("DELETE", "/api/host/mount")
    assert status == 200 and data["mounted"] is False and data["url"] is None
    assert host_call("GET", "/")[0] == 503
