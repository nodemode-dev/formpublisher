import '../styles/dropdown.css';
import { el, escapeHtml, patchList, setAttr, setClass, setHidden, setText } from './dom';
import { icon } from './icons';

export interface DropdownOption {
  value: string;
  label: string;
  detail?: string;
  disabled?: boolean;
  literal?: boolean;
}

export interface DropdownSpec {
  label: string;
  options: readonly DropdownOption[];
  value?: string;
  cls?: string;
  title?: string;
  data?: Record<string, string>;
}

export interface DropdownInit {
  label: string;
  options: readonly DropdownOption[];
  value?: string;
  change?: (value: string) => void;
}

const TOP_LAYER = typeof HTMLElement !== 'undefined' && 'showPopover' in HTMLElement.prototype;
const TYPE_AHEAD_MS = 600;
const PAGE = 10;
const GAP = 4;
const PAD = 4;

const keyOf = (o: DropdownOption): string => `v:${o.value}`;
const painted = new WeakMap<Element, string>();
let seq = 0;

const textHtml = (text: string, literal: boolean, detail: string): string =>
  `<span class="fp-dd-text"><span class="fp-dd-l"${literal ? ' translate="no"' : ''}>${escapeHtml(text)}</span><span class="fp-dd-d"${detail ? '' : ' hidden'}>${escapeHtml(detail)}</span></span>`;

const pickOf = (options: readonly DropdownOption[], value: string | undefined): DropdownOption | null =>
  (value !== undefined ? options.find((o) => o.value === value) : undefined) ?? options.find((o) => !o.disabled) ?? null;

export function dropdownHtml(spec: DropdownSpec): string {
  const cur = pickOf(spec.options, spec.value);
  const data = Object.entries(spec.data ?? {}).map(([k, v]) => ` data-${k}="${escapeHtml(v)}"`).join('');
  const title = spec.title ? ` title="${escapeHtml(spec.title)}"` : '';
  const sizer = spec.options.map((o) => `<span class="fp-dd-size" data-key="${escapeHtml(keyOf(o))}">${textHtml(o.label, !!o.literal, o.detail ?? '')}</span>`).join('');
  return `<button class="fp-dd${spec.cls ? ` ${spec.cls}` : ''}" type="button" aria-haspopup="listbox" aria-expanded="false" aria-label="${escapeHtml(spec.label)}"${title}${data}><span class="fp-dd-face"><span class="fp-dd-cur">${textHtml(cur?.label ?? '', !!cur?.literal, cur?.detail ?? '')}</span><span class="fp-dd-sizer" aria-hidden="true">${sizer}</span></span>${icon('chevronDown', 12)}</button>`;
}

function paintText(box: Element, text: string, literal: boolean, detail: string): void {
  const sig = `${literal ? 1 : 0}\u0000${text}\u0000${detail}`;
  if (painted.get(box) === sig) return;
  painted.set(box, sig);
  const l = box.querySelector('.fp-dd-l');
  const d = box.querySelector<HTMLElement>('.fp-dd-d');
  if (l) {
    if (literal) setAttr(l, 'translate', 'no'); else if (l.hasAttribute('translate')) l.removeAttribute('translate');
    if (l.textContent !== text) l.textContent = text;
  }
  if (d) {
    if (d.textContent !== detail) d.textContent = detail;
    setHidden(d, !detail);
  }
}

export class Dropdown {
  readonly button: HTMLButtonElement;
  private readonly pop: HTMLElement;
  private readonly cur: HTMLElement;
  private readonly sizer: HTMLElement;
  private readonly id: string;
  private readonly change: ((value: string) => void) | null;
  private opts: DropdownOption[] = [];
  private nodes: HTMLElement[] = [];
  private shorts = new Map<string, string>();
  private chosen = -1;
  private active = -1;
  private typed = '';
  private typedAt = 0;
  private optSeq = 0;
  private live = false;
  private readonly outside = (e: Event): void => {
    const t = e.target as Node | null;
    if (t && (this.pop.contains(t) || this.button.contains(t))) return;
    this.close(false);
  };
  private readonly scrolled = (e: Event): void => {
    const t = e.target as Node | null;
    if (t && t !== document && this.pop.contains(t)) return;
    this.close(false);
  };
  private readonly dismiss = (): void => this.close(false);

