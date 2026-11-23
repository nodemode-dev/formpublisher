import json
import os
import re
import stat

import pytest

from .support import call


def write_routes():
    from app.main import app
    from app.services import window_key

    found = []
    for path, operations in app.openapi()["paths"].items():
        if path in window_key.OPEN:
            continue
        for method in sorted(m.upper() for m in operations):
            if method not in window_key.READS:
                found.append((method, re.sub(r"\{[^}]+\}", "x", path)))
    return found


def test_every_write_route_refuses_a_caller_without_the_window_key():
    from app.services import window_key

    routes = write_routes()
    assert ("POST", "/api/keys") in routes and ("PUT", "/api/settings") in routes and ("DELETE", "/api/keys/x") in routes
    wrong = []
    for method, path in routes:
        status, _, data, _ = call(method, path, {}, key=None)
        if status != 403 or data != {"detail": window_key.REFUSED, "code": "forbidden"}:
            wrong.append((method, path, status))
    assert wrong == []


def test_every_write_route_refuses_a_guessed_window_key():
    routes = write_routes()
    assert len(routes) > 10
    wrong = []
    for method, path in routes:
        status, _, _, _ = call(method, path, {}, key="guessed-key")
        if status != 403:
            wrong.append((method, path, status))
    assert wrong == []


def test_check_route_accepts_the_local_key():
    status, _, data, _ = call("POST", "/api/window/check")
    assert status == 200 and data == {"ok": True}


def test_window_from_an_allowed_origin_claims_a_key_that_opens_write_routes(monkeypatch):
    from app.services import window_key

    monkeypatch.delenv("FORMPUBLISHER_ORIGINS", raising=False)
    monkeypatch.delenv("FORMPUBLISHER_DESKTOP", raising=False)
    status, _, data, _ = call("POST", "/api/window/key", headers={"origin": "http://localhost:5280"}, key=None)
    assert status == 200
    claimed = data["key"]
    assert claimed == window_key.WINDOW_KEY
    assert call("POST", "/api/window/check", key=claimed)[0] == 200


def test_desktop_engine_never_hands_out_its_key_over_http(monkeypatch):
    monkeypatch.delenv("FORMPUBLISHER_ORIGINS", raising=False)
    monkeypatch.setenv("FORMPUBLISHER_DESKTOP", "1")
    status, _, data, payload = call("POST", "/api/window/key", headers={"origin": "http://localhost:5280"}, key=None)
    assert status == 404 and b"key\"" not in payload.replace(b"\"detail\"", b"")


def test_key_claim_without_an_origin_is_not_found(monkeypatch):
    monkeypatch.delenv("FORMPUBLISHER_DESKTOP", raising=False)
    status, _, data, _ = call("POST", "/api/window/key", key=None)
    assert status == 404 and "key" not in data


def test_key_claim_from_a_foreign_origin_is_refused(monkeypatch):
    monkeypatch.delenv("FORMPUBLISHER_ORIGINS", raising=False)
    status, _, data, _ = call("POST", "/api/window/key", headers={"origin": "https://evil.test"}, key=None)
    assert status == 403 and data["detail"] == "Origin is not allowed."


def test_issued_tab_token_opens_write_routes_until_revoked():
    from app.services import window_key

    token = window_key.issue_tab()
    try:
        assert call("POST", "/api/window/check", key=token)[0] == 200
    finally:
        window_key.revoke_tab(token)
    assert call("POST", "/api/window/check", key=token)[0] == 403


def test_key_file_is_private_and_reads_back_the_local_key(home):
    from app.services import window_key

    window_key.write_key_file()
    target = home / "engine.key"
    assert stat.S_IMODE(os.stat(target).st_mode) == 0o600
    assert window_key.read_key_file() == window_key.LOCAL_KEY
    assert json.loads(target.read_text(encoding="utf-8"))["pid"] == os.getpid()
    window_key.remove_key_file()
    assert not target.exists()
    assert window_key.read_key_file() == ""


def test_reads_pass_without_any_key():
    status, _, data, _ = call("GET", "/api/health", key=None)
    assert status == 200 and data["ok"] is True


@pytest.mark.parametrize("host", ["evil.test:18299", "127.0.0.1:1", "127.0.0.1.nip.io:18299"])
def test_engine_answers_only_exact_loopback_hostnames(host):
    import asyncio

    from app.main import app
    from conftest import asgi_call

    status, _, payload = asyncio.run(asgi_call(app, "GET", "/api/health", b"", {"host": host}))
    assert status == 421
    assert json.loads(payload)["detail"] == "This service accepts exact loopback hostnames only."
