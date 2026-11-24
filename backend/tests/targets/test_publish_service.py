import hashlib
import json
import logging
import os
import zipfile
from pathlib import Path

import pytest

from app.services import package

from .support import ALL, PAGES, api, made, make_site, other_site, out, prepared, tree  # noqa: F401

FORM_PAGE = b'<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><title>C</title></head><body><form name="c" method="post" netlify><input name="a"></form></body></html>\n'


def prepare(api, build, targets=None, **extra):
    body = {"build": build, **extra}
    if targets is not None:
        body["targets"] = targets
    return api.post("/api/publish/prepare", body)


def test_target_list_names_the_six_hosts_in_documented_order(api):
    body = api.get("/api/targets").json()
    assert [t["id"] for t in body["targets"]] == ALL
    assert body["count"] == 6
    assert [t["name"] for t in body["targets"]] == ["Static zip", "Netlify", "Cloudflare Pages", "Vercel", "GitHub Pages", "nginx"]


def test_each_target_names_a_local_command_to_look_at_the_site(api):
    tools = {t["id"]: t["localTool"] for t in api.get("/api/targets").json()["targets"]}
    assert tools["netlify"] == "npx netlify-cli@27 dev --dir site"
    assert tools["cloudflare-pages"] == "npx wrangler@4 pages dev site"
    assert tools["vercel"] == "npx vercel@66 dev site"
    assert tools["static-zip"] == "python3 -m http.server -d site 8080"
    assert tools["nginx"] == "sh nginx-check.sh"


def test_prepare_with_no_target_list_writes_all_six_hosts(api, made):
    answer = prepare(api, made["build"]).json()
    assert list(answer["results"]) == ALL
    assert answer["build"] == made["build"]


def test_prepare_names_each_target_once_even_when_listed_twice(api, made):
    answer = prepare(api, made["build"], ["vercel", "vercel", "netlify"]).json()
    assert list(answer["results"]) == ["vercel", "netlify"]


def test_prepare_refuses_an_unknown_target_by_name_and_writes_nothing(api, made, home):
    answer = prepare(api, made["build"], ["netlify", "ftp"])
    assert answer.status_code == 404
    assert answer.json() == {"detail": "unknown target: 'ftp'", "code": "target-unknown"}
    assert api.get(f"/api/publish/{made['build']}").json()["results"] == {}


@pytest.mark.parametrize("body,message", [
    ({}, "build is required"),
    ({"build": ""}, "build is required"),
    ({"build": 7}, "build is required"),
    ({"build": "x", "targets": "netlify"}, "targets must be a list of target ids"),
    ({"build": "x", "includeModel": "yes"}, "includeModel must be true or false"),
])
def test_prepare_refuses_a_bad_request_with_a_plain_message(api, body, message):
    answer = api.post("/api/publish/prepare", body)
    assert answer.status_code == 400
    assert answer.json()["detail"] == message


def test_prepare_refuses_a_list_of_non_text_target_ids(api, made):
    answer = prepare(api, made["build"], [3])
    assert answer.status_code == 400
    assert answer.json()["detail"] == "targets must be a list of target ids"
    assert api.get(f"/api/publish/{made['build']}").json()["results"] == {}


def test_prepare_refuses_a_body_that_is_not_json_or_not_an_object(api):
    assert api.post("/api/publish/prepare", raw=b"{nope").json()["detail"] == "the body is not valid JSON"
    assert api.post("/api/publish/prepare", raw=b"[1]").json()["detail"] == "the body must be an object"


def test_prepare_refuses_an_unknown_build(api):
    answer = prepare(api, "nosuchbuild", ["netlify"])
    assert answer.status_code == 404
    assert answer.json()["code"] == "build-missing"


@pytest.mark.parametrize("method,path", [
    ("post", "/api/publish/prepare"),
    ("post", "/api/publish/b/netlify/verify"),
    ("post", "/api/publish/b/netlify/reveal"),
    ("delete", "/api/publish/b/netlify"),
])
def test_every_publish_change_is_refused_without_the_window_key(api, method, path):
    answer = getattr(api, method)(path, keyed=False) if method == "delete" else api.post(path, {"build": "b"}, keyed=False)
    assert answer.status_code == 403


def test_a_wrong_window_key_is_refused_too(api, made):
    answer = api.http.post("/api/publish/prepare", json={"build": made["build"]}, headers={api.header: api.key + "x"})
    assert answer.status_code == 403
    assert api.get(f"/api/publish/{made['build']}").json()["results"] == {}


def test_prepared_folders_sit_under_site_and_build_in_the_data_folder(prepared, home):
    for target in ALL:
        assert out(prepared, target) == home / "prepared" / prepared["site"] / prepared["build"] / target


