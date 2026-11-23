import json
import zipfile

from .compile_lane import DEMO


def test_opening_a_bundled_demo_creates_it_once_and_then_reuses_it(http):
    first = json.loads(http("POST", "/api/demo/open/lowlight")[2])
    second = json.loads(http("POST", "/api/demo/open/lowlight")[2])
    assert first["created"] is True
    assert second["created"] is False
    assert second["site"]["id"] == first["site"]["id"]
    assert second["updated"] is False


def test_an_opened_demo_holds_the_files_of_its_bundled_zip(http, home):
    site = json.loads(http("POST", "/api/demo/open/lowlight")[2])["site"]
    with zipfile.ZipFile(DEMO / "sites" / "lowlight.zip") as archive:
        expected = {i.filename: archive.read(i) for i in archive.infolist() if not i.is_dir()}
    root = home / "sites" / site["id"] / site["revision"]
    assert (root / "index.html").read_bytes() == expected["index.html"]


def test_a_demo_that_is_not_bundled_is_refused_as_missing(http):
    status, _h, data = http("POST", "/api/demo/open/no-such-demo")
    assert status == 404
    assert json.loads(data)["detail"] == "that demo is missing from this install"


def test_a_demo_id_with_capitals_is_refused_as_not_a_demo_id(http):
    status, _h, data = http("POST", "/api/demo/open/Lowlight")
    assert status == 404
    assert json.loads(data)["detail"] == "that is not a demo id"


def test_formweb_status_says_unreachable_at_the_configured_address_when_nothing_listens(http):
    status, _h, data = http("GET", "/api/formweb/status")
    body = json.loads(data)
    assert status == 200
    assert body["reachable"] is False
    assert body["url"] == "http://127.0.0.1:18298"


def test_templates_list_is_empty_before_anything_was_fetched(http):
    status, _h, data = http("GET", "/api/templates")
    assert status == 200
    assert json.loads(data)["items"] == []
