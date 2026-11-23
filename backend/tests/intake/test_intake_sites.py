import hashlib
import json
import os

from app.services import paths

from .support import SITE_PAGES, call, import_path, multipart_upload, receive, tree_digest, write_zip


def expected_digest(files: dict) -> dict:
    return {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}


def test_imported_zip_is_listed_with_its_name_routes_and_size(tmp_path):
    status, site = import_path(write_zip(tmp_path / "a.zip", SITE_PAGES), "Alpha Site")
    assert status == 200
    listed = call("GET", "/api/sites")[1]
    assert listed["count"] == 1
    row = listed["sites"][0]
    assert row["id"] == site["id"]
    assert row["name"] == "Alpha Site"
    assert row["routes"] == 2
    assert row["files"] == 3
    assert row["bytes"] == sum(len(v) for v in SITE_PAGES.values())
    assert row["source"]["kind"] == "zip"


def test_stored_files_equal_the_files_in_the_zip(tmp_path):
    status, site = import_path(write_zip(tmp_path / "a.zip", SITE_PAGES))
    stored = tree_digest(paths.sites_dir() / site["id"] / site["revision"])
    assert stored == expected_digest(SITE_PAGES)


def test_site_without_a_name_takes_the_zip_file_name(tmp_path):
    status, site = import_path(write_zip(tmp_path / "harvest-fair.zip", SITE_PAGES))
    assert site["name"] == "harvest-fair"
    assert site["id"].startswith("harvest-fair-")


def test_zip_with_one_wrapper_folder_opens_as_the_site_inside_it(tmp_path):
    archive = write_zip(tmp_path / "wrapped.zip", SITE_PAGES, prefix="export/")
    status, site = import_path(archive)
    stored = tree_digest(paths.sites_dir() / site["id"] / site["revision"])
    assert stored == expected_digest(SITE_PAGES)
    assert site["routes"] == 2


def test_routes_of_a_site_without_routes_json_come_from_its_index_pages(tmp_path):
    status, site = import_path(write_zip(tmp_path / "a.zip", SITE_PAGES))
    status, data = call("GET", f"/api/sites/{site['id']}/routes")
    assert status == 200
    assert data["source"] == "walk"
    assert [r["path"] for r in data["routes"]] == ["/", "/about/"]
    assert [r["page"] for r in data["routes"]] == ["index.html", "about/index.html"]


def test_routes_json_in_a_zip_decides_the_routes(tmp_path):
    table = {"routes": [{"path": "/", "page": "index.html"}, {"path": "/x/", "page": "x/index.html"}, {"path": "/y/", "page": "y/index.html"}]}
    files = {**SITE_PAGES, "routes.json": json.dumps(table).encode()}
    status, site = import_path(write_zip(tmp_path / "r.zip", files))
    status, data = call("GET", f"/api/sites/{site['id']}/routes")
    assert data["source"] == "routes.json"
    assert data["count"] == 3
    assert [r["path"] for r in data["routes"]] == ["/", "/x/", "/y/"]


def test_redirects_file_is_counted_by_status(tmp_path):
    redirects = [{"from": "/a", "to": "/b", "status": 301}, {"from": "/c", "to": "/d", "status": 302}, {"from": "/e", "to": "/f"}]
    files = {**SITE_PAGES, "redirects.json": json.dumps(redirects).encode(), "sitemap.xml": b"<urlset/>"}
    status, site = import_path(write_zip(tmp_path / "r.zip", files))
    assert site["redirects"]["count"] == 3
    assert site["redirects"]["byStatus"] == {"301": 2, "302": 1}
    assert site["sitemap"] is True
    assert site["robots"] is False


def test_redirect_loop_in_redirects_json_is_reported(tmp_path):
    redirects = [{"from": "/a", "to": "/b"}, {"from": "/b", "to": "/a"}]
    files = {**SITE_PAGES, "redirects.json": json.dumps(redirects).encode()}
    status, site = import_path(write_zip(tmp_path / "r.zip", files))
    assert site["redirects"]["loops"] == 2


def test_get_site_answers_the_record_and_where_it_is_stored(tmp_path):
    status, site = import_path(write_zip(tmp_path / "a.zip", SITE_PAGES), "Alpha")
    status, data = call("GET", f"/api/sites/{site['id']}")
    assert status == 200
    assert data["name"] == "Alpha"
    assert data["path"] == str(paths.sites_dir() / site["id"] / site["revision"])
    assert os.path.isfile(os.path.join(data["path"], "index.html"))


def test_unknown_site_is_answered_404_with_site_missing():
    status, data = call("GET", "/api/sites/no-such-site")
    assert status == 404
    assert data["code"] == "site-missing"
    assert call("GET", "/api/sites/no-such-site/routes")[0] == 404
    assert call("GET", "/api/sites/no-such-site/revisions")[0] == 404


def test_site_id_with_a_path_in_it_is_not_found():
    assert call("GET", "/api/sites/..%2F..%2Fetc")[0] in (404, 400)
    assert call("GET", "/api/sites/Bad_ID")[1]["code"] == "site-missing"


def test_same_zip_path_again_is_the_same_site_with_one_more_revision(tmp_path):
    archive = tmp_path / "a.zip"
    write_zip(archive, SITE_PAGES)
    first = import_path(archive)[1]
    second = import_path(archive)[1]
    assert second["id"] == first["id"]
    assert second["revisions"][0] == first["revision"]
    assert len(second["revisions"]) == 2
    assert second["revision"] == second["revisions"][-1]
    assert call("GET", "/api/sites")[1]["count"] == 1


