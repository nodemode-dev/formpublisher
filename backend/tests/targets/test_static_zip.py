import hashlib
import io
import json
import re
import zipfile

from .support import PAGES, REDIRECTS, api, made, out, prepared  # noqa: F401


def test_site_zip_read_back_equals_the_hand_made_site_byte_for_byte(prepared):
    with zipfile.ZipFile(out(prepared, "static-zip") / "site.zip") as archive:
        assert archive.testzip() is None
        got = {name: archive.read(name) for name in archive.namelist() if not name.endswith("/")}
    for rel, data in PAGES.items():
        assert got[rel] == data
    assert set(got) == set(PAGES) | {"redirects.json"}


def test_site_zip_holds_every_byte_value_of_a_binary_file_unchanged(prepared):
    with zipfile.ZipFile(out(prepared, "static-zip") / "site.zip") as archive:
        assert archive.read("assets/dot.bin") == bytes(range(256))


def test_sha256sums_lines_follow_the_sha256sum_format_and_match_the_files(prepared):
    folder = out(prepared, "static-zip")
    lines = (folder / "SHA256SUMS").read_text(encoding="ascii").splitlines()
    assert len(lines) == 2
    seen = {}
    for line in lines:
        found = re.fullmatch(r"([0-9a-f]{64})  (\S+)", line)
        assert found, line
        seen[found.group(2)] = found.group(1)
    assert seen == {name: hashlib.sha256((folder / name).read_bytes()).hexdigest() for name in ("publish.json", "site.zip")}


def test_publish_json_lists_each_site_file_with_its_real_sha256_and_size(prepared):
    manifest = json.loads((out(prepared, "static-zip") / "publish.json").read_bytes())
    rows = {row["path"]: row for row in manifest["files"]}
    for rel, data in PAGES.items():
        assert rows[rel]["sha256"] == hashlib.sha256(data).hexdigest()
        assert rows[rel]["size"] == len(data)


def test_publish_json_package_hash_is_the_hash_of_site_zip(prepared):
    folder = out(prepared, "static-zip")
    manifest = json.loads((folder / "publish.json").read_bytes())
    assert manifest["package"]["sha256"] == hashlib.sha256((folder / "site.zip").read_bytes()).hexdigest()


def test_publish_json_carries_the_redirects_written_in_redirects_json(prepared):
    manifest = json.loads((out(prepared, "static-zip") / "publish.json").read_bytes())
    assert manifest["redirects"] == REDIRECTS


def test_file_sizes_reported_by_prepare_match_the_files_on_disk(prepared):
    folder = out(prepared, "static-zip")
    for row in prepared["results"]["static-zip"]["files"]:
        data = (folder / row["path"]).read_bytes()
        assert row["size"] == len(data)
        assert row["sha256"] == hashlib.sha256(data).hexdigest()


def test_two_builds_of_the_same_site_give_the_same_site_zip_bytes(prepared, api, client):
    first = (out(prepared, "static-zip") / "site.zip").read_bytes()
    again = client.build(prepared["site"])
    answer = api.post("/api/publish/prepare", {"build": again["id"], "targets": ["static-zip"]}).json()
    from pathlib import Path

    second = (Path(answer["results"]["static-zip"]["folder"]) / "site.zip").read_bytes()
    assert zipfile.ZipFile(io.BytesIO(second)).namelist() == zipfile.ZipFile(io.BytesIO(first)).namelist()
    assert second == first


def test_readme_names_the_site_and_the_three_files_beside_it(prepared):
    text = (out(prepared, "static-zip") / "README.txt").read_text(encoding="utf-8")
    assert "handmade" in text.splitlines()[0]
    for name in ("site.zip", "publish.json", "SHA256SUMS"):
        assert name in text
