import type { PreviewMotion, PreviewTheme, PreviewThrottle } from '../api-host';
import { emit } from '../events';
import { onLanguage, t } from '../i18n';
import { el, q, setDisabled } from './dom';
import { Dropdown, dropdownHtml, type DropdownOption } from './dropdown';
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

const opts = (list: ReadonlyArray<readonly [string, string]>): DropdownOption[] => list.map(([value, label]) => ({ value, label }));

const CHOICES: Record<string, { label: string; options: DropdownOption[] }> = {
  device: { label: 'Device', options: opts([['desktop', 'Desktop 1440 x 900'], ['laptop', 'Laptop 1280 x 800'], ['tablet', 'Tablet 834 x 1112'], ['phone', 'Phone 390 x 844'], ['custom', 'Custom']]) },
  zoom: { label: 'Zoom', options: opts([['fit', 'Fit'], ['50', '50%'], ['75', '75%'], ['100', '100%']]) },
  theme: { label: 'Preview theme', options: opts([['auto', 'Theme: Auto'], ['dark', 'Theme: Dark'], ['light', 'Theme: Light']]) },
  motion: { label: 'Preview motion', options: opts([['auto', 'Motion: Auto'], ['reduce', 'Motion: Reduce']]) },
  throttle: { label: 'Preview network', options: opts([['none', 'Network: None'], ['fast', 'Network: Fast'], ['slow', 'Network: Slow']]) },
};

const select = (ctl: string): string => dropdownHtml({ cls: 'fp-tb-select', label: CHOICES[ctl].label, title: CHOICES[ctl].label, data: { ctl }, options: CHOICES[ctl].options });

