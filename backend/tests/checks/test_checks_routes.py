import asyncio
import json

from conftest import asgi_call

from checks_site import make_site, page_html


def call(method, path, payload=None, keyed=True):
    from app.main import app
    from app.services import window_key

    body = json.dumps(payload).encode() if payload is not None else b""
    headers = {"content-type": "application/json"} if body else {}
    if keyed:
        headers[window_key.HEADER] = window_key.LOCAL_KEY
    status, _, raw = asyncio.run(asgi_call(app, method, path, body, headers))
    return status, json.loads(raw)


def imported(client, tmp_path, **kw):
    site = client.import_path(str(make_site(tmp_path / "src", **kw)))
    return site["id"]


def revision_of(client, site_id):
    return client.get_checks(site_id)["revision"]


def test_running_the_static_tier_over_http_on_a_clean_site_stores_zero_problems(client, tmp_path):
    site_id = imported(client, tmp_path)
    status, answer = call("POST", "/api/checks/run", {"site": site_id})
    assert status == 200 and len(answer["run"]) == 12
    status, report = call("GET", f"/api/checks/{site_id}/{revision_of(client, site_id)}")
    assert status == 200
    assert report["problems"] == []
    assert report["summary"] == {"errors": 0, "warnings": 0, "infos": 0, "tiers": {"static": 0, "live": 0, "deep": 0}, "ran": ["static"]}
    assert report["running"] is None
    assert report["inp"] == "not measured"


def test_report_over_http_counts_one_error_one_warning_one_info(client, tmp_path):
    site_id = imported(client, tmp_path, title=None, lang="", body="<h1>One</h1><h3>Three</h3>")
    call("POST", "/api/checks/run", {"site": site_id})
    _, report = call("GET", f"/api/checks/{site_id}/{revision_of(client, site_id)}")
    assert sorted((p["code"], p["severity"], p["file"]) for p in report["problems"]) == [("heading.order", "info", "index.html"), ("meta.lang", "warning", "index.html"), ("meta.title", "error", "index.html")]
    assert (report["summary"]["errors"], report["summary"]["warnings"], report["summary"]["infos"]) == (1, 1, 1)
    assert report["summary"]["tiers"]["static"] == 3
    for p in report["problems"]:
        assert p["tier"] == "static" and p["id"] and p["route"] == "/" and p["message"] and p["fix"]


def test_before_any_run_the_report_says_no_tier_ran(client, tmp_path):
    site_id = imported(client, tmp_path)
    _, report = call("GET", f"/api/checks/{site_id}/{revision_of(client, site_id)}")
    assert report["summary"]["ran"] == [] and report["problems"] == []


def test_checking_an_unknown_site_is_refused_with_404_and_a_code(client):
    status, answer = call("POST", "/api/checks/run", {"site": "no-such-site"})
    assert status == 404
    assert "site" in json.dumps(answer).lower()
    status, _ = call("GET", "/api/checks/no-such-site/r1")
    assert status == 404


def test_running_checks_without_the_window_key_is_refused_and_stores_nothing(client, tmp_path):
    site_id = imported(client, tmp_path, title=None)
    status, answer = call("POST", "/api/checks/run", {"site": site_id}, keyed=False)
    assert status == 403 and answer["code"] == "forbidden"
    _, report = call("GET", f"/api/checks/{site_id}/{revision_of(client, site_id)}")
    assert report["summary"]["ran"] == []


def test_an_unknown_tier_is_refused(client, tmp_path):
    site_id = imported(client, tmp_path)
    status, _ = call("POST", "/api/checks/run", {"site": site_id, "tiers": ["quick"]})
    assert status == 422


def test_live_problems_posted_over_http_join_the_report_as_the_live_tier(client, tmp_path):
    from app.services import checks

    site_id = imported(client, tmp_path)
    revision = revision_of(client, site_id)
    problem = {"id": "live:console:/:1", "tier": "live", "severity": "error", "code": "live.console", "route": "/", "message": "boom", "fix": "Fix the script."}
    try:
        status, answer = call("POST", "/api/checks/live", {"site": site_id, "revision": revision, "problems": [problem]})
        assert status == 200 and answer["count"] == 1
        _, report = call("GET", f"/api/checks/{site_id}/{revision}")
        assert report["summary"]["ran"] == ["live"]
        assert report["summary"]["tiers"]["live"] == 1 and report["summary"]["errors"] == 1
    finally:
        checks.clear_live(site_id, revision)


def test_a_missing_thumbnail_answers_404(client, tmp_path):
    site_id = imported(client, tmp_path)
    from app.main import app

    status, _, _ = asyncio.run(asgi_call(app, "GET", f"/api/checks/{site_id}/{revision_of(client, site_id)}/thumbs/{'a' * 40}.png"))
    assert status == 404


def test_default_error_codes_follow_the_http_status():
    from app.services import codes

    assert codes.default_code(404) == "not-found"
    assert codes.default_code(409) == "conflict"
    assert codes.default_code(413) == "too-large"
    assert codes.default_code(503) == "unavailable"
    assert codes.default_code(418) == "invalid"
    assert codes.default_code(599) == "internal"
