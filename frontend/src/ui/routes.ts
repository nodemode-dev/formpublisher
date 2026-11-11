import type { RouteInfo } from '../api';
import { el, patchList, setAttr, setText } from './dom';

export interface RouteListHooks {
  select(path: string): void;
}

export class RouteList {
  private selected: string | null = null;
  private items: RouteInfo[] = [];

  constructor(private readonly host: HTMLElement, private readonly hooks: RouteListHooks) {
    host.addEventListener('click', (e) => {
      const row = (e.target as HTMLElement).closest<HTMLElement>('.fp-route');
      if (row?.dataset.key) hooks.select(row.dataset.key);
    });
    host.addEventListener('keydown', (e) => this.onKey(e));
  }

  render(items: readonly RouteInfo[], selected: string | null): void {
    this.items = items.slice();
    this.selected = selected;
    const tabStop = selected !== null && items.some((r) => r.path === selected) ? selected : items[0]?.path;
    patchList(this.host, this.items, {
      key: (r) => r.path,
      create: (r) => {
        const node = el(`<button class="fp-route" type="button" role="option" tabindex="-1" aria-selected="false"><span class="fp-route-path" translate="no"></span><span class="fp-route-page" translate="no"></span></button>`);
        this.paint(node, r, tabStop);
        return node;
      },
      update: (node, r) => this.paint(node, r, tabStop),
    });
  }

  private paint(node: HTMLElement, r: RouteInfo, tabStop: string | undefined): void {
    setText(node.querySelector('.fp-route-path'), r.path);
    setText(node.querySelector('.fp-route-page'), r.page);
    setAttr(node, 'aria-selected', String(r.path === this.selected));
    setAttr(node, 'tabindex', r.path === tabStop ? '0' : '-1');
    setAttr(node, 'title', r.page ? `${r.path} · ${r.page}` : r.path);
  }

  private onKey(e: KeyboardEvent): void {
    const row = (e.target as HTMLElement).closest<HTMLElement>('.fp-route');
    if (!row) return;
    const rows = Array.from(this.host.querySelectorAll<HTMLElement>('.fp-route'));
    const at = rows.indexOf(row);
    let to = -1;
    if (e.key === 'ArrowDown') to = Math.min(rows.length - 1, at + 1);
    else if (e.key === 'ArrowUp') to = Math.max(0, at - 1);
    else if (e.key === 'Home') to = 0;
    else if (e.key === 'End') to = rows.length - 1;
    else if (e.key === 'PageDown') to = Math.min(rows.length - 1, at + 8);
    else if (e.key === 'PageUp') to = Math.max(0, at - 8);
    else if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      if (row.dataset.key) this.hooks.select(row.dataset.key);
      return;
    }
    if (to < 0) return;
    e.preventDefault();
    rows.forEach((r, i) => setAttr(r, 'tabindex', i === to ? '0' : '-1'));
    rows[to].focus();
    rows[to].scrollIntoView({ block: 'nearest' });
  }
}
