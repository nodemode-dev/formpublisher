import type { Commands } from './commands';
import { anyDialogOpen } from './dialogs';
import { el, isMac, q, setClass, setDisabled, setText } from './dom';
import { icon } from './icons';

export type MenuItem = string | SubMenu;
export interface SubMenu { label: string; items: MenuItem[] }
export interface MenuDef { label: string; items: MenuItem[] | (() => MenuItem[]) }

export const itemsOf = (def: MenuDef): MenuItem[] => (typeof def.items === 'function' ? def.items() : def.items);

const isSub = (i: MenuItem): i is SubMenu => typeof i === 'object';
const MIN_DROP = 160;
const TYPE_AHEAD_MS = 700;

export class PopupMenu {
  readonly panel: HTMLElement;
  private rows: Array<{ id: string; node: HTMLButtonElement }> = [];
  private subs: Array<{ sub: SubMenu; node: HTMLButtonElement; menu: PopupMenu }> = [];
  private key = '';
  private openSub: PopupMenu | null = null;
  private openRow: HTMLElement | null = null;
  private subTop = 0;
  onClose: (() => void) | null = null;
  onPick: ((id: string) => void) | null = null;

  constructor(private readonly commands: Commands, private readonly parent: PopupMenu | null = null) {
    this.panel = el('<div class="fp-menu" role="menu" hidden></div>');
    document.getElementById('overlay-root')?.appendChild(this.panel);
    this.panel.addEventListener('contextmenu', (e) => e.preventDefault());
    this.panel.addEventListener('pointerdown', (e) => e.preventDefault());
    this.panel.addEventListener('scroll', () => { if (this.panel.scrollTop !== this.subTop) this.closeSub(); }, { passive: true });
  }

  get isOpen(): boolean { return !this.panel.hidden; }

  get submenu(): PopupMenu | null { return this.openSub && this.openSub.isOpen ? this.openSub : null; }

  contains(t: Node): boolean { return this.panel.contains(t) || !!this.openSub?.contains(t); }

  deepest(): PopupMenu { let m: PopupMenu = this; while (m.submenu) m = m.submenu; return m; }

  parentMenu(): PopupMenu | null { return this.parent; }

  setItems(items: MenuItem[]): void {
    const key = JSON.stringify(items);
    if (key === this.key) return;
    this.key = key;
    this.closeSub();
    for (const s of this.subs) s.menu.panel.remove();
    this.panel.textContent = '';
    this.rows = [];
    this.subs = [];
    this.panel.classList.toggle('has-checks', items.some((i) => typeof i === 'string' && i !== '-' && !!this.commands.get(i)?.checked));
    for (const item of items) {
      if (item === '-') { this.panel.appendChild(el('<div class="fp-menu-sep" role="separator"></div>')); continue; }
      if (isSub(item)) {
        const node = el<HTMLButtonElement>(`<button class="fp-menu-item fp-menu-sub" role="menuitem" aria-haspopup="menu" type="button" tabindex="-1"><span class="fp-menu-check"></span><span class="fp-menu-label"></span><span class="fp-menu-keys">${icon('chevronRight', 12)}</span></button>`);
        setText(q(node, '.fp-menu-label'), item.label);
        const menu = new PopupMenu(this.commands, this);
        menu.setItems(item.items);
        node.addEventListener('pointerenter', () => this.showSub(menu, node));
        node.addEventListener('click', () => this.showSub(menu, node));
        this.subs.push({ sub: item, node, menu });
        this.panel.appendChild(node);
        continue;
      }
      const cmd = this.commands.get(item);
      if (!cmd) continue;
      const node = el<HTMLButtonElement>(`<button class="fp-menu-item" role="menuitem" type="button" tabindex="-1"><span class="fp-menu-check">${icon('check', 14)}</span><span class="fp-menu-label"></span><span class="fp-menu-keys"></span></button>`);
      node.dataset.cmd = item;
      node.addEventListener('pointerenter', () => this.closeSub());
      node.addEventListener('click', () => this.root().onPick?.(item));
      this.rows.push({ id: item, node });
      this.panel.appendChild(node);
    }
    this.refresh();
  }

