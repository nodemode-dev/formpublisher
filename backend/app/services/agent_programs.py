import json
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

from app.services import agent_lookup, paths, terminal, window_key

AGENTS = ("claude", "codex", "cursor", "antigravity")
TITLES = {"claude": "Claude Code", "codex": "Codex", "cursor": "Cursor", "antigravity": "Antigravity"}
INSTALL = {kind: agent_lookup.install(kind) for kind in AGENTS}
OVERRIDES = {"claude": ("FORMPUBLISHER_CLAUDE_BIN",), "codex": ("FORMPUBLISHER_CODEX_BIN",), "cursor": ("FORMPUBLISHER_CURSOR_BIN",), "antigravity": ("FORMPUBLISHER_AGY_BIN",)}
ENTRY = "formpublisher_tab"
TABS_FOLDER = "agent-tabs"
KEY_FILE = "tab.key"
SHELL_WAIT = 10.0
CHECK_WAIT = 15.0
CACHE_SECONDS = 30.0

_cache: dict[str, tuple[float, agent_lookup.Found, bool | None]] = {}
_cache_lock = threading.Lock()
_open_lock = threading.Lock()


class NotInstalled(LookupError):
    pass


def child_env(path: str | None = None) -> dict:
    return agent_lookup.child_env(path, base=terminal.scrubbed_env(), shell_timeout=SHELL_WAIT)


def _signed_in(path: str) -> bool | None:
    try:
        out = agent_lookup.run([path, "auth", "status"], child_env(path), CHECK_WAIT)
        data = json.loads(out.stdout)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    return bool(data.get("loggedIn")) if isinstance(data, dict) and "loggedIn" in data else None


def _locate(kind: str, fresh: bool) -> tuple[agent_lookup.Found, bool | None]:
    found = agent_lookup.find(kind, setting=None, override_vars=OVERRIDES[kind], shell_timeout=SHELL_WAIT, fresh=fresh)
    found = agent_lookup.check(found, child_env(found.path), CHECK_WAIT, fresh)
    signed = _signed_in(found.path) if kind == "claude" and found.state == "runs" else None
    return found, signed


def located(kind: str, fresh: bool = False) -> tuple[agent_lookup.Found, bool | None]:
    now = time.monotonic()
    with _cache_lock:
        kept = _cache.get(kind)
    if kept is not None and not fresh and now - kept[0] < CACHE_SECONDS:
        return kept[1], kept[2]
    found, signed = _locate(kind, fresh)
    with _cache_lock:
        _cache[kind] = (time.monotonic(), found, signed)
    return found, signed


def status(fresh: bool = False) -> dict:
    out = {}
    for kind in AGENTS:
        found, signed = located(kind, fresh)
        runs = found.state == "runs"
        record = {"installed": runs, "version": found.version if runs else None, "install": "" if runs else INSTALL[kind], "signedIn": signed if kind != "antigravity" else None}
        if found.state == "broken":
            record["note"] = agent_lookup.sentence(found, INSTALL[kind])
        out[kind] = record
    return out


def runnable_kinds() -> list[str]:
    return [kind for kind in AGENTS if located(kind)[0].state == "runs"]


def _usable(kind: str) -> agent_lookup.Found:
    found, _signed = located(kind)
    if found.state != "runs":
        found, _signed = located(kind, fresh=True)
    if found.state != "runs":
        raise NotInstalled(agent_lookup.sentence(found, INSTALL[kind]))
    return found


def server_command(key_file: Path) -> tuple[str, list[str]]:
    if paths.frozen():
        return sys.executable, ["mcp", "--tab-key-file", str(key_file)]
    return sys.executable, [str(paths.backend_dir() / "formpublisher_engine.py"), "mcp", "--tab-key-file", str(key_file)]


def server_env() -> dict:
    return {"FORMPUBLISHER_PORT": str(paths.port()), "FORMPUBLISHER_HOME": str(paths.home())}


def _private_folder(folder: Path) -> None:
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name != "nt":
        os.chmod(folder, 0o700)


def _write_private(target: Path, text: str) -> None:
    _private_folder(target.parent)
    temp = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    temp.unlink(missing_ok=True)
    handle = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(handle, "w", encoding="utf-8") as out:
        out.write(text)
    os.replace(temp, target)


def _toml(value: str) -> str:
    return json.dumps(value)


def _entry(command: str, args: list[str]) -> dict:
    return {"mcpServers": {ENTRY: {"command": command, "args": args, "env": server_env()}}}


def _argv(kind: str, path: str, folder: Path, prompt: str | None, resume: str | None) -> list[str]:
    command, args = server_command(folder / KEY_FILE)
    config = json.dumps(_entry(command, args), indent=2) + "\n"
    if kind == "claude":
        target = folder / "mcp.json"
        _write_private(target, config)
        cmd = [path, "--mcp-config", str(target)]
        if resume:
            cmd += ["--resume", resume]
        if prompt:
            cmd += ["--", prompt]
        return cmd
    if kind == "codex":
        base = f"mcp_servers.{ENTRY}"
        listed = "[" + ", ".join(_toml(a) for a in args) + "]"
        table = "{" + ", ".join(f"{k} = {_toml(v)}" for k, v in server_env().items()) + "}"
        return [path, "-c", f"{base}.command={_toml(command)}", "-c", f"{base}.args={listed}", "-c", f"{base}.env={table}"]
    if kind == "cursor":
        _write_private(folder / ".cursor" / "mcp.json", config)
        return [path]
    _write_private(folder / ".agents" / "mcp_config.json", config)
    return [path]


def tabs_root() -> Path:
    root = paths.home() / TABS_FOLDER
    _private_folder(root)
    return root


def open_agent(kind: str, cols: int, rows: int, prompt: str | None = None, resume: str | None = None) -> dict:
    with _open_lock:
        if kind == "claude" and prompt and not resume:
            running = terminal.live_claude()
            if running is not None:
                terminal.type_into(running.id, prompt)
                return running.describe()
        found = _usable(kind)
        sid = terminal.new_id()
        folder = tabs_root() / sid
        _private_folder(folder)
        held = {"token": ""}

        def prepare() -> None:
            window_key.revoke_tab(held["token"])
            held["token"] = window_key.issue_tab()
            _write_private(folder / KEY_FILE, held["token"])

        def ended() -> None:
            window_key.revoke_tab(held["token"])

        def closed() -> None:
            window_key.revoke_tab(held["token"])
            held["token"] = ""
            shutil.rmtree(folder, ignore_errors=True)

        try:
            argv = agent_lookup.start_argv(_argv(kind, found.path, folder, prompt if kind == "claude" else None, resume if kind == "claude" else None))
            title = f"{TITLES[kind]} (resumed)" if resume else TITLES[kind]
            session = terminal.open_session(kind, title, str(folder), argv, child_env(found.path), cols, rows, found.path,
                                            sid=sid, prepare=prepare, on_exit=[ended], on_close=[closed])
        except Exception:
            closed()
            raise
        return session.describe()
