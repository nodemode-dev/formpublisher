import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { SiteTabs, type SiteTabHooks } from '../../../src/ui/tabs';
import { toast, dismissToast } from '../../../src/ui/toast';

function mount(): { host: HTMLElement; tabs: SiteTabs; calls: string[] } {
  document.body.innerHTML = '<div id="h"></div>';
  const host = document.getElementById('h') as HTMLElement;
  const calls: string[] = [];
  const hooks: SiteTabHooks = {
    activate: (id) => { calls.push(`activate:${id}`); },
    close: (id) => { calls.push(`close:${id}`); },
    add: () => { calls.push('add'); },
  };
  return { host, tabs: new SiteTabs(host, hooks), calls };
}

const names = (host: HTMLElement): string[] => Array.from(host.querySelectorAll('.fp-tab-name')).map((n) => n.textContent ?? '');

describe('site tabs', () => {
  it('shows one tab per open site with its title and marks only the active one selected', () => {
    const { host, tabs } = mount();
    tabs.render([{ id: 'a', title: 'Alpha', active: false }, { id: 'b', title: 'Beta', active: true }]);
    expect(names(host)).toEqual(['Alpha', 'Beta']);
    const sel = Array.from(host.querySelectorAll('.fp-tab')).map((n) => n.getAttribute('aria-selected'));
    expect(sel).toEqual(['false', 'true']);
  });

  it('patches the same tab node in place when the data arrives again with a new title', () => {
    const { host, tabs } = mount();
    tabs.render([{ id: 'a', title: 'Alpha', active: true }]);
    const first = host.querySelector('.fp-tab');
    tabs.render([{ id: 'a', title: 'Alpha renamed', active: false }]);
    const again = host.querySelector('.fp-tab');
    expect(again).toBe(first);
    expect(names(host)).toEqual(['Alpha renamed']);
    expect(again?.getAttribute('aria-selected')).toBe('false');
    expect(again?.getAttribute('title')).toBe('Alpha renamed');
  });

  it('drops tabs of sites that are no longer open and keeps the order sent', () => {
    const { host, tabs } = mount();
    tabs.render([{ id: 'a', title: 'A', active: true }, { id: 'b', title: 'B', active: false }, { id: 'c', title: 'C', active: false }]);
    tabs.render([{ id: 'c', title: 'C', active: true }, { id: 'a', title: 'A', active: false }]);
    expect(names(host)).toEqual(['C', 'A']);
  });

  it('clicking a tab activates it and clicking its close button closes it', () => {
    const { host, tabs, calls } = mount();
    tabs.render([{ id: 'a', title: 'A', active: false }]);
    (host.querySelector('.fp-tab-name') as HTMLElement).click();
    (host.querySelector('.fp-tab-close') as HTMLElement).click();
    expect(calls).toEqual(['activate:a', 'close:a']);
  });

  it('the plus button asks to open a site', () => {
    const { host, calls } = mount();
    (host.querySelector('.fp-tab-add') as HTMLElement).click();
    expect(calls).toEqual(['add']);
  });

  it('a middle click closes the tab and Enter on a focused tab activates it', () => {
    const { host, tabs, calls } = mount();
    tabs.render([{ id: 'z', title: 'Z', active: false }]);
    const tab = host.querySelector('.fp-tab') as HTMLElement;
    tab.dispatchEvent(new MouseEvent('auxclick', { button: 1, bubbles: true, cancelable: true }));
    tab.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true }));
    tab.dispatchEvent(new KeyboardEvent('keydown', { key: 'a', bubbles: true, cancelable: true }));
    expect(calls).toEqual(['close:z', 'activate:z']);
  });
});

describe('toasts', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    document.body.innerHTML = '<div id="toast-root"></div>';
  });
  afterEach(() => { vi.useRealTimers(); });

  const root = (): HTMLElement => document.getElementById('toast-root') as HTMLElement;

  it('shows the message as a status and removes it after a few seconds', () => {
    toast('Saved the site');
    expect(root().children.length).toBe(1);
    expect(root().firstElementChild?.textContent).toBe('Saved the site');
    expect(root().firstElementChild?.getAttribute('role')).toBe('status');
    vi.advanceTimersByTime(3700);
    expect(root().children.length).toBe(0);
  });

  it('an error stays longer than an info message and is marked as an error', () => {
    toast('Could not save', 'error');
    const node = root().firstElementChild as HTMLElement;
    expect(node.classList.contains('is-error')).toBe(true);
    vi.advanceTimersByTime(4000);
    expect(root().children.length).toBe(1);
    vi.advanceTimersByTime(2100);
    expect(root().children.length).toBe(0);
  });

  it('the same message twice shows one toast, not two', () => {
    toast('Copied');
    toast('Copied');
    expect(root().children.length).toBe(1);
  });

  it('never shows more than four toasts, dropping the oldest', () => {
    for (const m of ['one', 'two', 'three', 'four', 'five']) toast(m);
    expect(Array.from(root().children).map((n) => n.textContent)).toEqual(['two', 'three', 'four', 'five']);
  });

  it('a toast with an action runs it once and closes when the action is pressed', () => {
    let ran = 0;
    toast('Moved to the trash', 'info', { label: 'Undo', run: () => { ran += 1; } });
    const btn = root().querySelector('button') as HTMLButtonElement;
    expect(btn.textContent).toBe('Undo');
    btn.click();
    expect(ran).toBe(1);
    expect(root().children.length).toBe(0);
  });

  it('dismissing a toast by hand removes it at once', () => {
    toast('Hello');
    dismissToast(root().firstElementChild as Element);
    expect(root().children.length).toBe(0);
  });

  it('does nothing when the page has no toast area', () => {
    document.body.innerHTML = '';
    expect(() => toast('Nowhere')).not.toThrow();
    expect(document.body.textContent).toBe('');
  });
});
