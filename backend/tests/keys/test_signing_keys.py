import base64
import json
import os
import stat

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .support import call, fingerprint, keys_folder, pem_body


def make(name="Studio key", passphrase=None):
    body = {"name": name}
    if passphrase:
        body["passphrase"] = passphrase
    status, _, data, _ = call("POST", "/api/keys", body)
    assert status == 200, data
    return data


def raw_public(key_id):
    status, _, data, _ = call("GET", f"/api/keys/{key_id}/public", key=None)
    assert status == 200, data
    return base64.b64decode(data["publicKey"])


def test_created_key_fingerprint_is_sha256_of_its_public_key():
    made = make()
    raw = raw_public(made["id"])
    assert len(raw) == 32
    assert made["fingerprint"] == fingerprint(raw)
    assert made["id"] == __import__("hashlib").sha256(raw).hexdigest()[:16]


def test_created_key_reply_holds_no_private_key():
    made = make()
    text = json.dumps(made)
    assert "PRIVATE" not in text and "pem" not in made and "publicKey" not in made
    assert made["name"] == "Studio key" and made["encrypted"] is False and made["canSign"] is True


def test_without_a_system_keyring_the_private_key_goes_to_a_private_file(home):
    made = make()
    assert made["secret"] == "file"
    pem = keys_folder(home) / f"{made['id']}.pem"
    assert pem.is_file()
    assert stat.S_IMODE(os.stat(pem).st_mode) == 0o600


def test_private_file_holds_the_key_that_matches_the_listed_public_key(home):
    made = make()
    pem = (keys_folder(home) / f"{made['id']}.pem").read_bytes()
    private = serialization.load_pem_private_key(pem, password=None)
    assert isinstance(private, Ed25519PrivateKey)
    raw = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    assert raw == raw_public(made["id"])


def test_listing_never_returns_the_private_key(home):
    first = make("One")
    second = make("Two")
    status, _, data, payload = call("GET", "/api/keys", key=None)
    assert status == 200
    assert data["count"] == 2
    assert sorted(row["name"] for row in data["keys"]) == ["One", "Two"]
    text = payload.decode("utf-8")
    for made in (first, second):
        body = pem_body((keys_folder(home) / f"{made['id']}.pem").read_bytes())
        assert body not in text
        assert body[:24] not in text
    assert "PRIVATE" not in text
    for row in data["keys"]:
        assert set(row) == {"id", "name", "fingerprint", "created", "encrypted", "secret", "canSign"}


def test_listing_reports_each_key_with_its_own_fingerprint():
    made = make("Listed")
    _, _, data, _ = call("GET", "/api/keys", key=None)
    row = next(r for r in data["keys"] if r["id"] == made["id"])
    assert row["fingerprint"] == fingerprint(raw_public(made["id"]))


def test_public_key_route_returns_only_public_material():
    made = make()
    status, _, data, _ = call("GET", f"/api/keys/{made['id']}/public", key=None)
    assert status == 200
    assert set(data) == {"id", "fingerprint", "publicKey"}


def test_removed_key_is_gone_from_the_list_and_its_public_route(home):
    made = make("Doomed")
    status, _, data, _ = call("DELETE", f"/api/keys/{made['id']}")
    assert status == 200
    assert data["removed"] is True and data["id"] == made["id"]
    _, _, listing, _ = call("GET", "/api/keys", key=None)
    assert made["id"] not in [r["id"] for r in listing["keys"]]
    assert listing["count"] == 0
    status, _, gone, _ = call("GET", f"/api/keys/{made['id']}/public", key=None)
    assert status == 404
    assert gone["detail"] == "key not found"


def test_removed_key_leaves_no_private_file_in_the_keys_folder(home):
    made = make()
    call("DELETE", f"/api/keys/{made['id']}")
    assert not (keys_folder(home) / f"{made['id']}.pem").exists()


def test_removing_one_key_keeps_the_other():
    keep = make("Keep")
    drop = make("Drop")
    call("DELETE", f"/api/keys/{drop['id']}")
    _, _, listing, _ = call("GET", "/api/keys", key=None)
    assert [r["id"] for r in listing["keys"]] == [keep["id"]]


