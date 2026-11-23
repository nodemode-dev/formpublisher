import json
import re
import socket
import ssl
from pathlib import Path

import httpx2
import pytest

from app import __version__
from app.services import live_site

from .support import ALL, PAGES, REDIRECTS, api, made, make_site, other_site  # noqa: F401

HOSTING = Path(__file__).resolve().parents[3] / "docs" / "HOSTING.md"
CSS = PAGES["assets/app.css"]


class Net:
    def __init__(self, folder: Path):
        self.files = {rel: data for rel, data in PAGES.items() if rel.endswith((".css", ".bin"))}
        self.files["redirects.json"] = (folder / "redirects.json").read_bytes()
        self.dns = {"example.com", "www.example.com"}
        self.log: list[httpx2.Request] = []
        self.rules: dict = {}
        self.fail: dict = {}
        self.redirects = {r["from"]: r for r in REDIRECTS if not r["from"].endswith("*")}

    def answer(self, request: httpx2.Request) -> httpx2.Response:
        self.log.append(request)
        url = request.url
        host, path, scheme = url.host, url.path, url.scheme
        if (scheme, host) in self.fail:
            raise self.fail[(scheme, host)]
        if (scheme, host, path) in self.rules:
            status, headers, body = self.rules[(scheme, host, path)]
            return httpx2.Response(status, headers=headers, content=body)
        if scheme == "http":
            return httpx2.Response(301, headers={"location": f"https://{host}{path}"})
        if host == "www.example.com" and path == "/":
            return httpx2.Response(301, headers={"location": "https://example.com/"})
        if path == "/":
            return httpx2.Response(200, content=PAGES["index.html"])
        if path in self.redirects:
            row = self.redirects[path]
            return httpx2.Response(row["status"], headers={"location": row["to"]})
        if path.lstrip("/") in self.files:
            return httpx2.Response(200, content=self.files[path.lstrip("/")])
        return httpx2.Response(404, content=PAGES["404.html"])


