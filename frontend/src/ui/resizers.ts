import type { Pane } from '../app-api';

const KEY = 'formpublisher.layout';

interface Layout { strip: number; props: number; hidden: Pane[] }

const LIMITS = { strip: [160, 420], props: [240, 520] } as const;

function read(): Layout {
  const base: Layout = { strip: 232, props: 308, hidden: [] };
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) || '{}') as Partial<Layout>;
    const clamp = (v: unknown, lim: readonly [number, number], d: number): number => (typeof v === 'number' && Number.isFinite(v) ? Math.min(lim[1], Math.max(lim[0], Math.round(v))) : d);
    return {
      strip: clamp(raw.strip, LIMITS.strip, base.strip),
      props: clamp(raw.props, LIMITS.props, base.props),
      hidden: Array.isArray(raw.hidden) ? raw.hidden.filter((p): p is Pane => p === 'strip' || p === 'props' || p === 'bottom') : [],
    };
  } catch {
    return base;
  }
}

export class LayoutState {
  private layout: Layout = read();

  constructor(private readonly root: HTMLElement) {
    root.style.setProperty('--fp-strip-w', `${this.layout.strip}px`);
    root.style.setProperty('--fp-props-w', `${this.layout.props}px`);
    for (const p of this.layout.hidden) root.classList.add(`is-${p}-hidden`);
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
    for (const handle of resizers) {
      const edge = handle.dataset.edge === 'props' ? 'props' : 'strip';
      handle.addEventListener('pointerdown', (e) => {
        if (e.button !== 0) return;
        e.preventDefault();
        handle.setPointerCapture(e.pointerId);
        handle.classList.add('is-dragging');
        const startX = e.clientX;
        const startW = this.layout[edge];
        const move = (ev: PointerEvent): void => {
          const dx = ev.clientX - startX;
          const raw = edge === 'strip' ? startW + dx : startW - dx;
          const w = Math.min(LIMITS[edge][1], Math.max(LIMITS[edge][0], Math.round(raw)));
          this.layout[edge] = w;
          this.root.style.setProperty(edge === 'strip' ? '--fp-strip-w' : '--fp-props-w', `${w}px`);
        };
        const stop = (): void => {
          handle.classList.remove('is-dragging');
          handle.removeEventListener('pointermove', move);
          handle.removeEventListener('pointerup', stop);
          handle.removeEventListener('pointercancel', stop);
          this.save();
        };
        handle.addEventListener('pointermove', move);
        handle.addEventListener('pointerup', stop);
        handle.addEventListener('pointercancel', stop);
      });
    }
  }

  private save(): void {
    try { localStorage.setItem(KEY, JSON.stringify(this.layout)); } catch { return; }
  }
}