  static create(spec: DropdownSpec, change?: (value: string) => void): Dropdown {
    return new Dropdown(el<HTMLButtonElement>(dropdownHtml(spec)), { label: spec.label, options: spec.options, value: spec.value, change });
  }

  constructor(button: HTMLButtonElement, init: DropdownInit) {
    this.button = button;
    this.id = `fp-dd-${++seq}`;
    this.change = init.change ?? null;
    const cur = button.querySelector<HTMLElement>('.fp-dd-cur');
    const sizer = button.querySelector<HTMLElement>('.fp-dd-sizer');
    if (!cur || !sizer) throw new Error('dropdown: the button is not from dropdownHtml');
    this.cur = cur;
    this.sizer = sizer;
    this.pop = el(`<div class="fp-pop fp-dd-pop" role="listbox" tabindex="-1"${TOP_LAYER ? ' popover="manual"' : ' hidden'}></div>`);
    this.pop.id = this.id;
    setAttr(this.pop, 'aria-label', init.label);
    setAttr(button, 'aria-controls', this.id);
    (document.getElementById('overlay-root') ?? document.body).appendChild(this.pop);
    this.setOptions(init.options, init.value);
    this.wire();
  }

  get value(): string {
    return this.chosen >= 0 ? this.opts[this.chosen].value : '';
  }

  get isOpen(): boolean {
    return this.live;
  }

  options(): readonly DropdownOption[] {
    return this.opts;
  }

  selected(): DropdownOption | null {
    return this.chosen >= 0 ? this.opts[this.chosen] : null;
  }

  set(value: string): void {
    const i = this.opts.findIndex((o) => o.value === value);
    if (i === this.chosen) return;
    this.chosen = i;
    this.paintChosen();
  }

  setOptions(list: readonly DropdownOption[], value?: string): void {
    const keep = value ?? this.value;
    this.opts = list.map((o) => ({ ...o }));
    const pick = pickOf(this.opts, keep);
    this.chosen = pick ? this.opts.indexOf(pick) : -1;
    patchList(this.sizer, this.opts, {
      key: keyOf,
      create: (o) => {
        const node = el(`<span class="fp-dd-size">${textHtml('', false, '')}</span>`);
        this.paintSize(node, o);
        return node;
      },
      update: (node, o) => this.paintSize(node, o),
    });
    patchList(this.pop, this.opts, {
      key: keyOf,
      create: (o) => {
        const node = el(`<div class="fp-dd-opt" role="option" aria-selected="false">${icon('check', 14)}${textHtml('', false, '')}</div>`);
        node.id = `${this.id}-${++this.optSeq}`;
        this.paintOption(node, o);
        return node;
      },
      update: (node, o) => this.paintOption(node, o),
    });
    this.nodes = Array.from(this.pop.children) as HTMLElement[];
    if (this.active >= this.opts.length) this.active = this.chosen;
    this.paintChosen();
  }

  setShorts(shorts: ReadonlyMap<string, string> | null): void {
    const next = new Map(shorts ?? []);
    if (next.size === this.shorts.size && [...next].every(([k, v]) => this.shorts.get(k) === v)) return;
    this.shorts = next;
    for (const node of Array.from(this.sizer.children) as HTMLElement[]) {
      const o = this.opts.find((x) => keyOf(x) === node.dataset.key);
      if (o) this.paintSize(node, o);
    }
    this.paintChosen();
  }

  setDisabled(disabled: boolean): void {
    if (this.button.disabled !== disabled) this.button.disabled = disabled;
    if (disabled) this.close(false);
  }

  open(at?: 'first' | 'last'): void {
    if (this.live || this.button.disabled || !this.opts.length) return;
    this.live = true;
    this.active = at === 'first' ? this.step(-1, 1) : at === 'last' ? this.step(this.opts.length, -1) : this.chosen >= 0 ? this.chosen : this.step(-1, 1);
    this.paintActive();
    this.pop.style.minWidth = '';
    this.pop.style.maxHeight = '';
    if (TOP_LAYER) this.pop.showPopover(); else setHidden(this.pop, false);
    this.place();
    setAttr(this.button, 'aria-expanded', 'true');
    setClass(this.button, 'is-open', true);
    this.reveal();
    document.addEventListener('pointerdown', this.outside, true);
    document.addEventListener('scroll', this.scrolled, true);
    window.addEventListener('resize', this.dismiss);
    window.addEventListener('blur', this.dismiss);
  }