@pytest.fixture
def net(made, monkeypatch):
    fake = Net(made["folder"])
    real_getaddrinfo = socket.getaddrinfo

    def getaddrinfo(name, *args, **kwargs):
        if name in fake.dns:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("203.0.113.7", 443))]
        if name in ("127.0.0.1", "localhost", "testserver"):
            return real_getaddrinfo(name, *args, **kwargs)
        raise socket.gaierror(-2, "Name or service not known")

    real_client = httpx2.Client

    def client(**kwargs):
        kwargs.pop("verify", None)
        return real_client(transport=httpx2.MockTransport(fake.answer), **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr(live_site.httpx2, "Client", client)
    fake.site = made["site"]
    fake.build = made["build"]
    return fake


def check(api, site, address="example.com", **extra):
    answer = api.post(f"/api/live/{site}", {"address": address, **extra})
    assert answer.status_code == 200, answer.text
    return answer.json()


def codes(result, severity=None):
    return [(p["code"], p["severity"]) for p in result["problems"] if severity is None or p["severity"] == severity]


def find(result, code, name=None):
    rows = [p for p in result["problems"] if p["code"] == code and (name is None or p["name"] == name)]
    assert rows, (code, codes(result))
    return rows


def test_a_site_that_is_deployed_right_has_no_warning_and_no_error(api, net):
    result = check(api, net.site)
    assert result["ok"] is True
    assert result["summary"]["errors"] == 0 and result["summary"]["warnings"] == 0
    assert result["primary"] == "example.com"
    assert result["names"] == ["example.com", "www.example.com"]
    assert result["build"] == net.build


def test_the_clean_run_says_all_redirects_hold_and_the_files_match_the_build(api, net):
    result = check(api, net.site)
    assert find(result, "live.redirect")[0]["message"] == "Redirects tested: 2 of 2. All hold."
    message = find(result, "live.build")[0]["message"]
    assert message.endswith(f"match build {net.build}, so the site online is this build.")
    assert "assets/app.css" in message


def test_the_reported_request_count_equals_the_requests_that_were_made(api, net):
    result = check(api, net.site)
    assert result["requests"] == len(net.log)


def test_the_check_only_reads_with_get_and_sends_no_body_cookie_or_credential(api, net):
    check(api, net.site)
    assert {r.method for r in net.log} == {"GET"}
    for request in net.log:
        assert request.content == b""
        assert not {"cookie", "authorization"} & set(request.headers)


def test_the_check_names_itself_with_the_user_agent_and_the_app_version(api, net):
    check(api, net.site)
    assert {r.headers["user-agent"] for r in net.log} == {f"formpublisher-live-check/{__version__}"}


def test_the_check_never_follows_a_redirect(api, net):
    check(api, net.site)
    hosts = {(r.url.scheme, r.url.host) for r in net.log}
    assert hosts <= {("https", "example.com"), ("https", "www.example.com"), ("http", "example.com"), ("http", "www.example.com")}
    assert [r.url.path for r in net.log if r.url.host == "www.example.com" and r.url.scheme == "https"] == ["/"]


def test_the_made_up_address_for_the_404_probe_has_the_documented_shape_and_changes_each_run(api, net):
    check(api, net.site)
    check(api, net.site)
    probes = [r.url.path for r in net.log if r.url.path.startswith("/formpublisher-live-check-")]
    assert len(probes) == 2 and probes[0] != probes[1]
    assert all(re.fullmatch(r"/formpublisher-live-check-[0-9a-f]{8}", p) for p in probes)


def test_only_exact_redirects_of_the_build_are_asked_and_splat_rules_are_skipped(api, net):
    check(api, net.site)
    asked = sorted(r.url.path for r in net.log if r.url.path in ("/old", "/team") or r.url.path.startswith("/blog"))
    assert asked == ["/old", "/team"]


def test_only_files_that_are_not_pages_are_compared_and_never_more_than_three(api, net):
    check(api, net.site)
    asked = {r.url.path for r in net.log if r.url.path.endswith((".css", ".bin", ".json", ".html"))}
    assert asked <= {"/assets/app.css", "/redirects.json"}
    assert not any(p.endswith(".html") for p in asked)


def test_a_redirect_that_answers_200_is_a_warning_naming_the_wanted_status(api, net):
    net.rules[("https", "example.com", "/old")] = (200, {}, b"page")
    result = check(api, net.site)
    row = find(result, "live.redirect")[0]
    assert row["severity"] == "warning"
    assert row["message"] == "/old should redirect to /about/ with 301, but answers 200."
    assert result["ok"] is False


def test_a_permanent_redirect_served_as_temporary_is_a_warning(api, net):
    net.rules[("https", "example.com", "/old")] = (302, {"location": "/about/"}, b"")
    row = find(check(api, net.site), "live.redirect")[0]
    assert row["severity"] == "warning" and "redirects to /about/ with 302 instead of /about/ with 301" in row["message"]


def test_a_301_and_a_308_both_count_as_permanent(api, net):
    net.rules[("https", "example.com", "/old")] = (308, {"location": "/about/"}, b"")
    result = check(api, net.site)
    assert find(result, "live.redirect")[0]["severity"] == "info"


def test_a_redirect_to_the_wrong_path_is_a_warning(api, net):
    net.rules[("https", "example.com", "/team")] = (308, {"location": "/elsewhere/"}, b"")
    row = find(check(api, net.site), "live.redirect")[0]
    assert row["severity"] == "warning" and "/team redirects to /elsewhere/ with 308 instead of /about/ with 308" in row["message"]


def test_an_absolute_location_with_the_right_path_and_the_same_site_passes(api, net):
    net.rules[("https", "example.com", "/old")] = (301, {"location": "https://www.example.com/about"}, b"")
    assert find(check(api, net.site), "live.redirect")[0]["severity"] == "info"


def test_a_redirect_that_leaves_for_another_site_is_a_warning(api, net):
    net.rules[("https", "example.com", "/old")] = (301, {"location": "https://evil.example.net/about/"}, b"")
    assert find(check(api, net.site), "live.redirect")[0]["severity"] == "warning"


def test_at_most_fifty_redirects_are_tested_and_the_message_counts_them(tmp_path, client, api, monkeypatch):
    rows = [{"from": f"/r{i}", "to": "/about/", "status": 301} for i in range(60)]
    folder = make_site(tmp_path / "many", redirects=rows)
    site = client.import_path(str(folder))
    client.build(site["id"])
    fake = Net(folder)
    fake.redirects = {r["from"]: r for r in rows}
    monkeypatch.setattr(socket, "getaddrinfo", lambda name, *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("203.0.113.7", 443))])
    real = httpx2.Client
    monkeypatch.setattr(live_site.httpx2, "Client", lambda **kw: real(transport=httpx2.MockTransport(fake.answer), **{k: v for k, v in kw.items() if k != "verify"}))
    result = check(api, site["id"])
    assert find(result, "live.redirect")[0]["message"] == "Redirects tested: 50 of 60. All hold."
    assert len([r for r in fake.log if re.fullmatch(r"/r\d+", r.url.path)]) == 50