  root(): PopupMenu { let m: PopupMenu = this; while (m.parent) m = m.parent; return m; }

  focusables(): HTMLButtonElement[] {
    return Array.from(this.panel.querySelectorAll<HTMLButtonElement>(':scope > .fp-menu-item')).filter((b) => !b.disabled);
  }

  focusAt(at: 'first' | 'last' | 'next' | 'prev'): void {
    const list = this.focusables();
    if (!list.length) return;
    const cur = list.indexOf(document.activeElement as HTMLButtonElement);
    const i = at === 'first' ? 0 : at === 'last' ? list.length - 1 : at === 'next' ? (cur + 1) % list.length : (cur <= 0 ? list.length - 1 : cur - 1);
    list[i].focus();
  }

  focusedSub(): PopupMenu | null {
    const active = document.activeElement;
    return this.subs.find((s) => s.node === active)?.menu ?? null;
  }

  showSubFor(menu: PopupMenu): void {
    const found = this.subs.find((s) => s.menu === menu);
    if (found) this.showSub(menu, found.node);
  }

  private showSub(menu: PopupMenu, row: HTMLElement): void {
    if (this.openSub === menu && menu.isOpen) return;
    this.closeSub();
    this.openSub = menu;
    this.openRow = row;
    this.subTop = this.panel.scrollTop;
    setClass(row, 'is-open', true);
    menu.onClose = () => setClass(row, 'is-open', false);
    menu.openBeside(row.getBoundingClientRect());
  }

  closeSub(): void {
    const s = this.openSub;
    this.openSub = null;
    this.openRow = null;
    s?.close();
  }

  focusRow(): HTMLElement | null { return this.openRow; }

  openAt(x: number, y: number): void {
    this.refresh();
    this.panel.style.visibility = 'hidden';
    this.panel.style.maxHeight = `${Math.max(MIN_DROP, window.innerHeight - y - 8)}px`;
    this.panel.hidden = false;
    this.panel.scrollTop = 0;
    const w = this.panel.offsetWidth;
    const left = Math.max(4, Math.min(x, window.innerWidth - w - 4));
    this.panel.style.left = `${Math.round(left)}px`;
    this.panel.style.top = `${Math.round(y)}px`;
    this.panel.style.visibility = '';
  }

  private openBeside(row: DOMRect): void {
    this.refresh();
    this.panel.style.visibility = 'hidden';
    this.panel.hidden = false;
    this.panel.scrollTop = 0;
    const w = this.panel.offsetWidth;
    const h = this.panel.offsetHeight;
    const pad = 4;
    const right = row.right - 2;
    const left = row.left - w + 2;
    const x = right + w <= window.innerWidth - pad ? right : Math.max(pad, left);
    const y = Math.max(pad, Math.min(row.top - pad, window.innerHeight - h - pad));
    this.panel.style.left = `${Math.round(x)}px`;
    this.panel.style.top = `${Math.round(y)}px`;
    this.panel.style.visibility = '';
  }

  refresh(): void {
    for (const r of this.rows) {
      const cmd = this.commands.get(r.id);
      if (!cmd) continue;
      setText(q(r.node, '.fp-menu-label'), this.commands.label(cmd));
      setText(q(r.node, '.fp-menu-keys'), this.commands.keyLabel(cmd));
      setDisabled(r.node, !this.commands.enabled(cmd));
      setClass(r.node, 'is-checked', !!cmd.checked?.());
    }
    for (const s of this.subs) s.menu.refresh();
  }

  close(): void {
    this.closeSub();
    if (this.panel.hidden) return;
    this.panel.hidden = true;
    this.onClose?.();
  }
}

export class MenuBar {
  private readonly menus: Array<{ btn: HTMLButtonElement; menu: PopupMenu; def: MenuDef }> = [];
  private openIndex = -1;
  private prior: HTMLElement | null = null;
  private barBack: HTMLElement | null = null;
  private altLone = false;
  private typed = '';
  private typedAt = 0;

