import asyncio
import codecs
import logging
import os
import secrets
import shutil
import threading
import time
import uuid
from collections import deque
from pathlib import Path

from app.services import paths

try:
    if os.name == "nt":
        from winpty import PtyProcess
    else:
        from ptyprocess import PtyProcessUnicode as PtyProcess
except ImportError:
    PtyProcess = None

log = logging.getLogger("formpublisher")
VERSION = "2.2.1"
KINDS = ("shell", "claude", "codex", "cursor", "antigravity")
SCROLLBACK = 256 * 1024
MIN_COLS, MIN_ROWS = 10, 4
MAX_COLS, MAX_ROWS = 500, 200
QUEUE_LIMIT = 2000
TICKET_SECONDS = 60.0
SECRET_NAMES = ("FORMPUBLISHER_SHELL_PID", "FORMPUBLISHER_DESKTOP")


def clamp(cols, rows) -> tuple[int, int]:
    return min(max(int(cols), MIN_COLS), MAX_COLS), min(max(int(rows), MIN_ROWS), MAX_ROWS)


class Session:
    def __init__(self, sid: str, title: str, kind: str, cwd: str, argv: list[str], env: dict, tip: str = "") -> None:
        self.id = sid
        self.title = title
        self.kind = kind
        self.cwd = cwd
        self.argv = argv
        self.env = env
        self.tip = tip
        self.proc = None
        self.chunks: deque[str] = deque()
        self.size = 0
        self.total = 0
        self.alive = False
        self.code: int | None = None
        self.gen = 0
        self.cols = 100
        self.rows = 30
        self.lock = threading.Lock()
        self.subscribers: set[asyncio.Queue] = set()
        self.prepare = None
        self.on_exit: list = []
        self.on_close: list = []

    def describe(self) -> dict:
        record = {"id": self.id, "title": self.title, "alive": self.alive, "kind": self.kind}
        if self.tip:
            record["tip"] = self.tip
        return record

    def keep(self, text: str) -> int:
        with self.lock:
            self.chunks.append(text)
            self.size += len(text)
            self.total += len(text)
            while self.size > SCROLLBACK and len(self.chunks) > 1:
                self.size -= len(self.chunks.popleft())
            return self.total

    def snapshot(self) -> tuple[str, int]:
        with self.lock:
            return "".join(self.chunks), self.total


SESSIONS: dict[str, Session] = {}
_tickets: dict[str, tuple[str, float]] = {}
_tickets_lock = threading.Lock()
_loop: asyncio.AbstractEventLoop | None = None


def bind(loop: asyncio.AbstractEventLoop | None) -> None:
    global _loop
    _loop = loop


def available() -> bool:
    return PtyProcess is not None


def _deliver(session: Session, message: tuple) -> None:
    for queue in list(session.subscribers):
        if message[0] == "closed" or queue.qsize() < QUEUE_LIMIT:
            queue.put_nowait(message)


def _send(session: Session, message: tuple) -> None:
    if _loop is not None and not _loop.is_closed():
        _loop.call_soon_threadsafe(_deliver, session, message)


def _exit_code(proc) -> int | None:
    for _ in range(50):
        try:
            if not proc.isalive():
                break
        except Exception:
            break
        time.sleep(0.02)
    try:
        if getattr(proc, "signalstatus", None) is not None:
            return None
        code = proc.exitstatus
        return int(code) if code is not None else None
    except Exception:
        return None


def _pump(session: Session, proc, gen: int) -> None:
    while True:
        try:
            text = proc.read(65536)
        except (EOFError, OSError):
            break
        if session.gen != gen:
            return
        if text:
            _send(session, ("data", session.keep(text), text))
    if session.gen != gen:
        return
    session.code = _exit_code(proc)
    session.alive = False
    for done in list(session.on_exit):
        try:
            done()
        except Exception:
            log.exception("terminal %s: an exit step failed", session.id)
    _send(session, ("exit", session.code))


def _start(session: Session) -> None:
    if PtyProcess is None:
        raise RuntimeError("no-pty")
    if session.prepare is not None:
        session.prepare()
    proc = PtyProcess.spawn(session.argv, cwd=session.cwd, env=session.env, dimensions=(session.rows, session.cols))
    if hasattr(proc, "decoder"):
        proc.decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    session.proc = proc
    session.code = None
    session.alive = True
    threading.Thread(target=_pump, args=(session, proc, session.gen), name=f"pty-{session.id}-{session.gen}", daemon=True).start()


