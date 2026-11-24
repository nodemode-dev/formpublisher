import json
import re
import shutil
import tomllib

import pytest

from .support import REPO, run_tool, setup_tool_copy

DOCK = "frontend/src/dock"
I18N = "frontend/src/i18n"
VENDOR = "vendor/formweb-native"
CRATES = ("formweb-model", "formweb-engine", "formweb-export", "formweb-core")


@pytest.fixture
def dock(tmp_path):
    script = setup_tool_copy(tmp_path, "dock_check.py", [DOCK])
    return script, tmp_path / DOCK


@pytest.fixture(scope="module")
def i18n_master(tmp_path_factory):
    root = tmp_path_factory.mktemp("i18n-master")
    setup_tool_copy(root, "i18n_check.py", [I18N])
    return root


@pytest.fixture
def i18n(i18n_master, tmp_path):
    shutil.copytree(i18n_master, tmp_path / "copy")
    return tmp_path / "copy" / "setup" / "i18n_check.py", tmp_path / "copy" / I18N


@pytest.fixture
def vendor(tmp_path):
    parts = [f"{VENDOR}/VENDOR.md", f"{VENDOR}/Cargo.toml", f"{VENDOR}/Cargo.lock"] + [f"{VENDOR}/crates/{name}/Cargo.toml" for name in CRATES]
    script = setup_tool_copy(tmp_path, "vendor_check.py", parts)
    return script, tmp_path / VENDOR


def test_dock_check_passes_on_an_unchanged_copy_and_counts_the_manifest_files(dock):
    script, folder = dock
    listed = json.loads((folder / "MANIFEST.json").read_text(encoding="utf-8"))["files"]
    run = run_tool(script)
    assert run.returncode == 0, run.stderr
    assert f": {len(listed)} files match MANIFEST.json" in run.stdout


def test_dock_check_catches_one_changed_byte(dock):
    script, folder = dock
    target = folder / "dock.ts"
    target.write_bytes(target.read_bytes() + b" ")
    run = run_tool(script)
    assert run.returncode == 1
    assert "[formpublisher] dock: dock.ts: differs from MANIFEST.json" in run.stderr


def test_dock_check_catches_an_extra_file(dock):
    script, folder = dock
    (folder / "stray.ts").write_text("export {}\n", encoding="utf-8")
    run = run_tool(script)
    assert run.returncode == 1
    assert "stray.ts: not listed in MANIFEST.json (extra file)" in run.stderr


def test_dock_check_catches_a_missing_file(dock):
    script, folder = dock
    (folder / "icons.ts").unlink()
    run = run_tool(script)
    assert run.returncode == 1
    assert "icons.ts: listed in MANIFEST.json but missing" in run.stderr


def test_dock_check_refuses_a_manifest_that_is_not_json(dock):
    script, folder = dock
    (folder / "MANIFEST.json").write_text("{broken", encoding="utf-8")
    run = run_tool(script)
    assert run.returncode == 1
    assert "MANIFEST.json cannot be read" in run.stderr


def first_locale_key(folder):
    part = sorted((folder / "keys").glob("*.json"))[0]
    keys = json.loads(part.read_text(encoding="utf-8"))
    locale = sorted(p for p in (folder / "locales").iterdir() if p.is_dir())[0]
    return part.name, keys, locale


def test_i18n_check_passes_on_an_unchanged_copy(i18n):
    script, folder = i18n
    parts = sorted((folder / "keys").glob("*.json"))
    total = sum(len(json.loads(p.read_text(encoding="utf-8"))) for p in parts)
    run = run_tool(script)
    assert run.returncode == 0, run.stderr[-600:]
    assert f"{total} strings in {len(parts)} key files" in run.stdout


def test_i18n_check_catches_a_missing_translation(i18n):
    script, folder = i18n
    name, keys, locale = first_locale_key(folder)
    table_path = locale / name
    table = json.loads(table_path.read_text(encoding="utf-8"))
    del table[keys[0]]
    table_path.write_text(json.dumps(table), encoding="utf-8")
    run = run_tool(script)
    assert run.returncode == 1
    assert f"locales/{locale.name}/{name}: no translation for {keys[0]!r}" in run.stderr
    assert "1 language problems" in run.stderr


def test_i18n_check_catches_a_translation_with_an_em_dash(i18n):
    script, folder = i18n
    name, keys, locale = first_locale_key(folder)
    table_path = locale / name
    table = json.loads(table_path.read_text(encoding="utf-8"))
    table[keys[0]] = table[keys[0]] + " \u2014 x"
    table_path.write_text(json.dumps(table, ensure_ascii=False), encoding="utf-8")
    run = run_tool(script)
    assert run.returncode == 1
    assert "an em dash in the translation of" in run.stderr