  constructor(host: HTMLElement, private readonly commands: Commands, defs: MenuDef[]) {
    defs.forEach((def, i) => {
      const btn = el<HTMLButtonElement>('<button class="fp-menu-btn" type="button" aria-haspopup="menu" aria-expanded="false"></button>');
      btn.textContent = def.label;
      btn.dataset.menu = def.label.toLowerCase();
      host.appendChild(btn);
      const menu = new PopupMenu(commands);
      menu.setItems(itemsOf(def));
      menu.onClose = () => { if (this.openIndex === i) { this.openIndex = -1; setClass(btn, 'is-open', false); btn.setAttribute('aria-expanded', 'false'); } };
      menu.onPick = (id) => this.pick(id);
      btn.addEventListener('pointerdown', (e) => { if (e.button !== 0) return; e.preventDefault(); if (this.openIndex === i) this.close(); else this.open(i); });
      btn.addEventListener('pointerenter', () => { if (this.openIndex >= 0 && this.openIndex !== i) this.open(i); });
      this.menus.push({ btn, menu, def });
    });
    document.addEventListener('pointerdown', (e) => {
      this.altLone = false;
      if (this.openIndex < 0) return;
      const m = this.menus[this.openIndex];
      const t = e.target as Node;
      if (!m.menu.contains(t) && !m.btn.contains(t)) this.close();
    }, true);
    document.addEventListener('keydown', (e) => this.onKey(e), true);
    document.addEventListener('keyup', (e) => this.altUp(e), true);
    window.addEventListener('blur', () => { this.altLone = false; setClass(document.documentElement, 'is-menu-mnemonics', false); this.close(); });
    window.addEventListener('resize', () => this.close());
  }

  get isOpen(): boolean { return this.openIndex >= 0; }

  private usable(): boolean {
    return this.menus.length > 0 && !anyDialogOpen() && !document.documentElement.classList.contains('has-native-menus');
  }

  private initial(btn: HTMLElement): string {
    return (btn.textContent ?? '').trim().charAt(0).toLowerCase();
  }

  private pick(id: string): void {
    const back = this.prior ?? this.barBack;
    this.barBack = null;
    this.close();
    if (back && back.isConnected) back.focus();
    this.commands.run(id);
  }

  private altUp(e: KeyboardEvent): void {
    if (e.key !== 'Alt') return;
    setClass(document.documentElement, 'is-menu-mnemonics', false);
    if (!this.altLone) return;
    this.altLone = false;
    if (this.openIndex >= 0 || !this.usable()) return;
    e.preventDefault();
    const from = document.activeElement;
    if (from instanceof HTMLElement && !this.menus.some((m) => m.btn === from)) this.barBack = from;
    this.menus[0].btn.focus();
  }

  private leaveBar(): void {
    const back = this.barBack;
    this.barBack = null;
    if (back && back.isConnected && back !== document.body) back.focus();
    else (document.activeElement as HTMLElement | null)?.blur();
  }

  private leave(leaf: PopupMenu): boolean {
    const up = leaf.parentMenu();
    if (!up) return false;
    const row = up.focusRow();
    up.closeSub();
    row?.focus();
    return true;
  }

