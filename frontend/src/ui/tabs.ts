import { el, patchList, setAttr, setText, setTitle } from './dom';
import { icon } from './icons';

export interface SiteTab {
  id: string;
  title: string;
  active: boolean;
}

export interface SiteTabHooks {
  activate(id: string): void;
  close(id: string): void;
  add(): void;
}

export class SiteTabs {
  private readonly list: HTMLElement;

  constructor(private readonly host: HTMLElement, hooks: SiteTabHooks) {
    this.list = el('<div class="fp-tab-list"></div>');
    const add = el<HTMLButtonElement>(`<button class="fp-tab-add" type="button" title="Open a site" aria-label="Open a site">${icon('plus', 14)}</button>`);
    host.append(this.list, add);
    add.addEventListener('click', () => hooks.add());
    host.addEventListener('click', (e) => {
      const target = e.target as HTMLElement;
      const tab = target.closest<HTMLElement>('.fp-tab');
      if (!tab?.dataset.key) return;
      if (target.closest('.fp-tab-close')) hooks.close(tab.dataset.key);
      else hooks.activate(tab.dataset.key);
    });
    host.addEventListener('auxclick', (e) => {
      const tab = (e.target as HTMLElement).closest<HTMLElement>('.fp-tab');
      if (e.button === 1 && tab?.dataset.key) { e.preventDefault(); hooks.close(tab.dataset.key); }
    });
    host.addEventListener('mousedown', (e) => {
      if (e.button === 1 && (e.target as HTMLElement).closest('.fp-tab')) e.preventDefault();
    });
    host.addEventListener('keydown', (e) => {
      const tab = (e.target as HTMLElement).closest<HTMLElement>('.fp-tab');
      if (!tab?.dataset.key || (e.target as HTMLElement).closest('.fp-tab-close')) return;
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); hooks.activate(tab.dataset.key); }
    });
  }

  render(tabs: SiteTab[]): void {
    patchList(this.list, tabs, {
      key: (t) => t.id,
      create: (t) => {
        const node = el(`<div class="fp-tab" role="tab" tabindex="0" aria-selected="false"><span class="fp-tab-name" translate="no"></span><button class="fp-tab-close" type="button" tabindex="-1" aria-label="Close tab" title="Close tab">${icon('close', 12)}</button></div>`);
        this.paint(node, t);
        return node;
      },
      update: (node, t) => this.paint(node, t),
    });
    const on = this.list.querySelector<HTMLElement>('.fp-tab[aria-selected="true"]');
    if (on) {
      const box = this.host.getBoundingClientRect();
      const r = on.getBoundingClientRect();
      if (r.left < box.left || r.right > box.right) on.scrollIntoView({ block: 'nearest', inline: 'nearest' });
    }
  }

  private paint(node: HTMLElement, t: SiteTab): void {
    setText(node.querySelector('.fp-tab-name'), t.title);
    setTitle(node, t.title);
    setAttr(node, 'aria-selected', String(t.active));
  }
}
