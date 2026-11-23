import json
import os
import time

from app.services import inbox, paths

from .support import SITE_PAGES, call, raw_get, receive, tree_digest, write_zip


def zip_of(tmp_path, files=None, name="x.zip") -> bytes:
    return write_zip(tmp_path / name, files or SITE_PAGES).read_bytes()


def drop(name: str, data: bytes, sidecar: dict | None = None, age: float = 60.0):
    target = paths.inbox_dir() / name
    target.write_bytes(data)
    stamp = time.time() - age
    os.utime(target, (stamp, stamp))
    if sidecar is not None:
        side = paths.inbox_dir() / (name + ".json")
        side.write_text(json.dumps(sidecar))
        os.utime(side, (stamp, stamp))
    return target


def test_received_site_is_answered_with_its_id_and_revision_and_is_listed(tmp_path):
    status, data = receive(zip_of(tmp_path), project="p-1", name="Fair")
    assert status == 200
    assert set(data) == {"site", "revision", "opened"}
    assert data["opened"] is False
    site = call("GET", f"/api/sites/{data['site']}")[1]
    assert site["name"] == "Fair"
    assert site["revision"] == data["revision"]
    assert site["source"] == {"kind": "formweb", "url": "receive:p-1"}


def test_received_files_equal_the_files_that_were_sent(tmp_path):
    data = receive(zip_of(tmp_path), project="p-1")[1]
    stored = tree_digest(paths.sites_dir() / data["site"] / data["revision"])
    import hashlib

    assert stored == {n: hashlib.sha256(b).hexdigest() for n, b in SITE_PAGES.items()}


def test_site_name_header_is_percent_decoded(tmp_path):
    data = receive(zip_of(tmp_path), project="p-2", name="My%20Caf%C3%A9%20Site")[1]
    assert call("GET", f"/api/sites/{data['site']}")[1]["name"] == "My Caf\u00e9 Site"


def test_site_name_header_is_cut_to_120_characters(tmp_path):
    data = receive(zip_of(tmp_path), project="p-2", name="n" * 300)[1]
    assert len(call("GET", f"/api/sites/{data['site']}")[1]["name"]) == 120


def test_same_project_sent_twice_is_one_site_with_two_revisions_in_send_order(tmp_path):
    first = receive(zip_of(tmp_path), project="p-3", name="Fair")[1]
    second = receive(zip_of(tmp_path, {**SITE_PAGES, "css/site.css": b"body{}"}, "y.zip"), project="p-3", name="Fair")[1]
    assert first["site"] == second["site"]
    assert first["revision"] != second["revision"]
    site = call("GET", f"/api/sites/{first['site']}")[1]
    assert site["revisions"] == [first["revision"], second["revision"]]
    assert call("GET", "/api/sites")[1]["count"] == 1


def test_two_different_projects_are_two_sites(tmp_path):
    a = receive(zip_of(tmp_path), project="p-a", name="Same")[1]
    b = receive(zip_of(tmp_path), project="p-b", name="Same")[1]
    assert a["site"] != b["site"]
    assert call("GET", "/api/sites")[1]["count"] == 2


def test_receive_without_a_project_header_still_makes_a_site(tmp_path):
    data = receive(zip_of(tmp_path))[1]
    assert call("GET", f"/api/sites/{data['site']}")[0] == 200


def test_octet_stream_is_accepted_as_a_zip_body(tmp_path):
    status, data = receive(zip_of(tmp_path), kind="application/octet-stream")
    assert status == 200


def test_content_type_with_parameters_is_accepted(tmp_path):
    status, data = receive(zip_of(tmp_path), kind="application/zip; charset=binary")
    assert status == 200


def test_receive_status_reports_the_endpoint_inbox_and_the_last_receipt(tmp_path):
    receive(zip_of(tmp_path), project="p-4", name="Fair")
    status, data = call("GET", "/api/receive/status")
    assert status == 200
    assert data["endpoint"].endswith("/api/receive/formweb")
    assert data["endpoint"].startswith("http://127.0.0.1:")
    assert data["inbox"] == str(paths.inbox_dir())
    assert data["pending"] == 0
    assert data["auto"] == {"check": False, "build": False}
    assert data["receipts"][0]["ok"] is True
    assert data["receipts"][0]["name"] == "Fair"
    assert data["receipts"][0]["via"] == "http"


def test_receipts_keep_only_the_last_five(tmp_path):
    for i in range(7):
        receive(zip_of(tmp_path), project=f"p-{i}", name=f"Site {i}")
    names = [r["name"] for r in call("GET", "/api/receive/status")[1]["receipts"]]
    assert names == [f"Site {i}" for i in (6, 5, 4, 3, 2)]


def test_receive_response_carries_the_nosniff_header(tmp_path):
    from app.main import app
    import asyncio

    from conftest import asgi_call

    status, headers, _ = asyncio.run(asgi_call(app, "GET", "/api/receive/status"))
    assert headers["x-content-type-options"] == "nosniff"


