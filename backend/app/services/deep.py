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
LCP_SETTLE_MS = 1000
LCP_GOOD_MS = 2500
LCP_POOR_MS = 4000
CONTRAST_CAP = 400
CONTRAST_LIST = 3
CONTRAST_ROUNDS = 6
CHROME_PATHS = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
)
INIT_SCRIPT = (
    "window.__fpcls=0;try{new PerformanceObserver(function(l){l.getEntries().forEach(function(e){"
    "if(!e.hadRecentInput)window.__fpcls+=e.value})}).observe({type:'layout-shift',buffered:true})}catch(e){}"
    "window.__fplcp=null;try{new PerformanceObserver(function(l){var a=l.getEntries();if(!a.length)return;"
    "var e=a[a.length-1],n=e.element,d='';if(n){d=n.tagName.toLowerCase();if(n.id)d+='#'+n.id;"
    "else if(n.classList&&n.classList.length)d+='.'+Array.prototype.slice.call(n.classList,0,2).join('.')}"
    "window.__fplcp={t:e.startTime,el:d,url:e.url||''}}).observe({type:'largest-contentful-paint',buffered:true})}catch(e){}"
)
CONTRAST_SCRIPT = r"""
async ([cap, rounds]) => {
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = 1;
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  const colors = new Map();
  const parse = (value) => {
    if (colors.has(value)) return colors.get(value);
    const m = /^rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:\s*[,/]\s*([\d.]+)(%?))?\s*\)$/.exec(value);
    let out;
    if (m) {
      const a = m[4] === undefined ? 1 : parseFloat(m[4]) / (m[5] ? 100 : 1);
      out = [+m[1], +m[2], +m[3], a];
    } else {
      ctx.clearRect(0, 0, 1, 1);
      ctx.fillStyle = 'rgba(0,0,0,0)';
      ctx.fillStyle = value;
      ctx.fillRect(0, 0, 1, 1);
      const d = ctx.getImageData(0, 0, 1, 1).data;
      out = [d[0], d[1], d[2], d[3] / 255];
    }
    colors.set(value, out);
    return out;
  };
  const layer = (c) => [c[0] / 255 * c[3], c[1] / 255 * c[3], c[2] / 255 * c[3], c[3]];
  const over = (top, under) => top.map((v, i) => v + under[i] * (1 - top[3]));
  const fade = (c, o) => c.map((v) => v * o);
  const lum = (c) => {
    const ch = c.slice(0, 3).map((v) => (v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4)));
    return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2];
  };
  const hex = (c) => '#' + c.slice(0, 3).map((v) => Math.round(Math.min(1, Math.max(0, v)) * 255).toString(16).padStart(2, '0')).join('');
  const moving = new Set();
  const levels = new Map();
  const watch = () => {
    moving.clear();
    levels.clear();
    for (const a of document.getAnimations()) {
      const fx = a.effect;
      if (a.playState !== 'running' || !fx || !fx.target) continue;
      const props = (fx.getKeyframes ? fx.getKeyframes() : []).flatMap((k) => Object.keys(k));
      if (a.transitionProperty) props.push(a.transitionProperty);
      if (props.some((p) => /opacity|color|background|filter|visibility|^all$/i.test(p))) moving.add(fx.target);
    }
  };
  watch();
  const painted = (s) => s.content !== 'none' && s.content !== 'normal' && (s.position === 'absolute' || s.position === 'fixed') && (s.backgroundImage !== 'none' || parse(s.backgroundColor)[3] > 0);
  const level = (node) => {
    if (levels.has(node)) return levels.get(node);
    const s = getComputedStyle(node);
    const info = {
      bg: layer(parse(s.backgroundColor)),
      image: s.backgroundImage !== 'none',
      opacity: parseFloat(s.opacity),
      hides: (s.overflowX !== 'visible' || s.overflowY !== 'visible' || s.clipPath !== 'none' || s.clip !== 'auto') && ((r) => r.width * r.height < 4)(node.getBoundingClientRect()),
      odd: s.filter !== 'none' || s.mixBlendMode !== 'normal' || painted(getComputedStyle(node, '::before')) || painted(getComputedStyle(node, '::after')),
    };
    levels.set(node, info);
    return info;
  };
  const describe = (node) => {
    const parts = [];
    for (let k = 0; node && node.nodeType === 1 && k < 3; k += 1, node = node.parentElement) {
      let s = node.tagName.toLowerCase();
      if (node.id) { parts.unshift(s + '#' + node.id); break; }
      const c = Array.from(node.classList).slice(0, 2);
      if (c.length) s += '.' + c.join('.');
      parts.unshift(s);
      if (node === document.body) break;
    }
    return parts.join(' > ');
  };
  const media = /^(IMG|VIDEO|CANVAS|PICTURE|IFRAME|OBJECT|EMBED)$/;
  const skipTags = /^(SCRIPT|STYLE|NOSCRIPT|TEMPLATE|TITLE|OPTION|SELECT)$/;
  const seen = new Set();
  const items = [];
  const walker = document.createTreeWalker(document.body || document.documentElement, NodeFilter.SHOW_TEXT);
  let truncated = false;
  for (let t = walker.nextNode(); t; t = walker.nextNode()) {
    const el = t.parentElement;
    if (!el || seen.has(el) || !t.nodeValue.trim()) continue;
    if (items.length >= cap) { truncated = true; break; }
    seen.add(el);
    items.push([el, t]);
  }
  const textRect = (t) => {
    const range = document.createRange();
    range.selectNodeContents(t);
    return Array.from(range.getClientRects()).find((r) => r.width * r.height >= 4);
  };
  const inView = (t) => {
    const r = textRect(t);
    return !!r && r.top + r.height / 2 >= 0 && r.top + r.height / 2 < window.innerHeight;
  };
  const judge = (el, t, scroll) => {
    const SKIP = { k: 'skip' }, UNMEASURED = { k: 'unmeasured' };
    if (skipTags.test(el.tagName) || el instanceof SVGElement || el.closest(':disabled, [aria-disabled="true"]')) return SKIP;
    if (el.checkVisibility && !el.checkVisibility({ opacityProperty: true, visibilityProperty: true, contentVisibilityAuto: true })) return SKIP;
    const st = getComputedStyle(el);
    let rect = textRect(t);
    if (!rect) return SKIP;
    const fill = parse(st.webkitTextFillColor || st.color);
    if (fill[3] === 0) return SKIP;
    if (rect.bottom + window.scrollY <= 0 || rect.right + window.scrollX <= 0 || rect.left + window.scrollX >= document.documentElement.scrollWidth) return SKIP;
    const cy = rect.top + rect.height / 2;
    if (scroll && (cy < 0 || cy >= window.innerHeight)) {
      el.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
      rect = textRect(t);
      if (!rect) return SKIP;
    }
    const x = rect.left + Math.min(rect.width, 8) / 2, y = rect.top + rect.height / 2;
    if (x < 0 || x >= window.innerWidth || y < 0 || y >= window.innerHeight) return UNMEASURED;
    let hidden = false;
    for (let n = el; n && n.nodeType === 1 && !hidden; n = n.parentElement) hidden = level(n).hides;
    if (hidden) return SKIP;
    let stack;
    if (st.pointerEvents === 'none') {
      const was = el.style.getPropertyValue('pointer-events'), how = el.style.getPropertyPriority('pointer-events');
      el.style.setProperty('pointer-events', 'auto', 'important');
      stack = document.elementsFromPoint(x, y);
      el.style.setProperty('pointer-events', was, how);
    } else {
      stack = document.elementsFromPoint(x, y);
    }
    const at = stack.indexOf(el);
    let blocked = at < 0;
    if (!blocked) {
      for (const n of stack.slice(at + 1)) {
        if (n.contains(el)) continue;
        const info = level(n);
        if (media.test(n.tagName) || n instanceof SVGElement || info.image || info.bg[3] > 0) { blocked = true; break; }
      }
    }
    if (blocked) return UNMEASURED;
    let text = layer(fill), back = [0, 0, 0, 0];
    for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
      const info = level(n);
      if (moving.has(n) || (back[3] < 0.999 && (info.image || info.odd))) return UNMEASURED;
      text = over(text, info.bg);
      back = over(back, info.bg);
      if (info.opacity < 1) { text = fade(text, info.opacity); back = fade(back, info.opacity); }
    }
    text = over(text, [1, 1, 1, 1]);
    back = over(back, [1, 1, 1, 1]);
    const a = lum(text), b = lum(back);
    const ratio = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
    const size = parseFloat(st.fontSize), weight = parseInt(st.fontWeight, 10) || 400;
    const large = size >= 24 || (size >= 18.66 && weight >= 700);
    const need = large ? 3 : 4.5;
    if (ratio >= need) return { k: 'ok' };
    if (st.textShadow !== 'none' || parseFloat(st.webkitTextStrokeWidth) > 0) return UNMEASURED;
    return { k: 'fail', what: describe(el), text: el.textContent.replace(/\s+/g, ' ').trim().slice(0, 40), ratio, need, fg: hex(text), bg: hex(back), large, size };
  };
  const tally = { skip: 0, unmeasured: 0, ok: 0, fail: 0 };
  let open = [];
  const startX = window.scrollX, startY = window.scrollY;
  for (const [el, t] of items) {
    const r = judge(el, t, true);
    if (r.k === 'fail') open.push({ el, t, x: window.scrollX, y: window.scrollY });
    else tally[r.k] += 1;
  }
  const settle = (ms) => new Promise((done) => setTimeout(done, ms));
  const fails = [];
  for (let round = 0; open.length && round < rounds; round += 1) {
    window.scrollTo({ left: open[0].x, top: open[0].y, behavior: 'instant' });
    await settle(400);
    const here = open.filter((f, i) => i === 0 || inView(f.t));
    watch();
    const before = here.map((f) => judge(f.el, f.t, false));
    await settle(150);
    watch();
    here.forEach((f, i) => {
      const p = before[i], q = judge(f.el, f.t, false);
      const steady = p.k === q.k && (q.k !== 'fail' || Math.abs(p.ratio - q.ratio) < 0.01);
      const k = steady ? q.k : 'unmeasured';
      if (k === 'fail') fails.push(q);
      else tally[k] += 1;
    });
    open = open.filter((f) => !here.includes(f));
  }
  for (const f of open) {
    const r = judge(f.el, f.t, true);
    if (r.k === 'fail') fails.push(r);
    else tally[r.k] += 1;
  }
  window.scrollTo({ left: startX, top: startY, behavior: 'instant' });
  fails.sort((p, q) => p.ratio / p.need - q.ratio / q.need);
  return { checked: tally.ok + fails.length, skipped: tally.skip, unmeasured: tally.unmeasured, truncated, failing: fails.length, worst: fails.slice(0, 5) };
}
"""
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
    return {"problems": [problem], "thumbs": {}, "widths": [], "motion": "auto", "routes": 0, "measures": [], "available": False}


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


