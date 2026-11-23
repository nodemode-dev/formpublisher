import hashlib
import json
import os
import subprocess
import sys
import zipfile

import pytest

from conftest import broken_site

from .support import BACKEND, DEMO_ZIP, REPO, run_cli, run_json

SIX_TARGETS = {"static-zip", "netlify", "cloudflare-pages", "vercel", "github-pages", "nginx"}


def demo_routes() -> list[dict]:
    with zipfile.ZipFile(DEMO_ZIP) as archive:
        return json.loads(archive.read("routes.json"))


def demo_files() -> dict[str, str]:
    with zipfile.ZipFile(DEMO_ZIP) as archive:
        return {info.filename: hashlib.sha256(archive.read(info)).hexdigest() for info in archive.infolist() if not info.is_dir()}


def imported(capsys) -> dict:
    return run_json(capsys, "import", str(DEMO_ZIP))


def built(capsys) -> tuple[dict, dict]:
    site = imported(capsys)
    return site, run_json(capsys, "build", site["id"])


def test_status_reports_this_version_the_data_folder_and_in_process_mode(capsys, home):
    from app import __version__

    data = run_json(capsys, "status")
    assert data["health"]["version"] == __version__
    assert data["engine"] == {"mode": "in-process", "url": None}
    assert data["sites"] == 0
    assert os.path.samefile(data["health"]["home"], home)


def test_status_text_names_the_version_and_the_in_process_engine(capsys):
    from app import __version__

    code, out, _ = run_cli(capsys, "status")
    assert code == 0
    lines = out.splitlines()
    assert lines[0].startswith(f"FormPublisher {__version__}")
    assert "in-process" in lines[1]
    assert lines[3].split() == ["sites", "0"]


def test_sites_with_nothing_imported_says_how_to_import(capsys):
    code, out, _ = run_cli(capsys, "sites")
    assert code == 0
    assert out.strip() == "no sites yet; import one with: import <path> or import-formweb"


def test_import_of_the_demo_zip_names_the_site_and_counts_its_routes(capsys):
    code, out, err = run_cli(capsys, "import", str(DEMO_ZIP))
    assert code == 0, err
    count = len(demo_routes())
    assert out.startswith("imported Lowlight  id ")
    assert f"  {count} routes  " in out
    listed = run_json(capsys, "sites")
    assert listed["count"] == 1
    assert listed["sites"][0]["name"] == "Lowlight"


def test_import_with_name_overrides_the_site_name(capsys):
    data = run_json(capsys, "import", str(DEMO_ZIP), "--name", "Renamed site")
    assert data["name"] == "Renamed site"


def test_routes_lists_every_route_from_the_exported_routes_json(capsys):
    site = imported(capsys)
    data = run_json(capsys, "routes", site["id"])
    assert data["count"] == len(demo_routes())
    assert sorted(row["page"] for row in data["routes"]) == sorted(row["page"] for row in demo_routes())


def test_importing_the_same_zip_twice_adds_a_revision_with_no_file_changes(capsys):
    first = imported(capsys)
    second = imported(capsys)
    assert second["id"] == first["id"]
    revisions = run_json(capsys, "revisions", first["id"])
    assert revisions["count"] == 2
    diff = run_json(capsys, "diff", first["id"])
    assert diff["added"] == [] and diff["removed"] == [] and diff["changed"] == []
    assert diff["same"] == len(demo_files())


def test_diff_names_a_page_changed_between_two_imports_of_a_publication_folder(capsys, tmp_path):
    folder = broken_site(tmp_path)
    first = run_json(capsys, "import", str(folder))
    page = folder / "shows" / "index.html"
    page.write_bytes(page.read_bytes() + b"<!-- changed -->")
    second = run_json(capsys, "import", str(folder))
    assert second["id"] == first["id"]
    diff = run_json(capsys, "diff", first["id"])
    assert [row["path"] for row in diff["changed"]] == ["shows/index.html"]
    code, out, _ = run_cli(capsys, "diff", first["id"])
    assert code == 0 and "shows/index.html" in out


def test_import_of_a_missing_path_fails_with_exit_one_and_the_path_missing_code(capsys, tmp_path):
    code, out, err = run_cli(capsys, "import", str(tmp_path / "absent.zip"))
    assert code == 1
    assert out == ""
    assert err.startswith("error [path-missing]: ")
    assert "does not exist" in err