def test_every_listed_file_has_the_real_size_and_sha256_of_the_file_on_disk(prepared):
    for target in ALL:
        folder = out(prepared, target)
        listed = {row["path"]: row for row in prepared["results"][target]["files"]}
        assert set(listed) == set(tree(folder))
        for rel, row in listed.items():
            data = (folder / rel).read_bytes()
            assert row["size"] == len(data)
            assert row["sha256"] == hashlib.sha256(data).hexdigest()


def test_reading_prepared_back_gives_the_same_files_commands_and_notes(api, prepared):
    again = api.get(f"/api/publish/{prepared['build']}").json()
    assert again["site"] == prepared["site"]
    for target in ALL:
        for key in ("files", "commands", "notes", "warnings", "folder", "leftOut"):
            assert again["results"][target][key] == prepared["results"][target][key]


def test_a_host_never_prepared_is_absent_from_the_read_back(api, made):
    prepare(api, made["build"], ["vercel"])
    assert list(api.get(f"/api/publish/{made['build']}").json()["results"]) == ["vercel"]


def test_preparing_again_replaces_the_folder_and_drops_files_put_there_since(api, prepared):
    folder = out(prepared, "netlify")
    (folder / "site/stray.txt").write_text("left by hand")
    assert prepare(api, prepared["build"], ["netlify"]).status_code == 200
    assert not (folder / "site/stray.txt").exists()
    assert (folder / "site/index.html").read_bytes() == PAGES["index.html"]


def test_preparing_again_gives_byte_identical_files(api, prepared):
    before = {t: tree(out(prepared, t)) for t in ALL}
    prepare(api, prepared["build"])
    assert {t: tree(out(prepared, t)) for t in ALL} == before


def test_no_working_folder_is_left_behind_in_prepared(api, prepared, home):
    leftovers = [p.name for p in (home / "prepared").iterdir() if p.name.startswith(".")]
    assert leftovers == []


def test_prepare_refuses_a_build_whose_zip_changed_after_it_was_built(api, made):
    archive = package.zip_path(made["build"])
    archive.write_bytes(archive.read_bytes() + b"x")
    answer = prepare(api, made["build"], ["netlify"])
    assert answer.status_code == 409
    assert answer.json() == {"detail": "site.zip no longer matches publish.json; build it again", "code": "build-damaged"}
    assert api.get(f"/api/publish/{made['build']}").json()["results"] == {}


@pytest.mark.parametrize("target", ALL)
def test_verify_passes_on_a_freshly_prepared_folder(api, prepared, target):
    answer = api.post(f"/api/publish/{prepared['build']}/{target}/verify").json()
    assert answer["ok"] is True
    assert answer["problems"] == []
    assert answer["checked"] == len(prepared["results"][target]["files"])


def test_verify_names_a_site_file_whose_bytes_were_changed(api, prepared):
    (out(prepared, "netlify") / "site/assets/app.css").write_bytes(b"body{}\n")
    answer = api.post(f"/api/publish/{prepared['build']}/netlify/verify").json()
    assert answer["ok"] is False
    assert {"path": "site/assets/app.css", "problem": "hash differs from publish.json", "source": "publish.json"} in answer["problems"]


def test_verify_names_a_site_file_that_was_deleted(api, prepared):
    (out(prepared, "vercel") / "site/about/index.html").unlink()
    problems = api.post(f"/api/publish/{prepared['build']}/vercel/verify").json()["problems"]
    assert {"path": "site/about/index.html", "problem": "missing", "source": "publish.json"} in problems


def test_verify_names_a_file_added_to_the_folder(api, prepared):
    (out(prepared, "cloudflare-pages") / "site/extra.txt").write_text("x")
    problems = api.post(f"/api/publish/{prepared['build']}/cloudflare-pages/verify").json()["problems"]
    assert {"path": "site/extra.txt", "problem": "extra file", "source": "prepare"} in problems


def test_verify_names_a_host_file_that_no_longer_matches_a_fresh_prepare(api, prepared):
    path = out(prepared, "netlify") / "site/_redirects"
    path.write_text(path.read_text() + "/zzz /about/ 301\n")
    problems = api.post(f"/api/publish/{prepared['build']}/netlify/verify").json()["problems"]
    assert {"path": "site/_redirects", "problem": "differs from a fresh prepare", "source": "prepare"} in problems


def test_verify_of_static_zip_names_a_changed_package(api, prepared):
    path = out(prepared, "static-zip") / "site.zip"
    path.write_bytes(path.read_bytes() + b"0")
    problems = api.post(f"/api/publish/{prepared['build']}/static-zip/verify").json()["problems"]
    assert {"path": "site.zip", "problem": "hash differs from publish.json", "source": "publish.json"} in problems


