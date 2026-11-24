import hashlib
import io
import json
import zipfile

from .compile_lane import DEMO, entries_of


def test_fpub_holds_exactly_three_entries_in_the_stated_order(fpub_bytes):
    assert [name for name, _ in entries_of(fpub_bytes)] == ["fpub.json", "publish.json", "site.zip"]


def test_fpub_passes_the_zip_integrity_check(fpub_bytes):
    with zipfile.ZipFile(io.BytesIO(fpub_bytes)) as archive:
        assert archive.testzip() is None


def test_fpub_manifest_names_the_format_version_and_build(fpub_bytes, built):
    site, build = built
    meta = json.loads(dict(entries_of(fpub_bytes))["fpub.json"])
    assert meta["format"] == "formpublisher-package"
    assert meta["version"] == 1
    assert meta["build"] == build["id"]
    assert meta["site"]["id"] == site["id"]
    assert meta["signature"] is None


def test_fpub_manifest_checksum_and_size_match_the_inner_site_zip(fpub_bytes):
    parts = dict(entries_of(fpub_bytes))
    meta = json.loads(parts["fpub.json"])
    assert meta["package"]["sha256"] == hashlib.sha256(parts["site.zip"]).hexdigest()
    assert meta["package"]["size"] == len(parts["site.zip"])


def test_inner_site_zip_has_no_absolute_or_parent_paths(fpub_bytes):
    names = [name for name, _ in entries_of(dict(entries_of(fpub_bytes))["site.zip"])]
    assert names
    for name in names:
        assert not name.startswith("/")
        assert "\\" not in name
        assert ".." not in name.split("/")


def test_publish_manifest_lists_every_packed_file_with_its_own_checksum(fpub_bytes):
    parts = dict(entries_of(fpub_bytes))
    publish = json.loads(parts["publish.json"])
    packed = dict(entries_of(parts["site.zip"]))
    listed = {row["path"]: row for row in publish["files"]}
    assert set(listed) == set(packed)
    for path, payload in packed.items():
        assert listed[path]["sha256"] == hashlib.sha256(payload).hexdigest()
        assert listed[path]["size"] == len(payload)


def test_packed_files_are_the_same_bytes_as_the_imported_site(fpub_bytes):
    packed = dict(entries_of(dict(entries_of(fpub_bytes))["site.zip"]))
    with zipfile.ZipFile(DEMO / "sites" / "lowlight.zip") as source:
        original = {i.filename: source.read(i) for i in source.infolist() if not i.is_dir()}
    assert packed["index.html"] == original["index.html"]
    assert {k: hashlib.sha256(v).hexdigest() for k, v in packed.items()} == {k: hashlib.sha256(v).hexdigest() for k, v in original.items() if k in packed}
    assert len(packed) >= 1


def test_packed_file_names_are_in_byte_order(fpub_bytes):
    names = [name for name, _ in entries_of(dict(entries_of(fpub_bytes))["site.zip"])]
    assert names == sorted(names, key=lambda n: n.encode("utf-8"))


def test_the_same_build_downloads_as_the_same_fpub_bytes(fpub_bytes, built, http):
    _status, _headers, again = http("GET", f"/api/builds/{built[1]['id']}/fpub")
    assert hashlib.sha256(again).hexdigest() == hashlib.sha256(fpub_bytes).hexdigest()


def test_fpub_download_is_named_after_site_and_build(built, http):
    site, build = built
    status, headers, _data = http("GET", f"/api/builds/{build['id']}/fpub")
    assert status == 200
    assert f"{site['id']}-{build['id']}.fpub" in headers["content-disposition"]


def test_write_file_reports_the_checksum_of_the_file_it_wrote(built, tmp_path):
    from app.services import fpub

    target = tmp_path / "out.fpub"
    made = fpub.write_file(built[1]["id"], target)
    assert made["sha256"] == hashlib.sha256(target.read_bytes()).hexdigest()
    assert made["size"] == target.stat().st_size


def test_fpub_for_an_unknown_build_is_refused_as_not_found(http):
    status, _headers, data = http("GET", "/api/builds/000000000000/fpub")
    assert status == 404
    assert json.loads(data)["detail"] == "build not found"