def test_removing_a_key_twice_answers_not_found_the_second_time():
    made = make()
    assert call("DELETE", f"/api/keys/{made['id']}")[0] == 200
    status, _, data, _ = call("DELETE", f"/api/keys/{made['id']}")
    assert status == 404
    assert data["code"] == "key-missing"


@pytest.mark.parametrize("key_id", ["0123456789abcdef", "not-a-key", "ABCDEF0123456789"])
def test_unknown_or_malformed_key_id_is_not_found(key_id):
    status, _, data, _ = call("GET", f"/api/keys/{key_id}/public", key=None)
    assert status == 404
    assert data["detail"] == "key not found"


@pytest.mark.parametrize("name", ["", "   ", None])
def test_key_without_a_name_is_refused(name):
    status, _, data, _ = call("POST", "/api/keys", {"name": name})
    assert status == 400
    assert data["detail"] == "name is required"
    _, _, listing, _ = call("GET", "/api/keys", key=None)
    assert listing["count"] == 0


def test_key_name_is_trimmed_and_capped_at_120_characters():
    made = make("  " + "n" * 200 + "  ")
    assert made["name"] == "n" * 120


def test_body_that_is_not_json_is_refused():
    status, _, data, _ = call("POST", "/api/keys", raw=b"{not json")
    assert status == 400
    assert data["detail"] == "the body is not valid JSON"


def test_body_that_is_not_an_object_is_refused():
    status, _, data, _ = call("POST", "/api/keys", ["name"])
    assert status == 400
    assert data["detail"] == "the body must be an object"


def test_passphrase_key_is_marked_encrypted_and_its_file_needs_the_passphrase(home):
    made = make("Locked", passphrase="correct horse")
    assert made["encrypted"] is True
    pem = (keys_folder(home) / f"{made['id']}.pem").read_bytes()
    with pytest.raises(TypeError):
        serialization.load_pem_private_key(pem, password=None)
    private = serialization.load_pem_private_key(pem, password=b"correct horse")
    raw = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    assert raw == raw_public(made["id"])


def test_export_round_trips_to_the_same_public_key():
    made = make()
    status, _, data, _ = call("POST", f"/api/keys/{made['id']}/export", {"passphrase": "longenough"})
    assert status == 200
    assert data["encrypted"] is True
    private = serialization.load_pem_private_key(data["pem"].encode("ascii"), password=b"longenough")
    raw = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    assert raw == raw_public(made["id"])


def test_exported_pem_cannot_be_opened_without_its_passphrase():
    made = make()
    _, _, data, _ = call("POST", f"/api/keys/{made['id']}/export", {"passphrase": "longenough"})
    with pytest.raises(TypeError):
        serialization.load_pem_private_key(data["pem"].encode("ascii"), password=None)


@pytest.mark.parametrize("passphrase", ["", "short", "1234567", None])
def test_export_refuses_a_passphrase_under_eight_characters(passphrase):
    made = make()
    status, _, data, _ = call("POST", f"/api/keys/{made['id']}/export", {"passphrase": passphrase})
    assert status == 400
    assert data["code"] == "passphrase-short"
    assert "at least 8 characters" in data["detail"]


def test_export_of_a_locked_key_with_the_wrong_current_passphrase_is_refused():
    made = make("Locked", passphrase="right one")
    status, _, data, _ = call("POST", f"/api/keys/{made['id']}/export", {"passphrase": "longenough", "current": "wrong one"})
    assert status == 400
    assert data["detail"] == "The passphrase does not unlock this key."


def test_export_of_a_locked_key_without_its_passphrase_is_refused():
    made = make("Locked", passphrase="right one")
    status, _, data, _ = call("POST", f"/api/keys/{made['id']}/export", {"passphrase": "longenough"})
    assert status == 400
    assert data["code"] == "passphrase-required"