def test_verify_of_a_rewritten_github_404_page_compares_with_a_fresh_prepare(api, prepared):
    path = out(prepared, "github-pages") / "site/404.html"
    path.write_bytes(path.read_bytes() + b"<!-- edited -->")
    problems = api.post(f"/api/publish/{prepared['build']}/github-pages/verify").json()["problems"]
    assert [p["problem"] for p in problems if p["path"] == "site/404.html"] == ["differs from a fresh prepare"]


def test_verify_result_is_kept_and_shows_in_the_prepared_read_back(api, prepared):
    answer = api.post(f"/api/publish/{prepared['build']}/vercel/verify").json()
    kept = api.get(f"/api/publish/{prepared['build']}").json()["results"]
    assert kept["vercel"]["verified"]["verifiedAt"] == answer["verifiedAt"]
    assert kept["vercel"]["verified"]["ok"] is True
    assert kept["netlify"]["verified"] is None


def test_preparing_a_host_again_deletes_its_kept_verify_result_only(api, prepared):
    for target in ("vercel", "netlify"):
        api.post(f"/api/publish/{prepared['build']}/{target}/verify")
    prepare(api, prepared["build"], ["vercel"])
    kept = api.get(f"/api/publish/{prepared['build']}").json()["results"]
    assert kept["vercel"]["verified"] is None
    assert kept["netlify"]["verified"]["ok"] is True


def test_verify_of_a_host_that_was_never_prepared_is_refused(api, made):
    answer = api.post(f"/api/publish/{made['build']}/netlify/verify")
    assert answer.status_code == 404
    assert answer.json()["code"] == "prepared-missing"


def test_verify_of_an_unknown_host_is_refused(api, prepared):
    answer = api.post(f"/api/publish/{prepared['build']}/ftp/verify")
    assert answer.status_code == 404
    assert answer.json()["code"] == "target-unknown"


def test_remove_moves_the_folder_to_trash_and_forgets_the_host(api, prepared, home):
    folder = out(prepared, "netlify")
    answer = api.delete(f"/api/publish/{prepared['build']}/netlify").json()
    assert answer["removed"] is True
    assert not folder.exists()
    moved = Path(answer["trash"])
    assert moved.is_dir() and moved.parent == home / "trash"
    assert (moved / "site/index.html").read_bytes() == PAGES["index.html"]
    assert "netlify" not in api.get(f"/api/publish/{prepared['build']}").json()["results"]


def test_removing_one_host_leaves_the_others(api, prepared):
    api.delete(f"/api/publish/{prepared['build']}/vercel")
    assert set(api.get(f"/api/publish/{prepared['build']}").json()["results"]) == set(ALL) - {"vercel"}


def test_removing_twice_is_refused_the_second_time(api, prepared):
    assert api.delete(f"/api/publish/{prepared['build']}/nginx").status_code == 200
    again = api.delete(f"/api/publish/{prepared['build']}/nginx")
    assert again.status_code == 404 and again.json()["code"] == "prepared-missing"


def test_reveal_of_a_host_never_prepared_is_refused(api, made):
    answer = api.post(f"/api/publish/{made['build']}/netlify/reveal")
    assert answer.status_code == 404
    assert answer.json()["detail"] == "nothing is prepared for that build and target"


def test_reveal_names_the_folder_and_opens_nothing_without_a_desktop(api, prepared, monkeypatch):
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    answer = api.post(f"/api/publish/{prepared['build']}/netlify/reveal").json()
    assert answer["path"] == str(out(prepared, "netlify"))
    assert answer["opened"] is False


def test_cloudflare_commands_name_the_site_as_the_project_in_the_documented_order(prepared):
    runs = [c["run"] for c in prepared["results"]["cloudflare-pages"]["commands"]]
    slug = prepared["site"]
    assert runs == [
        f"npx wrangler@4 pages project create {slug} --production-branch main",
        f"npx wrangler@4 pages deploy site --project-name {slug}",
        "npx wrangler@4 pages dev site",
    ]


def test_vercel_and_netlify_commands_are_the_documented_ones(prepared):
    assert [c["run"] for c in prepared["results"]["vercel"]["commands"]] == ["npx vercel@66 deploy site", "npx vercel@66 deploy site --prod", "npx vercel@66 dev site"]
    assert [c["run"] for c in prepared["results"]["netlify"]["commands"]] == ["npx netlify-cli@27 deploy --dir site", "npx netlify-cli@27 deploy --dir site --prod", "npx netlify-cli@27 dev --dir site"]


def test_static_zip_commands_unpack_and_serve_locally(prepared):
    assert [c["run"] for c in prepared["results"]["static-zip"]["commands"]] == ["unzip site.zip -d site", "python3 -m http.server -d site 8080"]


def test_commands_for_hosts_run_inside_the_prepared_folder(prepared):
    for target in ("netlify", "cloudflare-pages", "vercel", "nginx", "static-zip"):
        assert {c["cwd"] for c in prepared["results"][target]["commands"]} == {"."}


