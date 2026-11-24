import json
import os
import re
import stat
import subprocess

import pytest

from .support import ALL, PAGES, api, directives, made, make_site, nginx_parse, other_site, out, prepared, resolve, server_block, standin_nginx  # noqa: F401

SYSTEM = "/usr/bin:/bin"


def conf_text(prepared_run):
    return (out(prepared_run, "nginx") / "formpublisher.conf").read_text(encoding="utf-8")


def first(server, name):
    found = directives(server, name)
    assert found, name
    return found[0][0]


def publish_json(prepared_run):
    return json.loads((out(prepared_run, "static-zip") / "publish.json").read_text(encoding="utf-8"))


def prepare_nginx(tmp_path, client, api, redirects, pages=PAGES):
    return other_site(tmp_path, client, api, pages, redirects, ["nginx"])


def test_server_block_parses_under_nginx_syntax_rules_as_one_server(prepared):
    server = server_block(conf_text(prepared))
    assert directives(server, "listen")
    assert directives(server, "location")


def test_server_block_listens_on_port_80_for_ipv4_and_ipv6(prepared):
    server = server_block(conf_text(prepared))
    assert [args for args, _ in directives(server, "listen")] == [["80"], ["[::]:80"]]


def test_server_block_serves_the_document_root_of_the_official_nginx_image(prepared):
    server = server_block(conf_text(prepared))
    assert first(server, "root") == ["/usr/share/nginx/html"]
    assert first(server, "index") == ["index.html"]
    assert first(server, "absolute_redirect") == ["off"]


def test_error_page_404_points_at_the_sites_404_page(prepared):
    server = server_block(conf_text(prepared))
    assert first(server, "error_page") == ["404", "/404.html"]


def test_site_without_404_page_has_no_error_page_directive(tmp_path, client, api):
    pages = {k: v for k, v in PAGES.items() if k != "404.html"}
    run = prepare_nginx(tmp_path, client, api, None, pages)
    server = server_block((out(run, "nginx") / "formpublisher.conf").read_text(encoding="utf-8"))
    assert directives(server, "error_page") == []


def test_catch_all_location_tries_file_then_folder_then_html_then_404(prepared):
    server = server_block(conf_text(prepared))
    catch = [body for args, body in directives(server, "location") if args == ["/"]]
    assert len(catch) == 1
    assert directives(catch[0], "try_files")[0][0] == ["$uri", "$uri/", "$uri.html", "=404"]


@pytest.mark.parametrize("path,query,status,target", [
    ("/old", "", 301, "/about/"),
    ("/old/", "", 301, "/about/"),
    ("/team", "", 308, "/about/"),
    ("/old", "a=1", 301, "/about/?a=1"),
])
def test_exact_redirects_answer_with_their_status_and_keep_the_query_string(prepared, path, query, status, target):
    server = server_block(conf_text(prepared))
    assert resolve(server, path, query) == (status, target)


@pytest.mark.parametrize("path,query,target", [
    ("/blog/a", "", "/news/a"),
    ("/blog/a/b", "", "/news/a/b"),
    ("/blog/a/b", "x=1", "/news/a/b?x=1"),
    ("/blog/", "", "/news/"),
])
def test_splat_redirect_carries_the_rest_of_the_path_to_the_target(prepared, path, query, target):
    server = server_block(conf_text(prepared))
    assert resolve(server, path, query) == (302, target)


def test_splat_redirect_does_not_catch_a_longer_first_segment(prepared):
    server = server_block(conf_text(prepared))
    assert resolve(server, "/blogger/a") is None


def test_dot_in_a_splat_prefix_matches_only_a_real_dot(tmp_path, client, api):
    run = prepare_nginx(tmp_path, client, api, [{"from": "/v1.0/*", "to": "/docs/:splat", "status": 301}])
    server = server_block((out(run, "nginx") / "formpublisher.conf").read_text(encoding="utf-8"))
    assert resolve(server, "/v1.0/x") == (301, "/docs/x")
    assert resolve(server, "/v1x0/x") is None


@pytest.mark.xfail(strict=True, reason="DEFECT: a redirect whose target has its own query (/find to /search?q=1) is skipped on nginx with a warning about characters needing quotes; docs/MANUAL.md says nginx redirects keep the query string unless the target has its own, so the rule should be written without $args")
def test_redirect_target_with_its_own_query_does_not_get_the_request_query_added(tmp_path, client, api):
    run = prepare_nginx(tmp_path, client, api, [{"from": "/find", "to": "/search?q=1", "status": 302}])
    server = server_block((out(run, "nginx") / "formpublisher.conf").read_text(encoding="utf-8"))
    assert resolve(server, "/find", "z=9") == (302, "/search?q=1")