def test_a_soft_404_is_a_warning(api, net, monkeypatch):
    original = net.answer

    def soft(request):
        if request.url.path.startswith("/formpublisher-live-check-"):
            net.log.append(request)
            return httpx2.Response(200, content=b"home")
        return original(request)

    monkeypatch.setattr(net, "answer", soft)
    row = find(check(api, net.site), "live.404")[0]
    assert row["severity"] == "warning" and "(a soft 404)" in row["message"]


def test_a_missing_address_answering_500_is_a_warning_that_says_what_it_answered(api, net):
    net.rules = {}
    original = net.answer

    def broken(request):
        if request.url.path.startswith("/formpublisher-live-check-"):
            net.log.append(request)
            return httpx2.Response(500)
        return original(request)

    net.answer = broken
    row = find(check(api, net.site), "live.404")[0]
    assert row["severity"] == "warning" and "answers 500 instead of 404" in row["message"]


def test_a_real_404_is_only_information(api, net):
    row = find(check(api, net.site), "live.404")[0]
    assert (row["severity"], row["message"]) == ("info", "An address that does not exist gets 404.")


def test_a_changed_file_online_means_the_site_online_is_not_this_build(api, net):
    net.files["assets/app.css"] = b"body{color:red}\n"
    result = check(api, net.site)
    row = [p for p in find(result, "live.build") if p["severity"] == "warning"][0]
    assert row["message"] == f"/assets/app.css online differs from build {net.build}, so the site online is not this build."
    assert result["ok"] is False


def test_a_file_missing_online_is_named_with_the_status_it_answers(api, net):
    del net.files["assets/app.css"]
    result = check(api, net.site)
    row = [p for p in find(result, "live.build") if p["severity"] == "warning"][0]
    assert row["message"] == f"/assets/app.css is missing online (it answers 404), so the site online is not build {net.build}."


def test_a_name_with_no_dns_record_is_a_warning_while_the_other_name_is_checked(api, net):
    net.dns = {"example.com"}
    result = check(api, net.site)
    row = find(result, "live.www", "www.example.com")[0]
    assert row["severity"] == "warning"
    assert row["message"] == "www.example.com has no DNS record that answers, so visitors who type it get nothing."
    assert result["primary"] == "example.com"


def test_with_no_dns_record_at_all_it_is_one_error_and_no_request_is_made(api, net):
    net.dns = set()
    result = check(api, net.site)
    assert codes(result) == [("live.dns", "error")]
    assert result["requests"] == 0 and net.log == []
    assert result["primary"] is None and result["ok"] is False
    assert find(result, "live.dns")[0]["message"] == "Neither example.com nor www.example.com has a DNS record that answers."