def test_i18n_check_catches_a_placeholder_that_differs_from_the_english_key(i18n):
    script, folder = i18n
    _, _, locale = first_locale_key(folder)
    found = [(part.name, key) for part in sorted((folder / "keys").glob("*.json")) for key in json.loads(part.read_text(encoding="utf-8")) if re.search(r"\{[a-zA-Z]+\}", key)]
    name, with_placeholder = found[0]
    table_path = locale / name
    table = json.loads(table_path.read_text(encoding="utf-8"))
    table[with_placeholder] = re.sub(r"\{[a-zA-Z]+\}", "{renamed}", table[with_placeholder])
    table_path.write_text(json.dumps(table, ensure_ascii=False), encoding="utf-8")
    run = run_tool(script)
    assert run.returncode == 1
    assert f"placeholders differ for {with_placeholder!r}" in run.stderr


def test_i18n_check_catches_a_translation_for_a_key_that_does_not_exist(i18n):
    script, folder = i18n
    name, _, locale = first_locale_key(folder)
    table_path = locale / name
    table = json.loads(table_path.read_text(encoding="utf-8"))
    table["A sentence nobody wrote"] = "x"
    table_path.write_text(json.dumps(table, ensure_ascii=False), encoding="utf-8")
    run = run_tool(script)
    assert run.returncode == 1
    assert "'A sentence nobody wrote' is not a key" in run.stderr


def test_i18n_check_catches_a_locale_folder_not_listed_in_index_ts(i18n):
    script, folder = i18n
    shutil.copytree(sorted(p for p in (folder / "locales").iterdir() if p.is_dir())[0], folder / "locales" / "xx")
    run = run_tool(script)
    assert run.returncode == 1
    assert "xx: listed in index.ts or present in locales, not both" in run.stderr


def workspace_version(folder) -> str:
    return tomllib.loads((folder / "Cargo.toml").read_text(encoding="utf-8"))["workspace"]["package"]["version"]


def test_vendor_check_passes_outside_git_and_names_the_workspace_version(vendor):
    script, folder = vendor
    run = run_tool(script, "--check")
    assert run.returncode == 0, run.stdout
    assert "vendor: not a git checkout, so the tree hashes and uncommitted changes were not checked" in run.stdout
    assert run.stdout.strip().splitlines()[-1] == f"vendor: in step at {workspace_version(folder)}"


def test_vendor_check_catches_a_table_version_that_differs_from_cargo_toml(vendor):
    script, folder = vendor
    table = folder / "VENDOR.md"
    table.write_text(re.sub(r"^\| Version \| .* \|$", "| Version | 9.9.9 |", table.read_text(encoding="utf-8"), count=1, flags=re.M), encoding="utf-8")
    run = run_tool(script, "--check")
    assert run.returncode == 1
    assert f"vendor: VENDOR.md says Version 9.9.9 but Cargo.toml has {workspace_version(folder)}" in run.stdout
    assert "in step" not in run.stdout


def test_vendor_check_catches_a_crate_locked_at_another_version(vendor):
    script, folder = vendor
    lock = folder / "Cargo.lock"
    text = lock.read_text(encoding="utf-8")
    version = workspace_version(folder)
    changed = text.replace(f'name = "formweb-export"\nversion = "{version}"', 'name = "formweb-export"\nversion = "0.0.1"', 1)
    assert changed != text
    lock.write_text(changed, encoding="utf-8")
    run = run_tool(script, "--check")
    assert run.returncode == 1
    assert f"vendor: Cargo.lock lists formweb-export at 0.0.1 but the workspace is {version}" in run.stdout


def test_vendor_check_catches_a_crate_with_its_own_version(vendor):
    script, folder = vendor
    manifest = folder / "crates" / "formweb-model" / "Cargo.toml"
    text = manifest.read_text(encoding="utf-8")
    changed = re.sub(r"^version(\.workspace)?\s*=.*$", 'version = "0.0.2"', text, count=1, flags=re.M)
    assert changed != text
    manifest.write_text(changed, encoding="utf-8")
    run = run_tool(script, "--check")
    assert run.returncode == 1
    assert "vendor: crates/formweb-model resolves to 0.0.2 but the workspace is" in run.stdout


def test_vendor_check_refuses_an_unknown_argument_with_exit_two_and_its_usage(vendor):
    script, _ = vendor
    run = run_tool(script, "--fix")
    assert run.returncode == 2
    assert "./formpublisher vendor --check" in run.stdout