def first_line(exc: Exception) -> str:
    text = str(exc).strip()
    return text.splitlines()[0][:200] if text else type(exc).__name__


def skipped(collector: Collector, record: dict, what: str, exc: Exception) -> None:
    reason = first_line(exc)
    record["notes"].append(f"{what[0].upper()}{what[1:]} was not measured: {reason}")
    collector.add(
        "deep.skipped", "info", what,
        f"The {what} could not be measured on {collector.where()}: {reason}.",
        "Run the deep check again; the rest of the page was checked.",
    )


def read_lcp(page, collector: Collector, record: dict) -> None:
    data = page.evaluate("()=>window.__fplcp")
    if not data:
        record["notes"].append("No largest contentful paint was reported before load.")
        return
    ms = float(data.get("t") or 0)
    seconds = round(ms / 1000, 2)
    record["lcp"] = seconds
    record["lcpElement"] = data.get("el") or ""
    if ms <= LCP_GOOD_MS:
        return
    element = f"; the largest element is {data['el']}" if data.get("el") else ""
    collector.add(
        "deep.lcp", "error" if ms > LCP_POOR_MS else "warning", "lcp",
        f"The largest contentful paint came after {seconds:.2f} s on {collector.where()} (a lab value from this computer, with the CPU and network slowed){element}.",
        "Make the largest image or text block show sooner: make the file smaller, do not lazy-load it, and do not add it with a script. Good is 2.5 s or less. Responsiveness to input (INP) needs a real visitor and is not measured here.",
        data.get("url") or None,
    )


