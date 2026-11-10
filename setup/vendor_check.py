#!/usr/bin/env python3
"""./formpublisher vendor --check: the vendored FormWeb crates stay in step with their table.

Passes only when the Version row of vendor/formweb-native/VENDOR.md equals the workspace version in
vendor/formweb-native/Cargo.toml, the four crates resolve to that version and Cargo.lock lists them at it.
Inside a git checkout it also compares each crate's tree hash row with the tree of its staged files and
refuses unstaged changes and untracked files under vendor/formweb-native outside target/. Changes go to
FormWeb first; after vendoring update the table and run git add vendor/formweb-native. Exits 1 when
anything is out of step.
"""

import hashlib
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "vendor" / "formweb-native"
REL = "vendor/formweb-native"
CRATES = ("formweb-model", "formweb-engine", "formweb-export", "formweb-core")
FIX = "vendor the crates from FormWeb unchanged (changes go to FormWeb first), then update the table in vendor/formweb-native/VENDOR.md"


def _git(*args: str) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)
    except OSError:
        return None


def _in_checkout() -> bool:
    got = _git("rev-parse", "--show-toplevel")
    return bool(got and got.returncode == 0 and Path(got.stdout.strip()).resolve() == ROOT)


def _tree_id(node: dict) -> str:
    items = []
    for name, value in node.items():
        if isinstance(value, dict):
            items.append((name.encode() + b"/", b"40000 " + name.encode() + b"\0" + bytes.fromhex(_tree_id(value))))
        else:
            mode, blob = value
            items.append((name.encode(), mode.encode() + b" " + name.encode() + b"\0" + bytes.fromhex(blob)))
    body = b"".join(entry for _, entry in sorted(items))
    return hashlib.sha1(b"tree %d\0" % len(body) + body).hexdigest()


def staged_tree(crate: str) -> str:
    """The id git would give the staged state of one vendored crate, computed without writing into .git."""
    prefix = f"{REL}/crates/{crate}/"
    got = _git("ls-files", "--stage", "-z", "--", prefix)
    if not got or got.returncode != 0 or not got.stdout:
        return ""
    root: dict = {}
    for entry in got.stdout.split("\0"):
        if not entry:
            continue
        meta, path = entry.split("\t", 1)
        mode, blob, _stage = meta.split()
        parts = path[len(prefix):].split("/")
        node = root
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = (mode, blob)
    return _tree_id(root)


def _table(text: str) -> dict[str, str]:
    rows = {}
    for key, value in re.findall(r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$", text, re.M):
        rows[key.strip("` ")] = value.strip("` ")
    return rows


def _load(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def check() -> tuple[list[str], list[str]]:
    bad, notes = [], []
    try:
        rows = _table((VENDOR / "VENDOR.md").read_text(encoding="utf-8"))
        workspace = _load(VENDOR / "Cargo.toml")["workspace"]["package"]["version"]
    except (OSError, KeyError, tomllib.TOMLDecodeError) as err:
        return [f"vendor: cannot read the vendored files ({err}); restore vendor/formweb-native from git"], notes
    table_version = rows.get("Version", "")
    if table_version != workspace:
        bad.append(f"vendor: VENDOR.md says Version {table_version or 'nothing'} but Cargo.toml has {workspace}; {FIX}")
    for name in CRATES:
        try:
            package = _load(VENDOR / "crates" / name / "Cargo.toml")["package"]
        except (OSError, KeyError, tomllib.TOMLDecodeError) as err:
            bad.append(f"vendor: crates/{name}/Cargo.toml cannot be read ({err}); restore it from git")
            continue
        version = package.get("version")
        got = workspace if isinstance(version, dict) and version.get("workspace") else version
        if got != workspace:
            bad.append(f"vendor: crates/{name} resolves to {got} but the workspace is {workspace}; {FIX}")
    try:
        locked = {p["name"]: p.get("version") for p in _load(VENDOR / "Cargo.lock").get("package", []) if "source" not in p}
    except (OSError, tomllib.TOMLDecodeError) as err:
        locked = {}
        bad.append(f"vendor: Cargo.lock cannot be read ({err}); restore it from git")
    else:
        for name in CRATES:
            if locked.get(name) != workspace:
                bad.append(f"vendor: Cargo.lock lists {name} at {locked.get(name) or 'nothing'} but the workspace is {workspace}; copy FormWeb's Cargo.lock over vendor/formweb-native/Cargo.lock")
    if not _in_checkout():
        notes.append("vendor: not a git checkout, so the tree hashes and uncommitted changes were not checked")
        return bad, notes
    for name in CRATES:
        want = rows.get(f"crates/{name}", "")
        have = staged_tree(name)
        if not have:
            bad.append(f"vendor: crates/{name} is not staged; run git add {REL} after vendoring")
        elif have != want:
            bad.append(f"vendor: crates/{name} staged tree is {have} but VENDOR.md says {want or 'nothing'}; if the files are FormWeb's unedited, update the row and run git add {REL}, otherwise revert the edit and make the change in FormWeb first")
    for label, args, fix in (
        ("unstaged change in", ("diff", "--name-only", "-z", "--", REL), "run git add {REL} if it is FormWeb's unedited file and the table is updated, otherwise git checkout -- {path} (changes go to FormWeb first)"),
        ("untracked file", ("ls-files", "--others", "--exclude-standard", "-z", "--", REL), "run git add {REL} after vendoring, or delete it"),
    ):
        found = _git(*args)
        if found and found.returncode == 0:
            for path in found.stdout.split("\0"):
                if path and not path.startswith(f"{REL}/target/"):
                    bad.append(f"vendor: {label} {path}; " + fix.format(REL=REL, path=path))
    return bad, notes


def main(argv: list[str]) -> int:
    if argv not in ([], ["--check"]):
        print(__doc__)
        return 2
    bad, notes = check()
    for line in notes + bad:
        print(line)
    if bad:
        return 1
    version = _load(VENDOR / "Cargo.toml")["workspace"]["package"]["version"]
    print(f"vendor: in step at {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
