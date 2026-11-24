import asyncio
import json

import pytest

from .compile_lane import DEMO, asgi_call


@pytest.fixture
def http():
    from app.main import app
    from app.services import window_key

    def call(method, path, body=None):
        raw = json.dumps(body).encode("utf-8") if body is not None else b""
        headers = {"content-type": "application/json"} if body is not None else {}
        if method not in window_key.READS:
            headers[window_key.HEADER] = window_key.LOCAL_KEY
        status, out, data = asyncio.run(asgi_call(app, method, path, raw, headers))
        return status, out, data

    return call


@pytest.fixture
def built(client):
    site = client.import_path(str(DEMO / "sites" / "lowlight.zip"))
    return site, client.build(site["id"])


@pytest.fixture
def fpub_bytes(built, http):
    status, _headers, data = http("GET", f"/api/builds/{built[1]['id']}/fpub")
    assert status == 200
    return data
