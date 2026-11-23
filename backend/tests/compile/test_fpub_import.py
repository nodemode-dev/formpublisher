import json

import pytest

from app.cli import OpError

from .compile_lane import entries_of, pack


def write(tmp_path, data, name="in.fpub"):
    target = tmp_path / name
    target.write_bytes(data)
    return str(target)


def edit_meta(parts, change):
    meta = json.loads(parts["fpub.json"])
    change(meta)
    parts["fpub.json"] = json.dumps(meta).encode("utf-8")


def test_fpub_read_back_restores_the_same_build_after_it_was_removed(client, built, fpub_bytes, http, tmp_path):
    site, build = built
    status, _h, _d = http("DELETE", f"/api/builds/{build['id']}")
    assert status == 200
    back = client.import_path(write(tmp_path, fpub_bytes))
    assert back["id"] == site["id"]
    assert back["build"]["id"] == build["id"]
    assert back["build"]["remapped"] is False
    assert back["build"]["signed"] is False
    status, _h, zipped = http("GET", f"/api/builds/{build['id']}/download")
    assert zipped == dict(entries_of(fpub_bytes))["site.zip"]


def test_fpub_read_back_while_the_build_exists_gets_a_new_id_and_keeps_the_old_one(client, built, fpub_bytes, tmp_path):
    back = client.import_path(write(tmp_path, fpub_bytes))
    assert back["build"]["originalId"] == built[1]["id"]
    assert back["build"]["remapped"] is True
    assert back["build"]["id"] != built[1]["id"]
    ids = {row["id"] for row in client.builds()["builds"]}
    assert {built[1]["id"], back["build"]["id"]} <= ids


def test_fpub_read_back_gives_the_same_fpub_package_checksum_again(client, built, fpub_bytes, http, tmp_path):
    http("DELETE", f"/api/builds/{built[1]['id']}")
    back = client.import_path(write(tmp_path, fpub_bytes))
    _s, _h, again = http("GET", f"/api/builds/{back['build']['id']}/fpub")
    first = json.loads(dict(entries_of(fpub_bytes))["fpub.json"])
    second = json.loads(dict(entries_of(again))["fpub.json"])
    assert second["package"] == first["package"]


def flip_site_zip(parts):
    data = bytearray(parts["site.zip"])
    data[len(data) // 2] ^= 0xFF
    parts["site.zip"] = bytes(data)


def other_site(parts):
    publish = json.loads(parts["publish.json"])
    publish["site"]["id"] = "someone-else"
    parts["publish.json"] = json.dumps(publish).encode("utf-8")


TAMPERS = {
    "one byte of site.zip changed": (flip_site_zip, "site.zip does not match the checksum recorded in fpub.json"),
    "site.zip cut short": (lambda p: p.update({"site.zip": p["site.zip"][:-10]}), "site.zip does not match the size recorded in fpub.json"),
    "manifest version 2": (lambda p: edit_meta(p, lambda m: m.update(version=2)), "this .fpub is version 2; this FormPublisher reads version 1"),
    "manifest of another format": (lambda p: edit_meta(p, lambda m: m.update(format="something-else")), "that file is not a FormPublisher package (format formpublisher-package)"),
    "manifest not JSON": (lambda p: p.update({"fpub.json": b"{nope"}), "fpub.json is not valid JSON"),
    "site id with a path in it": (lambda p: edit_meta(p, lambda m: m["site"].update(id="../escape")), "fpub.json is missing a valid site id"),
    "build id that is not twelve hex digits": (lambda p: edit_meta(p, lambda m: m.update(build="../../etc")), "fpub.json is missing a valid build id"),
    "package file renamed": (lambda p: edit_meta(p, lambda m: m["package"].update(file="../site.zip")), "fpub.json is missing a valid package"),
    "publish.json of another site": (other_site, "publish.json belongs to a different site than fpub.json"),
    "publish.json of another format": (lambda p: p.update({"publish.json": b"{}"}), "publish.json is not a FormPublisher build manifest"),
    "signature claimed without a signature entry": (
        lambda p: edit_meta(p, lambda m: m.update(signature={"file": "site.zip.sig", "keyId": "a", "fingerprint": "b", "publicKey": "c"})),
        "fpub.json and the entries disagree about whether the package is signed",
    ),
}


@pytest.mark.parametrize("label", sorted(TAMPERS))
def test_tampered_fpub_is_refused_with_its_reason(label, client, built, fpub_bytes, tmp_path):
    change, message = TAMPERS[label]
    parts = dict(entries_of(fpub_bytes))
    change(parts)
    before = len(client.builds()["builds"])
    with pytest.raises(OpError) as caught:
        client.import_path(write(tmp_path, pack([(n, parts[n]) for n in ("fpub.json", "publish.json", "site.zip")])))
    assert caught.value.message == message
    assert len(client.builds()["builds"]) == before


ENTRY_RULE = "the .fpub must hold exactly fpub.json, publish.json, site.zip and, when signed, site.zip.sig, in that order"


@pytest.mark.parametrize(
    "order",
    [
        ["fpub.json", "site.zip", "publish.json"],
        ["fpub.json", "publish.json"],
        ["fpub.json", "publish.json", "site.zip", "extra.txt"],
    ],
    ids=["entries out of order", "site.zip missing", "an extra entry"],
)
def test_fpub_with_other_entries_is_refused_with_the_entry_rule(order, client, fpub_bytes, tmp_path):
    parts = dict(entries_of(fpub_bytes))
    with pytest.raises(OpError) as caught:
        client.import_path(write(tmp_path, pack([(n, parts.get(n, b"x")) for n in order])))
    assert caught.value.message == ENTRY_RULE


@pytest.mark.parametrize("name", ["../outside.txt", "/abs.txt", "a/../../b.txt"])
def test_fpub_with_an_escaping_entry_name_is_refused_and_writes_nothing_outside(name, client, fpub_bytes, tmp_path, home):
    parts = entries_of(fpub_bytes) + [(name, b"owned")]
    with pytest.raises(OpError) as caught:
        client.import_path(write(tmp_path, pack(parts)))
    assert "unsafe path" in caught.value.message
    assert not list(home.rglob("outside.txt")) and not list(tmp_path.rglob("b.txt"))


@pytest.mark.parametrize("keep", [0, 100, 0.5, 0.9], ids=["empty", "first 100 bytes", "first half", "last tenth missing"])
def test_truncated_fpub_is_refused_as_not_a_valid_fpub(keep, client, fpub_bytes, tmp_path):
    size = int(len(fpub_bytes) * keep) if isinstance(keep, float) else keep
    with pytest.raises(OpError) as caught:
        client.import_path(write(tmp_path, fpub_bytes[:size]))
    assert caught.value.message == "that file is not a valid .fpub"


def test_refused_fpub_leaves_no_work_folder_in_the_builds_library(client, fpub_bytes, tmp_path, home):
    with pytest.raises(OpError):
        client.import_path(write(tmp_path, fpub_bytes[:200]))
    assert [p.name for p in (home / "builds").iterdir() if p.name.startswith(".fpub-")] == []


def test_fpub_is_recognised_by_first_entry_even_without_the_file_ending(client, built, fpub_bytes, http, tmp_path):
    http("DELETE", f"/api/builds/{built[1]['id']}")
    back = client.import_path(write(tmp_path, fpub_bytes, "renamed.zip"))
    assert back["build"]["id"] == built[1]["id"]
