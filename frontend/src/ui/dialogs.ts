import { el, q, setText } from './dom';
import { icon } from './icons';

let openCount = 0;
export const anyDialogOpen = (): boolean => openCount > 0;

const FOCUSABLE = 'button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])';

export class Dialog {
  readonly scrim: HTMLElement;
  readonly panel: HTMLElement;
  readonly body: HTMLElement;
  readonly foot: HTMLElement;
  private readonly titleEl: HTMLElement;
  private lastFocus: HTMLElement | null = null;
  onClose: (() => void) | null = null;

  constructor(title: string, width = 440, cls = '') {
    this.scrim = el(`<div class="fp-scrim" hidden><div class="fp-dialog fp-dlg${cls ? ` ${cls}` : ''}" role="dialog" aria-modal="true" tabindex="-1"><div class="fp-dialog-head"><span class="fp-dialog-title"></span><button class="fp-icon-btn is-round" type="button" data-close title="Close" aria-label="Close">${icon('close', 16)}</button></div><div class="fp-dlg-body"></div><div class="fp-dlg-foot"></div></div></div>`);
    this.panel = q(this.scrim, '.fp-dialog');
    this.panel.style.setProperty('--fp-dialog-w', `${width}px`);
    this.titleEl = q(this.scrim, '.fp-dialog-title');
    this.body = q(this.scrim, '.fp-dlg-body');
    this.foot = q(this.scrim, '.fp-dlg-foot');
    this.panel.setAttribute('aria-label', title);
    setText(this.titleEl, title);
    q(this.scrim, '[data-close]').addEventListener('click', () => this.close());
    this.scrim.addEventListener('pointerdown', (e) => { if (e.target === this.scrim) this.close(); });
    this.scrim.addEventListener('keydown', (e) => {
      e.stopPropagation();
      if (e.key === 'Escape') { e.preventDefault(); this.close(); return; }
      if (e.key === 'Tab') this.trap(e);
    });
    document.getElementById('overlay-root')?.appendChild(this.scrim);
  }

  get isOpen(): boolean { return !this.scrim.hidden; }

  setTitle(title: string): void {
    setText(this.titleEl, title);
    this.panel.setAttribute('aria-label', title);
  }

  open(focus?: HTMLElement | null): void {
    if (this.isOpen) return;
    this.lastFocus = document.activeElement as HTMLElement | null;
    this.scrim.hidden = false;
    openCount += 1;
    const preferred = focus ?? this.scrim.querySelector<HTMLElement>('input, select, .fp-btn-primary:not(:disabled)');
    preferred?.focus();
    if (!this.scrim.contains(document.activeElement)) this.panel.focus();
  }

  close(): void {
    if (!this.isOpen) return;
    this.scrim.hidden = true;
    openCount -= 1;
    this.onClose?.();
    if (this.scrim.contains(document.activeElement)) (document.activeElement as HTMLElement).blur();
    this.lastFocus?.focus?.();
  }

  button(label: string, kind: '' | 'primary' | 'ghost' | 'danger', run: () => void): HTMLButtonElement {
    const b = el<HTMLButtonElement>(`<button class="fp-btn${kind ? ` fp-btn-${kind}` : ''}" type="button"></button>`);
    b.textContent = label;
    b.addEventListener('click', run);
    this.foot.appendChild(b);
    return b;
  }

  private trap(e: KeyboardEvent): void {
    const nodes = Array.from(this.panel.querySelectorAll<HTMLElement>(FOCUSABLE)).filter((n) => n.offsetParent !== null);
    if (!nodes.length) { e.preventDefault(); this.panel.focus(); return; }
    const first = nodes[0];
    const last = nodes[nodes.length - 1];
    const active = document.activeElement;
    if (e.shiftKey && (active === first || active === this.panel)) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && active === last) { e.preventDefault(); first.focus(); }
  }
}

class Confirm extends Dialog {
  private readonly text = el('<p class="fp-note"></p>');
  private readonly ok: HTMLButtonElement;
  private resolve: ((v: boolean) => void) | null = null;

  constructor() {
    super('Confirm', 400);
    this.body.appendChild(this.text);
    this.button('Cancel', 'ghost', () => this.finish(false));
    this.ok = this.button('OK', 'primary', () => this.finish(true));
    this.onClose = () => this.finish(false);
  }

  ask(title: string, text: string, okLabel: string, danger: boolean): Promise<boolean> {
    this.finish(false);
    this.setTitle(title);
    setText(this.text, text);
    setText(this.ok, okLabel);
    this.ok.className = danger ? 'fp-btn fp-btn-danger' : 'fp-btn fp-btn-primary';
    this.open(this.ok);
    return new Promise((r) => { this.resolve = r; });
  }

  private finish(v: boolean): void {
    const r = this.resolve;
    this.resolve = null;
    if (this.isOpen) this.close();
    r?.(v);
  }
}

let confirmDialog: Confirm | null = null;

export function confirmAction(title: string, text: string, okLabel = 'OK', danger = false): Promise<boolean> {
  confirmDialog ??= new Confirm();
  return confirmDialog.ask(title, text, okLabel, danger);
}
