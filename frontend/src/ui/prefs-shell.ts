import '../styles/prefs.css';
import { el, q, setAttr, setClass, setHidden } from './dom';
import { icon, ICONS } from './icons';

Object.assign(ICONS, {
  pfFold: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M11 6l-6 6 6 6M19 6l-6 6 6 6"/></svg>',
});

const RAIL_KEY = 'formpublisher.prefsRailCollapsed';
const ARC = 10;

export type PrefsSectionDef = readonly [id: string, label: string, icon: string];

export class PrefsShell {
  private readonly nav = el('<div class="fp-prefs-nav" role="tablist" aria-orientation="vertical" aria-label="Preferences sections"></div>');
  private readonly rail = el('<div class="fp-prefs-rail"></div>');
  private readonly fold = el<HTMLButtonElement>(`<button class="fp-prefs-fold" type="button">${icon('pfFold', 16)}</button>`);
  private readonly port = el('<span class="fp-prefs-port" aria-hidden="true"></span>');
  private readonly shade: SVGPathElement;
  private readonly line: SVGPathElement;
  private readonly head: HTMLElement;
  private readonly sections = new Map<string, HTMLElement>();
  private readonly tabs = new Map<string, HTMLButtonElement>();
  private collapsed = false;
  private current = '';
  private wireRaf = 0;
  private spyRaf = 0;
  private spyMuted = 0;
  private reveal = true;
  private wireD = '';
  private portY = Number.NaN;

  constructor(private readonly frame: HTMLElement, private readonly pages: HTMLElement, defs: readonly PrefsSectionDef[]) {
    this.head = q(frame, '.fp-dialog-head');
    this.head.prepend(el(`<span class="fp-prefs-headicon">${icon('settings', 16)}</span>`));
    const order: string[] = [];
    for (const [id, label, ic] of defs) {
      const sec = q<HTMLElement>(pages, `.fp-prefs-sec[data-section="${id}"]`);
      const secHead = el<HTMLButtonElement>(`<button class="fp-prefs-sechead" type="button" aria-expanded="true"><span class="fp-prefs-secicon">${icon(ic, 16)}</span><span class="fp-prefs-seclabel">${label}</span><span class="fp-prefs-chev">${icon('chevronDown', 16)}</span></button>`);
      secHead.addEventListener('click', () => this.foldSection(id));
      sec.prepend(secHead);
      const tab = el<HTMLButtonElement>(`<button class="fp-prefs-railtab" type="button" role="tab" aria-selected="false" title="${label}"><span class="fp-prefs-tabicon">${icon(ic, 18)}</span><span class="fp-prefs-tablabel">${label}</span></button>`);
      tab.dataset.section = id;
      tab.addEventListener('click', () => this.show(id, 'smooth'));
      tab.addEventListener('keydown', (e) => {
        if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
        e.preventDefault();
        const next = order[(order.indexOf(id) + (e.key === 'ArrowDown' ? 1 : -1) + order.length) % order.length];
        this.tabs.get(next)?.focus();
        this.show(next, 'smooth');
      });
      this.nav.appendChild(tab);
      this.sections.set(id, sec);
      this.tabs.set(id, tab);
      order.push(id);
    }
    try { this.collapsed = localStorage.getItem(RAIL_KEY) === '1'; } catch { this.collapsed = false; }
    this.fold.addEventListener('click', () => {
      this.collapsed = !this.collapsed;
      try { localStorage.setItem(RAIL_KEY, this.collapsed ? '1' : '0'); } catch { this.paintRail(); }
      this.paintRail();
      this.draw();
    });
    this.paintRail();
    this.rail.append(this.nav, this.fold);
    const wire = el('<svg class="fp-prefs-wire" aria-hidden="true"><path class="fp-prefs-wire-shade"></path><path class="fp-prefs-wire-line"></path></svg>');
    this.shade = q<SVGPathElement>(wire, '.fp-prefs-wire-shade');
    this.line = q<SVGPathElement>(wire, '.fp-prefs-wire-line');
    frame.append(this.rail, wire, this.port);
    pages.addEventListener('scroll', () => this.queueSpy(), { passive: true });
    this.nav.addEventListener('scroll', () => this.queueWire(false), { passive: true });
    new ResizeObserver(() => this.draw()).observe(frame);
    window.addEventListener('resize', () => this.queueWire());
    if (order.length) this.mark(order[0]);
  }

  get section(): string { return this.current; }

  tab(id = this.current): HTMLElement | null { return this.tabs.get(id) ?? null; }

  show(id: string, scroll: ScrollBehavior | null = null): void {
    if (!this.sections.has(id)) return;
    this.mark(id);
    if (scroll) this.scrollTo(id, scroll);
  }