def test_http_that_does_not_redirect_to_https_is_a_warning(api, net):
    net.rules[("http", "example.com", "/")] = (200, {}, b"plain")
    row = find(check(api, net.site), "live.http", "example.com")[0]
    assert row["severity"] == "warning" and row["message"] == "http://example.com/ answers 200 instead of redirecting to https."


def test_http_that_does_not_answer_on_port_80_is_a_warning(api, net):
    net.fail[("http", "example.com")] = httpx2.ConnectError("refused")
    row = find(check(api, net.site), "live.http", "example.com")[0]
    assert row["severity"] == "warning" and row["message"] == "http://example.com/ does not answer on port 80."


def test_a_www_name_that_answers_something_else_than_a_redirect_to_the_bare_name_is_a_warning(api, net):
    net.rules[("https", "www.example.com", "/")] = (302, {"location": "https://example.com/"}, b"")
    row = find(check(api, net.site), "live.www", "www.example.com")[0]
    assert row["severity"] == "warning" and "answers 302 at / instead of the home page or a permanent redirect to example.com" in row["message"]


def test_a_certificate_the_system_does_not_trust_is_an_error_with_the_reason(api, net):
    cause = ssl.SSLCertVerificationError(1, "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed")
    cause.verify_code = 18
    cause.verify_message = "self-signed certificate"
    error = httpx2.ConnectError("tls")
    error.__cause__ = cause
    net.fail[("https", "example.com")] = error
    row = find(check(api, net.site), "live.tls", "example.com")[0]
    assert row["severity"] == "error"
    assert row["message"] == "The certificate of example.com is not valid: self-signed certificate."


def test_when_no_name_answers_on_port_443_it_is_an_error(api, net):
    net.fail[("https", "example.com")] = httpx2.ConnectError("refused")
    net.fail[("https", "www.example.com")] = httpx2.ConnectError("refused")
    result = check(api, net.site)
    assert [p["severity"] for p in find(result, "live.www")] == ["error", "error"]
    assert result["primary"] is None


def test_when_neither_name_serves_the_home_page_the_site_is_reported_as_not_deployed(api, net):
    net.rules[("https", "example.com", "/")] = (404, {}, b"")
    net.rules[("https", "www.example.com", "/")] = (404, {}, b"")
    result = check(api, net.site)
    row = [p for p in find(result, "live.build") if p["severity"] == "error"][0]
    assert row["message"] == "Neither name serves the home page, so the site does not seem to be deployed."
    assert result["primary"] is None


def test_the_primary_name_is_the_one_that_serves_the_home_page_when_the_given_one_redirects(api, net):
    net.rules[("https", "example.com", "/")] = (301, {"location": "https://www.example.com/"}, b"")
    net.rules[("https", "www.example.com", "/")] = (200, {}, b"home")
    result = check(api, net.site)
    assert result["primary"] == "www.example.com"
    assert result["ok"] is True


def test_findings_are_sorted_errors_then_warnings_then_information(api, net):
    net.rules[("https", "example.com", "/old")] = (200, {}, b"")
    net.rules[("http", "example.com", "/")] = (200, {}, b"")
    cause = ssl.SSLCertVerificationError(1, "verify failed")
    cause.verify_code = 18
    cause.verify_message = "self-signed certificate"
    error = httpx2.ConnectError("tls")
    error.__cause__ = cause
    net.fail[("https", "www.example.com")] = error
    order = {"error": 0, "warning": 1, "info": 2}
    ranks = [order[p["severity"]] for p in check(api, net.site)["problems"]]
    assert ranks == sorted(ranks)
    assert ranks[0] == 0 and ranks[-1] == 2


def test_each_finding_carries_code_severity_name_message_fix_and_guide(api, net):
    net.rules[("https", "example.com", "/old")] = (200, {}, b"")
    for row in check(api, net.site)["problems"]:
        assert set(row) == {"code", "severity", "name", "message", "fix", "guide", "guideTopic"}
        assert row["severity"] in ("error", "warning", "info")


