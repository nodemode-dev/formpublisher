import json
import os

import pytest

from .support import call


def test_settings_start_from_the_documented_defaults_and_report_the_data_folder(home):
    status, _, data, _ = call("GET", "/api/settings", key=None)
    assert status == 200
    assert data["theme"] == "dark" and data["language"] == "en" and data["density"] == "comfortable"
    assert data["receive.autoCheck"] is False and data["receive.autoBuild"] is False
    assert data["home"] == str(home)


def test_formweb_address_default_comes_from_the_environment():
    _, _, data, _ = call("GET", "/api/settings", key=None)
    assert data["formwebUrl"] == "http://127.0.0.1:18298"


def test_saved_setting_reads_back_and_lands_in_the_settings_file(home):
    status, _, data, _ = call("PUT", "/api/settings", {"theme": "light", "receive.autoBuild": True})
    assert status == 200
    assert data["theme"] == "light" and data["receive.autoBuild"] is True
    _, _, again, _ = call("GET", "/api/settings", key=None)
    assert again["theme"] == "light" and again["receive.autoBuild"] is True
    on_disk = json.loads((home / "settings.json").read_text(encoding="utf-8"))
    assert on_disk == {"theme": "light", "receive.autoBuild": True}


def test_unknown_setting_is_refused_by_name_and_nothing_is_saved(home):
    status, _, data, _ = call("PUT", "/api/settings", {"theme": "light", "colour": "red", "zoom": 2})
    assert status == 400
    assert data["detail"] == "unknown settings: colour, zoom"
    assert not (home / "settings.json").exists()
    _, _, again, _ = call("GET", "/api/settings", key=None)
    assert again["theme"] == "dark"


def test_null_value_returns_a_setting_to_its_default():
    call("PUT", "/api/settings", {"density": "compact"})
    _, _, data, _ = call("PUT", "/api/settings", {"density": None})
    assert data["density"] == "comfortable"


def test_home_in_a_settings_body_is_ignored(home, tmp_path):
    status, _, data, _ = call("PUT", "/api/settings", {"home": str(tmp_path / "elsewhere"), "language": "fr"})
    assert status == 200
    assert data["home"] == str(home) and data["language"] == "fr"


@pytest.mark.parametrize("value", ["true", 1, "yes"])
def test_receive_flags_accept_only_true_or_false(value):
    status, _, data, _ = call("PUT", "/api/settings", {"receive.autoCheck": value})
    assert status == 400
    assert data["detail"] == "receive.autoCheck must be true or false"


@pytest.mark.parametrize("url", ["https://example.com", "http://10.0.0.5:8240", "ftp://127.0.0.1:8240", "http://127.0.0.1.evil:8240"])
def test_formweb_address_must_be_loopback(url):
    status, _, data, _ = call("PUT", "/api/settings", {"formwebUrl": url})
    assert status == 400
    assert data["detail"].startswith("formwebUrl must be an http(s) loopback address")


@pytest.mark.parametrize("url", ["http://localhost:9000/", "https://[::1]:8240", "http://127.0.0.1"])
def test_loopback_formweb_address_is_saved_without_a_trailing_slash(url):
    status, _, data, _ = call("PUT", "/api/settings", {"formwebUrl": url})
    assert status == 200
    assert data["formwebUrl"] == url.rstrip("/")


@pytest.mark.parametrize("value", ["", "   ", 7])
def test_text_setting_must_be_a_non_empty_string(value):
    status, _, data, _ = call("PUT", "/api/settings", {"theme": value})
    assert status == 400
    assert data["detail"] == "theme must be a non-empty string"


def test_text_setting_over_64_characters_is_refused():
    status, _, data, _ = call("PUT", "/api/settings", {"language": "x" * 65})
    assert status == 400
    assert data["detail"] == "language is too long"
    assert call("PUT", "/api/settings", {"language": "x" * 64})[0] == 200