def read_contrast(page, collector: Collector, record: dict) -> None:
    data = page.evaluate(CONTRAST_SCRIPT, [CONTRAST_CAP, CONTRAST_ROUNDS])
    record["contrast"] = {k: data[k] for k in ("checked", "failing", "unmeasured", "truncated")}
    if not data["failing"]:
        return
    parts = [
        f"{item['what']} \"{item['text']}\" {item['ratio']:.2f}:1, {item['fg']} on {item['bg']} (needs {item['need']:g}:1)"
        for item in data["worst"][:CONTRAST_LIST]
    ]
    more = data["failing"] - len(parts)
    tail = f"; and {more} more" if more > 0 else ""
    count = data["unmeasured"]
    note = ""
    if count:
        note = f" {count} text {'element' if count == 1 else 'elements'} over images, gradients, blending or moving content {'was' if count == 1 else 'were'} not measured."
    collector.add(
        "a11y.contrast", "warning", "contrast",
        f"Text contrast is too low on {collector.where()}: {'; '.join(parts)}{tail}.{note}",
        "Darken the text or lighten its background until normal text reaches 4.5:1 and large text (24 px, or 18.66 px bold) reaches 3:1.",
    )


def measure(browser, origin: str, route: str, width: int, motion: str) -> tuple[list[dict], dict]:
    height = HEIGHTS.get(width, 900 if width >= 900 else 844)
    collector = Collector(route, width, origin)
    record = {"route": route, "width": width, "cls": None, "lcp": None, "lcpElement": "", "contrast": None, "notes": []}
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
            return collector.problems, record
        page.wait_for_timeout(LCP_SETTLE_MS)
        try:
            read_lcp(page, collector, record)
        except Exception as exc:
            skipped(collector, record, "largest contentful paint", exc)
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
        record["cls"] = cls
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
        try:
            read_contrast(page, collector, record)
        except Exception as exc:
            skipped(collector, record, "text contrast", exc)
    finally:
        try:
            context.close()
        except Exception:
            pass
    return collector.problems, record


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
    measures: list[dict] = []
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
                                found, record = measure(browser, origin, route, width, motion)
                                problems.extend(found)
                                measures.append(record)
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
    return {
        "problems": problems, "thumbs": thumbs, "widths": widths, "motion": motion, "routes": len(routes),
        "measures": measures, "inp": "not measured: INP needs a real visitor's input", "available": True,
    }