def test_zip_left_in_the_inbox_is_imported_and_moved_to_imported(tmp_path):
    drop("fair.zip", zip_of(tmp_path))
    assert inbox.scan_once() == 1
    sites = call("GET", "/api/sites")[1]
    assert sites["count"] == 1
    assert sites["sites"][0]["name"] == "fair"
    assert not (paths.inbox_dir() / "fair.zip").exists()
    moved = list((paths.inbox_dir() / "imported").iterdir())
    assert len(moved) == 1
    assert moved[0].name.endswith("-fair.zip")
    assert moved[0].read_bytes() == zip_of(tmp_path)


def test_inbox_receipt_names_the_file_and_says_inbox(tmp_path):
    drop("fair.zip", zip_of(tmp_path))
    inbox.scan_once()
    receipt = call("GET", "/api/receive/status")[1]["receipts"][0]
    assert receipt["via"] == "inbox"
    assert receipt["file"] == "fair.zip"
    assert receipt["ok"] is True


def test_file_still_being_written_is_left_alone_until_it_has_settled(tmp_path):
    drop("fresh.zip", zip_of(tmp_path), age=0.0)
    assert inbox.scan_once() == 0
    assert (paths.inbox_dir() / "fresh.zip").exists()
    assert call("GET", "/api/receive/status")[1]["pending"] == 1
    assert call("GET", "/api/sites")[1]["count"] == 0


def test_files_that_are_not_zip_or_fweb_are_not_picked_up():
    drop("notes.txt", b"hello")
    drop(".hidden.zip", b"x")
    assert inbox.scan_once() == 0
    assert call("GET", "/api/receive/status")[1]["pending"] == 0


def test_bad_zip_in_the_inbox_moves_to_failed_with_the_reason_beside_it(tmp_path):
    drop("broken.zip", b"not a zip")
    assert inbox.scan_once() == 1
    failed = sorted(p.name for p in (paths.inbox_dir() / "failed").iterdir())
    assert len(failed) == 2
    reason = next(p for p in (paths.inbox_dir() / "failed").iterdir() if p.name.endswith(".txt"))
    assert reason.read_text().strip() == "that file is not a valid zip"
    assert call("GET", "/api/sites")[1]["count"] == 0
    receipt = call("GET", "/api/receive/status")[1]["receipts"][0]
    assert receipt["ok"] is False
    assert receipt["error"] == "that file is not a valid zip"


def test_escaping_zip_in_the_inbox_is_failed_and_writes_nothing_outside(tmp_path):
    drop("evil.zip", write_zip(tmp_path / "e.zip", {"index.html": b"x", "../evil.html": b"y"}).read_bytes())
    inbox.scan_once()
    reason = next(p for p in (paths.inbox_dir() / "failed").iterdir() if p.name.endswith(".txt"))
    assert "unsafe path" in reason.read_text()
    assert call("GET", "/api/sites")[1]["count"] == 0
    assert not (paths.home() / "evil.html").exists()
    assert not (paths.home().parent / "evil.html").exists()


def test_sidecar_gives_an_inbox_site_its_name_and_project(tmp_path):
    drop("a.zip", zip_of(tmp_path), {"siteName": "Named Fair", "project": "proj-9", "version": "0.19"})
    inbox.scan_once()
    site = call("GET", "/api/sites")[1]["sites"][0]
    assert site["name"] == "Named Fair"
    assert site["source"]["url"] == "receive:proj-9"
    assert sorted(p.name for p in (paths.inbox_dir() / "imported").iterdir() if p.name.endswith(".json")) != []
    assert not (paths.inbox_dir() / "a.zip.json").exists()


def test_inbox_arrival_of_a_known_project_adds_a_revision_to_the_same_site(tmp_path):
    first = receive(zip_of(tmp_path), project="proj-9", name="Named Fair")[1]
    drop("b.zip", zip_of(tmp_path, {**SITE_PAGES, "index.html": b"<html><body>new</body></html>"}, "z.zip"), {"siteName": "Named Fair", "project": "proj-9"})
    inbox.scan_once()
    sites = call("GET", "/api/sites")[1]
    assert sites["count"] == 1
    assert sites["sites"][0]["id"] == first["site"]
    assert len(sites["sites"][0]["revisions"]) == 2


def test_two_files_with_the_same_name_in_the_inbox_over_time_both_end_up_in_imported(tmp_path):
    for i in range(2):
        drop("same.zip", zip_of(tmp_path), {"project": f"pp-{i}"})
        inbox.scan_once()
    assert len(list((paths.inbox_dir() / "imported").glob("*same.zip"))) == 2


def test_inbox_keeps_a_fweb_project_that_is_not_json_as_failed(tmp_path):
    drop("proj.fweb", b"{ not json")
    inbox.scan_once()
    assert call("GET", "/api/sites")[1]["count"] == 0
    assert any(p.name.endswith("proj.fweb") for p in (paths.inbox_dir() / "failed").iterdir())
