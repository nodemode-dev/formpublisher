import type { PreviewMotion, PreviewTheme, PreviewThrottle } from '../api-host';
import { emit } from '../events';
import { q, setDisabled } from './dom';
import { icon } from './icons';

const KEY = 'formpublisher.preview';

export type Zoom = 'fit' | '50' | '75' | '100';
export type Device = 'desktop' | 'laptop' | 'tablet' | 'phone' | 'custom';
export type ChangeKind = 'view' | 'mount';

export interface PreviewState {
  device: Device;
  width: number;
  height: number;
  zoom: Zoom;
  theme: PreviewTheme;
  motion: PreviewMotion;
  throttle: PreviewThrottle;
}

export interface ToolbarHooks {
  navigate(path: string): void;
  reload(): void;
  openBrowser(): void;
  packageSite(): void;
  change(state: PreviewState, kind: ChangeKind): void;
}

export const PRESETS: Record<Exclude<Device, 'custom'>, readonly [number, number]> = {
  desktop: [1440, 900],
  laptop: [1280, 800],
  tablet: [834, 1112],
  phone: [390, 844],
};

const MIN_SIZE = 200;
const MAX_SIZE = 4000;

const DEFAULTS: PreviewState = { device: 'desktop', width: 1440, height: 900, zoom: 'fit', theme: 'auto', motion: 'auto', throttle: 'none' };

const pick = <T extends string>(v: unknown, allowed: readonly T[], d: T): T => (typeof v === 'string' && (allowed as readonly string[]).includes(v) ? (v as T) : d);
const clampSize = (v: unknown, d: number): number => (typeof v === 'number' && Number.isFinite(v) ? Math.min(MAX_SIZE, Math.max(MIN_SIZE, Math.round(v))) : d);

export function loadPreviewState(): PreviewState {
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) || '{}') as Partial<PreviewState>;
    return {
      device: pick(raw.device, ['desktop', 'laptop', 'tablet', 'phone', 'custom'] as const, DEFAULTS.device),
      width: clampSize(raw.width, DEFAULTS.width),
      height: clampSize(raw.height, DEFAULTS.height),
      zoom: pick(raw.zoom, ['fit', '50', '75', '100'] as const, DEFAULTS.zoom),
      theme: pick(raw.theme, ['auto', 'dark', 'light'] as const, DEFAULTS.theme),
      motion: pick(raw.motion, ['auto', 'reduce'] as const, DEFAULTS.motion),
      throttle: pick(raw.throttle, ['none', 'fast', 'slow'] as const, DEFAULTS.throttle),
    };
  } catch {
    return { ...DEFAULTS };
  }
}

const rotateIcon = (size: number): string => `<span class="icon" style="width:${size}px;height:${size}px" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="8" y="3.5" width="8" height="13" rx="1.5"/><path d="M4.5 14.5v2.5a2.5 2.5 0 0 0 2.5 2.5h5M10 17.5l2.5 2-2.5 2"/></svg></span>`;

const select = (ctl: string, label: string, options: ReadonlyArray<readonly [string, string]>): string =>
  `<select class="fp-tb-select" data-ctl="${ctl}" aria-label="${label}" title="${label}">${options.map(([v, t]) => `<option value="${v}">${t}</option>`).join('')}</select>`;

const FIT_BELOW = 1400;

const shortLabel = (ctl: string, text: string): string => {
  if (ctl === 'device') return text.replace(/\s+\d+\s*x\s*\d+$/, '');
  if (ctl === 'theme' || ctl === 'motion' || ctl === 'throttle') {
    const i = text.indexOf(': ');
    if (i > 0) return text.charAt(i + 2).toLocaleUpperCase(document.documentElement.lang || undefined) + text.slice(i + 3);
  }
  return text;
};

