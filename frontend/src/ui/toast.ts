import { el } from './dom';

const timers = new WeakMap<Element, number>();
const MAX = 4;

export type ToastKind = 'info' | 'ok' | 'error';

export function toast(text: string, kind: ToastKind = 'info'): void {
  const root = document.getElementById('toast-root');
  if (!root) return;
  const ms = kind === 'error' ? 6000 : 3600;
  const cls = `fp-toast${kind === 'error' ? ' is-error' : ''}`;
  const same = Array.from(root.children).find((n) => (n as HTMLElement).dataset.text === text && n.className === cls);
  if (same) {
    window.clearTimeout(timers.get(same));
    timers.set(same, window.setTimeout(() => dismissToast(same), ms));
    return;
  }
  const node = el(`<div class="${cls}" role="status"></div>`);
  node.textContent = text;
  node.dataset.text = text;
  root.appendChild(node);
  while (root.children.length > MAX) dismissToast(root.firstElementChild as Element);
  stack(root);
  timers.set(node, window.setTimeout(() => dismissToast(node), ms));
}

export function dismissToast(node: Element): void {
  const root = node.parentElement;
  window.clearTimeout(timers.get(node));
  node.remove();
  if (root) stack(root);
}

function stack(root: HTMLElement): void {
  let y = 0;
  for (const n of Array.from(root.children) as HTMLElement[]) {
    n.style.setProperty('--toast-y', `${-y}px`);
    y += n.offsetHeight + 8;
  }
}
