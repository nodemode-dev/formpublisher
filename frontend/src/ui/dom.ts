export type Disposer = () => void;

export interface PatchListOptions<T> {
  key: (item: T) => string;
  create: (item: T) => HTMLElement;
  update: (node: HTMLElement, item: T) => void;
}

export function patchList<T>(container: HTMLElement, items: T[], opts: PatchListOptions<T>): void {
  const byKey = new Map<string, HTMLElement>();
  for (const child of Array.from(container.children)) {
    const k = (child as HTMLElement).dataset.key;
    if (k !== undefined) byKey.set(k, child as HTMLElement);
  }
  let cursor: Element | null = container.firstElementChild;
  const seen = new Set<string>();
  for (const item of items) {
    const k = opts.key(item);
    seen.add(k);
    let node = byKey.get(k);
    if (node) {
      opts.update(node, item);
    } else {
      node = opts.create(item);
      node.dataset.key = k;
    }
    if (node !== cursor) container.insertBefore(node, cursor);
    else cursor = cursor.nextElementSibling;
  }
  for (const [k, node] of byKey) if (!seen.has(k)) node.remove();
}

export function setText(node: Element | null, text: string): void {
  if (node && node.textContent !== text) node.textContent = text;
}

export function setClass(node: Element | null, cls: string, on: boolean): void {
  if (!node) return;
  if (node.classList.contains(cls) !== on) node.classList.toggle(cls, on);
}

export function setHidden(node: HTMLElement, hidden: boolean): void {
  if (node.hidden !== hidden) node.hidden = hidden;
}

export function setDisabled(node: HTMLButtonElement | HTMLInputElement, disabled: boolean): void {
  if (node.disabled !== disabled) node.disabled = disabled;
}

export function setTitle(node: HTMLElement, title: string): void {
  if (node.title !== title) node.title = title;
}

export function setAttr(node: Element, name: string, value: string): void {
  if (node.getAttribute(name) !== value) node.setAttribute(name, value);
}

export function setValue(node: HTMLInputElement, value: string): void {
  if (node.value !== value && document.activeElement !== node) node.value = value;
}

export function setStyleVar(node: HTMLElement, name: string, value: string): void {
  if (node.style.getPropertyValue(name) !== value) node.style.setProperty(name, value);
}

export function mountOnce(host: HTMLElement, html: string): void {
  if (host.childElementCount > 0) {
    throw new Error('mountOnce: host already rendered; patch in place instead of rebuilding');
  }
  host.innerHTML = html;
}

export function el<T extends HTMLElement = HTMLElement>(html: string): T {
  const t = document.createElement('template');
  t.innerHTML = html.trim();
  return t.content.firstElementChild as T;
}

export function q<T extends Element = HTMLElement>(root: ParentNode, sel: string): T {
  const n = root.querySelector(sel);
  if (!n) throw new Error(`missing element: ${sel}`);
  return n as T;
}

export function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c] ?? c);
}

export const isMac = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);

export const inTauri = (): boolean => '__TAURI_INTERNALS__' in window;

export function revealApp(): void {
  if (document.body.classList.contains('app-ready')) return;
  let done = false;
  const go = (): void => {
    if (done) return;
    done = true;
    const base = document.querySelector('.fp-app') ?? document.body;
    const rgb = (getComputedStyle(base).backgroundColor.match(/\d+(\.\d+)?/g) ?? []).slice(0, 3).map((n) => Math.round(Number(n)));
    const bg = rgb.length === 3 ? rgb : null;
    document.body.classList.add('app-ready');
    if (!inTauri()) return;
    void import('@tauri-apps/api/core')
      .then((m) => m.invoke('app_ready', { bg }))
      .catch(() => undefined);
  };
  const frames = (): Promise<void> => new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r())));
  const imagesReady = (): Promise<unknown> => {
    const imgs = Array.from(document.querySelectorAll<HTMLImageElement>('#app img'));
    return Promise.allSettled(imgs.map((i) => i.decode()));
  };
  const fontsReady = (): Promise<unknown> => Promise.all([
    document.fonts.load('400 12px Inter'),
    document.fonts.load('500 12px Inter'),
    document.fonts.load('600 12px Inter'),
    document.fonts.load('400 12px "JetBrains Mono"'),
  ]).then(() => document.fonts.ready);
  const settled = Promise.all([fontsReady(), imagesReady()]).catch(() => undefined);
  const cap = new Promise<void>((r) => window.setTimeout(r, 2500));
  void Promise.race([settled, cap]).then(frames).then(go);
  window.setTimeout(go, 4000);
}
