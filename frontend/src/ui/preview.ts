import '../styles/preview.css';
import { hostApi, type HostMount } from '../api-host';
import { emit, type ProbeMessage } from '../events';
import { inTauri, q, setClass, setHidden, setStyleVar, setText } from './dom';
import type { PreviewState } from './toolbar';

export interface PreviewHooks {
  path(path: string, source: 'show' | 'frame'): void;
  error(text: string): void;
}

type Json = Record<string, unknown>;

const isObj = (v: unknown): v is Json => typeof v === 'object' && v !== null && !Array.isArray(v);

const STAGE = `<div class="fp-preview" hidden>
<div class="fp-pv-scroll is-fit">
<div class="fp-pv-column">
<div class="fp-pv-label"><span class="fp-pv-load" aria-hidden="true"></span><span class="fp-pv-route" translate="no"></span><span class="fp-pv-size" translate="no"></span></div>
<div class="fp-pv-box"><div class="fp-pv-device">
<iframe class="fp-pv-frame" title="Site preview" sandbox="allow-scripts allow-forms allow-same-origin allow-popups" referrerpolicy="no-referrer"></iframe>
<iframe class="fp-pv-frame" title="Site preview" sandbox="allow-scripts allow-forms allow-same-origin allow-popups" referrerpolicy="no-referrer"></iframe>
</div></div>
</div>
</div>
</div>`;

export const routeKey = (p: string): string => {
  let v = p.split('#')[0].split('?')[0];
  if (v.endsWith('/index.html')) v = v.slice(0, -10);
  if (v.length > 1 && v.endsWith('/')) v = v.slice(0, -1);
  return v || '/';
};

async function openExternal(target: string): Promise<void> {
  if (inTauri()) {
    const { invoke } = await import('@tauri-apps/api/core');
    await invoke('plugin:shell|open', { path: target });
    return;
  }
  window.open(target, '_blank', 'noopener');
}

export class Preview {
  readonly element: HTMLElement;
  private readonly scroll: HTMLElement;
  private readonly column: HTMLElement;
  private readonly labelRoute: HTMLElement;
  private readonly labelSize: HTMLElement;
  private readonly loadDot: HTMLElement;
  private readonly frames: HTMLIFrameElement[];
  private front: HTMLIFrameElement | null = null;
  private pending: HTMLIFrameElement | null = null;
  private expecting = false;
  private loadId = 0;
  private requested = '/';
  private buffer: MessageEvent[] = [];
  private siteId: string | null = null;
  private frontSite: string | null = null;
  private lastRoute: string | null = null;
  private framePath: string | null = null;
  private mount: HostMount | null = null;
  private mountKey = '';
  private mounting: { key: string; promise: Promise<HostMount> } | null = null;
  private gen = -1;
  private origin = '';
  private view: PreviewState;
  private visible = false;
  private relayoutQueued = false;
  private pad = 16;

  constructor(stage: HTMLElement, private readonly hooks: PreviewHooks, state: PreviewState) {
    this.view = { ...state };
    stage.insertAdjacentHTML('beforeend', STAGE);
    this.element = q(stage, '.fp-preview');
    this.scroll = q(this.element, '.fp-pv-scroll');
    this.column = q(this.element, '.fp-pv-column');
    this.labelRoute = q(this.element, '.fp-pv-route');
    this.labelSize = q(this.element, '.fp-pv-size');
    this.loadDot = q(this.element, '.fp-pv-load');
    this.frames = Array.from(this.element.querySelectorAll<HTMLIFrameElement>('.fp-pv-frame'));
    for (const f of this.frames) f.addEventListener('load', () => this.onLoad(f));
    window.addEventListener('message', (e) => this.onMessage(e));
    new ResizeObserver(() => this.queueRelayout()).observe(this.scroll);
    this.relayout();
  }

  setVisible(visible: boolean): void {
    if (this.visible === visible) return;
    this.visible = visible;
    setHidden(this.element, !visible);
    if (visible) this.relayout();
  }