def test_redirect_to_another_site_keeps_the_full_address(tmp_path, client, api):
    run = prepare_nginx(tmp_path, client, api, [{"from": "/ext", "to": "https://example.org/x", "status": 301}])
    server = server_block((out(run, "nginx") / "formpublisher.conf").read_text(encoding="utf-8"))
    assert resolve(server, "/ext") == (301, "https://example.org/x")


def test_root_redirect_is_written_once_for_the_exact_root_only(tmp_path, client, api):
    run = prepare_nginx(tmp_path, client, api, [{"from": "/", "to": "/about/", "status": 302}])
    server = server_block((out(run, "nginx") / "formpublisher.conf").read_text(encoding="utf-8"))
    exact = [args for args, _ in directives(server, "location") if args[0] == "="]
    assert exact == [["=", "/"]]


@pytest.mark.parametrize("row", [
    {"from": "/x;evil", "to": "/y", "status": 301},
    {"from": "/x", "to": "/y; root /etc", "status": 301},
    {"from": "/x", "to": "/y}", "status": 301},
    {"from": "/x?a=1", "to": "/y", "status": 301},
    {"from": "/x", "to": "/y$host", "status": 301},
    {"from": "/x", "to": 'http://e.org/"q', "status": 301},
])
def test_redirect_holding_characters_nginx_needs_quoted_is_skipped_with_a_warning(tmp_path, client, api, row):
    run = prepare_nginx(tmp_path, client, api, [row, {"from": "/ok", "to": "/about/", "status": 301}])
    text = (out(run, "nginx") / "formpublisher.conf").read_text(encoding="utf-8")
    server = server_block(text)
    assert resolve(server, "/ok") == (301, "/about/")
    assert [args[1] for args, _ in directives(server, "location") if args[0] == "="] == ["/ok", "/ok/"]
    assert any("Skipped the redirect" in w for w in run["results"]["nginx"]["warnings"])
    assert "evil" not in text and "/etc" not in text


@pytest.mark.xfail(strict=True, reason="DEFECT: two redirects whose sources differ only by a trailing slash (/old and /old/) both write location = /old, and nginx refuses a duplicate location (nginx docs, ngx_http_core_module location); the config should keep one rule per address")
def test_two_redirects_that_differ_by_a_trailing_slash_write_no_duplicate_location(tmp_path, client, api):
    rows = [{"from": "/old", "to": "/a/", "status": 301}, {"from": "/old/", "to": "/b/", "status": 301}]
    run = prepare_nginx(tmp_path, client, api, rows)
    server = server_block((out(run, "nginx") / "formpublisher.conf").read_text(encoding="utf-8"))
    names = [tuple(args) for args, _ in directives(server, "location")]
    assert len(names) == len(set(names))


def test_global_headers_are_added_with_always_so_error_pages_carry_them(prepared):
    rows = [r for r in publish_json(prepared)["headers"] if r["for"] == "/*"]
    server = server_block(conf_text(prepared))
    got = {args[0]: (args[1], args[2:]) for args, _ in directives(server, "add_header")}
    assert got == {k: (v, ["always"]) for k, v in rows[0]["values"].items()}


def test_scoped_location_repeats_the_global_headers_because_nginx_does_not_inherit_add_header(prepared):
    data = publish_json(prepared)
    global_values = next(r["values"] for r in data["headers"] if r["for"] == "/*")
    scoped = next(r for r in data["headers"] if r["for"] == "/assets/*")
    server = server_block(conf_text(prepared))
    body = next(b for args, b in directives(server, "location") if args == ["/assets/"])
    got = {args[0]: args[1] for args, _ in directives(body, "add_header")}
    assert got == {**global_values, **scoped["values"]}
    assert directives(body, "try_files")


def test_scoped_header_location_overrides_a_global_value_of_the_same_name(prepared):
    server = server_block(conf_text(prepared))
    body = next(b for args, b in directives(server, "location") if args == ["/assets/"])
    names = [args[0] for args, _ in directives(body, "add_header")]
    assert len(names) == len(set(names))


def test_gzip_is_on_with_a_minimum_length_and_vary(prepared):
    server = server_block(conf_text(prepared))
    assert first(server, "gzip") == ["on"]
    assert first(server, "gzip_vary") == ["on"]
    assert first(server, "gzip_min_length") == ["256"]


def test_gzip_types_never_list_text_html_which_nginx_always_compresses(prepared):
    server = server_block(conf_text(prepared))
    types = first(server, "gzip_types")
    assert "text/html" not in types
    assert "text/css" in types and "application/json" in types and "image/svg+xml" in types