def test_routes_of_an_unknown_site_fails_with_site_missing(capsys):
    code, _, err = run_cli(capsys, "routes", "no-such-site")
    assert code == 1
    assert err.strip() == "error [site-missing]: site not found"


def test_build_lists_every_file_of_the_export_with_its_sha256(capsys):
    _, build = built(capsys)
    files = {row["path"]: row["sha256"] for row in build["publish"]["files"]}
    assert files == demo_files()
    assert build["files"] == len(files)


def test_build_package_hash_and_size_match_the_site_zip_it_reports(capsys, home):
    _, build = built(capsys)
    package = build["publish"]["package"]
    zips = [p for p in home.rglob("site.zip") if build["id"] in p.parts]
    assert len(zips) == 1
    assert hashlib.sha256(zips[0].read_bytes()).hexdigest() == package["sha256"]
    assert zips[0].stat().st_size == package["size"] == build["size"]


def test_building_the_same_revision_again_says_already_built(capsys):
    site, first = built(capsys)
    code, out, _ = run_cli(capsys, "build", site["id"])
    assert code == 0
    assert out.startswith(f"build {first['id']}  ")
    assert "(already built, same bytes)" in out
    assert run_json(capsys, "builds")["count"] == 1


def test_reproduce_rebuilds_the_same_bytes_and_exits_zero(capsys):
    _, build = built(capsys)
    data = run_json(capsys, "reproduce", build["id"])
    assert data["same"] is True
    assert data["sha256"] == data["expected"] == build["publish"]["package"]["sha256"]


def test_compare_of_a_build_with_itself_finds_every_file_the_same(capsys):
    _, build = built(capsys)
    data = run_json(capsys, "compare", build["id"], build["id"])
    assert data["added"] == [] and data["removed"] == [] and data["changed"] == []
    assert data["same"] == build["files"]


def test_fpub_without_out_writes_site_build_fpub_in_the_current_folder(capsys, tmp_path, monkeypatch):
    site, build = built(capsys)
    monkeypatch.chdir(tmp_path)
    code, out, _ = run_cli(capsys, "fpub", build["id"])
    target = tmp_path / f"{site['id']}-{build['id']}.fpub"
    assert code == 0
    assert target.is_file()
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    assert out.strip() == f"saved build {build['id']} as {target}  {target.stat().st_size} bytes  sha256 {digest}"


def test_fpub_is_a_zip_whose_first_entry_is_fpub_json_holding_the_package_digest(capsys, tmp_path):
    _, build = built(capsys)
    target = tmp_path / "one.fpub"
    run_json(capsys, "fpub", build["id"], "--out", str(target))
    with zipfile.ZipFile(target) as archive:
        names = archive.namelist()
        assert names[0] == "fpub.json"
        assert {"publish.json", "site.zip"} <= set(names)
        inner = archive.read("site.zip")
        assert all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in archive.infolist())
    assert hashlib.sha256(inner).hexdigest() == build["publish"]["package"]["sha256"]


def test_saving_the_same_build_twice_gives_identical_bytes(capsys, tmp_path):
    _, build = built(capsys)
    run_json(capsys, "fpub", build["id"], "--out", str(tmp_path / "a.fpub"))
    run_json(capsys, "fpub", build["id"], "--out", str(tmp_path / "b.fpub"))
    assert (tmp_path / "a.fpub").read_bytes() == (tmp_path / "b.fpub").read_bytes()


def test_fpub_refuses_an_existing_file_without_force_and_replaces_it_with_force(capsys, tmp_path):
    _, build = built(capsys)
    target = tmp_path / "taken.fpub"
    target.write_bytes(b"keep me")
    code, _, err = run_cli(capsys, "fpub", build["id"], "--out", str(target))
    assert code == 1
    assert "already exists; use --force to replace it" in err
    assert target.read_bytes() == b"keep me"
    code, _, _ = run_cli(capsys, "fpub", build["id"], "--out", str(target), "--force")
    assert code == 0
    assert zipfile.is_zipfile(target)


@pytest.mark.parametrize(("name", "message"), [
    ("site.zip", "the file name must end in .fpub"),
    ("no-folder/x.fpub", "does not exist"),
])
def test_fpub_refuses_a_bad_out_path(capsys, tmp_path, name, message):
    _, build = built(capsys)
    code, _, err = run_cli(capsys, "fpub", build["id"], "--out", str(tmp_path / name))
    assert code == 1
    assert message in err
    assert not (tmp_path / name).exists()


