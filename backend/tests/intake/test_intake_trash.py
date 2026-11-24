import json
import shutil

from app.services import paths, trash

from .support import SITE_PAGES, call, import_path, tree_digest, write_zip


def remove(tmp_path, name="Doomed", files=None, zip_name="a.zip"):
    site = import_path(write_zip(tmp_path / zip_name, files or SITE_PAGES), name)[1]
    tree = tree_digest(paths.sites_dir() / site["id"])
    record = json.loads((paths.sites_dir() / site["id"] / "site.json").read_text())
    assert call("DELETE", f"/api/sites/{site['id']}")[0] == 200
    return site, tree, record


def only_entry():
    data = call("GET", "/api/trash")[1]
    assert data["count"] == 1
    return data["entries"][0]


def test_removed_site_is_found_in_the_trash_with_its_name_origin_and_size(tmp_path):
    site, tree, record = remove(tmp_path)
    entry = only_entry()
    assert entry["kind"] == "site"
    assert entry["label"] == "Doomed"
    assert entry["origin"] == f"sites/{site['id']}"
    assert entry["originInferred"] is False
    assert entry["size"] >= sum(len(v) for v in SITE_PAGES.values())
    assert call("GET", "/api/trash")[1]["size"] == entry["size"]


def test_removed_site_comes_back_byte_for_byte(tmp_path):
    site, tree, record = remove(tmp_path)
    entry = only_entry()
    status, answer = call("POST", f"/api/trash/{entry['entry']}/restore")
    assert status == 200
    assert answer["restored"] is True
    assert answer["origin"] == f"sites/{site['id']}"
    assert tree_digest(paths.sites_dir() / site["id"]) == tree
    assert call("GET", "/api/trash")[1]["count"] == 0
    listed = call("GET", "/api/sites")[1]
    assert [s["id"] for s in listed["sites"]] == [site["id"]]
    assert listed["sites"][0] == record


def test_restored_site_serves_its_routes_and_revisions_again(tmp_path):
    archive = tmp_path / "a.zip"
    write_zip(archive, SITE_PAGES)
    site = import_path(archive, "Twice")[1]
    write_zip(archive, {**SITE_PAGES, "index.html": b"<html><body>v2</body></html>"})
    site = import_path(archive, "Twice")[1]
    call("DELETE", f"/api/sites/{site['id']}")
    call("POST", f"/api/trash/{only_entry()['entry']}/restore")
    revisions = call("GET", f"/api/sites/{site['id']}/revisions")[1]
    assert revisions["count"] == 2
    assert [r["revision"] for r in reversed(revisions["revisions"])] == site["revisions"]
    assert call("GET", f"/api/sites/{site['id']}/routes")[1]["count"] == 2


def test_restore_is_refused_while_something_sits_at_the_origin(tmp_path):
    archive = tmp_path / "a.zip"
    write_zip(archive, SITE_PAGES)
    site = import_path(archive, "Same")[1]
    call("DELETE", f"/api/sites/{site['id']}")
    again = import_path(archive, "Same")[1]
    assert again["id"] == site["id"]
    status, data = call("POST", f"/api/trash/{only_entry()['entry']}/restore")
    assert status == 409
    assert data["code"] == "place-taken"
    assert f"sites/{site['id']}" in data["detail"]
    assert call("GET", "/api/trash")[1]["count"] == 1
    assert call("GET", "/api/sites")[1]["count"] == 1


def test_removing_the_same_site_twice_keeps_two_separate_trash_entries(tmp_path):
    archive = tmp_path / "a.zip"
    write_zip(archive, SITE_PAGES)
    site = import_path(archive, "Same")[1]
    call("DELETE", f"/api/sites/{site['id']}")
    import_path(archive, "Same")
    call("DELETE", f"/api/sites/{site['id']}")
    data = call("GET", "/api/trash")[1]
    assert data["count"] == 2
    assert len({e["entry"] for e in data["entries"]}) == 2