  close(restore = true): void {
    if (!this.live) return;
    this.live = false;
    document.removeEventListener('pointerdown', this.outside, true);
    document.removeEventListener('scroll', this.scrolled, true);
    window.removeEventListener('resize', this.dismiss);
    window.removeEventListener('blur', this.dismiss);
    if (TOP_LAYER) { if (this.pop.matches(':popover-open')) this.pop.hidePopover(); } else setHidden(this.pop, true);
    setAttr(this.button, 'aria-expanded', 'false');
    setClass(this.button, 'is-open', false);
    if (this.button.hasAttribute('aria-activedescendant')) this.button.removeAttribute('aria-activedescendant');
    this.typed = '';
    if (restore && document.activeElement !== this.button && this.button.isConnected) this.button.focus();
  }

  private paintSize(node: HTMLElement, o: DropdownOption): void {
    const short = this.shorts.get(o.value);
    paintText(node, short ?? o.label, !!o.literal || short !== undefined, o.detail ?? '');
  }

  private paintOption(node: HTMLElement, o: DropdownOption): void {
    paintText(node, o.label, !!o.literal, o.detail ?? '');
    const off = !!o.disabled;
    if (off) setAttr(node, 'aria-disabled', 'true'); else if (node.hasAttribute('aria-disabled')) node.removeAttribute('aria-disabled');
    setClass(node, 'is-disabled', off);
  }

  private paintChosen(): void {
    const o = this.selected();
    const short = o ? this.shorts.get(o.value) : undefined;
    paintText(this.cur, o ? short ?? o.label : '', !!o?.literal || short !== undefined, o?.detail ?? '');
    this.nodes.forEach((n, i) => {
      setAttr(n, 'aria-selected', String(i === this.chosen));
      setClass(n, 'is-chosen', i === this.chosen);
    });
  }

  private paintActive(): void {
    this.nodes.forEach((n, i) => setClass(n, 'is-active', i === this.active));
    const node = this.nodes[this.active];
    if (this.live && node) setAttr(this.button, 'aria-activedescendant', node.id);
    else if (this.button.hasAttribute('aria-activedescendant')) this.button.removeAttribute('aria-activedescendant');
  }

  private reveal(): void {
    const node = this.nodes[this.active];
    if (!node) return;
    const top = node.offsetTop;
    const bottom = top + node.offsetHeight;
    const pad = parseFloat(getComputedStyle(this.pop).paddingTop) || 0;
    if (top - pad < this.pop.scrollTop) this.pop.scrollTop = Math.max(0, top - pad);
    else if (bottom + pad > this.pop.scrollTop + this.pop.clientHeight) this.pop.scrollTop = bottom + pad - this.pop.clientHeight;
  }

  private place(): void {
    const r = this.button.getBoundingClientRect();
    const vw = document.documentElement.clientWidth;
    const vh = document.documentElement.clientHeight;
    this.pop.style.minWidth = `${Math.round(r.width)}px`;
    const below = vh - r.bottom - GAP - PAD;
    const above = r.top - GAP - PAD;
    const h = this.pop.offsetHeight;
    const down = h <= below || below >= above;
    const room = Math.max(0, Math.floor(down ? below : above));
    if (h > room) this.pop.style.maxHeight = `${room}px`;
    const height = Math.min(h, room);
    const w = this.pop.offsetWidth;
    const rtl = getComputedStyle(this.button).direction === 'rtl';
    const x = Math.max(PAD, Math.min(rtl ? r.right - w : r.left, vw - w - PAD));
    const y = down ? r.bottom + GAP : r.top - GAP - height;
    this.pop.style.left = `${Math.round(x)}px`;
    this.pop.style.top = `${Math.round(y)}px`;
    setClass(this.pop, 'is-above', !down);
  }

  private step(from: number, dir: 1 | -1): number {
    for (let i = from + dir; i >= 0 && i < this.opts.length; i += dir) if (!this.opts[i].disabled) return i;
    return from >= 0 && from < this.opts.length ? from : -1;
  }