def test_importing_a_saved_fpub_restores_the_build_under_a_fresh_id(capsys, tmp_path):
    _, build = built(capsys)
    target = tmp_path / "round.fpub"
    run_json(capsys, "fpub", build["id"], "--out", str(target))
    back = run_json(capsys, "import", str(target))
    assert back["build"]["remapped"] is True
    assert back["build"]["originalId"] == build["id"]
    restored = run_json(capsys, "inspect", back["build"]["id"])
    assert restored["publish"]["package"]["sha256"] == build["publish"]["package"]["sha256"]


def test_importing_an_fpub_with_one_changed_byte_in_site_zip_is_refused(capsys, tmp_path):
    _, build = built(capsys)
    good = tmp_path / "good.fpub"
    run_json(capsys, "fpub", build["id"], "--out", str(good))
    bad = tmp_path / "bad.fpub"
    with zipfile.ZipFile(good) as source, zipfile.ZipFile(bad, "w", zipfile.ZIP_DEFLATED) as out:
        for info in source.infolist():
            data = source.read(info)
            if info.filename == "site.zip":
                data = data[:100] + bytes([data[100] ^ 1]) + data[101:]
            out.writestr(info, data)
    code, _, err = run_cli(capsys, "import", str(bad))
    assert code == 1
    assert "error [fpub-tampered]" in err
    assert "site.zip does not match the checksum recorded in fpub.json" in err


def test_verify_of_an_unsigned_build_exits_one_with_not_valid(capsys):
    _, build = built(capsys)
    code, out, _ = run_cli(capsys, "verify", build["id"])
    assert code == 1
    assert out.startswith("not valid: ")


def test_keys_with_none_made_says_how_to_create_one(capsys):
    code, out, _ = run_cli(capsys, "keys")
    assert code == 0
    assert out.strip() == "no keys yet; create one with: keys --create NAME"


def test_sign_without_any_key_is_refused(capsys):
    _, build = built(capsys)
    code, out, err = run_cli(capsys, "sign", build["id"])
    assert code == 1
    assert out == ""
    assert err.startswith("error [")


def test_a_build_signed_with_your_own_key_verifies_and_exits_zero(capsys):
    _, build = built(capsys)
    key = run_json(capsys, "keys", "--create", "Lane key")
    assert key["canSign"] is True
    signed = run_json(capsys, "sign", build["id"])
    assert signed["keyId"] == key["id"]
    code, out, _ = run_cli(capsys, "verify", build["id"])
    assert code == 0
    assert out.startswith("verified  signed by your key Lane key")
    assert key["fingerprint"] in out


def test_a_signed_build_whose_zip_changed_no_longer_verifies(capsys, home):
    _, build = built(capsys)
    run_json(capsys, "keys", "--create", "Lane key")
    run_json(capsys, "sign", build["id"])
    zips = [p for p in home.rglob("site.zip") if build["id"] in p.parts]
    data = bytearray(zips[0].read_bytes())
    data[-30] ^= 1
    zips[0].write_bytes(bytes(data))
    code, out, _ = run_cli(capsys, "verify", build["id"])
    assert code == 1
    assert out.startswith("not valid: ")


def test_keys_export_without_to_is_refused(capsys):
    key = run_json(capsys, "keys", "--create", "Lane key")
    code, _, err = run_cli(capsys, "keys", "--export", key["id"])
    assert code == 1
    assert "give the file to write with --to FILE" in err


def test_keys_export_refuses_a_passphrase_under_eight_characters(capsys, tmp_path, monkeypatch):
    key = run_json(capsys, "keys", "--create", "Lane key")
    monkeypatch.setenv("FORMPUBLISHER_KEY_PASSPHRASE", "short")
    code, _, err = run_cli(capsys, "keys", "--export", key["id"], "--to", str(tmp_path / "k.pem"))
    assert code == 1
    assert "error [passphrase-short]: the passphrase must be at least 8 characters" in err
    assert not (tmp_path / "k.pem").exists()


def test_targets_lists_exactly_the_six_documented_hosts(capsys):
    data = run_json(capsys, "targets")
    assert {row["id"] for row in data["targets"]} == SIX_TARGETS


def test_prepare_leaves_out_the_model_files_and_verify_prepared_passes(capsys):
    _, build = built(capsys)
    data = run_json(capsys, "prepare", build["id"], "--target", "netlify")
    result = data["results"]["netlify"]
    assert set(result["leftOut"]) == {"site.formweb.json", "asset-access.json"}
    paths = {row["path"] for row in result["files"]}
    assert "site/index.html" in paths and "site/site.formweb.json" not in paths
    code, _, _ = run_cli(capsys, "verify-prepared", build["id"], "netlify")
    assert code == 0