def slug(title: str) -> str:
    return re.sub(r"[^a-z0-9 -]", "", title.lower()).replace(" ", "-")


def hosting_sections() -> dict:
    parts, current = {}, None
    for line in HOSTING.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            current = slug(line[3:])
            parts[current] = ""
        elif current:
            parts[current] += line + "\n"
    return parts


@pytest.mark.parametrize("target,part", [
    ("static-zip", "static-zip"), ("netlify", "netlify"), ("cloudflare-pages", "cloudflare-pages"),
    ("vercel", "vercel"), ("github-pages", "github-pages"), ("nginx", "nginx-on-your-own-server"),
])
def test_findings_point_at_the_hosting_guide_part_and_paragraph_of_the_chosen_host(api, net, target, part):
    net.rules[("https", "example.com", "/old")] = (200, {}, b"")
    net.dns = {"example.com"}
    result = check(api, net.site, target=target)
    sections = hosting_sections()
    assert result["target"] == target
    for row in result["problems"]:
        if row["code"] in ("live.www", "live.redirect"):
            assert row["guide"] == part
            assert part in sections
            assert f"**{row['guideTopic']}:**" in sections[part]
    assert {r["guideTopic"] for r in result["problems"] if r["code"] == "live.redirect"} == {"The folder"}
    assert {r["guideTopic"] for r in result["problems"] if r["code"] == "live.www" and r["severity"] == "warning"} == {"Your domain"}


def test_build_findings_point_at_updating_the_site_later_without_a_paragraph(api, net):
    result = check(api, net.site, target="netlify")
    row = find(result, "live.build")[0]
    assert (row["guide"], row["guideTopic"]) == ("updating-the-site-later", None)
    assert "updating-the-site-later" in hosting_sections()


def test_without_a_host_known_findings_point_at_before_you_start(api, net):
    result = check(api, net.site)
    assert result["target"] is None
    assert find(result, "live.404")[0]["guide"] == "before-you-start"
    assert "before-you-start" in hosting_sections()


def test_the_host_defaults_to_the_one_host_prepared_for_the_build(api, net):
    api.post("/api/publish/prepare", {"build": net.build, "targets": ["vercel"]})
    assert check(api, net.site)["target"] == "vercel"


def test_static_zip_is_passed_over_when_another_host_is_prepared_too(api, net):
    api.post("/api/publish/prepare", {"build": net.build, "targets": ["static-zip", "netlify"]})
    assert check(api, net.site)["target"] == "netlify"


def test_two_prepared_hosts_besides_static_zip_leave_the_host_unknown(api, net):
    api.post("/api/publish/prepare", {"build": net.build, "targets": ["netlify", "vercel"]})
    assert check(api, net.site)["target"] is None


def test_the_last_result_is_kept_and_read_back_with_its_address_as_the_suggestion(api, net):
    before = api.get(f"/api/live/{net.site}").json()
    assert before == {"site": net.site, "suggested": None, "last": None}
    result = check(api, net.site, "www.example.com")
    after = api.get(f"/api/live/{net.site}").json()
    assert after["last"] == result
    assert after["suggested"] == "www.example.com"


def test_a_second_check_replaces_the_kept_result(api, net, home):
    check(api, net.site)
    net.rules[("https", "example.com", "/old")] = (200, {}, b"")
    second = check(api, net.site)
    kept = json.loads((home / "live" / f"{net.site}.json").read_text(encoding="utf-8"))
    assert kept == second
    assert kept["ok"] is False


def test_the_kept_result_is_json_with_two_space_indent_and_a_newline(api, net, home):
    check(api, net.site)
    text = (home / "live" / f"{net.site}.json").read_text(encoding="utf-8")
    assert text.endswith("}\n") and text.startswith('{\n  "')


