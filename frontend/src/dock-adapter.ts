import { ApiError } from './api';
import type { DockAdapter, DockAgentStatus, DockChannel, DockKind, DockTerminal, PtyKind } from './dock/adapter';
import type { DockState } from './dock/state';
import { t } from './i18n';

export type OwnKind = 'antigravity';
type Offered = DockKind | OwnKind;
type Program = 'claude' | 'codex' | 'cursor' | 'antigravity';

export const DOCK_KEY = 'formpublisher.agentDock';
export const DOCK_SIZES = { minHeight: 120, maxHeightShare: 0.7, defaultHeight: 280, minWidth: 320, maxWidthShare: 0.6, defaultWidth: 440 };
const RIGHT_FROM = 960;
const PROGRAMS: readonly Program[] = ['claude', 'codex', 'cursor', 'antigravity'];
const OFFERS: readonly Offered[] = ['shell', 'claude', 'codex', 'cursor', 'antigravity'];
const KINDS: ReadonlyArray<PtyKind | OwnKind> = ['shell', 'claude', 'codex', 'cursor', 'agent', 'antigravity'];
const WORDS = { app: 'formpublisher', noun: 'site', start: './formpublisher boot' };
const EXAMPLE = 'check the site and fix what the checks find';
const NO_PTY = 'This computer gives the engine no terminal, so terminal tabs cannot open here.';
const MISSING_ROUTE = /^(Not Found|Method Not Allowed)$/i;

export interface DockHost {
  isChord(event: KeyboardEvent): boolean;
  chordLabel(): string;
  passKey(event: KeyboardEvent): boolean;
  openSettings(): void;
  tabsChanged(): void;
}

interface RawTerminal { id?: unknown; title?: unknown; alive?: unknown; kind?: unknown; tip?: unknown; status?: unknown }
interface Listing { version?: unknown; available?: unknown; terminals?: unknown }

const isObj = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v);
const text = (v: unknown): string => (typeof v === 'string' ? v : '');
const path = (id: string): string => `/api/terminal/${encodeURIComponent(id)}`;

let offered: Offered[] = ['shell', 'claude'];

