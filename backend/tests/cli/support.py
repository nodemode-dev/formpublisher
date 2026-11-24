import json
import os
import select
import shutil
import subprocess
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
REPO = BACKEND.parent
DEMO_ZIP = REPO / "demo" / "sites" / "lowlight.zip"


def run_cli(capsys, *argv: str, in_process: bool = True) -> tuple[int, str, str]:
    from app import cli

    capsys.readouterr()
    args = list(argv) + (["--in-process"] if in_process and "--engine" not in argv else [])
    code = cli.main(args)
    got = capsys.readouterr()
    return code, got.out, got.err


def run_json(capsys, *argv: str) -> dict:
    code, out, err = run_cli(capsys, *argv, "--json")
    assert code == 0, err
    return json.loads(out)


class McpSession:
    def __init__(self, *extra: str, env: dict | None = None) -> None:
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "app.mcp", *extra],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=str(BACKEND), env=env or dict(os.environ), text=True, bufsize=1,
        )
        self.buffer: list[dict] = []

    def send(self, message: dict | str) -> None:
        line = message if isinstance(message, str) else json.dumps(message)
        self.proc.stdin.write(line + "\n")
        self.proc.stdin.flush()

    def wait_for(self, match, timeout: float = 30.0) -> dict:
        end = time.monotonic() + timeout
        while True:
            for item in self.buffer:
                if match(item):
                    self.buffer.remove(item)
                    return item
            left = end - time.monotonic()
            if left <= 0:
                raise AssertionError("no answer from the MCP server in time")
            ready, _, _ = select.select([self.proc.stdout], [], [], left)
            if ready:
                line = self.proc.stdout.readline()
                if not line:
                    raise AssertionError("the MCP server closed its output: " + self.proc.stderr.read()[-800:])
                self.buffer.append(json.loads(line))

    def request(self, ident, method: str, params: dict | None = None) -> dict:
        message = {"jsonrpc": "2.0", "id": ident, "method": method}
        if params is not None:
            message["params"] = params
        self.send(message)
        return self.wait_for(lambda m: m.get("id") == ident and ("result" in m or "error" in m))

    def initialize(self, version: str = "2025-06-18") -> dict:
        answer = self.request(0, "initialize", {"protocolVersion": version, "capabilities": {}, "clientInfo": {"name": "lane-test", "version": "1"}})
        self.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return answer

    def call(self, ident, name: str, arguments: dict) -> dict:
        return self.request(ident, "tools/call", {"name": name, "arguments": arguments})["result"]

    def close(self) -> None:
        try:
            self.proc.stdin.close()
        except OSError:
            pass
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()
        for stream in (self.proc.stdout, self.proc.stderr):
            stream.close()


def text_of(result: dict) -> str:
    return "\n".join(part.get("text", "") for part in result.get("content", []))


def setup_tool_copy(root: Path, tool: str, parts: list[str]) -> Path:
    (root / "setup").mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO / "setup" / tool, root / "setup" / tool)
    for part in parts:
        source = REPO / part
        if source.is_dir():
            shutil.copytree(source, root / part)
        else:
            (root / part).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, root / part)
    return root / "setup" / tool


def run_tool(script: Path, *args: str) -> subprocess.CompletedProcess:
    empty = script.parent.parent / "no-path"
    empty.mkdir(exist_ok=True)
    env = {"PATH": str(empty), "HOME": str(script.parent.parent), "LANG": "C.UTF-8", "PYTHONIOENCODING": "utf-8"}
    return subprocess.run([sys.executable, "-I", str(script), *args], capture_output=True, text=True, env=env, cwd=str(script.parent.parent), timeout=60)


def isolated_env(folder: Path) -> dict:
    user = folder / "user"
    user.mkdir(parents=True, exist_ok=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith("FORMPUBLISHER_") and not k.startswith("XDG_")}
    env.update({
        "HOME": str(user), "USERPROFILE": str(user), "PATH": "/usr/bin:/bin",
        "PYTHON_KEYRING_BACKEND": "keyring.backends.fail.Keyring",
        "FORMPUBLISHER_HOME": str(folder / "home"), "FORMPUBLISHER_PORT": "18299",
        "FORMPUBLISHER_FORMWEB_URL": "http://127.0.0.1:18298",
        "XDG_CONFIG_HOME": str(user / "config"), "XDG_DATA_HOME": str(user / "data"), "XDG_CACHE_HOME": str(user / "cache"),
    })
    return env
