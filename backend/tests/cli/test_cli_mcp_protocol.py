import hashlib
import json
import re

import pytest

from .support import DEMO_ZIP, REPO, McpSession, isolated_env, text_of

MANUAL = REPO / "docs" / "MANUAL.md"


@pytest.fixture(scope="module")
def session(tmp_path_factory):
    opened = McpSession(env=isolated_env(tmp_path_factory.mktemp("mcp")))
    opened.initialize()
    yield opened
    opened.close()


@pytest.fixture
def own_session(home):
    opened = McpSession()
    opened.initialize()
    yield opened
    opened.close()


def manual_tool_classes() -> dict[str, str]:
    text = MANUAL.read_text(encoding="utf-8")
    part = text.split("## The MCP server", 1)[1]
    return {name: kind for name, kind in re.findall(r"^\| `([a-z_]+)` \| (read|data|path) \|", part, re.M)}


def listed_tools(session) -> list[dict]:
    return session.request("list", "tools/list", {})["result"]["tools"]


def test_initialize_answers_a_jsonrpc_result_with_the_server_name_and_its_own_version(home):
    from app import __version__

    opened = McpSession()
    try:
        answer = opened.request(41, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}})
    finally:
        opened.close()
    assert answer["jsonrpc"] == "2.0"
    assert answer["id"] == 41
    assert "error" not in answer
    result = answer["result"]
    assert result["serverInfo"]["name"] == "formpublisher"
    assert result["serverInfo"]["version"] == __version__
    assert result["protocolVersion"] == "2025-06-18"
    assert "tools" in result["capabilities"]
    assert result["instructions"].startswith("FormPublisher turns a site built in FormWeb")


