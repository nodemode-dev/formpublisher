import logging
import re
from logging.handlers import RotatingFileHandler

import pytest

from .support import TempKeyring, call, keys_folder, pem_body


@pytest.fixture
def engine_log(monkeypatch):
    from app.services import enginelog

    root = logging.getLogger()
    level = root.level
    monkeypatch.setattr(enginelog, "_attached", None)
    target = enginelog.attach()
    yield target
    for name in enginelog.LOGGERS:
        logger = logging.getLogger(name)
        for handler in list(logger.handlers):
            if isinstance(handler, RotatingFileHandler) and handler.baseFilename == str(target):
                logger.removeHandler(handler)
                handler.close()
    root.setLevel(level)


def file_handler(target):
    return next(h for h in logging.getLogger().handlers if isinstance(h, RotatingFileHandler) and h.baseFilename == str(target))


def test_health_answers_the_app_own_version():
    import app

    status, _, data, _ = call("GET", "/api/health", key=None)
    assert status == 200
    assert data["version"] == app.__version__
    assert re.fullmatch(r"\d+\.\d+\.\d+", data["version"])
    assert data["app"] == "formpublisher" and data["ok"] is True


def test_health_reports_the_data_folder_and_loaded_routers(home):
    _, _, data, _ = call("GET", "/api/health", key=None)
    assert data["home"] == str(home)
    assert {"health", "settings", "keys", "host", "window"} <= set(data["routers"])
    assert data["routerErrors"] == {}


def test_health_counts_live_subscribers():
    from app.services.bus import bus

    before = call("GET", "/api/health", key=None)[2]["liveClients"]
    queue = bus.subscribe()
    try:
        assert call("GET", "/api/health", key=None)[2]["liveClients"] == before + 1
    finally:
        bus.unsubscribe(queue)
    assert call("GET", "/api/health", key=None)[2]["liveClients"] == before


def test_engine_log_lives_in_the_logs_folder_and_rotates_at_one_megabyte_keeping_three(home, engine_log):
    assert engine_log == home / "logs" / "engine.log"
    handler = file_handler(engine_log)
    assert handler.maxBytes == 1024 * 1024 and handler.backupCount == 3


def test_engine_log_rotates_and_keeps_only_three_older_files(home, monkeypatch, engine_log):
    handler = file_handler(engine_log)
    monkeypatch.setattr(handler, "maxBytes", 2000)
    log = logging.getLogger("formpublisher.lane")
    for number in range(200):
        log.info("line %04d %s", number, "x" * 80)
    handler.flush()
    names = sorted(p.name for p in (home / "logs").iterdir())
    assert names == ["engine.log", "engine.log.1", "engine.log.2", "engine.log.3"]
    assert "line 0199" in engine_log.read_text(encoding="utf-8")
    for path in (home / "logs").iterdir():
        assert path.stat().st_size <= 2000
    assert "line 0000" not in "".join(p.read_text(encoding="utf-8") for p in (home / "logs").iterdir())


def test_engine_log_never_holds_a_private_key_or_window_key(home, engine_log):
    from app.services import window_key

    _, _, made, _ = call("POST", "/api/keys", {"name": "Logged", "passphrase": "longenough"})
    _, _, exported, _ = call("POST", f"/api/keys/{made['id']}/export", {"passphrase": "longenough", "current": "longenough"})
    call("POST", f"/api/keys/{made['id']}/export", {"passphrase": "longenough", "current": "wrong one"})
    call("POST", "/api/keys/import", {"pem": exported["pem"], "passphrase": "longenough"})
    call("PUT", "/api/settings", {"theme": "light"})
    logging.getLogger("formpublisher.lane").info("marker")
    file_handler(engine_log).flush()
    text = engine_log.read_text(encoding="utf-8")
    assert "marker" in text
    secret = pem_body((keys_folder(home) / f"{made['id']}.pem").read_bytes())
    for value in (secret[:32], pem_body(exported["pem"].encode())[:32], window_key.LOCAL_KEY, window_key.WINDOW_KEY, "longenough"):
        assert value not in text


@pytest.fixture
def temp_store(tmp_path, monkeypatch):
    import keyring

    previous = keyring.get_keyring()
    store = TempKeyring(tmp_path / "store")
    (tmp_path / "store").mkdir()
    keyring.set_keyring(store.backend)
    yield store
    keyring.set_keyring(previous)


def test_with_a_password_store_the_private_key_goes_there_and_not_to_a_file(home, temp_store):
    from app.services import keys

    _, _, made, _ = call("POST", "/api/keys", {"name": "Stored"})
    assert made["secret"] == "store"
    assert not (keys_folder(home) / f"{made['id']}.pem").exists()
    stored = temp_store.entries()[f"{keys.SERVICE}\n{made['id']}"]
    assert "PRIVATE KEY" in stored
    _, _, listing, payload = call("GET", "/api/keys", key=None)
    assert listing["keys"][0]["secret"] == "store"
    assert pem_body(stored.encode())[:24] not in payload.decode()


def test_removing_a_stored_key_clears_it_from_the_password_store(temp_store):
    _, _, made, _ = call("POST", "/api/keys", {"name": "Stored"})
    assert temp_store.entries()
    assert call("DELETE", f"/api/keys/{made['id']}")[0] == 200
    assert temp_store.entries() == {}


def test_stored_key_exports_to_the_same_public_key(temp_store):
    import base64

    from cryptography.hazmat.primitives import serialization

    _, _, made, _ = call("POST", "/api/keys", {"name": "Stored"})
    status, _, exported, _ = call("POST", f"/api/keys/{made['id']}/export", {"passphrase": "longenough"})
    assert status == 200
    private = serialization.load_pem_private_key(exported["pem"].encode(), password=b"longenough")
    raw = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    assert raw == base64.b64decode(call("GET", f"/api/keys/{made['id']}/public", key=None)[2]["publicKey"])


def test_file_kept_key_moves_into_a_password_store_once_one_appears(home, monkeypatch, tmp_path):
    import keyring

    from app.services import keys

    _, _, made, _ = call("POST", "/api/keys", {"name": "Mover"})
    assert made["secret"] == "file"
    previous = keyring.get_keyring()
    (tmp_path / "later").mkdir()
    store = TempKeyring(tmp_path / "later")
    keyring.set_keyring(store.backend)
    try:
        assert call("POST", f"/api/keys/{made['id']}/export", {"passphrase": "longenough"})[0] == 200
        assert f"{keys.SERVICE}\n{made['id']}" in store.entries()
        assert not (keys_folder(home) / f"{made['id']}.pem").exists()
        assert call("GET", "/api/keys", key=None)[2]["keys"][0]["secret"] == "store"
    finally:
        keyring.set_keyring(previous)
