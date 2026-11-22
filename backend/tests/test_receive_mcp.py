import asyncio
import json

from conftest import DEMO, asgi_call


def test_receive_takes_a_zip_from_this_computer(client):
    from app.main import app

    body = (DEMO / "sites" / "lowlight.zip").read_bytes()
    status, headers, payload = asyncio.run(asgi_call(app, "POST", "/api/receive/formweb", body, {"content-type": "application/zip", "x-formweb-project": "p-1", "x-formweb-site-name": "Lowlight"}))
    assert status == 200, payload
    answer = json.loads(payload)
    assert answer["site"] and answer["revision"]
    assert headers["x-content-type-options"] == "nosniff"
    assert client.sites()["count"] == 1


def test_receive_refuses_another_computer_and_other_types():
    from app.main import app

    body = (DEMO / "sites" / "lowlight.zip").read_bytes()
    status, _, _ = asyncio.run(asgi_call(app, "POST", "/api/receive/formweb", body, {"content-type": "application/zip"}, client_host="192.0.2.7"))
    assert status == 403
    status, _, payload = asyncio.run(asgi_call(app, "POST", "/api/receive/formweb", body, {"content-type": "text/plain"}))
    assert status == 415
    status, _, payload = asyncio.run(asgi_call(app, "POST", "/api/receive/formweb", b"", {"content-type": "application/zip"}))
    assert status == 400


def test_engine_refuses_a_host_name_that_is_not_loopback():
    from app.main import app

    status, _, _ = asyncio.run(asgi_call(app, "GET", "/api/health", headers={"host": "example.com"}))
    assert status in (400, 421)


def tool_names() -> list[str]:
    from app import mcp
    from app.cli import Client

    return [t.name for t in asyncio.run(mcp.build(Client(in_process=True)).list_tools())]


def test_mcp_lists_the_tools():
    names = tool_names()
    for name in ("formpublisher_status", "import_site", "run_checks", "build_package", "sign_build", "verify_build", "prepare_publish", "restore_from_trash", "list_templates", "start_from_template"):
        assert name in names
    assert len(names) == len(set(names))


def test_mcp_call_imports_and_lists(home):
    from app import mcp
    from app.cli import Client

    server = mcp.build(Client(in_process=True))
    asyncio.run(server.call_tool("import_site", {"path": str(DEMO / "sites" / "lowlight.zip")}))
    result = asyncio.run(server.call_tool("list_sites", {}))
    data = json.loads(result.content[0].text)
    assert data["count"] == 1
    assert data["sites"][0]["name"] == "Lowlight"