@pytest.fixture
def form_run(tmp_path, client, api):
    pages = {**PAGES, "contact/index.html": FORM_PAGE}
    return other_site(tmp_path, client, api, pages, None)


def test_a_netlify_form_gets_a_note_on_netlify_telling_how_to_turn_form_detection_on(form_run):
    notes = form_run["results"]["netlify"]["notes"]
    assert any("Enable form detection" in n and "contact/index.html" in n for n in notes)
    assert form_run["results"]["netlify"]["warnings"] == []


@pytest.mark.parametrize("target", ["cloudflare-pages", "vercel", "github-pages", "nginx"])
def test_a_netlify_form_is_a_warning_on_every_other_host_because_it_delivers_nothing(form_run, target):
    warnings = form_run["results"][target]["warnings"]
    assert any("that form delivers nothing" in w and "contact/index.html" in w for w in warnings)


def test_a_netlify_form_on_static_zip_warns_unless_the_host_is_netlify(form_run):
    assert any(w.startswith("A form on contact/index.html") and "Unless your host is Netlify" in w for w in form_run["results"]["static-zip"]["warnings"])


def test_a_site_without_a_netlify_form_gets_no_form_warning(prepared):
    for target in ALL:
        assert not any("form" in w.lower() for w in prepared["results"][target]["warnings"])


MODEL = {"site.formweb.json": b'{"settings":{}}\n', "asset-access.json": b"{}\n"}


def test_verify_knows_the_left_out_model_files_and_reports_the_host_clean(tmp_path, client, api):
    run = other_site(tmp_path, client, api, {**PAGES, **MODEL}, None, ["netlify", "static-zip"])
    answer = api.post(f"/api/publish/{run['build']}/netlify/verify").json()
    assert answer["ok"] is True
    assert sorted(answer["leftOut"]) == sorted(MODEL)
    assert api.post(f"/api/publish/{run['build']}/static-zip/verify").json()["leftOut"] == []


def test_static_zip_keeps_the_model_files_while_the_host_folder_leaves_them_out(tmp_path, client, api):
    run = other_site(tmp_path, client, api, {**PAGES, **MODEL}, None, ["netlify", "static-zip"])
    with zipfile.ZipFile(out(run, "static-zip") / "site.zip") as zf:
        assert set(MODEL) <= set(zf.namelist())
    assert not set(MODEL) & set(tree(out(run, "netlify") / "site"))
    assert any("Left out FormWeb's model files" in n for n in run["results"]["netlify"]["notes"])


def test_include_model_puts_the_model_files_back_and_verify_remembers_it(tmp_path, client, api):
    run = other_site(tmp_path, client, api, {**PAGES, **MODEL}, None, ["vercel"], include_model=True)
    assert tree(out(run, "vercel") / "site")["site.formweb.json"] == MODEL["site.formweb.json"]
    answer = api.post(f"/api/publish/{run['build']}/vercel/verify").json()
    assert answer["ok"] is True and answer["includeModel"] is True and answer["leftOut"] == []


SECRETS = {"GH_TOKEN": "ghp_SENTINEL0123456789", "GITHUB_TOKEN": "ghs_SENTINEL9876543210", "NETLIFY_AUTH_TOKEN": "nfp_SENTINEL_netlify", "CLOUDFLARE_API_TOKEN": "cf_SENTINEL_cloudflare", "VERCEL_TOKEN": "vc_SENTINEL_vercel", "CF_ACCOUNT_ID": "acct_SENTINEL"}


def test_tokens_in_the_environment_never_reach_the_prepared_files_the_answers_or_the_log(tmp_path, client, api, monkeypatch, caplog, capfd):
    for name, value in SECRETS.items():
        monkeypatch.setenv(name, value)
    caplog.set_level(logging.DEBUG)
    run = other_site(tmp_path, client, api, PAGES, None)
    answers = [json.dumps(run["results"])]
    for target in ALL:
        answers.append(api.post(f"/api/publish/{run['build']}/{target}/verify").text)
        answers.append(api.post(f"/api/publish/{run['build']}/{target}/reveal").text)
    answers.append(api.get(f"/api/publish/{run['build']}").text)
    seen = "\n".join(answers) + caplog.text + "".join(capfd.readouterr())
    on_disk = b"".join(data for target in ALL for data in tree(out(run, target)).values())
    for value in SECRETS.values():
        assert value not in seen
        assert value.encode() not in on_disk


def test_the_prepared_commands_never_carry_a_credential_argument(prepared):
    for target in ALL:
        for command in prepared["results"][target]["commands"]:
            text = command["run"].lower()
            assert "token" not in text and "--auth" not in text and "password" not in text and "api_key" not in text
