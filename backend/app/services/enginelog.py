import logging
import os
import sys
import threading
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.services import paths

LOG_FOLDER = "logs"
LOG_NAME = "engine.log"
LOG_BYTES = 1_048_576
LOG_KEPT = 3
SHELL_ENV = "FORMPUBLISHER_SHELL_PID"
POLL = 2.0
SYNCHRONIZE = 0x00100000
WAIT_TIMEOUT = 0x102
ACCESS_DENIED = 5
LOGGERS = ("", "uvicorn", "uvicorn.access")

_attached: Path | None = None


def log_file() -> Path:
    return paths.home() / LOG_FOLDER / LOG_NAME


def attach() -> Path | None:
    global _attached
    if _attached is not None:
        return _attached
    target = log_file()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(target, maxBytes=LOG_BYTES, backupCount=LOG_KEPT, encoding="utf-8", delay=True)
    except OSError:
        return None
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    handler.setLevel(logging.INFO)
    for name in LOGGERS:
        logger = logging.getLogger(name)
        logger.addHandler(handler)
        if name == "":
            logger.setLevel(logging.INFO)
    _attached = target
    return target


def attached() -> Path | None:
    return _attached


def shell_pid() -> int:
    raw = os.environ.get(SHELL_ENV, "").strip()
    return int(raw) if raw.isdecimal() else 0


def _alive_windows(pid: int) -> bool:
    import ctypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.OpenProcess.argtypes = (ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32)
    kernel.WaitForSingleObject.restype = ctypes.c_uint32
    kernel.WaitForSingleObject.argtypes = (ctypes.c_void_p, ctypes.c_uint32)
    kernel.CloseHandle.argtypes = (ctypes.c_void_p,)
    handle = kernel.OpenProcess(SYNCHRONIZE, 0, pid)
    if not handle:
        return ctypes.get_last_error() == ACCESS_DENIED
    try:
        return kernel.WaitForSingleObject(handle, 0) == WAIT_TIMEOUT
    finally:
        kernel.CloseHandle(handle)


def _alive_posix(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def alive(pid: int) -> bool:
    return _alive_windows(pid) if sys.platform == "win32" else _alive_posix(pid)


def watch_shell(leave) -> bool:
    shell = shell_pid()
    if shell <= 1:
        return False

    def run() -> None:
        while alive(shell):
            time.sleep(POLL)
        logging.getLogger("formpublisher").info("the app that started this engine is gone (process %s), stopping", shell)
        leave()

    threading.Thread(target=run, name="formpublisher-shell-watch", daemon=True).start()
    return True