  private move(to: number): void {
    if (to < 0 || to === this.active) return;
    this.active = to;
    this.paintActive();
    this.reveal();
  }

  private pick(i: number): void {
    const o = this.opts[i];
    if (!o || o.disabled) return;
    this.close(true);
    if (i === this.chosen) return;
    this.chosen = i;
    this.paintChosen();
    this.change?.(o.value);
  }

  private typeAhead(ch: string): void {
    const now = performance.now();
    this.typed = now - this.typedAt < TYPE_AHEAD_MS ? this.typed + ch.toLocaleLowerCase() : ch.toLocaleLowerCase();
    this.typedAt = now;
    const word = this.typed;
    const same = [...word].every((c) => c === word[0]);
    const needle = same ? word[0] : word;
    const base = this.live ? this.active : this.chosen;
    const from = same || word.length === 1 ? base + 1 : Math.max(0, base);
    const n = this.opts.length;
    for (let k = 0; k < n; k++) {
      const i = (((from + k) % n) + n) % n;
      if (this.opts[i].disabled) continue;
      const shown = (this.nodes[i]?.querySelector('.fp-dd-l')?.textContent ?? this.opts[i].label).trim().toLocaleLowerCase();
      if (shown.startsWith(needle)) { this.move(i); return; }
    }
  }

  private onKey(e: KeyboardEvent): void {
    if (e.isComposing || e.ctrlKey || e.metaKey) return;
    const take = (): void => { e.preventDefault(); e.stopPropagation(); };
    const printable = e.key.length === 1 && !e.altKey;
    if (!this.live) {
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp' || e.key === 'Enter' || e.key === ' ') { take(); this.open(); return; }
      if (e.key === 'Home' || e.key === 'End') { take(); this.open(e.key === 'Home' ? 'first' : 'last'); return; }
      if (printable && /\S/.test(e.key)) { take(); this.open(); this.typeAhead(e.key); }
      return;
    }
    switch (e.key) {
      case 'ArrowDown': take(); this.move(this.step(this.active, 1)); return;
      case 'ArrowUp':
        take();
        if (e.altKey) this.pick(this.active); else this.move(this.step(this.active, -1));
        return;
      case 'Home': take(); this.move(this.step(-1, 1)); return;
      case 'End': take(); this.move(this.step(this.opts.length, -1)); return;
      case 'PageDown': take(); this.move(this.step(Math.min(this.opts.length - 1, this.active + PAGE - 1), 1)); return;
      case 'PageUp': take(); this.move(this.step(Math.max(0, this.active - PAGE + 1), -1)); return;
      case 'Enter': take(); this.pick(this.active); return;
      case 'Escape': take(); this.close(true); return;
      case 'Tab': this.close(false); return;
      default: break;
    }
    if (e.key === ' ' && !(this.typed && performance.now() - this.typedAt < TYPE_AHEAD_MS)) { take(); this.pick(this.active); return; }
    if (printable) { take(); this.typeAhead(e.key); }
  }

  private wire(): void {
    let keyed = false;
    this.button.addEventListener('keydown', (e) => {
      keyed = e.key === 'Enter' || e.key === ' ';
      this.onKey(e);
    });
    this.button.addEventListener('keyup', (e) => { if (e.key === ' ' || e.key === 'Enter') e.preventDefault(); });
    this.button.addEventListener('click', () => {
      if (keyed) { keyed = false; return; }
      if (this.live) this.close(true); else this.open();
    });
    this.button.addEventListener('pointerdown', () => { keyed = false; });
    const hold = (e: Event): void => e.preventDefault();
    this.pop.addEventListener('pointerdown', hold);
    this.pop.addEventListener('mousedown', hold);
    this.pop.addEventListener('pointermove', (e) => {
      const node = (e.target as HTMLElement).closest<HTMLElement>('.fp-dd-opt');
      const i = node ? this.nodes.indexOf(node) : -1;
      if (i >= 0 && !this.opts[i].disabled && i !== this.active) { this.active = i; this.paintActive(); }
    });
    this.pop.addEventListener('click', (e) => {
      const node = (e.target as HTMLElement).closest<HTMLElement>('.fp-dd-opt');
      const i = node ? this.nodes.indexOf(node) : -1;
      if (i >= 0) this.pick(i);
    });
  }
}
