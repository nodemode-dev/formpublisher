import asyncio
import os
import sys
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

from app import host as site_host
from app.services import checks, paths, settings

CPU_RATE = 4
LATENCY_MS = 150
BANDWIDTH = 204800
HEIGHTS = {1440: 900, 390: 844}
THUMB_WIDTH = 320
THUMB_VIEW = (1440, 900)
SCROLL_STEPS = 8
SCROLL_PAUSE_MS = 300
GOTO_TIMEOUT_MS = 120000
CHROME_PATHS = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
)
INIT_SCRIPT = (
    "window.__fpcls=0;try{new PerformanceObserver(function(l){l.getEntries().forEach(function(e){"
    "if(!e.hadRecentInput)window.__fpcls+=e.value})}).observe({type:'layout-shift',buffered:true})}catch(e){}"
)
INSTALL_FIX = "Run ./formpublisher_oc_install to install the deep check requirements, and install Google Chrome."
BROWSER_FIX = "Install Google Chrome or Microsoft Edge, or set the browser's path in Preferences, then run the deep check again."


ENGINE_LOOP: asyncio.AbstractEventLoop | None = None


def attach(loop: asyncio.AbstractEventLoop | None) -> None:
    """Record the engine's event loop so deep runs on worker threads can start the revision host on it."""
    global ENGINE_LOOP
    ENGINE_LOOP = loop