def test_chrome_path_must_be_absolute_and_name_an_existing_file(tmp_path):
    status, _, data, _ = call("PUT", "/api/settings", {"checks.chromePath": "bin/chrome"})
    assert status == 400 and "absolute path" in data["detail"]
    status, _, data, _ = call("PUT", "/api/settings", {"checks.chromePath": str(tmp_path / "none")})
    assert status == 400 and data["detail"] == "There is no file at that path."
    real = tmp_path / "chrome"
    real.write_text("x", encoding="utf-8")
    status, _, data, _ = call("PUT", "/api/settings", {"checks.chromePath": str(real)})
    assert status == 200 and data["checks.chromePath"] == str(real)


def test_settings_body_that_is_not_an_object_is_refused():
    status, _, _, _ = call("PUT", "/api/settings", ["theme"])
    assert status in (400, 422)


def test_saving_settings_without_the_window_key_changes_nothing(home):
    status, _, data, _ = call("PUT", "/api/settings", {"theme": "light"}, key=None)
    assert status == 403 and data["code"] == "forbidden"
    _, _, again, _ = call("GET", "/api/settings", key=None)
    assert again["theme"] == "dark"


def test_saved_change_reaches_a_live_subscriber():
    import asyncio

    from app.services import settings
    from app.services.bus import bus

    async def run():
        previous = bus._loop
        bus.attach(asyncio.get_running_loop())
        queue = bus.subscribe()
        try:
            settings.update({"theme": "light"})
            return await asyncio.wait_for(queue.get(), 1)
        finally:
            bus.unsubscribe(queue)
            bus._loop = previous

    message = asyncio.run(run())
    assert message["type"] == "settings.changed"
    assert message["settings"]["theme"] == "light"


def test_data_folder_follows_the_environment_and_holds_the_documented_layout(home):
    from app.services import paths

    assert paths.home() == home
    assert {p.name for p in home.iterdir() if p.is_dir()} >= {"sites", "builds", "keys", "prepared", "trash", "inbox"}


def test_without_an_environment_folder_the_data_folder_is_formpublisher_in_the_home_folder(monkeypatch, tmp_path):
    from app.services import paths

    monkeypatch.delenv("FORMPUBLISHER_HOME")
    monkeypatch.setenv("HOME", str(tmp_path / "me"))
    assert paths.home() == tmp_path / "me" / "FormPublisher"
    assert (tmp_path / "me" / "FormPublisher").is_dir()


@pytest.mark.parametrize("raw,expected", [("9123", 9123), ("", 8280), ("abc", 8280), ("70000", 8280), ("0", 8280)])
def test_engine_port_comes_from_the_environment_or_falls_back_to_8280(monkeypatch, raw, expected):
    from app.services import paths

    monkeypatch.setenv("FORMPUBLISHER_PORT", raw)
    assert paths.port() == expected


@pytest.mark.parametrize("raw,expected", [("9124", 9124), ("", 8281), ("-1", 8281)])
def test_site_host_port_comes_from_the_environment_or_falls_back_to_8281(monkeypatch, raw, expected):
    from app.services import paths

    monkeypatch.setattr(paths, "_host_port_override", None)
    monkeypatch.setenv("FORMPUBLISHER_HOST_PORT", raw)
    assert paths.host_port() == expected
    assert paths.host_origin() == f"http://127.0.0.1:{expected}"


def test_allowed_origins_from_the_environment_are_trimmed(monkeypatch):
    from app.services import paths

    monkeypatch.setenv("FORMPUBLISHER_ORIGINS", " http://a.test/ ,, http://b.test:1 ")
    assert paths.origins() == ["http://a.test", "http://b.test:1"]


def test_default_origins_include_the_engine_own_port(monkeypatch):
    from app.services import paths

    monkeypatch.delenv("FORMPUBLISHER_ORIGINS", raising=False)
    found = paths.origins()
    assert "http://127.0.0.1:18299" in found and "http://localhost:5280" in found


def test_engine_file_announces_this_process_and_is_removed_only_by_it(home):
    from app.services import paths

    paths.write_engine_file("9.9.9")
    record = json.loads((home / "engine.json").read_text(encoding="utf-8"))
    assert record["pid"] == os.getpid() and record["port"] == 18299 and record["version"] == "9.9.9"
    paths.remove_engine_file()
    assert not (home / "engine.json").exists()
    (home / "engine.json").write_text(json.dumps({"pid": os.getpid() + 100000}), encoding="utf-8")
    paths.remove_engine_file()
    assert (home / "engine.json").exists()
