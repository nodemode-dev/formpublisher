import json
import zipfile

from conftest import DEMO, broken_site


def test_good_site_has_no_problems(client):
    site = client.import_path(str(DEMO / "sites" / "lowlight.zip"))
    result = client.check(site["id"])
    assert result["summary"]["errors"] == 0
    assert result["summary"]["warnings"] == 0
    assert result["summary"]["ran"] == ["static"]
    assert client.get_checks(site["id"])["summary"] == result["summary"]


def test_broken_link_is_an_error_on_its_route(client, tmp_path):
    site = client.import_path(str(broken_site(tmp_path)))
    result = client.check(site["id"])
    found = [p for p in result["problems"] if p["code"] == "link.broken"]
    assert result["summary"]["errors"] == 1
    assert [p["route"] for p in found] == ["/index.html"]
    assert found[0]["severity"] == "error"


def test_package_is_deterministic_and_lists_every_file(client, home):
    site = client.import_path(str(DEMO / "sites" / "lowlight.zip"))
    first = client.build(site["id"])
    again = client.build(site["id"])
    assert first["id"] == again["id"]
    folder = next((home / "builds").glob(f"*/{first['id']}"))
    manifest = json.loads((folder / "publish.json").read_text(encoding="utf-8"))
    with zipfile.ZipFile(folder / "site.zip") as archive:
        names = set(archive.namelist())
    listed = {f["path"] for f in manifest["files"]}
    assert "index.html" in names
    assert listed <= names
    assert all(len(f["sha256"]) == 64 for f in manifest["files"])


def test_signature_verifies_and_a_tampered_package_fails(client, home):
    site = client.import_path(str(DEMO / "sites" / "lowlight.zip"))
    build = client.build(site["id"])
    assert client.verify(build["id"])["valid"] is False
    key = client.create_key("test key")
    signed = client.sign(build["id"], key["id"])
    assert signed["signed"] is True
    good = client.verify(build["id"])
    assert good["valid"] is True and good["key"] == key["fingerprint"]
    package = next((home / "builds").glob(f"*/{build['id']}/site.zip"))
    data = bytearray(package.read_bytes())
    data[len(data) // 2] ^= 0xFF
    package.write_bytes(bytes(data))
    bad = client.verify(build["id"])
    assert bad["valid"] is False
    assert bad["reason"]