async function call<T>(url: string, method = 'GET', body?: unknown): Promise<T> {
  let r: Response;
  try {
    r = await fetch(url, body === undefined ? { method } : { method, headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
  } catch {
    throw new ApiError('The engine is not reachable', 0, 'unreachable');
  }
  if (!r.ok) {
    const said = (await r.json().catch(() => ({}))) as { detail?: unknown; code?: unknown };
    const code = text(said.code) || (r.status >= 500 ? 'unreachable' : '');
    throw new ApiError(text(said.detail) || r.statusText || String(r.status), r.status, code);
  }
  return (await r.json()) as T;
}

const missingRoute = (err: unknown): boolean => err instanceof ApiError && (err.status === 405 || (err.status === 404 && MISSING_ROUTE.test(err.message)));

const record = (x: RawTerminal): DockTerminal<OwnKind> => ({
  id: text(x.id),
  title: text(x.title),
  alive: x.alive !== false,
  kind: KINDS.find((k) => k === x.kind) ?? 'shell',
  ...(text(x.tip) ? { tip: text(x.tip) } : {}),
  ...(text(x.status) ? { status: text(x.status) } : {}),
});

function learn(list: Listing, host: DockHost): void {
  const named = Array.isArray(list.available) ? list.available.filter((x): x is string => typeof x === 'string') : [];
  const next = OFFERS.filter((k) => named.includes(k) || (k === 'claude' && named.includes('shell')));
  if (next.length === offered.length && next.every((k, i) => k === offered[i])) return;
  offered = next;
  host.tabsChanged();
}

async function listing(host: DockHost): Promise<Listing> {
  try {
    const list = await call<Listing>('/api/terminal');
    learn(isObj(list) ? list : {}, host);
    return list;
  } catch (err) {
    if (missingRoute(err)) learn({ available: [] }, host);
    throw err;
  }
}

export function reserveDock(): void {
  const html = document.documentElement;
  let s: Partial<DockState> = {};
  try {
    const raw = localStorage.getItem(DOCK_KEY);
    const kept: unknown = raw ? JSON.parse(raw) : null;
    s = isObj(kept) ? kept as Partial<DockState> : {};
  } catch { s = {}; }
  const z = DOCK_SIZES;
  const h = Math.round(Math.max(z.minHeight, Math.min(window.innerHeight * z.maxHeightShare, typeof s.h === 'number' ? s.h : z.defaultHeight)));
  const w = Math.round(Math.max(z.minWidth, Math.min(window.innerWidth * z.maxWidthShare, typeof s.w === 'number' ? s.w : z.defaultWidth)));
  const right = s.side === 'right' && window.innerWidth >= RIGHT_FROM;
  const want: Array<[string, string]> = [['data-ft-dock', s.open === true ? 'open' : 'closed'], ['data-ft-dock-side', right ? 'right' : 'bottom'], ['data-ft-dock-h', String(h)], ['data-ft-dock-w', String(w)]];
  for (const [name, value] of want) if (html.getAttribute(name) !== value) html.setAttribute(name, value);
  const sizes: Array<[string, string]> = [['--ft-dock-size', `${h}px`], ['--ft-dock-wsize', `${w}px`]];
  for (const [name, value] of sizes) if (html.style.getPropertyValue(name) !== value) html.style.setProperty(name, value);
}

function socketChannel(socket: WebSocket): DockChannel {
  let data = (_chunk: string | Uint8Array): void => undefined;
  let exit = (): void => undefined;
  let closed = (): void => undefined;
  socket.binaryType = 'arraybuffer';
  socket.addEventListener('message', (msg) => {
    if (typeof msg.data === 'string') { data(msg.data); return; }
    try { if ((JSON.parse(new TextDecoder().decode(msg.data as ArrayBuffer)) as { type?: unknown }).type === 'exit') exit(); } catch { return; }
  });
  socket.addEventListener('close', () => closed());
  const send = (frame: string): void => {
    if (socket.readyState === WebSocket.OPEN) socket.send(frame);
    else if (socket.readyState === WebSocket.CONNECTING) socket.addEventListener('open', () => socket.send(frame), { once: true });
  };
  return {
    send: (chunk) => send(JSON.stringify({ type: 'input', data: chunk })),
    resize: (cols, rows) => send(JSON.stringify({ type: 'resize', cols, rows })),
    onData: (handler) => { data = handler; },
    onExit: (handler) => { exit = handler; },
    onClose: (handler) => { closed = handler; },
    close: () => socket.close(),
  };
}

export function formpublisherDock(host: DockHost): DockAdapter<OwnKind> {
  void listing(host).catch(() => undefined);
  return {
    words: { ...WORDS, example: t(EXAMPLE), lead: 'Ask Claude Code to work on your site in the line below.' },
    strings: { empty: 'No terminal is open. Start a shell with the plus button, or Claude Code with the agent button.' },
    placement: {
      mode: 'own',
      storage: { key: DOCK_KEY },
      sizes: DOCK_SIZES,
      canDockRight: () => window.innerWidth >= RIGHT_FROM,
    },
    isDockChord: (e) => host.isChord(e),
    chordLabel: () => host.chordLabel(),
    passKey: (e) => host.passKey(e),
    tabs: () => ({ builtin: [...offered] }),
    classes: { iconButton: 'fp-icon-btn', button: 'fp-btn fp-btn-sm', primaryButton: 'fp-btn-primary', input: 'fp-input', select: 'fp-select', note: 'fp-note' },
    t: (_key, english) => t(english.replace(/\{(app|noun|start)\}/g, (_m, name: 'app' | 'noun' | 'start') => WORDS[name])),
    onTheme: (handler) => { document.addEventListener('fp:ui-settings-changed', handler); },
    errors: {
      message: (err) => {
        if (!(err instanceof ApiError) || err.status === 0) return null;
        if (err.code === 'no-pty') return t(err.message.endsWith('.') ? err.message : NO_PTY);
        return err.message.endsWith('.') ? t(err.message) : null;
      },
      kind: (err) => {
        if (err instanceof TypeError) return 'unreachable';
        if (!(err instanceof ApiError)) return null;
        if (err.status === 0 || err.code === 'unreachable') return 'unreachable';
        if (err.status === 403 || err.code === 'forbidden' || err.code === 'no-pty') return 'refused';
        if (err.code === 'not-installed') return 'notInstalled';
        if (missingRoute(err)) return 'oldEngine';
        return err.status === 502 || err.status === 504 ? 'unreachable' : null;
      },
    },
    terminal: {
      list: async () => {
        const list = await listing(host);
        return (Array.isArray(list.terminals) ? list.terminals : []).filter(isObj).map((x) => record(x as RawTerminal));
      },
      open: async (kind, o) => record(await call<RawTerminal>('/api/terminal', 'POST', {
        kind, cols: o.cols, rows: o.rows, ...(o.prompt ? { prompt: o.prompt } : {}), ...(o.resume ? { resume: o.resume } : {}),
      })),
      restart: async (id) => { await call<RawTerminal>(`${path(id)}/restart`, 'POST', {}); },
      close: async (id) => {
        try { await call<{ ok?: unknown }>(path(id), 'DELETE'); } catch (err) { if (!(err instanceof ApiError && err.status === 404)) throw err; }
      },
      channel: async (id) => {
        const said = await call<{ ticket?: unknown }>(`${path(id)}/ticket`, 'POST', {});
        const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
        return socketChannel(new WebSocket(`${proto}//${location.host}${path(id)}/stream?ticket=${encodeURIComponent(text(said.ticket))}`));
      },
    },
    agentStatus: async () => {
      let said: unknown;
      try { said = await call<unknown>('/api/agent-programs'); } catch { return null; }
      if (!isObj(said)) return null;
      const out: DockAgentStatus<OwnKind> = {};
      for (const kind of PROGRAMS) {
        const s = said[kind];
        if (!isObj(s)) continue;
        out[kind] = {
          installed: s.installed === true,
          version: text(s.version) || null,
          install: text(s.install),
          signedIn: typeof s.signedIn === 'boolean' ? s.signedIn : null,
          ...(text(s.note) ? { note: t(text(s.note)) } : {}),
        };
      }
      return out;
    },
    openSettings: () => host.openSettings(),
  };
}