def _stop(proc) -> None:
    if proc is None:
        return
    try:
        proc.terminate(force=True)
    except Exception:
        pass
    try:
        proc.close()
    except Exception:
        pass


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def scrubbed_env(base: dict | None = None) -> dict:
    source = dict(os.environ if base is None else base)
    out = {}
    for name, value in source.items():
        upper = name.upper()
        if upper in SECRET_NAMES or upper.startswith("FORMPUBLISHER_"):
            continue
        out[name] = value
    out["TERM"] = "xterm-256color"
    out["COLORTERM"] = "truecolor"
    out["FORMPUBLISHER_TERMINAL"] = "1"
    out["FORMPUBLISHER_PORT"] = str(paths.port())
    out["FORMPUBLISHER_HOME"] = str(paths.home())
    return out


def login_shell() -> list[str]:
    if os.name == "nt":
        return [os.environ.get("COMSPEC", "cmd.exe")]
    return [os.environ.get("SHELL") or shutil.which("bash") or "/bin/sh", "-l"]


def open_session(kind: str, title: str, cwd: str, argv: list[str], env: dict, cols: int, rows: int, tip: str = "",
                 sid: str | None = None, prepare=None, on_exit: list | None = None, on_close: list | None = None) -> Session:
    session = Session(sid or new_id(), title, kind, cwd, argv, env, tip)
    session.cols, session.rows = clamp(cols, rows)
    session.prepare = prepare
    session.on_exit = list(on_exit or [])
    session.on_close = list(on_close or [])
    _start(session)
    SESSIONS[session.id] = session
    return session


def open_shell(cols: int, rows: int) -> Session:
    shells = sum(1 for s in SESSIONS.values() if s.kind == "shell")
    where = str(Path.home())
    return open_session("shell", f"Terminal {shells + 1}", where, login_shell(), scrubbed_env(), cols, rows, where)


def get(sid: str) -> Session:
    session = SESSIONS.get(sid)
    if session is None:
        raise KeyError(sid)
    return session


def restart(sid: str) -> Session:
    session = get(sid)
    old = session.proc
    session.gen += 1
    _stop(old)
    with session.lock:
        session.chunks.clear()
        session.size = 0
    _send(session, ("reset",))
    _start(session)
    return session


def write(sid: str, data: str) -> None:
    session = SESSIONS.get(sid)
    if session is not None and session.alive and session.proc is not None:
        try:
            session.proc.write(data)
        except (OSError, EOFError):
            pass


def resize(sid: str, cols, rows) -> None:
    session = get(sid)
    session.cols, session.rows = clamp(cols, rows)
    if session.alive and session.proc is not None:
        try:
            session.proc.setwinsize(session.rows, session.cols)
        except Exception:
            pass


def close(sid: str) -> None:
    session = SESSIONS.pop(sid, None)
    if session is None:
        return
    session.gen += 1
    _stop(session.proc)
    session.alive = False
    for done in list(session.on_close):
        try:
            done()
        except Exception:
            log.exception("terminal %s: a close step failed", sid)
    _send(session, ("closed",))


def close_all() -> None:
    for sid in list(SESSIONS):
        close(sid)


def listing() -> list[dict]:
    return [s.describe() for s in SESSIONS.values()]


def live_claude() -> Session | None:
    return next((s for s in SESSIONS.values() if s.kind == "claude" and s.alive), None)


def type_into(sid: str, text: str) -> None:
    write(sid, text.replace("\r\n", "\n").replace("\r", "\n") + "\r")


def buy_ticket(sid: str) -> str:
    get(sid)
    ticket = secrets.token_urlsafe(24)
    now = time.monotonic()
    with _tickets_lock:
        for old in [t for t, (_owner, until) in _tickets.items() if until <= now]:
            del _tickets[old]
        _tickets[ticket] = (sid, now + TICKET_SECONDS)
    return ticket


def spend_ticket(ticket: str, sid: str) -> bool:
    if not ticket:
        return False
    with _tickets_lock:
        held = _tickets.pop(ticket, None)
    return held is not None and held[0] == sid and held[1] > time.monotonic()