  private onKey(e: KeyboardEvent): void {
    const stop = (): void => { e.preventDefault(); e.stopPropagation(); };
    const count = this.menus.length;
    if (e.key === 'Alt') {
      if (!e.repeat && !isMac && this.openIndex < 0 && this.usable() && !e.ctrlKey && !e.metaKey && !e.shiftKey) {
        this.altLone = true;
        setClass(document.documentElement, 'is-menu-mnemonics', true);
      }
      return;
    }
    this.altLone = false;
    if (this.openIndex < 0) {
      if (!this.usable() || e.ctrlKey || e.metaKey) return;
      const at = this.menus.findIndex((m) => m.btn === document.activeElement);
      if (at >= 0 && !e.altKey && !e.shiftKey) {
        const focus = (i: number): void => this.menus[(i + count) % count].btn.focus();
        if (e.key === 'ArrowRight') { stop(); focus(at + 1); return; }
        if (e.key === 'ArrowLeft') { stop(); focus(at - 1); return; }
        if (e.key === 'Home') { stop(); focus(0); return; }
        if (e.key === 'End') { stop(); focus(-1); return; }
        if (e.key === 'ArrowDown' || e.key === 'ArrowUp' || e.key === 'Enter' || e.key === ' ') { stop(); this.open(at, true); return; }
        if (e.key === 'Escape') { stop(); this.leaveBar(); return; }
        if (e.key.length === 1 && /\S/.test(e.key)) {
          const hit = this.menus.findIndex((m) => this.initial(m.btn) === e.key.toLowerCase());
          if (hit >= 0) { stop(); this.open(hit, true); }
          return;
        }
      }
      if (e.key === 'F10' && !e.altKey && !e.shiftKey) { stop(); this.open(0, true); return; }
      if (!e.altKey || e.shiftKey || isMac || !/^Key[A-Z]$/.test(e.code)) return;
      const letter = e.code.slice(3).toLowerCase();
      const hit = this.menus.findIndex((m) => this.initial(m.btn) === letter);
      if (hit < 0) return;
      stop();
      this.open(hit, true);
      return;
    }
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const leaf = this.menus[this.openIndex].menu.deepest();
    const rows = leaf.focusables();
    const at = rows.indexOf(document.activeElement as HTMLButtonElement);
    if (e.key === 'ArrowDown') { stop(); leaf.focusAt('next'); }
    else if (e.key === 'ArrowUp') { stop(); leaf.focusAt('prev'); }
    else if (e.key === 'Home') { stop(); leaf.focusAt('first'); }
    else if (e.key === 'End') { stop(); leaf.focusAt('last'); }
    else if (e.key === 'ArrowRight') {
      stop();
      const sub = leaf.focusedSub();
      if (sub) { leaf.showSubFor(sub); sub.focusAt('first'); }
      else this.open((this.openIndex + 1) % count, true);
    } else if (e.key === 'ArrowLeft') {
      stop();
      if (!this.leave(leaf)) this.open((this.openIndex - 1 + count) % count, true);
    } else if ((e.key === 'Enter' || e.key === ' ') && at >= 0) {
      stop();
      const sub = leaf.focusedSub();
      if (sub) { leaf.showSubFor(sub); sub.focusAt('first'); }
      else rows[at].click();
    } else if (e.key === 'Escape') {
      stop();
      if (!this.leave(leaf)) this.close(true);
    } else if (e.key === 'Tab') {
      stop();
      this.close(true);
    } else if (e.key.length === 1 && /\S/.test(e.key) && !e.shiftKey) {
      stop();
      const now = performance.now();
      const word = now - this.typedAt < TYPE_AHEAD_MS ? this.typed + e.key.toLowerCase() : e.key.toLowerCase();
      this.typed = word;
      this.typedAt = now;
      const starts = (n: HTMLElement): boolean => (n.querySelector('.fp-menu-label')?.textContent ?? '').trim().toLowerCase().startsWith(word);
      const from = word.length === 1 ? at + 1 : Math.max(0, at);
      for (let k = 0; k < rows.length; k++) {
        const n = rows[(from + k) % rows.length];
        if (starts(n)) { n.focus(); break; }
      }
    }
  }

  open(i: number, focus = false): void {
    const wasOpen = this.openIndex >= 0;
    const back = this.prior;
    this.close();
    if (!wasOpen) {
      const a = document.activeElement as HTMLElement | null;
      this.prior = a && !a.classList.contains('fp-menu-btn') ? a : null;
    } else this.prior = back;
    const m = this.menus[i];
    m.menu.setItems(itemsOf(m.def));
    const b = m.btn.getBoundingClientRect();
    this.openIndex = i;
    setClass(m.btn, 'is-open', true);
    m.btn.setAttribute('aria-expanded', 'true');
    m.menu.openAt(b.left, b.bottom + 4);
    if (focus) m.menu.focusAt('first');
  }

  close(restore = false): void {
    if (this.openIndex < 0) return;
    const m = this.menus[this.openIndex];
    this.openIndex = -1;
    setClass(m.btn, 'is-open', false);
    m.btn.setAttribute('aria-expanded', 'false');
    m.menu.close();
    if (restore) {
      const back = this.prior;
      if (back && back.isConnected) back.focus(); else m.btn.focus();
    }
  }
}
