import { RESERVE_KEYS, RESERVE_LABELS } from './reserve-labels';

const column = (key: string): string[] => {
  const at = RESERVE_KEYS.indexOf(key);
  return RESERVE_LABELS.map(([, strings]) => strings[at] ?? key);
};

const columnShown = (keys: readonly string[], shown: string): string[] | null => {
  const text = shown.trim();
  for (const key of keys) {
    const all = column(key);
    if (all.includes(text)) return all;
  }
  return null;
};

const ghost = <T extends HTMLElement>(host: HTMLElement, node: T): T => {
  node.setAttribute('translate', 'no');
  node.setAttribute('aria-hidden', 'true');
  node.removeAttribute('id');
  for (const inner of Array.from(node.querySelectorAll('[id]'))) inner.removeAttribute('id');
  node.style.position = 'absolute';
  node.style.visibility = 'hidden';
  node.style.pointerEvents = 'none';
  host.appendChild(node);
  return node;
};

const widest = (probe: HTMLElement, fill: (text: string) => void, strings: readonly string[]): number => {
  let most = 0;
  for (const text of strings) {
    fill(text);
    most = Math.max(most, probe.getBoundingClientRect().width);
  }
  return most;
};

const setVar = (node: HTMLElement, name: string, px: number): void => {
  if (px <= 0) return;
  const value = `${Math.ceil(px)}px`;
  if (node.style.getPropertyValue(name) !== value) node.style.setProperty(name, value);
};

const MENUS = ['File', 'Edit', 'View', 'Site', 'Window', 'Help'];

export function reserveMenubar(bar: HTMLElement): void {
  const run = (): void => {
    const buttons = Array.from(bar.querySelectorAll<HTMLElement>('.fp-menu-btn'));
    const host = bar.parentElement;
    if (!host || !buttons.length || !bar.offsetWidth) return;
    const columns = buttons.map((b) => column(MENUS.find((m) => m.toLowerCase() === b.dataset.menu) ?? ''));
    const probe = ghost(host, bar.cloneNode(true) as HTMLElement);
    probe.style.width = 'max-content';
    probe.style.maxWidth = 'none';
    const cells = Array.from(probe.querySelectorAll<HTMLElement>('.fp-menu-btn'));
    let most = 0;
    for (let i = 0; i < RESERVE_LABELS.length; i += 1) {
      cells.forEach((cell, at) => { cell.textContent = columns[at][i]; });
      most = Math.max(most, probe.getBoundingClientRect().width);
    }
    probe.remove();
    setVar(bar, '--fp-menubar-w', most);
  };
  run();
  document.fonts?.addEventListener('loadingdone', run);
}

export function reserveHint(root: HTMLElement): void {
  const fills: Array<[string, string, string[], (probe: HTMLElement) => HTMLElement]> = [
    ['--fp-hint-count-w', '<span class="fp-hint-count"></span>', ['Step 1 of 4', 'Step 2 of 4', 'Step 3 of 4', 'Step 4 of 4'].flatMap(column), (p) => p],
    ['--fp-hint-title-w', '<span class="fp-hint-title"></span>', ['Preview', 'Checks', 'Package', 'Publish'].flatMap(column), (p) => p],
    ['--fp-hint-back-w', '<button class="fp-btn fp-btn-sm" type="button"></button>', column('Back'), (p) => p],
    ['--fp-hint-next-w', '<button class="fp-btn fp-btn-sm fp-btn-primary" type="button"><span></span></button>', [...column('Next'), ...column('Done')], (p) => p.querySelector('span') as HTMLElement],
  ];
  const holder = document.createElement('template');
  for (const [name, html, strings, target] of fills) {
    holder.innerHTML = html;
    const probe = ghost(root, holder.content.firstElementChild as HTMLElement);
    const cell = target(probe);
    setVar(root, name, widest(probe, (text) => { cell.textContent = text; }, strings));
    probe.remove();
  }
}

const HINT_KEYS = ['The window changes to the language you choose.', 'How tall the bars and controls are.', 'FormWeb runs on this computer, for example http://127.0.0.1:8240. Test saves a changed address first.', 'Runs the static checks on each site FormWeb sends, so the problems are ready when you open it. Off by default.', 'Builds the package as soon as a site arrives, after the checks when both are on. Off by default.'];
const NAME_KEYS = ['Language', 'Accent colour', 'Accent intensity', 'Density', 'FormWeb address', 'Check a site when it arrives', 'Build a site when it arrives'];
const watched = new WeakSet<HTMLElement>();

const reserveRows = (pages: HTMLElement): void => {
  if (!pages.offsetWidth) return;
  for (const row of Array.from(pages.querySelectorAll<HTMLElement>('.fp-pref-row, .fp-pref-block'))) {
    const hints = Array.from(row.querySelectorAll<HTMLElement>('.fp-pref-hint'));
    const parent = row.parentElement;
    if (!hints.length || !parent) continue;
    const names = Array.from(row.querySelectorAll<HTMLElement>('.fp-pref-name'));
    const hintColumns = hints.map((h) => columnShown(HINT_KEYS, h.textContent ?? ''));
    const nameColumns = names.map((n) => columnShown(NAME_KEYS, n.textContent ?? ''));
    if (hintColumns.some((c) => !c)) continue;
    const probe = ghost(parent, row.cloneNode(true) as HTMLElement);
    probe.style.width = `${row.offsetWidth}px`;
    probe.style.left = '0';
    probe.style.top = '0';
    const probeHints = Array.from(probe.querySelectorAll<HTMLElement>('.fp-pref-hint'));
    const probeNames = Array.from(probe.querySelectorAll<HTMLElement>('.fp-pref-name'));
    for (const h of probeHints) h.style.minHeight = '';
    const tallest = hints.map(() => 0);
    for (let i = 0; i < RESERVE_LABELS.length; i += 1) {
      probeNames.forEach((n, at) => { const all = nameColumns[at]; if (all) n.textContent = all[i]; });
      probeHints.forEach((h, at) => { h.textContent = (hintColumns[at] as string[])[i]; });
      probeHints.forEach((h, at) => { tallest[at] = Math.max(tallest[at], h.offsetHeight); });
    }
    const line = (h: HTMLElement): number => {
      const style = getComputedStyle(h);
      return parseFloat(style.lineHeight) || parseFloat(style.fontSize) * 1.2;
    };
    hints.forEach((h, at) => {
      const each = line(h);
      const px = `${Math.max(1, Math.round(tallest[at] / each)) * each}px`;
      if (h.style.minHeight !== px) h.style.minHeight = px;
    });
    probe.remove();
  }
};

export function reservePrefs(pages: HTMLElement, done: HTMLElement | null): void {
  reserveRows(pages);
  if (done?.parentElement && done.offsetWidth) {
    const probe = ghost(done.parentElement, done.cloneNode(true) as HTMLElement);
    probe.style.minWidth = '0';
    setVar(done, 'min-width', widest(probe, (text) => { probe.textContent = text; }, column('Done')));
    probe.remove();
  }
  if (watched.has(pages)) return;
  watched.add(pages);
  let width = pages.offsetWidth;
  new ResizeObserver(() => {
    if (!pages.offsetWidth || pages.offsetWidth === width) return;
    width = pages.offsetWidth;
    reserveRows(pages);
  }).observe(pages);
}