def test_export_to_a_file_writes_a_pem_that_opens_with_the_passphrase(tmp_path):
    made = make()
    target = tmp_path / "out" / "mine.pem"
    target.parent.mkdir()
    status, _, data, _ = call("POST", f"/api/keys/{made['id']}/export", {"passphrase": "longenough", "path": str(target)})
    assert status == 200
    assert data["file"] == str(target)
    private = serialization.load_pem_private_key(target.read_bytes(), password=b"longenough")
    raw = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    assert raw == raw_public(made["id"])


def test_export_to_a_taken_path_is_refused_without_force(tmp_path):
    made = make()
    target = tmp_path / "taken.pem"
    target.write_text("keep me", encoding="utf-8")
    status, _, data, _ = call("POST", f"/api/keys/{made['id']}/export", {"passphrase": "longenough", "path": str(target)})
    assert status == 409
    assert data["detail"] == "A file already exists at that path."
    assert target.read_text(encoding="utf-8") == "keep me"


def test_removed_key_comes_back_with_the_same_identity_after_import():
    made = make("Traveller")
    _, _, exported, _ = call("POST", f"/api/keys/{made['id']}/export", {"passphrase": "longenough"})
    call("DELETE", f"/api/keys/{made['id']}")
    status, _, back, _ = call("POST", "/api/keys/import", {"pem": exported["pem"], "passphrase": "longenough", "name": "Traveller"})
    assert status == 200, back
    assert back["id"] == made["id"]
    assert back["fingerprint"] == made["fingerprint"]
    assert back["canSign"] is True
    assert "PRIVATE" not in json.dumps(back)


def test_importing_a_key_you_already_have_is_refused():
    made = make()
    _, _, exported, _ = call("POST", f"/api/keys/{made['id']}/export", {"passphrase": "longenough"})
    status, _, data, _ = call("POST", "/api/keys/import", {"pem": exported["pem"], "passphrase": "longenough"})
    assert status == 409
    assert data["detail"] == "This key is already one of your signing keys."


def test_importing_with_the_wrong_passphrase_is_refused():
    made = make()
    _, _, exported, _ = call("POST", f"/api/keys/{made['id']}/export", {"passphrase": "longenough"})
    call("DELETE", f"/api/keys/{made['id']}")
    status, _, data, _ = call("POST", "/api/keys/import", {"pem": exported["pem"], "passphrase": "not the one"})
    assert status == 400
    assert data["detail"] == "The passphrase does not unlock this key."


def test_importing_text_that_is_not_a_pem_key_is_refused():
    status, _, data, _ = call("POST", "/api/keys/import", {"pem": "hello"})
    assert status == 400
    assert data["code"] == "pem-invalid"


def test_importing_an_outside_ed25519_key_lists_it_with_its_own_fingerprint():
    outside = Ed25519PrivateKey.generate()
    pem = outside.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    raw = outside.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    status, _, data, _ = call("POST", "/api/keys/import", {"pem": pem.decode("ascii"), "name": "Outside"})
    assert status == 200, data
    assert data["fingerprint"] == fingerprint(raw)
    assert raw_public(data["id"]) == raw


def test_creating_a_key_without_the_window_key_is_refused_and_creates_nothing():
    status, _, data, _ = call("POST", "/api/keys", {"name": "Sneaky"}, key=None)
    assert status == 403
    assert data["detail"] == "Only the FormPublisher window, its command line or its MCP server can do this."
    _, _, listing, _ = call("GET", "/api/keys", key=None)
    assert listing["count"] == 0


def test_removing_a_key_with_a_wrong_window_key_is_refused_and_keeps_it():
    made = make()
    status, _, data, _ = call("DELETE", f"/api/keys/{made['id']}", key="guess")
    assert status == 403
    assert data["code"] == "forbidden"
    _, _, listing, _ = call("GET", "/api/keys", key=None)
    assert [r["id"] for r in listing["keys"]] == [made["id"]]


def test_exporting_without_the_window_key_is_refused():
    made = make()
    status, _, data, payload = call("POST", f"/api/keys/{made['id']}/export", {"passphrase": "longenough"}, key=None)
    assert status == 403
    assert b"PRIVATE" not in payload