def test_gzip_types_are_distinct_media_types_of_text_like_content(prepared):
    types = first(server_block(conf_text(prepared)), "gzip_types")
    assert len(types) == len(set(types))
    assert all(re.fullmatch(r"[a-z]+/[a-z0-9.+-]+", t) for t in types)
    assert not any(t.startswith(("image/png", "image/jpeg", "font/")) for t in types)


def test_test_wrapper_has_events_and_an_http_block_that_includes_the_server_config(prepared):
    rows = nginx_parse((out(prepared, "nginx") / "nginx-test.conf").read_text(encoding="utf-8"))
    assert directives(rows, "daemon")[0][0] == ["off"]
    assert directives(rows, "events")
    http = directives(rows, "http")[0][1]
    assert directives(http, "include")[0][0] == ["formpublisher.conf"]


def test_test_wrapper_pid_is_relative_so_nginx_t_needs_no_system_folder(prepared):
    rows = nginx_parse((out(prepared, "nginx") / "nginx-test.conf").read_text(encoding="utf-8"))
    assert not directives(rows, "pid")[0][0][0].startswith("/")


@pytest.mark.parametrize("extension,mime", [
    ("css", "text/css"), ("js", "application/javascript"), ("json", "application/json"),
    ("svg", "image/svg+xml"), ("png", "image/png"), ("jpg", "image/jpeg"), ("webp", "image/webp"),
    ("woff2", "font/woff2"), ("ico", "image/x-icon"), ("html", "text/html"), ("webmanifest", "application/manifest+json"),
])
def test_types_table_maps_each_extension_to_its_registered_media_type(prepared, extension, mime):
    http = directives(nginx_parse((out(prepared, "nginx") / "nginx-test.conf").read_text(encoding="utf-8")), "http")[0][1]
    table = directives(http, "types")[0][1]
    owners = [words[0] for words, _ in table if extension in words[1:]]
    assert owners == [mime]


