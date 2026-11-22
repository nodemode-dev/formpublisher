import importlib
import json
import logging
import os
import pkgutil
import sys
import threading
import time

if sys.stdin is None:
    sys.stdin = open(os.devnull, encoding="utf-8")
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")


def resource_dir() -> str:
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def core_runs(binary: str) -> bool:
    import subprocess

    try:
        done = subprocess.run([binary, "--selfcheck"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return False
    return done.returncode == 0


def selfcheck() -> int:
    info: dict = {"python": sys.version.split()[0]}
    failed = False
    for name in ("fastapi", "uvicorn", "starlette", "pydantic", "multipart", "websockets", "httpx2", "mcp"):
        try:
            module = importlib.import_module(name)
            info[name] = getattr(module, "__version__", "ok")
        except Exception as exc:
            info[name] = f"missing: {exc}"
            failed = True
    try:
        from app import __version__, routers, services
        from app.services import paths

        info["formpublisher"] = __version__
        loaded = []
        for package in (routers, services):
            for module in pkgutil.iter_modules(package.__path__):
                if module.name.startswith("_"):
                    continue
                importlib.import_module(f"{package.__name__}.{module.name}")
                loaded.append(f"{package.__name__.split('.')[-1]}/{module.name}")
        importlib.import_module("app.cli")
        mcp_module = importlib.import_module("app.mcp")
        mcp_module.build()
        import app.main as engine

        info["modules"] = loaded
        info["routers"] = engine.app.state.routers
        info["routerErrors"] = engine.app.state.router_errors
        info["frontend"] = bool(paths.frontend_dist())
        info["demo"] = (paths.resource_dir() / "demo" / "sample-site.zip").is_file()
        from app.services import compile as compiler

        core = compiler.core_binary()
        info["core"] = bool(core) and core_runs(str(core))
        if paths.frozen():
            failed = failed or not info["frontend"] or not info["demo"] or not info["core"]
        failed = failed or bool(info["routerErrors"])
    except Exception as exc:
        info["app"] = f"failed: {exc!r}"
        print(json.dumps(info))
        return 1
    print("OK" if not failed else "FAILED")
    print(json.dumps(info))
    return 1 if failed else 0


def watch_parent() -> None:
    if os.environ.get("FORMPUBLISHER_WATCH_PARENT", "1") == "0":
        return
    from app.services import enginelog, paths

    def leave() -> None:
        paths.remove_engine_file()
        os._exit(0)

    if enginelog.watch_shell(leave) or os.name != "posix":
        return
    parent = os.getppid()
    if parent <= 1:
        return

    def run() -> None:
        while os.getppid() == parent:
            time.sleep(2)
        os._exit(0)

    threading.Thread(target=run, name="formpublisher-parent-watch", daemon=True).start()


def passthrough(module_name: str, argv: list[str]) -> int:
    module = importlib.import_module(module_name)
    result = module.main(argv)
    return int(result or 0)


def serve() -> int:
    bundled = os.path.join(resource_dir(), "frontend_dist")
    if os.path.isdir(bundled):
        os.environ.setdefault("FORMPUBLISHER_DIST", bundled)
    import uvicorn

    from app.main import app as fastapi_app
    from app.services import enginelog, paths, window_key

    window_key.announce()
    host = os.environ.get("FORMPUBLISHER_HOST", "127.0.0.1")
    server = uvicorn.Server(uvicorn.Config(fastapi_app, host=host, port=paths.port(), log_level="info"))
    kept = enginelog.attach()
    logging.getLogger("formpublisher").info("engine %s starting on %s:%s, log %s", fastapi_app.version, host, paths.port(), kept)
    watch_parent()
    server.run()
    return 0 if server.started else 3


def main() -> int:
    args = sys.argv[1:]
    if "--version" in args:
        from app import __version__

        print(f"formpublisher {__version__}")
        return 0
    if "--selfcheck" in args:
        return selfcheck()
    if args and args[0] == "cli":
        return passthrough("app.cli", args[1:])
    if args and args[0] == "mcp":
        return passthrough("app.mcp", args[1:])
    return serve()


if __name__ == "__main__":
    import multiprocessing

    multiprocessing.freeze_support()
    sys.exit(main())