  setView(state: PreviewState): void {
    this.view = { ...state };
    this.relayout();
  }

  setOptions(state: PreviewState): void {
    const changed = state.theme !== this.view.theme || state.motion !== this.view.motion || state.throttle !== this.view.throttle;
    this.view = { ...state };
    this.relayout();
    if (changed && this.siteId !== null) void this.go(this.currentPath());
  }

  show(siteId: string | null, route: string | null): void {
    if (siteId === null) {
      this.clear();
      return;
    }
    const changed = siteId !== this.siteId;
    if (changed) {
      this.siteId = siteId;
      this.mount = null;
      this.mountKey = '';
      this.lastRoute = null;
      this.framePath = null;
    }
    if (route === null) return;
    if (this.lastRoute !== null && routeKey(route) === routeKey(this.lastRoute)) return;
    this.lastRoute = route;
    this.hooks.path(route, 'show');
    void this.go(route);
  }

  navigate(path: string): void {
    if (this.siteId === null) return;
    this.lastRoute = path;
    this.hooks.path(path, 'frame');
    void this.go(path);
  }

  reload(): void {
    if (this.siteId === null) return;
    this.mount = null;
    this.mountKey = '';
    void this.go(this.currentPath());
  }

  openInBrowser(): void {
    if (this.siteId === null || !this.mount) return;
    void openExternal(this.urlFor(this.mount, this.currentPath()));
  }

  private currentPath(): string {
    return this.framePath ?? this.lastRoute ?? '/';
  }

  private urlFor(m: HostMount, path: string): string {
    try { return new URL(path.startsWith('/') ? path : `/${path}`, m.url).toString(); } catch { return m.url; }
  }

  private clear(): void {
    if (this.siteId === null) return;
    this.siteId = null;
    this.frontSite = null;
    this.lastRoute = null;
    this.framePath = null;
    this.mount = null;
    this.mountKey = '';
    this.loadId += 1;
    this.expecting = false;
    this.pending = null;
    this.buffer = [];
    this.setLoading(false);
    this.hooks.path('', 'show');
    setText(this.labelRoute, '');
    for (const f of this.frames) {
      setClass(f, 'is-front', false);
      setClass(f, 'is-idle', false);
      setClass(f, 'is-under', false);
      if (f.getAttribute('src')) f.removeAttribute('src');
    }
    this.front = null;
    void hostApi.unmount().catch(() => undefined);
  }

  private keyNow(): string {
    const v = this.view;
    return [this.siteId, v.theme, v.motion, v.throttle].join('|');
  }

  private ensureMount(): Promise<HostMount> {
    const site = this.siteId as string;
    const v = this.view;
    const key = this.keyNow();
    if (this.mount && this.mountKey === key) return Promise.resolve(this.mount);
    if (this.mounting && this.mounting.key === key) return this.mounting.promise;
    const promise = hostApi.mount({ site, probe: true, theme: v.theme, motion: v.motion, throttle: v.throttle }).then((m) => {
      if (this.keyNow() === key) {
        this.mount = m;
        this.mountKey = key;
        this.gen = m.generation;
        this.origin = m.origin;
      }
      return m;
    }).finally(() => { if (this.mounting?.promise === promise) this.mounting = null; });
    this.mounting = { key, promise };
    return promise;
  }

  private async go(path: string): Promise<void> {
    const id = ++this.loadId;
    this.expecting = false;
    this.setLoading(true);
    const site = this.siteId;
    try {
      const m = await this.ensureMount();
      if (id !== this.loadId || site !== this.siteId) return;
      const target = this.frames.find((f) => f !== this.front) as HTMLIFrameElement;
      this.pending = target;
      this.requested = path;
      this.buffer = [];
      setClass(target, 'is-idle', false);
      setClass(target, 'is-under', false);
      this.expecting = true;
      target.src = this.urlFor(m, path);
    } catch (e) {
      if (id !== this.loadId) return;
      this.setLoading(false);
      this.hooks.error(e instanceof Error ? e.message : 'The preview could not start');
    }
  }