def test_check_script_is_written_executable_and_is_valid_shell(prepared):
    path = out(prepared, "nginx") / "nginx-check.sh"
    assert path.stat().st_mode & stat.S_IXUSR
    done = subprocess.run(["sh", "-n", str(path)], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr


def run_check(folder, path_dirs, extra_env=None):
    env = {"PATH": path_dirs, "TMPDIR": str(folder.parent), "HOME": str(folder.parent)}
    env.update(extra_env or {})
    return subprocess.run(["sh", str(folder / "nginx-check.sh")], capture_output=True, text=True, env=env, timeout=30)


def test_check_script_says_so_and_exits_127_when_nginx_is_not_installed(prepared):
    done = run_check(out(prepared, "nginx"), SYSTEM)
    assert done.returncode == 127
    assert "nginx was not found" in done.stderr


def passes(log):
    return [(log / name).read_text(encoding="utf-8") for name in sorted(os.listdir(log))]


def test_check_script_runs_nginx_t_twice_first_with_unix_sockets_then_on_loopback_ports(prepared, tmp_path):
    bin_dir, log = tmp_path / "bin", tmp_path / "log"
    standin_nginx(bin_dir, log)
    done = run_check(out(prepared, "nginx"), f"{bin_dir}:{SYSTEM}", {"STANDIN_LOG": str(log), "NGINX_CHECK_PORT": "24680"})
    assert done.returncode == 0, done.stderr
    assert "both passes passed" in done.stdout
    one, two = [directives(server_block(text), "listen") for text in passes(log)]
    assert [args[0].startswith("unix:") and args[0].endswith(".sock") for args, _ in one] == [True, True]
    assert [args[0] for args, _ in two] == ["127.0.0.1:24680", "127.0.0.1:24681"]


def test_check_script_reports_the_nginx_error_with_the_path_of_the_prepared_folder(prepared, tmp_path):
    bin_dir, log = tmp_path / "bin", tmp_path / "log"
    standin_nginx(bin_dir, log)
    folder = out(prepared, "nginx")
    done = run_check(folder, f"{bin_dir}:{SYSTEM}", {"STANDIN_LOG": str(log), "STANDIN_MODE": "fail"})
    assert done.returncode == 1
    assert f'unknown directive "bogus" in {folder}/formpublisher.conf:3' in done.stderr


def test_check_script_tries_the_next_port_when_the_first_is_in_use_and_still_exits_0(prepared, tmp_path):
    bin_dir, log = tmp_path / "bin", tmp_path / "log"
    standin_nginx(bin_dir, log)
    done = run_check(out(prepared, "nginx"), f"{bin_dir}:{SYSTEM}", {"STANDIN_LOG": str(log), "STANDIN_MODE": "busy", "STANDIN_BUSY": "2", "NGINX_CHECK_PORT": "24700"})
    assert done.returncode == 0, done.stderr
    ports = [directives(server_block(text), "listen")[0][0][0] for text in passes(log)[1:]]
    assert ports == ["127.0.0.1:24700", "127.0.0.1:24701", "127.0.0.1:24702"]


def test_check_script_leaves_the_prepared_folder_unchanged(prepared, tmp_path):
    bin_dir, log = tmp_path / "bin", tmp_path / "log"
    standin_nginx(bin_dir, log)
    folder = out(prepared, "nginx")
    before = {p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob("*") if p.is_file()}
    run_check(folder, f"{bin_dir}:{SYSTEM}", {"STANDIN_LOG": str(log)})
    after = {p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob("*") if p.is_file()}
    assert after == before


def test_prepare_says_nginx_was_not_checked_when_it_is_not_installed(prepared):
    notes = prepared["results"]["nginx"]["notes"]
    assert any("nginx was not found on this machine" in n for n in notes)


def test_verify_without_nginx_installed_answers_ran_false_and_still_passes(prepared, api):
    answer = api.post(f"/api/publish/{prepared['build']}/nginx/verify").json()
    assert answer["ok"] is True
    assert answer["nginx"] == {"ran": False, "ok": None, "version": "", "output": ""}


def test_verify_runs_nginx_t_on_both_passes_when_nginx_is_installed(tmp_path, client, api, monkeypatch):
    bin_dir, log = tmp_path / "bin", tmp_path / "log"
    standin_nginx(bin_dir, log)
    monkeypatch.setenv("STANDIN_LOG", str(log))
    monkeypatch.setenv("PATH", f"{bin_dir}:{SYSTEM}")
    run = other_site(tmp_path, client, api, PAGES, None, ["nginx"])
    notes = run["results"]["nginx"]["notes"]
    assert any(n.startswith("The config passed nginx -t with nginx 1.99.0") and "loopback port" in n for n in notes)
    answer = api.post(f"/api/publish/{run['build']}/nginx/verify").json()
    assert answer["ok"] is True
    assert answer["nginx"]["ran"] is True and answer["nginx"]["version"] == "1.99.0"
    assert answer["nginx"]["listen"]["ran"] is True


def test_nginx_config_is_handed_to_nginx_with_every_listen_line_pointed_at_loopback(tmp_path, client, api, monkeypatch):
    bin_dir, log = tmp_path / "bin", tmp_path / "log"
    standin_nginx(bin_dir, log)
    monkeypatch.setenv("STANDIN_LOG", str(log))
    monkeypatch.setenv("PATH", f"{bin_dir}:{SYSTEM}")
    other_site(tmp_path, client, api, PAGES, None, ["nginx"])
    one, two = [directives(server_block(text), "listen") for text in passes(log)[:2]]
    assert all(args[0].startswith("unix:") for args, _ in one)
    assert all(re.fullmatch(r"127\.0\.0\.1:\d+", args[0]) for args, _ in two)
    assert len({args[0] for args, _ in two}) == 2


def test_failing_nginx_t_becomes_a_warning_on_prepare_and_a_problem_on_verify(tmp_path, client, api, monkeypatch):
    bin_dir, log = tmp_path / "bin", tmp_path / "log"
    standin_nginx(bin_dir, log)
    monkeypatch.setenv("STANDIN_LOG", str(log))
    monkeypatch.setenv("STANDIN_MODE", "fail")
    monkeypatch.setenv("PATH", f"{bin_dir}:{SYSTEM}")
    run = other_site(tmp_path, client, api, PAGES, None, ["nginx"])
    assert any(w.startswith("nginx -t failed:") and 'unknown directive "bogus"' in w for w in run["results"]["nginx"]["warnings"])
    answer = api.post(f"/api/publish/{run['build']}/nginx/verify").json()
    assert answer["ok"] is False
    rows = [p for p in answer["problems"] if p["source"] == "nginx -t"]
    assert len(rows) == 1 and rows[0]["path"] == "formpublisher.conf" and 'unknown directive "bogus"' in rows[0]["problem"]


def test_docker_command_mounts_site_and_config_read_only_on_the_official_paths(prepared):
    commands = prepared["results"]["nginx"]["commands"]
    docker = next(c["run"] for c in commands if c["run"].startswith("docker run"))
    assert "-v \"$PWD/site:/usr/share/nginx/html:ro\"" in docker
    assert "-v \"$PWD/formpublisher.conf:/etc/nginx/conf.d/default.conf:ro\"" in docker
    assert "-p 8080:80" in docker
