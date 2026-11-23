import hashlib
import json

from app.services import paths

from .support import SITE_PAGES, call, import_path, tree_digest, write_zip

V1 = dict(SITE_PAGES)
V2 = {**SITE_PAGES, "css/site.css": b"body { color: #000; }\n", "contact/index.html": b"<html><body>Contact</body></html>"}
V3 = {k: v for k, v in V2.items() if k != "about/index.html"}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def three_revisions(tmp_path):
    archive = tmp_path / "s.zip"
    seen = []
    saved = []
    for files in (V1, V2, V3):
        write_zip(archive, files)
        site = import_path(archive, "Rev Site")[1]
        seen.append(site["revision"])
        saved.append(tree_digest(paths.sites_dir() / site["id"] / site["revision"]))
    return site["id"], seen, saved


def test_revisions_are_kept_in_the_order_they_were_saved(tmp_path):
    site_id, seen, saved = three_revisions(tmp_path)
    record = call("GET", f"/api/sites/{site_id}")[1]
    assert record["revisions"] == seen
    assert len(set(seen)) == 3
    assert record["revision"] == seen[-1]


def test_revision_list_is_newest_first_and_marks_the_latest(tmp_path):
    site_id, seen, saved = three_revisions(tmp_path)
    data = call("GET", f"/api/sites/{site_id}/revisions")[1]
    assert data["count"] == 3
    assert data["latest"] == seen[-1]
    assert [r["revision"] for r in data["revisions"]] == list(reversed(seen))
    assert [r["latest"] for r in data["revisions"]] == [True, False, False]


def test_revision_list_counts_files_bytes_and_routes_of_each_revision(tmp_path):
    site_id, seen, saved = three_revisions(tmp_path)
    rows = {r["revision"]: r for r in call("GET", f"/api/sites/{site_id}/revisions")[1]["revisions"]}
    for revision, files in zip(seen, (V1, V2, V3)):
        assert rows[revision]["files"] == len(files)
        assert rows[revision]["bytes"] == sum(len(v) for v in files.values())
    assert [rows[r]["routes"] for r in seen] == [2, 3, 2]


def test_revision_list_says_what_changed_from_the_one_before(tmp_path):
    site_id, seen, saved = three_revisions(tmp_path)
    rows = {r["revision"]: r for r in call("GET", f"/api/sites/{site_id}/revisions")[1]["revisions"]}
    assert rows[seen[0]]["changes"] is None
    assert rows[seen[1]]["changes"] == {"added": 1, "removed": 0, "changed": 1}
    assert rows[seen[2]]["changes"] == {"added": 0, "removed": 1, "changed": 0}


def test_revision_time_is_read_from_its_name(tmp_path):
    site_id, seen, saved = three_revisions(tmp_path)
    row = call("GET", f"/api/sites/{site_id}/revisions")[1]["revisions"][-1]
    stamp = seen[0][:16]
    assert row["at"] == f"{stamp[0:4]}-{stamp[4:6]}-{stamp[6:8]}T{stamp[9:11]}:{stamp[11:13]}:{stamp[13:15]}Z"


def test_an_older_revision_is_still_exactly_what_was_saved_after_newer_ones(tmp_path):
    site_id, seen, saved = three_revisions(tmp_path)
    for revision, digest in zip(seen, saved):
        assert tree_digest(paths.sites_dir() / site_id / revision) == digest
    assert saved[0] == {n: sha(b) for n, b in V1.items()}
    assert saved[1] == {n: sha(b) for n, b in V2.items()}


def test_older_revision_serves_its_own_routes_and_the_latest_serves_its_own(tmp_path):
    site_id, seen, saved = three_revisions(tmp_path)
    old = call("GET", f"/api/sites/{site_id}/routes?revision={seen[0]}")[1]
    mid = call("GET", f"/api/sites/{site_id}/routes?revision={seen[1]}")[1]
    new = call("GET", f"/api/sites/{site_id}/routes")[1]
    assert [r["path"] for r in old["routes"]] == ["/", "/about/"]
    assert [r["path"] for r in mid["routes"]] == ["/", "/about/", "/contact/"]
    assert [r["path"] for r in new["routes"]] == ["/", "/contact/"]
    assert old["revision"] == seen[0] and new["revision"] == seen[-1]


def test_unknown_revision_is_answered_404_with_revision_missing(tmp_path):
    site_id, seen, saved = three_revisions(tmp_path)
    status, data = call("GET", f"/api/sites/{site_id}/routes?revision=20000101T000000Z")
    assert status == 404
    assert data["code"] == "revision-missing"
    assert call("GET", f"/api/sites/{site_id}/routes?revision=..")[0] == 404


def test_diff_without_arguments_compares_the_latest_with_the_one_before(tmp_path):
    site_id, seen, saved = three_revisions(tmp_path)
    data = call("GET", f"/api/sites/{site_id}/diff")[1]
    assert data["from"] == seen[1] and data["to"] == seen[2]
    assert [r["path"] for r in data["removed"]] == ["about/index.html"]
    assert data["removed"][0]["sha256"] == sha(V2["about/index.html"])
    assert data["added"] == [] and data["changed"] == []
    assert data["summary"]["same"] == 3
    assert data["routes"]["removed"] == ["/about/"]
    assert data["routes"]["added"] == []


