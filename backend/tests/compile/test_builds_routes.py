import hashlib
import io
import json
import zipfile


def test_builds_list_is_empty_before_any_build(http):
    status, _h, data = http("GET", "/api/builds")
    assert status == 200
    assert json.loads(data) == {"builds": [], "count": 0}


def test_builds_list_counts_one_after_building_the_same_revision_twice(client, built, http):
    again = client.build(built[0]["id"])
    body = json.loads(http("GET", "/api/builds")[2])
    assert again["created"] is False
    assert body["count"] == 1
    assert [row["id"] for row in body["builds"]] == [built[1]["id"]]


def test_build_record_read_back_names_its_site_revision_and_file_count(built, http):
    site, build = built
    body = json.loads(http("GET", f"/api/builds/{build['id']}")[2])
    with zipfile.ZipFile(io.BytesIO(http("GET", f"/api/builds/{build['id']}/download")[2])) as archive:
        count = len(archive.namelist())
    assert body["site"] == site["id"]
    assert body["revision"] == site["revision"]
    assert body["files"] == count
    assert body["signed"] is False


def test_build_download_matches_the_checksum_and_size_in_its_record(built, http):
    body = json.loads(http("GET", f"/api/builds/{built[1]['id']}")[2])
    data = http("GET", f"/api/builds/{built[1]['id']}/download")[2]
    assert body["publish"]["package"]["sha256"] == hashlib.sha256(data).hexdigest()
    assert body["size"] == len(data)


def test_build_id_is_twelve_hex_digits_of_site_id_and_package_checksum(built, http):
    site, build = built
    data = http("GET", f"/api/builds/{build['id']}/download")[2]
    expected = hashlib.sha256(f"{site['id']}:{hashlib.sha256(data).hexdigest()}".encode()).hexdigest()[:12]
    assert build["id"] == expected


def test_reading_an_unknown_or_malformed_build_id_is_not_found(http):
    for build_id in ("000000000000", "NOT-AN-ID"):
        status, _h, data = http("GET", f"/api/builds/{build_id}")
        assert status == 404
        assert json.loads(data) == {"detail": "build not found", "code": "build-missing"}


def test_creating_a_build_without_a_site_is_refused(http):
    status, _h, data = http("POST", "/api/builds", {})
    assert status == 400
    assert json.loads(data)["detail"] == "site is required"


def test_creating_a_build_with_a_list_body_is_refused(http):
    status, _h, data = http("POST", "/api/builds", [1])
    assert status == 400
    assert json.loads(data)["detail"] == "the body must be an object"


def test_a_build_compared_with_itself_has_every_file_the_same(built, http):
    build = built[1]
    body = json.loads(http("GET", f"/api/builds/{build['id']}/compare/{build['id']}")[2])
    assert body["added"] == [] and body["removed"] == [] and body["changed"] == []
    assert body["same"] == build["files"]


def test_reproducing_a_build_gives_the_recorded_checksum(built, http):
    data = http("GET", f"/api/builds/{built[1]['id']}/download")[2]
    status, _h, raw = http("POST", f"/api/builds/{built[1]['id']}/reproduce")
    body = json.loads(raw)
    assert status == 200
    assert body["same"] is True
    assert body["sha256"] == hashlib.sha256(data).hexdigest()


def test_a_removed_build_is_gone_from_the_list_and_not_found(built, http):
    status, _h, _d = http("DELETE", f"/api/builds/{built[1]['id']}")
    assert status == 200
    assert json.loads(http("GET", "/api/builds")[2])["count"] == 0
    assert http("GET", f"/api/builds/{built[1]['id']}")[0] == 404


def test_two_revisions_with_one_changed_file_compare_as_one_change(client, tmp_path, http):
    folder = tmp_path / "site"
    folder.mkdir()
    (folder / "index.html").write_text("<!doctype html><html><head><title>A</title></head><body>one</body></html>", encoding="utf-8")
    (folder / "about.html").write_text("<!doctype html><html><head><title>B</title></head><body>about</body></html>", encoding="utf-8")
    site = client.import_path(str(folder))
    first = client.build(site["id"])
    (folder / "index.html").write_text("<!doctype html><html><head><title>A</title></head><body>two</body></html>", encoding="utf-8")
    (folder / "new.html").write_text("<!doctype html><html><head><title>C</title></head><body>new</body></html>", encoding="utf-8")
    second = client.build(client.import_path(str(folder))["id"])
    body = json.loads(http("GET", f"/api/builds/{first['id']}/compare/{second['id']}")[2])
    assert body["added"] == ["new.html"]
    assert body["removed"] == []
    assert [row["path"] for row in body["changed"]] == ["index.html"]
    assert body["same"] == 1