const CONTROLS = `<span class="fp-sep"></span>
${select('device', 'Device', [['desktop', 'Desktop 1440 x 900'], ['laptop', 'Laptop 1280 x 800'], ['tablet', 'Tablet 834 x 1112'], ['phone', 'Phone 390 x 844'], ['custom', 'Custom']])}
<input class="fp-tb-num" data-ctl="width" type="number" inputmode="numeric" min="${MIN_SIZE}" max="${MAX_SIZE}" step="1" aria-label="Width" title="Width">
<span class="fp-tb-x" aria-hidden="true">x</span>
<input class="fp-tb-num" data-ctl="height" type="number" inputmode="numeric" min="${MIN_SIZE}" max="${MAX_SIZE}" step="1" aria-label="Height" title="Height">
<button class="fp-icon-btn" type="button" data-ctl="rotate" title="Rotate" aria-label="Rotate">${rotateIcon(16)}</button>
${select('zoom', 'Zoom', [['fit', 'Fit'], ['50', '50%'], ['75', '75%'], ['100', '100%']])}
<span class="fp-sep"></span>
${select('theme', 'Preview theme', [['auto', 'Theme: Auto'], ['dark', 'Theme: Dark'], ['light', 'Theme: Light']])}
${select('motion', 'Preview motion', [['auto', 'Motion: Auto'], ['reduce', 'Motion: Reduce']])}
${select('throttle', 'Preview network', [['none', 'Network: None'], ['fast', 'Network: Fast'], ['slow', 'Network: Slow']])}
<span class="fp-sep"></span>
<button class="fp-icon-btn" type="button" data-ctl="reload" title="Reload" aria-label="Reload">${icon('reload', 16)}</button>
<button class="fp-icon-btn" type="button" data-ctl="browser" title="Open in browser" aria-label="Open in browser">${icon('globe', 16)}</button>
<span class="fp-tb-grow"></span>
<button class="fp-btn" type="button" data-ctl="publish" title="Prepare this site for a host">${icon('publish', 14)}<span>Publish</span></button>
<button class="fp-btn fp-btn-primary" type="button" data-ctl="package" title="Package this site">${icon('archive', 14)}<span>Package</span></button>`;

export function normalizePath(input: string): string {
  let v = input.trim();
  if (!v) return '';
  const abs = /^https?:\/\/[^/]+(\/.*)?$/i.exec(v);
  if (abs) v = abs[1] ?? '/';
  return v.startsWith('/') ? v : `/${v}`;
}

export class Toolbar {
  private state: PreviewState = loadPreviewState();
  private shown = '';
  private readonly field: HTMLInputElement;
  private readonly device: HTMLSelectElement;
  private readonly width: HTMLInputElement;
  private readonly height: HTMLInputElement;
  private readonly zoom: HTMLSelectElement;
  private readonly theme: HTMLSelectElement;
  private readonly motion: HTMLSelectElement;
  private readonly throttle: HTMLSelectElement;
  private readonly gated: Array<HTMLButtonElement | HTMLInputElement | HTMLSelectElement>;
  private readonly selects: HTMLSelectElement[];
  private readonly probe: HTMLSelectElement;
  private rowWidth = Infinity;