def test_diff_between_two_chosen_revisions_lists_added_changed_and_unchanged_files(tmp_path):
    site_id, seen, saved = three_revisions(tmp_path)
    data = call("GET", f"/api/sites/{site_id}/diff?from={seen[0]}&to={seen[1]}")[1]
    assert [r["path"] for r in data["added"]] == ["contact/index.html"]
    assert data["added"][0]["sha256"] == sha(V2["contact/index.html"])
    assert data["added"][0]["size"] == len(V2["contact/index.html"])
    change = data["changed"][0]
    assert change["path"] == "css/site.css"
    assert change["from"] == {"size": len(V1["css/site.css"]), "sha256": sha(V1["css/site.css"])}
    assert change["to"] == {"size": len(V2["css/site.css"]), "sha256": sha(V2["css/site.css"])}
    assert data["summary"] == {
        "added": 1, "removed": 0, "changed": 1, "same": 2,
        "bytesFrom": sum(len(v) for v in V1.values()), "bytesTo": sum(len(v) for v in V2.values()), "identical": False,
    }


def test_diff_lists_the_routes_added_and_removed(tmp_path):
    site_id, seen, saved = three_revisions(tmp_path)
    data = call("GET", f"/api/sites/{site_id}/diff?from={seen[0]}&to={seen[2]}")[1]
    assert data["routes"] == {"added": ["/contact/"], "removed": ["/about/"], "from": 2, "to": 2}


def test_diff_reaches_back_across_all_revisions_and_forth_swaps_added_and_removed(tmp_path):
    site_id, seen, saved = three_revisions(tmp_path)
    forward = call("GET", f"/api/sites/{site_id}/diff?from={seen[0]}&to={seen[2]}")[1]
    back = call("GET", f"/api/sites/{site_id}/diff?from={seen[2]}&to={seen[0]}")[1]
    assert [r["path"] for r in forward["added"]] == [r["path"] for r in back["removed"]]
    assert [r["path"] for r in forward["removed"]] == [r["path"] for r in back["added"]]
    assert [c["path"] for c in forward["changed"]] == [c["path"] for c in back["changed"]]


def test_a_revision_compared_with_itself_is_identical(tmp_path):
    site_id, seen, saved = three_revisions(tmp_path)
    data = call("GET", f"/api/sites/{site_id}/diff?from={seen[1]}&to={seen[1]}")[1]
    assert data["summary"]["identical"] is True
    assert data["summary"]["same"] == len(V2)


def test_importing_unchanged_content_again_gives_an_identical_revision(tmp_path):
    archive = write_zip(tmp_path / "s.zip", V1)
    site = import_path(archive, "Twin")[1]
    site = import_path(archive, "Twin")[1]
    data = call("GET", f"/api/sites/{site['id']}/diff")[1]
    assert data["summary"]["identical"] is True
    rows = call("GET", f"/api/sites/{site['id']}/revisions")[1]["revisions"]
    assert rows[0]["changes"] == {"added": 0, "removed": 0, "changed": 0}


def test_diff_of_a_site_with_one_revision_says_there_is_nothing_earlier(tmp_path):
    site = import_path(write_zip(tmp_path / "s.zip", V1), "Solo")[1]
    status, data = call("GET", f"/api/sites/{site['id']}/diff")
    assert status == 400
    assert "no earlier revision" in data["detail"]


def test_diff_with_an_unknown_revision_is_answered_404(tmp_path):
    site_id, seen, saved = three_revisions(tmp_path)
    assert call("GET", f"/api/sites/{site_id}/diff?from=nope&to={seen[1]}")[0] == 404
    status, data = call("GET", f"/api/sites/{site_id}/diff?to=nope")
    assert status == 404
    assert data["code"] == "revision-missing"


def test_diff_of_an_unknown_site_is_answered_404():
    assert call("GET", "/api/sites/ghost/diff")[0] == 404


def test_revisions_two_in_the_same_second_get_distinct_names_and_both_stay(tmp_path):
    archive = write_zip(tmp_path / "s.zip", V1)
    names = [import_path(archive, "Fast")[1]["revision"] for _ in range(4)]
    assert len(set(names)) == 4
    site_id = import_path(archive, "Fast")[1]["id"]
    assert call("GET", f"/api/sites/{site_id}/revisions")[1]["count"] == 5


def test_revision_folders_on_disk_match_the_record_and_hold_nothing_else(tmp_path):
    site_id, seen, saved = three_revisions(tmp_path)
    folder = paths.sites_dir() / site_id
    on_disk = sorted(p.name for p in folder.iterdir() if p.is_dir())
    assert on_disk == sorted(seen)
    record = json.loads((folder / "site.json").read_text())
    assert record["revisions"] == seen
