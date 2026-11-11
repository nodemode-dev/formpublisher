import type { Commands } from './commands';
import { el, q, setClass, setDisabled, setText } from './dom';
import { icon } from './icons';

export type MenuItem = string | SubMenu;
export interface SubMenu { label: string; items: MenuItem[] }
export interface MenuDef { label: string; items: MenuItem[] }

const isSub = (i: MenuItem): i is SubMenu => typeof i === 'object';
const MIN_DROP = 160;

export class PopupMenu {
  readonly panel: HTMLElement;
  private rows: Array<{ id: string; node: HTMLButtonElement }> = [];
  private subs: Array<{ sub: SubMenu; node: HTMLButtonElement; menu: PopupMenu }> = [];
  private key = '';
  private openSub: PopupMenu | null = null;
  private openRow: HTMLElement | null = null;
  onClose: (() => void) | null = null;
  onPick: ((id: string) => void) | null = null;

  constructor(private readonly commands: Commands, private readonly parent: PopupMenu | null = null) {
    this.panel = el('<div class="fp-menu" role="menu" hidden></div>');
    document.getElementById('overlay-root')?.appendChild(this.panel);
    this.panel.addEventListener('contextmenu', (e) => e.preventDefault());
    this.panel.addEventListener('pointerdown', (e) => e.preventDefault());
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

  constructor(host: HTMLElement, private readonly commands: Commands, defs: MenuDef[]) {
    defs.forEach((def, i) => {
      const btn = el<HTMLButtonElement>('<button class="fp-menu-btn" type="button" aria-haspopup="menu" aria-expanded="false"></button>');
      btn.textContent = def.label;
      btn.dataset.menu = def.label.toLowerCase();
      host.appendChild(btn);
      const menu = new PopupMenu(commands);
      menu.setItems(def.items);
      menu.onClose = () => { if (this.openIndex === i) { this.openIndex = -1; setClass(btn, 'is-open', false); btn.setAttribute('aria-expanded', 'false'); } };
      menu.onPick = (id) => this.pick(id);
      btn.addEventListener('pointerdown', (e) => { if (e.button !== 0) return; e.preventDefault(); if (this.openIndex === i) this.close(); else this.open(i); });
      btn.addEventListener('pointerenter', () => { if (this.openIndex >= 0 && this.openIndex !== i) this.open(i); });
      btn.addEventListener('keydown', (e) => this.onButtonKey(e, i));
      this.menus.push({ btn, menu, def });
    });
    document.addEventListener('pointerdown', (e) => {
      if (this.openIndex < 0) return;
      const m = this.menus[this.openIndex];
      const t = e.target as Node;
      if (!m.menu.contains(t) && !m.btn.contains(t)) this.close();
    }, true);
    document.addEventListener('keydown', (e) => this.onKey(e), true);
    window.addEventListener('blur', () => this.close());
    window.addEventListener('resize', () => this.close());
  }

  get isOpen(): boolean { return this.openIndex >= 0; }

  private pick(id: string): void {
    const back = this.prior;
    this.close();
    if (back && back.isConnected) back.focus();
    this.commands.run(id);
  }

  private onButtonKey(e: KeyboardEvent, i: number): void {
    if (e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ') { e.preventDefault(); this.open(i, true); }
    else if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
      e.preventDefault();
      const next = (i + (e.key === 'ArrowRight' ? 1 : -1) + this.menus.length) % this.menus.length;
      this.menus[next].btn.focus();
    }
  }

  private onKey(e: KeyboardEvent): void {
    if (this.openIndex < 0) return;
    const m = this.menus[this.openIndex];
    const leaf = m.menu.deepest();
    const stop = (): void => { e.preventDefault(); e.stopPropagation(); };
    switch (e.key) {
      case 'Escape': stop(); this.close(true); break;
      case 'Tab': this.close(); break;
      case 'ArrowDown': stop(); leaf.focusAt('next'); break;
      case 'ArrowUp': stop(); leaf.focusAt('prev'); break;
      case 'Home': stop(); leaf.focusAt('first'); break;
      case 'End': stop(); leaf.focusAt('last'); break;
      case 'ArrowRight': {
        stop();
        const sub = leaf.focusedSub();
        if (sub) { leaf.showSubFor(sub); sub.focusAt('first'); }
        else this.open((this.openIndex + 1) % this.menus.length, true);
        break;
      }
      case 'ArrowLeft': {
        stop();
        const up = leaf.parentMenu();
        if (up) { const row = up.focusRow(); up.closeSub(); row?.focus(); }
        else this.open((this.openIndex - 1 + this.menus.length) % this.menus.length, true);
        break;
      }
      default: break;
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
    m.menu.setItems(m.def.items);
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