  private onLoad(frame: HTMLIFrameElement): void {
    if (!this.expecting || frame !== this.pending) return;
    const id = this.loadId;
    requestAnimationFrame(() => requestAnimationFrame(() => {
      if (id !== this.loadId || frame !== this.pending) return;
      this.swap(frame);
    }));
  }

  private swap(frame: HTMLIFrameElement): void {
    const old = this.front;
    setClass(frame, 'is-front', true);
    setClass(frame, 'is-idle', false);
    if (old) {
      setClass(old, 'is-front', false);
      setClass(old, 'is-under', true);
    }
    this.front = frame;
    this.frontSite = this.siteId;
    this.pending = null;
    this.expecting = false;
    this.framePath = this.requested;
    setText(this.labelRoute, this.requested);
    this.setLoading(false);
    const queued = this.buffer;
    this.buffer = [];
    for (const e of queued) this.accept(e);
    if (old) {
      requestAnimationFrame(() => requestAnimationFrame(() => {
        if (this.front !== frame || old === this.pending) return;
        setClass(old, 'is-under', false);
        setClass(old, 'is-idle', true);
      }));
    }
  }

  private setLoading(on: boolean): void {
    setClass(this.loadDot, 'is-on', on);
  }

  private valid(e: MessageEvent): Json | null {
    const d: unknown = e.data;
    if (!isObj(d) || d.source !== 'fp-probe' || typeof d.type !== 'string') return null;
    if (e.origin !== this.origin || d.gen !== this.gen) return null;
    return d;
  }

  private onMessage(e: MessageEvent): void {
    if (this.siteId === null) return;
    if (this.front && e.source === this.front.contentWindow) {
      this.accept(e);
    } else if (this.pending && e.source === this.pending.contentWindow && this.valid(e) && this.buffer.length < 200) {
      this.buffer.push(e);
    }
  }

  private accept(e: MessageEvent): void {
    if (!this.front || e.source !== this.front.contentWindow || this.frontSite === null) return;
    const d = this.valid(e);
    if (!d) return;
    emit('fp:probe', { ...d, siteId: this.frontSite } as ProbeMessage);
    if ((d.type === 'nav' || d.type === 'hello') && typeof d.path === 'string' && d.path !== '') this.onPath(d.path);
  }

  private onPath(path: string): void {
    if (this.framePath === path) return;
    this.framePath = path;
    this.lastRoute = path;
    setText(this.labelRoute, path);
    this.hooks.path(path, 'frame');
  }

  private queueRelayout(): void {
    if (this.relayoutQueued) return;
    this.relayoutQueued = true;
    requestAnimationFrame(() => {
      this.relayoutQueued = false;
      this.relayout();
    });
  }

  private relayout(): void {
    const { width: w, height: h, zoom } = this.view;
    let scale: number;
    if (zoom === 'fit') {
      const labelH = this.labelRoute.parentElement?.offsetHeight ?? 0;
      const cs = getComputedStyle(this.column);
      this.pad = parseFloat(cs.paddingLeft) || this.pad;
      const gap = parseFloat(cs.rowGap) || 0;
      const availW = this.scroll.clientWidth - this.pad * 2;
      const availH = this.scroll.clientHeight - this.pad * 2 - labelH - gap;
      if (availW <= 0 || availH <= 0) return;
      scale = Math.floor(Math.min(1, availW / w, availH / h) * 1000) / 1000;
    } else {
      scale = Number(zoom) / 100;
    }
    scale = Math.max(0.05, scale);
    setClass(this.scroll, 'is-fit', zoom === 'fit');
    const root = this.element;
    setStyleVar(root, '--pv-w', `${w}px`);
    setStyleVar(root, '--pv-h', `${h}px`);
    setStyleVar(root, '--pv-s', String(scale));
    setStyleVar(root, '--pv-bw', `${Math.round(w * scale)}px`);
    setStyleVar(root, '--pv-bh', `${Math.round(h * scale)}px`);
    setText(this.labelSize, `${w} x ${h}  ${Math.round(scale * 100)}%`);
  }
}