class LocalServer:
    """Serves a revision through host.serve_revision on the engine's event loop while the deep run works on a worker thread; without a running engine loop it uses a private one."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.loop = ENGINE_LOOP if ENGINE_LOOP is not None and ENGINE_LOOP.is_running() else None
        self.own = self.loop is None
        self.thread = None
        self.stop = None
        self.origin = ""

    def __enter__(self):
        if self.own:
            self.loop = asyncio.new_event_loop()
            self.thread = threading.Thread(target=self.loop.run_forever, name="formpublisher-deep-host", daemon=True)
            self.thread.start()
        self.origin, self.stop = asyncio.run_coroutine_threadsafe(site_host.serve_revision(self.root), self.loop).result(30)
        return self

    def __exit__(self, *_exc):
        try:
            if self.stop is not None:
                asyncio.run_coroutine_threadsafe(self.stop(), self.loop).result(15)
        finally:
            if self.own:
                self.loop.call_soon_threadsafe(self.loop.stop)
                self.thread.join(5)
                self.loop.close()


def chrome_path() -> str | None:
    configured = settings.value("checks.chromePath")
    if isinstance(configured, str) and configured.strip() and Path(configured.strip()).is_file():
        return configured.strip()
    return None


def launch(playwright):
    errors = []
    configured = chrome_path()
    if configured:
        try:
            return playwright.chromium.launch(executable_path=configured, headless=True)
        except Exception as exc:
            errors.append(str(exc))
    for channel in ("chrome", "msedge"):
        try:
            return playwright.chromium.launch(channel=channel, headless=True)
        except Exception as exc:
            errors.append(str(exc))
    candidates = list(CHROME_PATHS)
    program_files = os.environ.get("ProgramFiles")
    if program_files:
        candidates.append(str(Path(program_files) / "Google" / "Chrome" / "Application" / "chrome.exe"))
    for candidate in candidates:
        if Path(candidate).is_file():
            try:
                return playwright.chromium.launch(executable_path=candidate, headless=True)
            except Exception as exc:
                errors.append(str(exc))
    raise RuntimeError(errors[-1] if errors else "Chrome was not found")


def unavailable(reason: str) -> dict:
    problem = {
        "id": "deep:deep.unavailable:/:0",
        "tier": "deep",
        "severity": "info",
        "code": "deep.unavailable",
        "route": "/",
        "message": f"Deep checks are not available on this computer. {reason}".strip(),
        "fix": BROWSER_FIX if paths.frozen() else INSTALL_FIX,
    }
    return {"problems": [problem], "thumbs": {}, "widths": [], "motion": "auto", "routes": 0, "available": False}


class Collector:
    def __init__(self, route: str, width: int, origin: str) -> None:
        self.route = route
        self.width = width
        self.host = urlsplit(origin).netloc
        self.problems: list[dict] = []
        self.keys: set[str] = set()

    def add(self, code: str, severity: str, key: str, message: str, fix: str, url: str | None = None) -> None:
        marker = f"{code}|{key}"
        if marker in self.keys:
            return
        self.keys.add(marker)
        short = self.route.lstrip("/") or "/"
        item = {
            "id": f"deep:{code}:{short}:{self.width}:{checks.route_hash(key.replace(self.host, 'host'))[:8]}",
            "tier": "deep",
            "severity": severity,
            "code": code,
            "route": self.route,
            "message": message,
            "fix": fix,
        }
        if url:
            item["url"] = url
        self.problems.append(item)

    def where(self) -> str:
        return f"{self.route} at {self.width} px"

    def on_console(self, message) -> None:
        if message.type != "error":
            return
        text = message.text or ""
        if text.startswith("Failed to load resource"):
            return
        self.add(
            "deep.console", "error", text,
            f"Console error on {self.where()}: {text[:400]}",
            "Open the page in a browser, read the console, and fix the script that logs the error.",
        )

    def on_pageerror(self, error) -> None:
        text = str(getattr(error, "message", error) or error)
        self.add(
            "deep.pageerror", "error", text,
            f"Script error on {self.where()}: {text[:400]}",
            "Fix the script error; parts of the page may not work for visitors.",
        )

    def foreign(self, url: str) -> bool:
        parts = urlsplit(url)
        return parts.scheme in ("http", "https") and parts.netloc != self.host

    def on_failed(self, request) -> None:
        url = request.url
        failure = request.failure or ""
        if "ERR_ABORTED" in str(failure) or url.startswith(("data:", "blob:")):
            return
        if self.foreign(url):
            return self.on_foreign(url)
        self.add(
            "deep.request", "error", url,
            f"A request failed on {self.where()}: {url} ({failure or 'no response'}).",
            "Add the missing file or correct its address.", url,
        )

    def on_response(self, response) -> None:
        url = response.url
        if self.foreign(url):
            return
        if response.status >= 400:
            self.add(
                "deep.request", "error", url,
                f"A request failed on {self.where()}: {url} (status {response.status}).",
                "Add the missing file or correct its address.", url,
            )

    def on_request(self, request) -> None:
        if self.foreign(request.url):
            self.on_foreign(request.url)

    def on_foreign(self, url: str) -> None:
        self.add(
            "deep.external", "warning", url,
            f"The page on {self.where()} requested {url} from another host.",
            "Copy the file into the site and link to the local copy.", url,
        )


def measure(browser, origin: str, route: str, width: int, motion: str) -> list[dict]:
    height = HEIGHTS.get(width, 900 if width >= 900 else 844)
    collector = Collector(route, width, origin)
    context = browser.new_context(
        viewport={"width": width, "height": height},
        reduced_motion="reduce" if motion == "reduce" else "no-preference",
        service_workers="block",
    )
    try:
        context.add_init_script(INIT_SCRIPT)
        page = context.new_page()
        page.on("console", collector.on_console)
        page.on("pageerror", collector.on_pageerror)
        page.on("requestfailed", collector.on_failed)
        page.on("response", collector.on_response)
        page.on("request", collector.on_request)
        try:
            session = context.new_cdp_session(page)
            session.send("Emulation.setCPUThrottlingRate", {"rate": CPU_RATE})
            session.send("Network.enable")
            session.send(
                "Network.emulateNetworkConditions",
                {"offline": False, "latency": LATENCY_MS, "downloadThroughput": BANDWIDTH, "uploadThroughput": BANDWIDTH},
            )
        except Exception:
            pass
        try:
            page.goto(origin + route, wait_until="load", timeout=GOTO_TIMEOUT_MS)
        except Exception as exc:
            collector.add(
                "deep.request", "error", "goto",
                f"The page did not load on {collector.where()}: {str(exc).splitlines()[0][:300]}",
                "Check that the page opens in a browser and that its files are not too large.",
            )
            return collector.problems
        for step in range(1, SCROLL_STEPS + 1):
            page.evaluate(
                "([s,n])=>{var m=Math.max(0,document.documentElement.scrollHeight-window.innerHeight);window.scrollTo(0,m*s/n)}",
                [step, SCROLL_STEPS],
            )
            page.wait_for_timeout(SCROLL_PAUSE_MS)
        page.evaluate("window.scrollTo(0,0)")
        page.wait_for_timeout(SCROLL_PAUSE_MS)
        data = page.evaluate(
            "()=>({cls:window.__fpcls||0,sw:document.documentElement.scrollWidth,cw:document.documentElement.clientWidth})"
        )
        cls = round(float(data["cls"]), 4)
        if cls > 0:
            severe = cls >= 0.1
            collector.add(
                "deep.cls", "error" if severe else "warning", "cls",
                f"Layout shifted by {cls:g} on {collector.where()}.",
                "Set width and height on images and reserve space for content that loads late.",
            )
        if data["sw"] > data["cw"]:
            collector.add(
                "deep.overflow", "error", "overflow",
                f"The page is {data['sw']} px wide in a {data['cw']} px window on {collector.where()}.",
                "Find the element wider than the screen and let it wrap or scale down.",
            )
    finally:
        try:
            context.close()
        except Exception:
            pass
    return collector.problems


def thumbnail(browser, origin: str, route: str, target: Path) -> bool:
    context = browser.new_context(
        viewport={"width": THUMB_VIEW[0], "height": THUMB_VIEW[1]},
        device_scale_factor=THUMB_WIDTH / THUMB_VIEW[0],
        service_workers="block",
    )
    try:
        page = context.new_page()
        page.goto(origin + route, wait_until="load", timeout=30000)
        page.wait_for_timeout(400)
        data = page.screenshot(type="png", animations="disabled")
        tmp = target.with_suffix(".png.tmp")
        tmp.write_bytes(data)
        os.replace(tmp, target)
        return True
    except Exception:
        return False
    finally:
        try:
            context.close()
        except Exception:
            pass


def execute(site: str, revision: str, root: Path, routes: list[str], widths: list[int], motion: str, progress=None) -> dict:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        return unavailable(f"Playwright is not installed ({type(exc).__name__}).")
    thumbs_dir = checks.checks_dir(site, revision) / "thumbs"
    thumbs_dir.mkdir(parents=True, exist_ok=True)
    for old in thumbs_dir.glob("*.png"):
        old.unlink(missing_ok=True)
    problems: list[dict] = []
    thumbs: dict[str, str] = {}
    total = len(routes) * len(widths)
    done = 0
    try:
        with sync_playwright() as pw:
            try:
                browser = launch(pw)
            except Exception as exc:
                line = str(exc).strip().splitlines()[0][:200] if str(exc).strip() else "Chrome was not found."
                return unavailable(f"Chrome could not be started: {line}")
            try:
                with LocalServer(root) as server:
                    origin = server.origin
                    for route in routes:
                        for width in widths:
                            if progress:
                                progress(done, total, route, width)
                            try:
                                problems.extend(measure(browser, origin, route, width, motion))
                            except Exception as exc:
                                problems.append({
                                    "id": f"deep:deep.request:{route.lstrip('/') or '/'}:{width}:run",
                                    "tier": "deep",
                                    "severity": "error",
                                    "code": "deep.request",
                                    "route": route,
                                    "message": f"The check could not finish on {route} at {width} px: {str(exc).splitlines()[0][:300] if str(exc) else type(exc).__name__}.",
                                    "fix": "Run the check again; if it keeps failing, open the page in a browser to see what stops it.",
                                })
                            done += 1
                        name = checks.route_hash(route)
                        if thumbnail(browser, origin, route, thumbs_dir / f"{name}.png"):
                            thumbs[route] = name
                    if progress:
                        progress(done, total, "", 0)
            finally:
                try:
                    browser.close()
                except Exception:
                    pass
    except Exception as exc:
        print(f"deep run failed: {exc!r}", file=sys.stderr)
        return unavailable(f"The browser run stopped early ({type(exc).__name__}).")
    problems.sort(key=lambda p: (p["route"], p["code"], p["id"]))
    return {"problems": problems, "thumbs": thumbs, "widths": widths, "motion": motion, "routes": len(routes), "available": True}
