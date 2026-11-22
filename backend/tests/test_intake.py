from conftest import DEMO, starter_site, write_fweb


def test_export_zip_opens_with_its_routes(client):
    site = client.import_path(str(DEMO / "sites" / "lowlight.zip"))
    assert site["source"]["kind"] == "zip"
    assert site["name"] == "Lowlight"
    assert site["routes"] == 5
    paths = {r["path"] for r in client.routes(site["id"])["routes"]}
    assert {"index.html", "book/index.html", "404/index.html"} <= paths


def test_each_shipped_demo_zip_opens(client):
    for name in ("harbour-ferries", "looking-back", "lowlight"):
        site = client.import_path(str(DEMO / "sites" / f"{name}.zip"))
        assert site["routes"] > 0
    assert client.sites()["count"] == 3


def test_publication_folder_opens(client):
    site = client.import_path(str(DEMO / "sample-site"))
    assert site["source"]["kind"] == "folder"
    assert site["routes"] == 4


def test_same_source_again_adds_a_revision(client):
    first = client.import_path(str(DEMO / "sample-site.zip"))
    second = client.import_path(str(DEMO / "sample-site.zip"))
    assert second["id"] == first["id"]
    assert len(client.revisions(first["id"])["revisions"]) == 2


def test_fweb_version_1_opens_through_the_core(client, core, tmp_path):
    project = write_fweb(tmp_path / "starter.fweb", starter_site(core, "Version one"), 1)
    site = client.import_path(str(project))
    assert site["name"] == "Version one"
    assert site["routes"] >= 1


def test_fweb_version_2_opens_the_same_as_version_1(client, core, tmp_path):
    data = starter_site(core, "Both versions")
    one = client.import_path(str(write_fweb(tmp_path / "one.fweb", data, 1)))
    two = client.import_path(str(write_fweb(tmp_path / "two.fweb", data, 2)))
    assert one["routes"] == two["routes"]
    assert one["files"] == two["files"]


def test_core_reports_the_formweb_release_it_is(core):
    from app.services.compile import Session

    with Session(core) as session:
        assert session.call("hello", {})["version"] == "0.27.0"