def test_prepare_with_include_model_keeps_the_model_files(capsys):
    _, build = built(capsys)
    data = run_json(capsys, "prepare", build["id"], "--target", "netlify", "--include-model")
    paths = {row["path"] for row in data["results"]["netlify"]["files"]}
    assert {"site/site.formweb.json", "site/asset-access.json"} <= paths


def test_verify_prepared_exits_one_after_a_prepared_file_is_changed(capsys):
    _, build = built(capsys)
    data = run_json(capsys, "prepare", build["id"], "--target", "netlify")
    page = os.path.join(data["results"]["netlify"]["folder"], "site", "index.html")
    with open(page, "ab") as handle:
        handle.write(b"changed")
    code, out, _ = run_cli(capsys, "verify-prepared", build["id"], "netlify", "--json")
    assert code == 1
    answer = json.loads(out)
    assert answer["ok"] is False
    assert any("index.html" in row["path"] for row in answer["problems"])


def test_prepare_for_an_unknown_target_is_refused(capsys):
    _, build = built(capsys)
    code, _, err = run_cli(capsys, "prepare", build["id"], "--target", "no-such-host")
    assert code == 1
    assert "error [target-unknown]" in err


def test_prepare_without_a_target_is_a_usage_error_with_exit_two(capsys):
    with pytest.raises(SystemExit) as stopped:
        run_cli(capsys, "prepare", "any")
    assert stopped.value.code == 2
    assert "--target" in capsys.readouterr().err


def test_prepared_with_nothing_prepared_says_how_to_prepare(capsys):
    _, build = built(capsys)
    code, out, _ = run_cli(capsys, "prepared", build["id"])
    assert code == 0
    assert out.strip() == f"nothing is prepared for build {build['id']} yet; run: prepare {build['id']} --target T"


def test_trash_empty_refuses_without_yes(capsys):
    code, _, err = run_cli(capsys, "trash", "empty")
    assert code == 1
    assert err.strip() == "error [invalid]: emptying the trash deletes everything in it for good; run again with --yes to confirm"


def test_trash_with_nothing_in_it_says_it_is_empty(capsys):
    code, out, _ = run_cli(capsys, "trash")
    assert code == 0
    assert out.strip() == "the trash is empty"


def test_check_refuses_widths_that_are_not_whole_numbers(capsys):
    code, _, err = run_cli(capsys, "check", "any", "--widths", "390,wide")
    assert code == 1
    assert "--widths takes whole numbers separated by commas, for example 390,1440" in err


def test_check_finds_the_broken_link_planted_in_a_publication_folder(capsys, tmp_path):
    site = run_json(capsys, "import", str(broken_site(tmp_path)))
    data = run_json(capsys, "check", site["id"])
    hits = [row for row in data["problems"] if "no-such-page" in json.dumps(row)]
    assert hits
    assert hits[0]["route"] in ("/", "/index.html")
    stored = run_json(capsys, "check", site["id"], "--last")
    assert stored["problems"] == data["problems"]


def test_templates_without_a_kept_list_says_to_fetch_it(capsys):
    code, out, _ = run_cli(capsys, "templates")
    assert code == 0
    assert out.strip().endswith("no list kept yet; get it with: templates --fetch")


def test_an_engine_url_that_does_not_answer_exits_three_with_engine_unreachable(capsys):
    code, out, err = run_cli(capsys, "sites", "--engine", "http://127.0.0.1:9", in_process=False)
    assert code == 3
    assert out == ""
    assert err.strip() == "error [engine-unreachable]: no FormPublisher engine is answering at http://127.0.0.1:9"


def test_the_cli_as_a_program_prints_status_json_and_help(tmp_path):
    env = dict(os.environ)
    run = subprocess.run([sys.executable, "-m", "app.cli", "status", "--json", "--in-process"], cwd=str(BACKEND), env=env, capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr
    from app import __version__

    assert json.loads(run.stdout)["health"]["version"] == __version__
    shown = subprocess.run([sys.executable, "-m", "app.cli", "--help"], cwd=str(BACKEND), env=env, capture_output=True, text=True, timeout=60)
    assert shown.returncode == 0
    docs = json.loads((REPO / "docs" / "mcp-tools.json").read_text(encoding="utf-8"))
    for command in docs["commands"]:
        assert command in shown.stdout