@pytest.mark.parametrize("version", ["2024-11-05", "2025-11-25"])
def test_initialize_accepts_the_oldest_and_newest_handshake_revisions_the_manual_names(home, version):
    opened = McpSession()
    try:
        answer = opened.request(1, "initialize", {"protocolVersion": version, "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}})
    finally:
        opened.close()
    assert answer["result"]["protocolVersion"] == version


def test_initialize_with_an_unknown_revision_answers_a_revision_the_manual_names(home):
    opened = McpSession()
    try:
        answer = opened.request(1, "initialize", {"protocolVersion": "1999-01-01", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}})
    finally:
        opened.close()
    offered = answer["result"]["protocolVersion"]
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", offered)
    assert "2024-11-05" <= offered <= "2025-11-25"


def test_server_discover_answers_with_the_modern_revision_the_manual_names(home):
    from mcp.client import session as client_session

    opened = McpSession()
    try:
        answer = opened.request(9, "server/discover", {"_meta": {
            client_session.PROTOCOL_VERSION_META_KEY: "2026-07-28",
            client_session.CLIENT_INFO_META_KEY: {"name": "t", "version": "1"},
            client_session.CLIENT_CAPABILITIES_META_KEY: {},
        }})
    finally:
        opened.close()
    assert "error" not in answer, answer
    assert "2026-07-28" in json.dumps(answer["result"])


def test_ping_answers_an_empty_result_with_the_same_id(session):
    answer = session.request("p-1", "ping")
    assert answer == {"jsonrpc": "2.0", "id": "p-1", "result": {}}


def test_an_unknown_method_answers_the_jsonrpc_method_not_found_error(session):
    answer = session.request(77, "no/such/method", {})
    assert answer["id"] == 77
    assert answer["error"]["code"] == -32601
    assert "result" not in answer


@pytest.mark.xfail(strict=True, reason="DEFECT: a line that is not JSON gets no answer at all on stdio; JSON-RPC 2.0 section 5.1 says the server must answer a Parse error, code -32700, with id null")
def test_a_line_that_is_not_json_answers_a_parse_error(own_session):
    own_session.send("{this is not json")
    answer = own_session.wait_for(lambda m: "error" in m, timeout=2)
    assert answer["error"]["code"] == -32700
    assert answer["id"] is None


def test_every_listed_tool_has_the_mcp_tool_shape(session):
    tools = listed_tools(session)
    assert tools
    names = [tool["name"] for tool in tools]
    assert len(names) == len(set(names))
    for tool in tools:
        assert re.fullmatch(r"[a-z_]+", tool["name"])
        assert tool["description"].strip().endswith(".")
        assert tool["inputSchema"]["type"] == "object"
        assert isinstance(tool["inputSchema"].get("properties", {}), dict)
        for required in tool["inputSchema"].get("required", []):
            assert required in tool["inputSchema"]["properties"]


def test_the_listed_tools_and_their_classes_match_the_manual_table(session):
    tools = listed_tools(session)
    got = {tool["name"]: tool["_meta"]["formpublisher/class"] for tool in tools}
    assert got == manual_tool_classes()


def test_the_listed_tools_match_the_generated_docs_list(session):
    docs = json.loads((REPO / "docs" / "mcp-tools.json").read_text(encoding="utf-8"))
    tools = listed_tools(session)
    assert docs["counts"]["tools"] == len(tools)
    kinds = [tool["_meta"]["formpublisher/class"] for tool in tools]
    for kind in ("read", "data", "path"):
        assert docs["counts"][kind] == kinds.count(kind)


def test_read_class_tools_and_only_those_carry_the_read_only_hint(session):
    for tool in listed_tools(session):
        read = tool["_meta"]["formpublisher/class"] == "read"
        assert bool(tool["annotations"].get("readOnlyHint")) is read, tool["name"]


def test_calling_an_unknown_tool_answers_an_error_result_naming_it(session):
    result = session.call(3, "no_such_tool", {})
    assert result["isError"] is True
    assert "no_such_tool" in text_of(result)


def test_every_tool_with_required_arguments_refuses_a_call_without_them(session):
    tools = [tool for tool in listed_tools(session) if tool["inputSchema"].get("required")]
    assert len(tools) >= 15
    for index, tool in enumerate(tools):
        result = session.call(100 + index, tool["name"], {})
        message = text_of(result)
        assert result["isError"] is True, tool["name"]
        for required in tool["inputSchema"]["required"]:
            assert required in message, (tool["name"], message)
        assert "Field required" in message


def test_every_tool_argument_refuses_a_value_of_the_wrong_type(session):
    tools = [tool for tool in listed_tools(session) if tool["inputSchema"].get("properties")]
    for index, tool in enumerate(tools):
        props = tool["inputSchema"]["properties"]
        result = session.call(300 + index, tool["name"], {name: {"wrong": True} for name in props})
        message = text_of(result)
        assert result["isError"] is True, tool["name"]
        for name in props:
            assert re.search(rf"^{name}$", message, re.M), (tool["name"], name, message)
        assert "Input should be a valid" in message


@pytest.mark.parametrize(("tool", "arguments", "expected"), [
    ("site_routes", {"id": "no-such-site"}, "error [site-missing]: site not found"),
    ("list_revisions", {"id": "no-such-site"}, "error [site-missing]: site not found"),
    ("inspect_build", {"build": "no-such-build"}, "error [build-missing]"),
    ("prepare_publish", {"build": "no-such-build", "targets": ["netlify"]}, "error [build-missing]"),
    ("save_fpub", {"build": "x", "path": "relative.fpub"}, "error [invalid]: path must be absolute"),
    ("start_from_template", {"template": "formweb/demos/lowlight", "folder": "relative/folder"}, "error [invalid]: folder must be absolute"),
    ("restore_from_trash", {"entry": "no-such-entry"}, "error ["),
])
def test_a_tool_refusal_comes_back_as_an_error_result_with_the_reason(session, tool, arguments, expected):
    result = session.call(tool, tool, arguments)
    assert result["isError"] is True
    assert expected in text_of(result)


def test_import_site_refuses_a_path_that_does_not_exist_with_the_path_missing_code(session, tmp_path):
    result = session.call(5, "import_site", {"path": str(tmp_path / "absent.zip")})
    assert result["isError"] is True
    assert "error [path-missing]" in text_of(result)
    assert "does not exist" in text_of(result)


def test_save_fpub_over_stdio_writes_the_hash_it_reports_and_refuses_a_second_write(own_session, tmp_path):
    session = own_session
    imported = json.loads(text_of(session.call(1, "import_site", {"path": str(DEMO_ZIP)})))
    built = json.loads(text_of(session.call(2, "build_package", {"id": imported["id"]})))
    target = tmp_path / "out.fpub"
    saved = session.call(3, "save_fpub", {"build": built["id"], "path": str(target)})
    assert saved["isError"] is False, text_of(saved)
    answer = json.loads(text_of(saved))
    assert answer["sha256"] == hashlib.sha256(target.read_bytes()).hexdigest()
    assert answer["size"] == target.stat().st_size
    again = session.call(4, "save_fpub", {"build": built["id"], "path": str(target)})
    assert again["isError"] is True
    assert "already exists" in text_of(again)


def test_mcp_help_prints_one_usage_line_and_exits_zero(capsys):
    from app import mcp

    assert mcp.main(["--help"]) == 0
    assert "serve the FormPublisher tools over MCP on stdio" in capsys.readouterr().out


def test_mcp_refuses_a_tab_key_file_that_cannot_be_read_with_exit_two(capsys, tmp_path):
    from app import mcp

    assert mcp.main(["--tab-key-file", str(tmp_path / "missing.key")]) == 2
    assert "--tab-key-file needs the path of a readable tab key file" in capsys.readouterr().err
    empty = tmp_path / "empty.key"
    empty.write_text("  \n", encoding="utf-8")
    assert mcp.main([f"--tab-key-file={empty}"]) == 2
