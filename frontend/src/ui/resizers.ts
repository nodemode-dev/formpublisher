import '../styles/lists.css';
import type { Pane } from '../app-api';
import { el, setAttr, setClass } from './dom';
import { icon, ICONS } from './icons';

Object.assign(ICONS, {
  stripFold: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M11 6l-6 6 6 6M19 6l-6 6 6 6"/></svg>',
});

const KEY = 'formpublisher.layout';

type Edge = 'strip' | 'props' | 'bottom';

interface Layout { strip: number; props: number; bottom: number; hidden: Pane[]; folded: boolean }

const EDGES: readonly Edge[] = ['strip', 'props', 'bottom'];
const LIMITS: Record<Edge, readonly [number, number]> = { strip: [160, 420], props: [240, 520], bottom: [84, 520] };
const DEFAULTS: Record<Edge, number> = { strip: 232, props: 308, bottom: 132 };
const VARS: Record<Edge, string> = { strip: '--fp-strip-w', props: '--fp-props-w', bottom: '--fp-bottom-h' };
const LABELS: Record<Edge, string> = { strip: 'Resize the routes', props: 'Resize the inspector', bottom: 'Resize the panel' };
const STEP = 16;
const FOLD_AT = 110;
const RAIL = 52;

const clamp = (edge: Edge, v: number): number => Math.min(LIMITS[edge][1], Math.max(LIMITS[edge][0], Math.round(v)));

function read(): Layout {
  const base: Layout = { ...DEFAULTS, hidden: [], folded: false };
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) || '{}') as Partial<Layout>;
    const size = (edge: Edge): number => {
      const v = raw[edge];
      return typeof v === 'number' && Number.isFinite(v) ? clamp(edge, v) : DEFAULTS[edge];
    };
    return {
      strip: size('strip'),
      props: size('props'),
      bottom: size('bottom'),
      hidden: Array.isArray(raw.hidden) ? raw.hidden.filter((p): p is Pane => p === 'strip' || p === 'props' || p === 'bottom') : [],
      folded: raw.folded === true,
    };
  } catch {
    return base;
  }
}

const edgeOf = (handle: HTMLElement): Edge => (handle.dataset.edge === 'props' ? 'props' : handle.dataset.edge === 'bottom' ? 'bottom' : 'strip');

export class LayoutState {
  private layout: Layout = read();
  private handles: HTMLElement[] = [];
  private readonly fold: HTMLButtonElement | null;
  private frame = 0;
  private foldTimer = 0;

  constructor(private readonly root: HTMLElement) {
    for (const edge of EDGES) root.style.setProperty(VARS[edge], `${this.layout[edge]}px`);
    for (const p of this.layout.hidden) root.classList.add(`is-${p}-hidden`);
    if (this.layout.folded) root.classList.add('is-strip-folded');
    const bottom = root.querySelector<HTMLElement>('.fp-bottom');
    if (bottom && !root.querySelector('.fp-resizer[data-edge="bottom"]')) bottom.before(el('<div class="fp-resizer" data-edge="bottom" role="separator" aria-orientation="horizontal"></div>'));
    const head = root.querySelector<HTMLElement>('.fp-strip-head');
    this.fold = head ? el<HTMLButtonElement>(`<button class="fp-icon-btn is-sm fp-strip-fold" type="button" aria-expanded="true">${icon('stripFold', 14)}</button>`) : null;
    if (head && this.fold) {
      const tools = el('<span class="fp-strip-tools"></span>');
      tools.appendChild(this.fold);
      head.appendChild(tools);
      this.fold.addEventListener('click', () => this.setFolded(!this.layout.folded));
    }
    this.paintFold();
  }

  isFolded(): boolean {
    return this.layout.folded;
  }

  setFolded(folded: boolean): void {
    if (this.layout.folded === folded) return;
    this.layout.folded = folded;
    this.animate();
    setClass(this.root, 'is-strip-folded', folded);
    this.paintFold();
    this.paintHandles();
    this.save();
    this.root.dispatchEvent(new Event('fp-layout'));
  }

  private animate(): void {
    setClass(this.root, 'is-folding', true);
    window.clearTimeout(this.foldTimer);
    this.foldTimer = window.setTimeout(() => setClass(this.root, 'is-folding', false), 320);
  }

  private paintFold(): void {
    if (!this.fold) return;
    const label = this.layout.folded ? 'Unfold the routes' : 'Fold the routes';
    setAttr(this.fold, 'title', label);
    setAttr(this.fold, 'aria-label', label);
    setAttr(this.fold, 'aria-expanded', String(!this.layout.folded));
  }