def test_two_zip_files_with_the_same_name_in_different_folders_are_two_sites(tmp_path):
    (tmp_path / "one").mkdir()
    (tmp_path / "two").mkdir()
    a = import_path(write_zip(tmp_path / "one" / "s.zip", SITE_PAGES), "Same")[1]
    b = import_path(write_zip(tmp_path / "two" / "s.zip", SITE_PAGES), "Same")[1]
    assert a["id"] != b["id"]
    assert call("GET", "/api/sites")[1]["count"] == 2


def test_project_sent_again_under_a_new_name_lands_on_the_same_site_with_the_new_name(tmp_path):
    data = write_zip(tmp_path / "a.zip", SITE_PAGES).read_bytes()
    first = receive(data, project="proj-7", name="Before")[1]
    second = receive(data, project="proj-7", name="After")[1]
    assert second["site"] == first["site"]
    sites = call("GET", "/api/sites")[1]
    assert sites["count"] == 1
    assert sites["sites"][0]["name"] == "After"
    assert len(sites["sites"][0]["revisions"]) == 2


def test_folder_import_copies_files_and_leaves_out_git_and_links(tmp_path):
    folder = tmp_path / "pub"
    for name, data in SITE_PAGES.items():
        target = folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (folder / ".git").mkdir()
    (folder / ".git" / "config").write_text("secret")
    outside = tmp_path / "outside.txt"
    outside.write_text("outside")
    os.symlink(outside, folder / "leak.txt")
    status, site = import_path(folder)
    assert status == 200
    assert site["source"]["kind"] == "folder"
    assert site["skipped"] == 1
    stored = tree_digest(paths.sites_dir() / site["id"] / site["revision"])
    assert stored == expected_digest(SITE_PAGES)


def test_folder_import_does_not_follow_a_linked_directory(tmp_path):
    folder = tmp_path / "pub"
    folder.mkdir()
    (folder / "index.html").write_bytes(SITE_PAGES["index.html"])
    secret = tmp_path / "secret"
    secret.mkdir()
    (secret / "passwd.txt").write_text("root")
    os.symlink(secret, folder / "docs")
    status, site = import_path(folder)
    stored = tree_digest(paths.sites_dir() / site["id"] / site["revision"])
    assert list(stored) == ["index.html"]


def test_import_path_must_be_absolute_and_must_exist(tmp_path):
    status, data = call("POST", "/api/sites/import", {"path": "relative/site.zip"})
    assert status == 400
    assert data["detail"] == "path must be absolute"
    status, data = import_path(tmp_path / "missing.zip")
    assert status == 404
    assert data["code"] == "path-missing"
    status, data = call("POST", "/api/sites/import", {"path": "   "})
    assert status == 400
    assert data["detail"] == "path is required"


def test_import_refuses_a_body_that_is_not_json_or_a_form():
    status, data = call("POST", "/api/sites/import", b"x", {"content-type": "text/plain"})
    assert status == 415
    status, data = call("POST", "/api/sites/import", b"{not json", {"content-type": "application/json"})
    assert status == 400
    status, data = call("POST", "/api/sites/import", [1, 2])
    assert status == 400


def test_uploaded_zip_becomes_a_site_with_the_given_name(tmp_path):
    body, headers = multipart_upload("up.zip", write_zip(tmp_path / "a.zip", SITE_PAGES).read_bytes(), name="Uploaded")
    status, site = call("POST", "/api/sites/import", body, headers)
    assert status == 200
    assert site["name"] == "Uploaded"
    assert site["source"]["upload"] is True
    stored = tree_digest(paths.sites_dir() / site["id"] / site["revision"])
    assert stored == expected_digest(SITE_PAGES)


def test_upload_without_a_file_field_is_refused():
    body = b'--b\r\nContent-Disposition: form-data; name="name"\r\n\r\nx\r\n--b--\r\n'
    status, data = call("POST", "/api/sites/import", body, {"content-type": "multipart/form-data; boundary=b"})
    assert status == 400
    assert "multipart" in data["detail"]


def test_sites_are_listed_newest_import_first(tmp_path):
    old = import_path(write_zip(tmp_path / "old.zip", SITE_PAGES), "Old")[1]
    new = import_path(write_zip(tmp_path / "new.zip", SITE_PAGES), "New")[1]
    record_file = paths.sites_dir() / old["id"] / "site.json"
    record = json.loads(record_file.read_text())
    record["importedAt"] = "2001-01-01T00:00:00Z"
    record_file.write_text(json.dumps(record))
    ids = [s["id"] for s in call("GET", "/api/sites")[1]["sites"]]
    assert ids == [new["id"], old["id"]]


def test_removing_a_site_needs_the_window_key(tmp_path):
    site = import_path(write_zip(tmp_path / "a.zip", SITE_PAGES))[1]
    status, data = call("DELETE", f"/api/sites/{site['id']}", keyed=False)
    assert status == 403
    assert data["code"] == "forbidden"
    assert call("GET", "/api/sites")[1]["count"] == 1


def test_removed_site_leaves_the_list_and_is_answered_404(tmp_path):
    site = import_path(write_zip(tmp_path / "a.zip", SITE_PAGES), "Gone")[1]
    status, data = call("DELETE", f"/api/sites/{site['id']}")
    assert status == 200
    assert data["removed"] is True
    assert call("GET", "/api/sites")[1]["count"] == 0
    assert call("GET", f"/api/sites/{site['id']}")[0] == 404
    assert not (paths.sites_dir() / site["id"]).exists()


def test_removing_an_unknown_site_is_answered_404():
    status, data = call("DELETE", "/api/sites/never-existed")
    assert status == 404
    assert data["code"] == "site-missing"