@pytest.mark.parametrize("given", ["example.com", "Example.COM", "https://example.com", "https://example.com/", "http://example.com", "example.com.", "https://example.com:443", "  example.com  "])
def test_every_documented_way_to_write_the_address_names_the_same_domain(api, net, given):
    assert check(api, net.site, given)["address"] == "example.com"


def test_given_the_www_name_the_bare_name_is_the_other_one(api, net):
    result = check(api, net.site, "www.example.com")
    assert result["names"] == ["example.com", "www.example.com"]


def test_a_subdomain_gets_a_www_in_front_as_its_second_name(api, net):
    net.dns = {"blog.example.com"}
    result = check(api, net.site, "blog.example.com")
    assert result["names"] == ["blog.example.com", "www.blog.example.com"]
    assert find(result, "live.www", "www.blog.example.com")[0]["severity"] == "warning"


def test_a_domain_with_accents_is_checked_under_its_idna_name(api, net):
    net.dns = set()
    assert check(api, net.site, "bücher.example")["address"] == "xn--bcher-kva.example"


@pytest.mark.parametrize("given", [
    "https://example.com/path", "https://example.com?x=1", "https://example.com#top", "https://user@example.com",
    "https://user:pw@example.com", "https://example.com:8443", "ftp://example.com", "exa mple.com", "example.com\\x", "https://", "a..b.com",
])
def test_an_address_with_more_than_a_domain_is_refused_with_the_documented_shape(api, net, given):
    answer = api.post(f"/api/live/{net.site}", {"address": given})
    assert answer.status_code == 400
    assert answer.json() == {"detail": "The address must be a domain name or an https address with no path, for example example.com.", "code": "address-invalid"}


@pytest.mark.parametrize("given", ["192.168.1.5", "10.0.0.1", "127.0.0.1", "https://[::1]/", "localhost", "intranet", "printer.local", "host.internal", "router.lan", "-bad-.com", "example.123"])
def test_an_ip_address_or_a_local_name_is_refused(api, net, given):
    answer = api.post(f"/api/live/{net.site}", {"address": given})
    assert answer.status_code == 400
    assert answer.json()["code"] == "address-invalid"
    assert "public domain" in answer.json()["detail"]


@pytest.mark.parametrize("given", ["", "   ", None, 5, ["example.com"]])
def test_a_missing_or_empty_address_is_refused_before_anything_is_read(api, net, given):
    answer = api.post(f"/api/live/{net.site}", {"address": given})
    assert answer.status_code == 400
    assert net.log == []


def test_a_refused_address_stores_nothing(api, net, home):
    api.post(f"/api/live/{net.site}", {"address": "10.0.0.1"})
    assert not (home / "live" / f"{net.site}.json").exists()
    assert api.get(f"/api/live/{net.site}").json()["last"] is None


def test_the_check_is_refused_without_the_window_key_and_reads_nothing(api, net):
    answer = api.post(f"/api/live/{net.site}", {"address": "example.com"}, keyed=False)
    assert answer.status_code == 403
    assert net.log == []


def test_an_unknown_site_is_refused_for_both_reading_and_checking(api, net):
    assert api.get("/api/live/nosuchsite").status_code == 404
    answer = api.post("/api/live/nosuchsite", {"address": "example.com"})
    assert answer.status_code == 404 and answer.json()["code"] == "site-missing"


@pytest.mark.parametrize("body,message", [
    ({"address": "example.com", "build": 3}, "build must be a build id"),
    ({"address": "example.com", "build": ""}, "build must be a build id"),
    ({"address": "example.com", "target": 3}, "target must be a target id"),
    ({"address": "example.com", "target": ""}, "target must be a target id"),
    ({}, "address is required"),
])
def test_a_wrongly_typed_request_is_refused_with_a_plain_message(api, net, body, message):
    answer = api.post(f"/api/live/{net.site}", body)
    assert answer.status_code == 400 and answer.json()["detail"] == message


def test_a_body_that_is_not_json_or_not_an_object_is_refused(api, net):
    assert api.post(f"/api/live/{net.site}", raw=b"{oops").json()["detail"] == "the body is not valid JSON"
    assert api.post(f"/api/live/{net.site}", raw=b"[]").json()["detail"] == "the body must be an object"


