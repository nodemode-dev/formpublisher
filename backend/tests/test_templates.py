import asyncio
import hashlib
import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest

from conftest import starter_site, write_fweb


class Recorder(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        self.server.seen.append(self.path)
        super().do_GET()


@pytest.fixture
def repo(tmp_path, monkeypatch):
    root = tmp_path / "standin"
    (root / "apps" / "formweb" / "demos").mkdir(parents=True)
    (root / "apps" / "formweb" / "previews").mkdir(parents=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Recorder, directory=str(root)))
    server.seen = []
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("FORMPUBLISHER_TEMPLATES_URL", f"http://127.0.0.1:{server.server_port}/")
    yield root, server
    server.shutdown()
    server.server_close()


def publish_index(root, items):
    data = {"format": "formai-templates", "format_version": 1, "generated": "2026-11-22T00:00:00Z",
            "apps": [{"id": "formweb", "name": "FormWeb", "licence": "Apache-2.0", "version": "0.27.0", "items": items}]}
    (root / "index.json").write_text(json.dumps(data), encoding="utf-8")


def demo_item(root, core, sha=None):
    project = write_fweb(root / "apps" / "formweb" / "demos" / "harbour.fweb", starter_site(core, "Harbour"), 1)
    (root / "apps" / "formweb" / "previews" / "harbour.webp").write_bytes(b"RIFF0000WEBPVP8 ")
    data = project.read_bytes()
    return {"id": "formweb/demos/harbour", "kind": "demo", "name": "Harbour", "description": "A whole site.",
            "path": "apps/formweb/demos/harbour.fweb", "bytes": len(data), "sha256": sha or hashlib.sha256(data).hexdigest(),
            "licence": "Apache-2.0", "credit": "Test pictures", "preview": "apps/formweb/previews/harbour.webp"}


SECTION = {"id": "formweb/templates/formtxt-404", "kind": "template", "name": "FormTxt page not found", "description": "A section.",
           "path": "apps/formweb/templates/formtxt-404.json", "bytes": 10, "sha256": "0" * 64, "licence": "Apache-2.0", "credit": ""}


def test_nothing_is_fetched_before_the_button(client, repo):
    root, server = repo
    publish_index(root, [SECTION])
    from app import mcp
    from app.main import app  # noqa: F401

    assert client.templates()["fetched"] is False
    assert client.templates()["source"].endswith("Nothing is fetched until you ask.")
    asyncio.run(mcp.build(client).call_tool("list_templates", {}))
    client.status()
    assert server.seen == []


def test_good_index_offers_whole_sites_only_and_starts_one(client, core, repo, tmp_path):
    root, server = repo
    publish_index(root, [demo_item(root, core), SECTION])
    listed = client.fetch_templates()
    assert server.seen == ["/index.json"]
    assert listed["fetched"] is True and listed["fetchedAt"]
    assert [i["id"] for i in listed["items"]] == ["formweb/demos/harbour"]
    assert listed["notStartable"] == 1
    assert client.templates()["items"] == listed["items"]
    dest = tmp_path / "mine"
    dest.mkdir()
    made = client.start_template("formweb/demos/harbour", str(dest))
    assert made["project"] == str(dest / "harbour.fweb")
    assert (dest / "harbour.fweb").read_bytes() == (root / "apps/formweb/demos/harbour.fweb").read_bytes()
    assert made["core"] == "0.27.0"
    site = client.import_path(made["project"])
    assert site["name"] == "Harbour"
    with pytest.raises(Exception):
        client.start_template("formweb/demos/harbour", str(dest))


def test_a_section_is_not_offered_as_a_start(client, repo, tmp_path):
    root, _ = repo
    publish_index(root, [SECTION])
    client.fetch_templates()
    from app.cli import OpError

    with pytest.raises(OpError) as err:
        client.start_template(SECTION["id"], str(tmp_path))
    assert err.value.error_code == "not-found"


def test_wrong_sha256_keeps_nothing(client, core, repo, home, tmp_path):
    root, _ = repo
    publish_index(root, [demo_item(root, core, sha="f" * 64)])
    client.fetch_templates()
    from app.cli import OpError

    with pytest.raises(OpError) as err:
        client.start_template("formweb/demos/harbour", str(tmp_path))
    assert err.value.error_code == "template-mismatch"
    assert list(tmp_path.glob("*.fweb")) == []
    assert list((home / "templates" / "files").glob("*")) == []


def test_file_larger_than_the_index_says_is_refused(client, core, repo, tmp_path):
    root, _ = repo
    item = demo_item(root, core)
    item["bytes"] -= 10
    publish_index(root, [item])
    client.fetch_templates()
    from app.cli import OpError

    with pytest.raises(OpError) as err:
        client.start_template("formweb/demos/harbour", str(tmp_path))
    assert err.value.error_code == "too-large"
    assert list(tmp_path.glob("*.fweb")) == []


@pytest.mark.parametrize("path", ["apps/formweb/../../secret.fweb", "/etc/passwd", "apps/other/demos/x.fweb", "apps\\formweb\\x.fweb", "C:/x.fweb"])
def test_a_path_that_escapes_is_refused_and_nothing_is_kept(client, repo, path):
    root, server = repo
    bad = dict(SECTION, kind="demo", path=path)
    publish_index(root, [bad])
    from app.cli import OpError

    with pytest.raises(OpError) as err:
        client.fetch_templates()
    assert err.value.error_code == "template-path"
    assert client.templates()["fetched"] is False
    assert server.seen == ["/index.json"]


def test_preview_comes_through_the_engine_after_the_list(client, core, repo):
    root, server = repo
    publish_index(root, [demo_item(root, core)])
    client.fetch_templates()
    from app.services import templates

    data, kind = templates.preview("formweb/demos/harbour")
    assert kind == "image/webp" and data.startswith(b"RIFF")
    assert server.seen == ["/index.json", "/apps/formweb/previews/harbour.webp"]


def test_mcp_starts_a_site_from_a_kept_template(client, core, repo, tmp_path):
    root, _ = repo
    publish_index(root, [demo_item(root, core)])
    client.fetch_templates()
    from app import mcp

    server = mcp.build(client)
    listed = json.loads(asyncio.run(server.call_tool("list_templates", {})).content[0].text)
    assert listed["items"][0]["id"] == "formweb/demos/harbour"
    result = asyncio.run(server.call_tool("start_from_template", {"template": "formweb/demos/harbour", "folder": str(tmp_path)}))
    assert json.loads(result.content[0].text)["project"] == str(tmp_path / "harbour.fweb")