def test_trash_lists_newest_first(tmp_path):
    a = import_path(write_zip(tmp_path / "a.zip", SITE_PAGES), "First")[1]
    b = import_path(write_zip(tmp_path / "b.zip", SITE_PAGES), "Second")[1]
    call("DELETE", f"/api/sites/{a['id']}")
    call("DELETE", f"/api/sites/{b['id']}")
    entries = call("GET", "/api/trash")[1]["entries"]
    side = {e["entry"]: paths.trash_dir() / (e["entry"] + trash.SUFFIX) for e in entries}
    for e in entries:
        record = json.loads(side[e["entry"]].read_text())
        record["moved"] = "2020-01-01T00:00:00.000Z" if e["label"] == "First" else "2021-01-01T00:00:00.000Z"
        side[e["entry"]].write_text(json.dumps(record))
    labels = [e["label"] for e in call("GET", "/api/trash")[1]["entries"]]
    assert labels == ["Second", "First"]


def test_delete_for_good_removes_the_entry_and_its_record(tmp_path):
    remove(tmp_path)
    entry = only_entry()["entry"]
    status, data = call("DELETE", f"/api/trash/{entry}")
    assert status == 200
    assert data == {"entry": entry, "deleted": True}
    assert call("GET", "/api/trash")[1]["count"] == 0
    assert list(paths.trash_dir().iterdir()) == []
    assert call("POST", f"/api/trash/{entry}/restore")[0] == 404


def test_emptying_the_trash_deletes_every_entry_and_reports_the_count(tmp_path):
    for i in range(3):
        site = import_path(write_zip(tmp_path / f"s{i}.zip", SITE_PAGES), f"Site {i}")[1]
        call("DELETE", f"/api/sites/{site['id']}")
    assert call("GET", "/api/trash")[1]["count"] == 3
    status, data = call("DELETE", "/api/trash")
    assert status == 200
    assert data == {"deleted": 3, "emptied": True}
    after = call("GET", "/api/trash")[1]
    assert after["count"] == 0 and after["size"] == 0
    assert list(paths.trash_dir().iterdir()) == []


def test_emptying_an_empty_trash_deletes_nothing():
    status, data = call("DELETE", "/api/trash")
    assert status == 200
    assert data["deleted"] == 0


def test_emptying_the_trash_also_clears_a_record_left_without_its_entry():
    (paths.trash_dir() / "ghost-20260101T000000Z.trash.json").write_text(json.dumps({"kind": "site"}))
    call("DELETE", "/api/trash")
    assert list(paths.trash_dir().iterdir()) == []


def test_emptying_or_deleting_from_the_trash_needs_the_window_key(tmp_path):
    remove(tmp_path)
    entry = only_entry()["entry"]
    assert call("DELETE", "/api/trash", keyed=False)[0] == 403
    assert call("DELETE", f"/api/trash/{entry}", keyed=False)[0] == 403
    assert call("POST", f"/api/trash/{entry}/restore", keyed=False)[0] == 403
    assert call("GET", "/api/trash")[1]["count"] == 1


def test_restoring_or_deleting_an_unknown_entry_is_answered_404():
    status, data = call("POST", "/api/trash/nothing-here/restore")
    assert status == 404
    assert data["code"] == "trash-missing"
    assert call("DELETE", "/api/trash/nothing-here")[0] == 404


def test_entry_name_that_climbs_out_of_the_trash_is_not_accepted(tmp_path):
    (tmp_path / "keepme").mkdir()
    status, data = call("DELETE", "/api/trash/..%2F..%2Fkeepme")
    assert status in (404, 400)
    assert (tmp_path / "keepme").is_dir()
    assert paths.sites_dir().is_dir()


def test_entry_from_before_records_existed_is_inferred_from_its_site_json(tmp_path):
    site, tree, record = remove(tmp_path)
    entry = only_entry()
    (paths.trash_dir() / (entry["entry"] + trash.SUFFIX)).unlink()
    row = only_entry()
    assert row["kind"] == "site"
    assert row["origin"] == f"sites/{site['id']}"
    assert row["originInferred"] is True
    assert call("POST", f"/api/trash/{row['entry']}/restore")[0] == 200
    assert tree_digest(paths.sites_dir() / site["id"]) == tree