  isHidden(pane: Pane): boolean {
    return this.root.classList.contains(`is-${pane}-hidden`);
  }

  setHidden(pane: Pane, hidden: boolean): void {
    this.root.classList.toggle(`is-${pane}-hidden`, hidden);
    const set = new Set(this.layout.hidden);
    if (hidden) set.add(pane); else set.delete(pane);
    this.layout.hidden = Array.from(set);
    this.save();
  }

  install(resizers: HTMLElement[]): void {
    const extra = Array.from(this.root.querySelectorAll<HTMLElement>('.fp-resizer')).filter((h) => !resizers.includes(h));
    this.handles = [...resizers, ...extra];
    for (const handle of this.handles) {
      const edge = edgeOf(handle);
      setAttr(handle, 'tabindex', '0');
      setAttr(handle, 'aria-label', LABELS[edge]);
      setAttr(handle, 'aria-orientation', edge === 'bottom' ? 'horizontal' : 'vertical');
      setAttr(handle, 'aria-valuemin', String(LIMITS[edge][0]));
      setAttr(handle, 'aria-valuemax', String(LIMITS[edge][1]));
      handle.addEventListener('pointerdown', (e) => this.drag(handle, edge, e));
      handle.addEventListener('keydown', (e) => this.key(edge, e));
      handle.addEventListener('dblclick', () => {
        if (edge === 'strip' && this.layout.folded) this.setFolded(false);
        this.resize(edge, DEFAULTS[edge]);
        this.save();
      });
    }
    this.paintHandles();
  }

  private drag(handle: HTMLElement, edge: Edge, e: PointerEvent): void {
    if (e.button !== 0) return;
    e.preventDefault();
    handle.setPointerCapture(e.pointerId);
    setClass(handle, 'is-dragging', true);
    setClass(this.root, 'is-resizing', true);
    const startX = e.clientX;
    const startY = e.clientY;
    const startW = edge === 'strip' && this.layout.folded ? RAIL : this.layout[edge];
    const move = (ev: PointerEvent): void => {
      const raw = edge === 'strip' ? startW + ev.clientX - startX : edge === 'props' ? startW - (ev.clientX - startX) : startW - (ev.clientY - startY);
      if (edge === 'strip') {
        const fold = raw < FOLD_AT;
        if (fold !== this.layout.folded) this.setFolded(fold);
        if (fold) return;
      }
      this.resize(edge, raw);
    };
    const stop = (): void => {
      setClass(handle, 'is-dragging', false);
      setClass(this.root, 'is-resizing', false);
      handle.removeEventListener('pointermove', move);
      handle.removeEventListener('pointerup', stop);
      handle.removeEventListener('pointercancel', stop);
      this.save();
    };
    handle.addEventListener('pointermove', move);
    handle.addEventListener('pointerup', stop);
    handle.addEventListener('pointercancel', stop);
  }

  private key(edge: Edge, e: KeyboardEvent): void {
    const grow = edge === 'strip' ? 'ArrowRight' : edge === 'props' ? 'ArrowLeft' : 'ArrowUp';
    const shrink = edge === 'strip' ? 'ArrowLeft' : edge === 'props' ? 'ArrowRight' : 'ArrowDown';
    const now = this.layout[edge];
    let next: number;
    if (e.key === grow) next = now + STEP;
    else if (e.key === shrink) next = now - STEP;
    else if (e.key === 'Home') next = LIMITS[edge][0];
    else if (e.key === 'End') next = LIMITS[edge][1];
    else return;
    e.preventDefault();
    if (edge === 'strip' && this.layout.folded) {
      if (e.key === grow || e.key === 'End') this.setFolded(false);
      return;
    }
    this.resize(edge, next);
    this.save();
  }

  private resize(edge: Edge, raw: number): void {
    const w = clamp(edge, raw);
    if (w === this.layout[edge]) return;
    this.layout[edge] = w;
    if (this.frame) return;
    this.frame = requestAnimationFrame(() => {
      this.frame = 0;
      for (const ed of EDGES) this.root.style.setProperty(VARS[ed], `${this.layout[ed]}px`);
      this.paintHandles();
    });
  }

  private paintHandles(): void {
    for (const handle of this.handles) {
      const edge = edgeOf(handle);
      setAttr(handle, 'aria-valuenow', String(edge === 'strip' && this.layout.folded ? LIMITS.strip[0] : this.layout[edge]));
    }
  }

  private save(): void {
    try { localStorage.setItem(KEY, JSON.stringify(this.layout)); } catch { return; }
  }
}