const PROBE = `<span class="fp-dd fp-tb-select fp-tb-probe" translate="no" aria-hidden="true"><span class="fp-dd-face"><span class="fp-dd-cur"><span class="fp-dd-text"><span class="fp-dd-l"></span></span></span></span>${icon('chevronDown', 12)}</span>`;

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
${select('device')}
<input class="fp-tb-num" data-ctl="width" type="number" inputmode="numeric" min="${MIN_SIZE}" max="${MAX_SIZE}" step="1" aria-label="Width" title="Width">
<span class="fp-tb-x" aria-hidden="true">x</span>
<input class="fp-tb-num" data-ctl="height" type="number" inputmode="numeric" min="${MIN_SIZE}" max="${MAX_SIZE}" step="1" aria-label="Height" title="Height">
<button class="fp-icon-btn" type="button" data-ctl="rotate" title="Rotate" aria-label="Rotate">${rotateIcon(16)}</button>
${select('zoom')}
<span class="fp-sep"></span>
${select('theme')}
${select('motion')}
${select('throttle')}
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
  private readonly device: Dropdown;
  private readonly width: HTMLInputElement;
  private readonly height: HTMLInputElement;
  private readonly zoom: Dropdown;
  private readonly theme: Dropdown;
  private readonly motion: Dropdown;
  private readonly throttle: Dropdown;
  private readonly gated: Array<HTMLButtonElement | HTMLInputElement>;
  private readonly selects: Dropdown[];
  private readonly probe: HTMLElement;
  private readonly probeText: HTMLElement;
  private rowWidth = Infinity;
  private compact = false;
  private titleShown = '';

  constructor(private readonly host: HTMLElement, private readonly hooks: ToolbarHooks) {
    host.insertAdjacentHTML('beforeend', CONTROLS);
    this.field = q<HTMLInputElement>(host, '.fp-route-field');
    this.field.readOnly = false;
    this.field.disabled = true;
    const ctl = <T extends HTMLElement>(name: string): T => q<T>(host, `[data-ctl="${name}"]`);
    const choice = (name: string, change: (value: string) => void): Dropdown =>
      new Dropdown(ctl<HTMLButtonElement>(name), { label: CHOICES[name].label, options: CHOICES[name].options, value: this.state[name as 'device'], change });
    this.device = choice('device', (v) => {
      const d = v as Device;
      if (d !== 'custom') {
        const [w, h] = PRESETS[d];
        this.state.width = w;
        this.state.height = h;
      }
      this.state.device = d;
      this.deviceTitle();
      this.commit('view');
    });
    this.width = ctl('width');
    this.height = ctl('height');
    this.zoom = choice('zoom', (v) => { this.state.zoom = v as Zoom; this.commit('view'); });
    this.theme = choice('theme', (v) => { this.state.theme = v as PreviewTheme; this.commit('mount'); });
    this.motion = choice('motion', (v) => { this.state.motion = v as PreviewMotion; this.commit('mount'); });
    this.throttle = choice('throttle', (v) => { this.state.throttle = v as PreviewThrottle; this.commit('mount'); });
    const reload = ctl<HTMLButtonElement>('reload');
    const browser = ctl<HTMLButtonElement>('browser');
    const pack = ctl<HTMLButtonElement>('package');
    const publish = ctl<HTMLButtonElement>('publish');
    this.gated = [this.field, reload, browser, publish, pack];
    this.selects = [this.device, this.zoom, this.theme, this.motion, this.throttle];
    this.probe = el(PROBE);
    this.probeText = q(this.probe, '.fp-dd-l');
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
    reload.addEventListener('click', () => hooks.reload());
    browser.addEventListener('click', () => hooks.openBrowser());
    pack.addEventListener('click', () => hooks.packageSite());
    publish.addEventListener('click', () => emit('fp:publish', { source: 'toolbar' }));

    new ResizeObserver((entries) => {
      const box = entries[0];
      const w = box.contentBoxSize?.[0]?.inlineSize ?? box.contentRect.width;
      if (w > 0 && w !== this.rowWidth) { this.rowWidth = w; this.fit(); }
    }).observe(host);
    onLanguage(() => this.fit());
    document.fonts?.addEventListener('loadingdone', () => this.fit());
  }

  private fit(): void {
    let stage = this.rowWidth <= FIT_BELOW ? 1 : 0;
    for (;;) {
      this.host.classList.toggle('is-sized', stage >= 1);
      this.host.classList.toggle('is-tight', stage >= 2);
      this.host.classList.toggle('is-short', stage >= 3);
      this.host.classList.toggle('is-micro', stage >= 4);
      this.paint(stage >= 3);
      if (stage >= 4 || this.host.scrollWidth <= this.host.clientWidth) break;
      stage += 1;
    }
  }

  private measure(text: string): number {
    if (this.probeText.textContent !== text) this.probeText.textContent = text;
    return this.probe.getBoundingClientRect().width;
  }

  private customShort(s: Dropdown, full: string): string {
    const other = t('Other');
    if (other === 'Other') return '';
    let presets = 0;
    for (const o of s.options()) {
      if (o.value !== 'custom') presets = Math.max(presets, this.measure(shortLabel('device', t(o.label))));
    }
    return this.measure(full) > presets + 0.5 ? other : '';
  }

  private deviceTitle(): void {
    const base = t(CHOICES.device.label);
    const o = this.device.selected();
    const title = this.compact && o ? `${base}: ${t(o.label)}` : base;
    if (title === this.titleShown && this.device.button.title === title) return;
    this.titleShown = title;
    this.device.button.title = title;
  }

  private paint(compact: boolean): void {
    this.compact = compact;
    for (const s of this.selects) {
      const ctl = s.button.dataset.ctl ?? '';
      const shorts = new Map<string, string>();
      let widest = 0;
      for (const o of s.options()) {
        const text = t(o.label);
        let short = compact ? shortLabel(ctl, text) : '';
        if (compact && ctl === 'device' && o.value === 'custom') short = this.customShort(s, text);
        const shown = short && short !== text ? short : text;
        if (shown !== text) shorts.set(o.value, shown);
        widest = Math.max(widest, this.measure(shown));
      }
      s.setShorts(shorts.size ? shorts : null);
      const px = `${Math.ceil(widest)}px`;
      if (s.button.style.width !== px) s.button.style.width = px;
    }
    this.deviceTitle();
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
    this.device.set(s.device);
    this.deviceTitle();
    if (this.width.value !== String(s.width)) this.width.value = String(s.width);
    if (this.height.value !== String(s.height)) this.height.value = String(s.height);
    this.zoom.set(s.zoom);
    this.theme.set(s.theme);
    this.motion.set(s.motion);
    this.throttle.set(s.throttle);
  }
}