def make_unlabelled_entry(name="stray-20260101T000000Z"):
    folder = paths.trash_dir() / name
    folder.mkdir()
    (folder / "index.html").write_bytes(SITE_PAGES["index.html"])
    (folder / "site.json").write_text(json.dumps({"name": "Stray"}))
    return name


def test_entry_with_no_known_origin_is_refused_with_origin_unknown():
    name = make_unlabelled_entry()
    status, data = call("POST", f"/api/trash/{name}/restore")
    assert status == 409
    assert data["code"] == "origin-unknown"
    assert call("GET", "/api/trash")[1]["count"] == 1


def test_entry_with_no_known_origin_goes_to_the_named_place_inside_sites():
    name = make_unlabelled_entry()
    status, data = call("POST", f"/api/trash/{name}/restore", {"origin": "sites/stray-site"})
    assert status == 200
    assert data["origin"] == "sites/stray-site"
    assert (paths.sites_dir() / "stray-site" / "index.html").read_bytes() == SITE_PAGES["index.html"]
    assert call("GET", "/api/trash")[1]["count"] == 0
    assert json.loads((paths.sites_dir() / "stray-site" / "site.json").read_text())["id"] == "stray-site"


def test_named_place_that_leaves_the_sites_folder_is_refused(tmp_path):
    name = make_unlabelled_entry()
    for bad in ("../outside", "sites/../../outside", "/etc/outside", "builds/abc", "sites", "keys/x.pem"):
        status, data = call("POST", f"/api/trash/{name}/restore", {"origin": bad})
        assert status == 409, bad
        assert data["code"] == "place-invalid", bad
    assert not (paths.home().parent / "outside").exists()
    assert call("GET", "/api/trash")[1]["count"] == 1


def test_named_place_with_capital_letters_is_refused_as_a_bad_site_name():
    name = make_unlabelled_entry()
    status, data = call("POST", f"/api/trash/{name}/restore", {"origin": "sites/Bad Name"})
    assert status == 409
    assert "lowercase letters, digits and hyphens" in data["detail"]


def test_restore_body_that_is_not_json_or_has_wrong_types_is_a_400():
    name = make_unlabelled_entry()
    assert call("POST", f"/api/trash/{name}/restore", b"{oops", {"content-type": "application/json"})[0] == 400
    assert call("POST", f"/api/trash/{name}/restore", [1])[0] == 400
    assert call("POST", f"/api/trash/{name}/restore", {"origin": 5})[0] == 400
    assert call("POST", f"/api/trash/{name}/restore", {"passphrase": 5})[0] == 400


def test_recorded_origin_wins_over_one_given_in_the_request(tmp_path):
    site, tree, record = remove(tmp_path)
    entry = only_entry()["entry"]
    status, data = call("POST", f"/api/trash/{entry}/restore", {"origin": "sites/elsewhere"})
    assert status == 200
    assert data["origin"] == f"sites/{site['id']}"
    assert not (paths.sites_dir() / "elsewhere").exists()


def test_trash_entry_whose_recorded_origin_points_outside_sites_is_refused(tmp_path):
    site, tree, record = remove(tmp_path)
    entry = only_entry()
    side = paths.trash_dir() / (entry["entry"] + trash.SUFFIX)
    meta = json.loads(side.read_text())
    meta["origin"] = "../escaped"
    side.write_text(json.dumps(meta))
    status, data = call("POST", f"/api/trash/{entry['entry']}/restore")
    assert status == 409
    assert data["code"] == "place-invalid"
    assert not (paths.home().parent / "escaped").exists()


def test_trash_survives_a_site_folder_removed_by_hand_between_runs(tmp_path):
    site, tree, record = remove(tmp_path)
    shutil.rmtree(paths.sites_dir(), ignore_errors=True)
    paths.sites_dir()
    assert call("GET", "/api/sites")[1]["count"] == 0
    assert call("POST", f"/api/trash/{only_entry()['entry']}/restore")[0] == 200
    assert tree_digest(paths.sites_dir() / site["id"]) == tree