  mark(id: string): void {
    if (this.current === id || !this.sections.has(id)) return;
    this.current = id;
    for (const [n, sec] of this.sections) setClass(sec, 'is-current', n === id);
    for (const [n, tab] of this.tabs) {
      setClass(tab, 'is-active', n === id);
      setAttr(tab, 'aria-selected', String(n === id));
    }
    this.queueWire();
  }

  scrollTo(id: string, behavior: ScrollBehavior): void {
    const sec = this.sections.get(id);
    if (!sec) return;
    if (sec.classList.contains('is-folded')) this.foldSection(id);
    const top = sec.getBoundingClientRect().top - this.pages.getBoundingClientRect().top + this.pages.scrollTop - 12;
    this.spyMuted = performance.now() + 700;
    this.pages.scrollTo({ top, behavior });
  }

  draw(): void {
    this.reveal = true;
    this.drawWire();
  }

  private paintRail(): void {
    setClass(this.frame, 'is-rail-collapsed', this.collapsed);
    const label = this.collapsed ? 'Expand tabs' : 'Collapse tabs';
    setAttr(this.fold, 'title', label);
    setAttr(this.fold, 'aria-label', label);
    setAttr(this.fold, 'aria-expanded', String(!this.collapsed));
  }

  private foldSection(id: string): void {
    const sec = this.sections.get(id);
    if (!sec) return;
    const folded = !sec.classList.contains('is-folded');
    setClass(sec, 'is-folded', folded);
    setHidden(q(sec, '.fp-prefs-secbody'), folded);
    setAttr(q(sec, '.fp-prefs-sechead'), 'aria-expanded', String(!folded));
    this.queueWire();
    this.queueSpy();
  }

  private queueSpy(): void {
    if (this.spyRaf) return;
    this.spyRaf = requestAnimationFrame(() => {
      this.spyRaf = 0;
      const pages = this.pages;
      if (!pages.clientHeight || performance.now() < this.spyMuted) return;
      const edge = pages.getBoundingClientRect().top + 24;
      const names = Array.from(this.sections.keys());
      let best = '';
      let bestD = Infinity;
      if (pages.scrollHeight > pages.clientHeight + 4 && pages.scrollTop + pages.clientHeight >= pages.scrollHeight - 2) best = names[names.length - 1] ?? '';
      else for (const [n, sec] of this.sections) {
        const top = sec.getBoundingClientRect().top;
        const d = top <= edge ? edge - top : top - edge + 100000;
        if (d < bestD) { bestD = d; best = n; }
      }
      if (best) this.mark(best);
    });
  }

  private queueWire(reveal = true): void {
    if (reveal) this.reveal = true;
    if (this.wireRaf) return;
    this.wireRaf = requestAnimationFrame(() => { this.wireRaf = 0; this.drawWire(); });
  }

  private drawWire(): void {
    const F = this.frame.getBoundingClientRect();
    const tab = this.tabs.get(this.current);
    if (!F.width || !tab) return;
    const N = this.nav.getBoundingClientRect();
    let T = tab.getBoundingClientRect();
    if (this.reveal && (T.top < N.top || T.bottom > N.bottom)) {
      this.nav.scrollTop += T.top < N.top ? T.top - N.top - 6 : T.bottom - N.bottom + 6;
      T = tab.getBoundingClientRect();
    }
    this.reveal = false;
    const R = this.rail.getBoundingClientRect();
    const H = this.head.getBoundingClientRect();
    const portY = Math.round(H.bottom - F.top);
    const sx = Math.round(T.right - F.left);
    const ty = Math.round(Math.min(Math.max(T.top + T.height / 2, N.top + ARC), N.bottom - ARC) - F.top);
    const rr = R.right - F.left;
    const trunk = Math.round(rr - rr * 0.45);
    const dy = portY - ty;
    const r = ARC;
    const dir = dy > 0 ? 1 : -1;
    const d = Math.abs(dy) < 2 * r ? `M ${sx} ${ty} H ${trunk} V ${portY} H -7` : `M ${sx} ${ty} H ${trunk - r} a ${r} ${r} 0 0 ${dir > 0 ? 1 : 0} ${r} ${dir * r} V ${portY - dir * r} a ${r} ${r} 0 0 ${dir > 0 ? 0 : 1} ${r} ${dir * r} H -7`;
    if (d !== this.wireD) { this.wireD = d; this.shade.setAttribute('d', d); this.line.setAttribute('d', d); }
    if (portY !== this.portY) { this.portY = portY; this.port.style.transform = `translateY(${portY}px)`; }
  }
}