  constructor(private readonly host: HTMLElement, private readonly hooks: ToolbarHooks) {
    host.insertAdjacentHTML('beforeend', CONTROLS);
    this.field = q<HTMLInputElement>(host, '.fp-route-field');
    this.field.readOnly = false;
    this.field.disabled = true;
    const ctl = <T extends HTMLElement>(name: string): T => q<T>(host, `[data-ctl="${name}"]`);
    this.device = ctl('device');
    this.width = ctl('width');
    this.height = ctl('height');
    this.zoom = ctl('zoom');
    this.theme = ctl('theme');
    this.motion = ctl('motion');
    this.throttle = ctl('throttle');
    const reload = ctl<HTMLButtonElement>('reload');
    const browser = ctl<HTMLButtonElement>('browser');
    const pack = ctl<HTMLButtonElement>('package');
    const publish = ctl<HTMLButtonElement>('publish');
    this.gated = [this.field, reload, browser, publish, pack];
    this.selects = [this.device, this.zoom, this.theme, this.motion, this.throttle];
    this.probe = document.createElement('select');
    this.probe.className = 'fp-tb-select fp-tb-probe';
    this.probe.setAttribute('translate', 'no');
    this.probe.setAttribute('aria-hidden', 'true');
    this.probe.tabIndex = -1;
    this.probe.add(new Option(''));
    host.append(this.probe);
    this.paintControls();
    this.fit();
    this.setActive(false);

    this.field.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        const path = normalizePath(this.field.value);
        if (path) hooks.navigate(path);
        this.field.blur();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        this.field.blur();
      }
    });
    this.field.addEventListener('blur', () => { if (this.field.value !== this.shown) this.field.value = this.shown; });

    this.device.addEventListener('change', () => {
      const d = this.device.value as Device;
      if (d !== 'custom') {
        const [w, h] = PRESETS[d];
        this.state.width = w;
        this.state.height = h;
      }
      this.state.device = d;
      this.commit('view');
    });
    const size = (input: HTMLInputElement, key: 'width' | 'height'): void => {
      input.addEventListener('change', () => {
        this.state[key] = clampSize(Number(input.value), this.state[key]);
        this.state.device = 'custom';
        this.commit('view');
      });
    };
    size(this.width, 'width');
    size(this.height, 'height');
    ctl<HTMLButtonElement>('rotate').addEventListener('click', () => {
      [this.state.width, this.state.height] = [this.state.height, this.state.width];
      this.commit('view');
    });
    this.zoom.addEventListener('change', () => { this.state.zoom = this.zoom.value as Zoom; this.commit('view'); });
    this.theme.addEventListener('change', () => { this.state.theme = this.theme.value as PreviewTheme; this.commit('mount'); });
    this.motion.addEventListener('change', () => { this.state.motion = this.motion.value as PreviewMotion; this.commit('mount'); });
    this.throttle.addEventListener('change', () => { this.state.throttle = this.throttle.value as PreviewThrottle; this.commit('mount'); });
    reload.addEventListener('click', () => hooks.reload());
    browser.addEventListener('click', () => hooks.openBrowser());
    pack.addEventListener('click', () => hooks.packageSite());
    publish.addEventListener('click', () => emit('fp:publish', { source: 'toolbar' }));

    new ResizeObserver((entries) => {
      const box = entries[0];
      const w = box.contentBoxSize?.[0]?.inlineSize ?? box.contentRect.width;
      if (w > 0 && w !== this.rowWidth) { this.rowWidth = w; this.fit(); }
    }).observe(host);
    const refit = new MutationObserver(() => this.fit());
    for (const s of this.selects) {
      refit.observe(s, { childList: true, characterData: true, subtree: true });
    }
    document.fonts?.addEventListener('loadingdone', () => this.fit());
  }

  private fit(): void {
    const sized = this.rowWidth <= FIT_BELOW;
    let stage = sized ? 1 : 0;
    for (;;) {
      this.host.classList.toggle('is-tight', stage >= 2);
      this.host.classList.toggle('is-short', stage >= 3);
      this.paint(sized, stage >= 3);
      if (stage === 0 || stage >= 3 || this.host.scrollWidth <= this.host.clientWidth) break;
      stage += 1;
    }
  }

  private paint(sized: boolean, compact: boolean): void {
    for (const s of this.selects) {
      const ctl = s.dataset.ctl ?? '';
      for (const o of Array.from(s.options)) {
        const short = compact ? shortLabel(ctl, o.text) : '';
        if (short && short !== o.text) { if (o.label !== short) o.label = short; } else if (o.hasAttribute('label')) o.removeAttribute('label');
      }
      if (sized && s.options.length) {
        let widest = 0;
        for (const o of Array.from(s.options)) {
          this.probe.options[0].text = o.label;
          widest = Math.max(widest, this.probe.getBoundingClientRect().width);
        }
        const px = `${Math.ceil(widest)}px`;
        if (s.style.width !== px) s.style.width = px;
      } else if (s.style.width) {
        s.style.removeProperty('width');
      }
    }
  }

  current(): PreviewState {
    return { ...this.state };
  }

  setRoute(path: string): void {
    this.shown = path;
    if (document.activeElement !== this.field && this.field.value !== path) this.field.value = path;
  }

  setActive(active: boolean): void {
    for (const c of this.gated) setDisabled(c as HTMLButtonElement | HTMLInputElement, !active);
  }

  private commit(kind: ChangeKind): void {
    this.paintControls();
    try { localStorage.setItem(KEY, JSON.stringify(this.state)); } catch { void 0; }
    this.hooks.change({ ...this.state }, kind);
  }

  private paintControls(): void {
    const s = this.state;
    if (this.device.value !== s.device) this.device.value = s.device;
    if (this.width.value !== String(s.width)) this.width.value = String(s.width);
    if (this.height.value !== String(s.height)) this.height.value = String(s.height);
    if (this.zoom.value !== s.zoom) this.zoom.value = s.zoom;
    if (this.theme.value !== s.theme) this.theme.value = s.theme;
    if (this.motion.value !== s.motion) this.motion.value = s.motion;
    if (this.throttle.value !== s.throttle) this.throttle.value = s.throttle;
  }
}
