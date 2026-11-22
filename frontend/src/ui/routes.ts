import type { RouteInfo } from '../api';
import { on, type RouteStatus } from '../events';
import { el, patchList, setAttr, setClass, setText } from './dom';

const STATUS_TEXT: Record<RouteStatus, string> = { ok: 'No problems', warn: 'Warnings', error: 'Errors' };

export interface RouteListHooks {
  select(path: string): void;
}

export class RouteList {
  private selected: string | null = null;
  private items: RouteInfo[] = [];
  private siteId: string | null = null;
  private status: Record<string, RouteStatus> = {};
  private thumbs: Record<string, string> = {};

  constructor(private readonly host: HTMLElement, private readonly hooks: RouteListHooks) {
    host.addEventListener('click', (e) => {
      const row = (e.target as HTMLElement).closest<HTMLElement>('.fp-route');
      if (row?.dataset.key) hooks.select(row.dataset.key);
    });
    host.addEventListener('keydown', (e) => this.onKey(e));
    host.closest('.fp-app')?.addEventListener('fp-layout', () => {
      for (const node of Array.from(this.host.querySelectorAll<HTMLElement>('.fp-route'))) this.paintLabel(node, node.dataset.key ?? '');
    });
    on('fp:checks', (d) => {
      if (d.siteId !== this.siteId) return;
      this.status = d.status ?? {};
      this.thumbs = d.thumbs ?? {};
      for (const node of Array.from(this.host.querySelectorAll<HTMLElement>('.fp-route'))) this.paintChecks(node, node.dataset.key ?? '');
    });
  }

  setSite(siteId: string | null): void {
    if (siteId === this.siteId) return;
    this.siteId = siteId;
    this.status = {};
    this.thumbs = {};
    for (const node of Array.from(this.host.querySelectorAll<HTMLElement>('.fp-route'))) this.paintChecks(node, node.dataset.key ?? '');
  }

  render(items: readonly RouteInfo[], selected: string | null): void {
    this.items = items.slice();
    this.selected = selected;
    const tabStop = selected !== null && items.some((r) => r.path === selected) ? selected : items[0]?.path;
    patchList(this.host, this.items, {
      key: (r) => r.path,
      create: (r) => {
        const node = el(`<button class="fp-route" type="button" role="option" tabindex="-1" aria-selected="false"><span class="fp-route-thumb" aria-hidden="true"></span><span class="fp-route-path" translate="no"></span><span class="fp-route-page" translate="no"></span><span class="fp-route-dot"></span></button>`);
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
    this.paintLabel(node, r.path);
    this.paintChecks(node, r.path);
  }

  private paintLabel(node: HTMLElement, path: string): void {
    const folded = this.host.closest('.fp-app')?.classList.contains('is-strip-folded') === true;
    if (folded) setAttr(node, 'aria-label', path);
    else if (node.hasAttribute('aria-label')) node.removeAttribute('aria-label');
  }

  private paintChecks(node: HTMLElement, path: string): void {
    const state = this.status[path];
    const dot = node.querySelector<HTMLElement>('.fp-route-dot');
    if (dot) {
      setClass(dot, 'is-ok', state === 'ok');
      setClass(dot, 'is-warn', state === 'warn');
      setClass(dot, 'is-error', state === 'error');
      setAttr(dot, 'title', state ? STATUS_TEXT[state] : 'Not checked');
    }
    const box = node.querySelector<HTMLElement>('.fp-route-thumb');
    if (!box) return;
    const url = this.thumbs[path] ?? '';
    let img = box.querySelector('img');
    if (!url) {
      img?.remove();
      return;
    }
    if (!img) {
      img = document.createElement('img');
      img.alt = '';
      img.decoding = 'async';
      img.draggable = false;
      const shown = img;
      img.addEventListener('load', () => setClass(shown, 'is-loaded', true));
      box.appendChild(img);
    }
    if (img.getAttribute('src') !== url) {
      setClass(img, 'is-loaded', false);
      img.src = url;
    }
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