def test_an_unknown_host_name_is_refused_with_the_target_code(api, net):
    answer = api.post(f"/api/live/{net.site}", {"address": "example.com", "target": "ftp"})
    assert answer.status_code == 404 and answer.json()["code"] == "target-unknown"


def test_a_build_of_another_site_is_refused(tmp_path, client, api, net):
    other = other_site(tmp_path, client, api, PAGES, None, ["netlify"], name="second")
    answer = api.post(f"/api/live/{net.site}", {"address": "example.com", "build": other["build"]})
    assert answer.status_code == 400
    assert answer.json() == {"detail": "that build belongs to another site", "code": "build-site"}


def test_an_unknown_build_is_refused(api, net):
    answer = api.post(f"/api/live/{net.site}", {"address": "example.com", "build": "nosuch"})
    assert answer.status_code == 404 and answer.json()["code"] == "build-missing"


def test_a_chosen_older_build_is_the_one_compared_and_its_files_must_match(tmp_path, client, api, net):
    first = net.build
    source = Path(client.sites()["sites"][0]["source"]["path"])
    (source / "assets/app.css").write_bytes(b"body{color:blue}\n")
    client.import_path(str(source))
    second = client.build(net.site)["id"]
    assert second != first
    older = check(api, net.site, build=first)
    newer = check(api, net.site, build=second)
    assert older["build"] == first and newer["build"] == second
    assert [p["severity"] for p in find(older, "live.build")] == ["info"]
    assert [p["severity"] for p in find(newer, "live.build")] == ["warning"]


def test_a_site_with_no_build_is_still_checked_and_says_there_is_nothing_to_compare(tmp_path, client, api, monkeypatch):
    folder = make_site(tmp_path / "unbuilt")
    site = client.import_path(str(folder))
    fake = Net(folder)
    monkeypatch.setattr(socket, "getaddrinfo", lambda name, *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("203.0.113.7", 443))])
    real = httpx2.Client
    monkeypatch.setattr(live_site.httpx2, "Client", lambda **kw: real(transport=httpx2.MockTransport(fake.answer), **{k: v for k, v in kw.items() if k != "verify"}))
    result = check(api, site["id"])
    assert result["build"] is None
    assert find(result, "live.build")[0]["message"] == "There is no build of this site to compare the site online with."
    assert not any(r.url.path in ("/old", "/team") for r in fake.log)


def test_the_suggested_address_is_the_host_of_the_canonical_link_of_the_home_page(tmp_path, client, api):
    page = PAGES["index.html"].replace(b"<title>", b'<link rel="canonical" href="https://www.example.org/">\n<title>')
    folder = make_site(tmp_path / "canon", pages={**PAGES, "index.html": page})
    site = client.import_path(str(folder))
    client.build(site["id"])
    assert api.get(f"/api/live/{site['id']}").json()["suggested"] == "www.example.org"


def test_no_suggestion_when_the_canonical_link_names_an_ip_address(tmp_path, client, api):
    page = PAGES["index.html"].replace(b"<title>", b'<link rel="canonical" href="http://192.168.0.2/">\n<title>')
    folder = make_site(tmp_path / "canon2", pages={**PAGES, "index.html": page})
    site = client.import_path(str(folder))
    client.build(site["id"])
    assert api.get(f"/api/live/{site['id']}").json()["suggested"] is None


def test_a_link_that_is_not_canonical_gives_no_suggestion(tmp_path, client, api):
    page = PAGES["index.html"].replace(b"<title>", b'<link rel="alternate" href="https://example.org/">\n<title>')
    folder = make_site(tmp_path / "canon3", pages={**PAGES, "index.html": page})
    site = client.import_path(str(folder))
    client.build(site["id"])
    assert api.get(f"/api/live/{site['id']}").json()["suggested"] is None
