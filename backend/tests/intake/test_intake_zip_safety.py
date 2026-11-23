import zipfile

import pytest

from app.services import paths

from .support import SITE_PAGES, call, encrypted_flag_zip, import_path, inflated_size_zip, receive, symlink_zip, tree_digest, write_zip

MIB = 1024 * 1024


def nothing_left_behind(tmp_path):
    status, data = call("GET", "/api/sites")
    assert data["count"] == 0
    assert [p.name for p in paths.sites_dir().iterdir()] == []
    assert not (tmp_path / "evil.html").exists()
    assert not (paths.home() / "evil.html").exists()


@pytest.mark.parametrize(
    "member",
    ["../evil.html", "a/../../evil.html", "/evil.html", "C:/evil.html", "..\\evil.html", "docs/../../../evil.html"],
)
def test_zip_with_a_path_that_escapes_is_refused_and_leaves_nothing(tmp_path, member):
    archive = write_zip(tmp_path / "bad.zip", {"index.html": SITE_PAGES["index.html"], member: b"owned"})
    status, data = import_path(archive)
    assert status == 400
    assert "unsafe path" in data["detail"]
    nothing_left_behind(tmp_path)


def test_zip_that_holds_a_symbolic_link_is_refused_by_name(tmp_path):
    status, data = import_path(symlink_zip(tmp_path / "link.zip"))
    assert status == 400
    assert "symbolic link" in data["detail"]
    assert "link.html" in data["detail"]
    nothing_left_behind(tmp_path)


def test_encrypted_zip_is_refused_as_encrypted(tmp_path):
    status, data = import_path(encrypted_flag_zip(tmp_path / "locked.zip"))
    assert status == 400
    assert data["detail"] == "the zip is encrypted"
    nothing_left_behind(tmp_path)


def test_zip_that_declares_more_than_one_gibibyte_is_refused_with_413(tmp_path):
    archive = inflated_size_zip(tmp_path / "bomb.zip", [600 * MIB, 600 * MIB])
    status, data = import_path(archive)
    assert status == 413
    assert data["detail"] == "the zip expands to more than 1 GiB"
    nothing_left_behind(tmp_path)


def test_zip_that_declares_just_under_the_limit_is_not_refused_for_size(tmp_path):
    archive = inflated_size_zip(tmp_path / "edge.zip", [500 * MIB])
    status, data = import_path(archive)
    assert data.get("code") != "too-large"
    assert "1 GiB" not in str(data.get("detail", ""))


def test_zip_with_more_than_twenty_thousand_files_is_refused_with_413(tmp_path):
    archive = tmp_path / "many.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_STORED) as handle:
        handle.writestr("index.html", SITE_PAGES["index.html"])
        for i in range(20_000):
            handle.writestr(f"f/{i}.txt", b"")
    status, data = import_path(archive)
    assert status == 413
    assert "more than 20000 files" in data["detail"]
    nothing_left_behind(tmp_path)


def test_zip_with_two_paths_that_differ_only_in_case_is_refused_as_duplicate(tmp_path):
    archive = write_zip(tmp_path / "dup.zip", {"index.html": SITE_PAGES["index.html"], "About.html": b"a", "about.html": b"b"})
    status, data = import_path(archive)
    assert status == 400
    assert "duplicate path" in data["detail"]
    nothing_left_behind(tmp_path)


def test_file_that_is_not_a_zip_is_refused_as_not_a_zip(tmp_path):
    junk = tmp_path / "junk.zip"
    junk.write_bytes(b"this is plain text, not an archive")
    status, data = import_path(junk)
    assert status == 400
    assert data["detail"] == "that file is not a valid zip"
    nothing_left_behind(tmp_path)


def test_zip_without_a_page_is_refused_as_not_a_site(tmp_path):
    archive = write_zip(tmp_path / "notes.zip", {"notes/readme.txt": b"hello"})
    status, data = import_path(archive)
    assert status == 400
    assert data["code"] == "not-a-site"
    nothing_left_behind(tmp_path)


def test_empty_zip_is_refused_as_not_a_site(tmp_path):
    archive = tmp_path / "empty.zip"
    with zipfile.ZipFile(archive, "w"):
        pass
    status, data = import_path(archive)
    assert status == 400
    assert data["code"] == "not-a-site"


def test_a_refused_zip_does_not_disturb_a_site_already_imported(tmp_path):
    good = write_zip(tmp_path / "good.zip", SITE_PAGES)
    status, site = import_path(good, "Keeper")
    before = tree_digest(paths.sites_dir() / site["id"])
    bad = write_zip(tmp_path / "bad.zip", {"index.html": b"x", "../escape.html": b"y"})
    assert import_path(bad)[0] == 400
    assert tree_digest(paths.sites_dir() / site["id"]) == before
    assert call("GET", "/api/sites")[1]["count"] == 1


def test_receive_route_refuses_an_escaping_zip_and_adds_no_site(tmp_path):
    archive = write_zip(tmp_path / "bad.zip", {"index.html": SITE_PAGES["index.html"], "../evil.html": b"owned"})
    status, data = receive(archive.read_bytes(), project="p-evil")
    assert status == 400
    assert "unsafe path" in data["detail"]
    nothing_left_behind(tmp_path)


def test_receive_route_refuses_a_zip_with_a_symbolic_link(tmp_path):
    status, data = receive(symlink_zip(tmp_path / "link.zip").read_bytes())
    assert status == 400
    assert "symbolic link" in data["detail"]
    assert call("GET", "/api/sites")[1]["count"] == 0


def test_receive_route_refuses_bytes_that_are_not_a_zip():
    status, data = receive(b"not a zip at all")
    assert status == 400
    assert data["detail"] == "that file is not a valid zip"


def multipart(filename: str, payload: bytes) -> tuple[bytes, dict]:
    boundary = "xBOUNDARYx"
    head = f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: application/zip\r\n\r\n'.encode()
    body = head + payload + f"\r\n--{boundary}--\r\n".encode()
    return body, {"content-type": f"multipart/form-data; boundary={boundary}"}


def test_upload_route_refuses_an_escaping_zip(tmp_path):
    archive = write_zip(tmp_path / "bad.zip", {"index.html": SITE_PAGES["index.html"], "../evil.html": b"owned"})
    body, headers = multipart("bad.zip", archive.read_bytes())
    status, data = call("POST", "/api/sites/import", body, headers)
    assert status == 400
    assert "unsafe path" in data["detail"]
    nothing_left_behind(tmp_path)


def test_macos_metadata_folder_in_a_zip_is_left_out_of_the_site(tmp_path):
    archive = write_zip(tmp_path / "mac.zip", {**SITE_PAGES, "__MACOSX/._index.html": b"junk"})
    status, site = import_path(archive)
    assert status == 200
    stored = tree_digest(paths.sites_dir() / site["id"] / site["revision"])
    assert set(stored) == set(SITE_PAGES)
    assert site["files"] == len(SITE_PAGES)
