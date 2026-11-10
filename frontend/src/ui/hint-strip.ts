import '../styles/demo.css';
import type { App } from '../app-api';
import { on } from '../events';
import { anyDialogOpen } from './dialogs';
import { el, q, setClass, setDisabled, setHidden, setText } from './dom';
import { icon } from './icons';

const KEY = 'formpublisher.hints';

interface Step { title: string; text: string; target: string }

const STEPS: readonly Step[] = [
  { title: 'Preview', text: 'Every route renders here at the device width you pick. Click a route on the left to move around the site.', target: '.fp-stage' },
  { title: 'Checks', text: 'Open the panel to run the checks. Problems list the broken links and missing details, and each one says how to fix it.', target: '.fp-status [data-act="toggle-bottom"]' },
  { title: 'Package', text: 'Package turns the site into one reproducible zip with a hash for every file, ready to sign.', target: '[data-ctl="package"]' },
  { title: 'Publish', text: 'Publish writes a folder and the exact commands for each host. FormPublisher never uploads anything.', target: '[data-ctl="publish"]' },
];

const read = (): boolean => {
  try { return localStorage.getItem(KEY) === 'done'; } catch { return false; }
};

const write = (): void => {
  try { localStorage.setItem(KEY, 'done'); } catch { return; }
};

class HintStrip {
  private readonly root: HTMLElement;
  private readonly count: HTMLElement;
  private readonly title: HTMLElement;
  private readonly text: HTMLElement;
  private readonly back: HTMLButtonElement;
  private readonly next: HTMLElement;
  private step = 0;
  private lit: Element | null = null;
  private open = false;

  constructor(private readonly app: App) {
    this.root = el(`<section class="fp-hint" aria-label="Quick tour" hidden>
<span class="fp-hint-count" translate="no"></span>
<span class="fp-hint-title"></span>
<span class="fp-hint-text"></span>
<span class="fp-hint-actions">
<button class="fp-btn fp-btn-sm" type="button" data-hint="back">Back</button>
<button class="fp-btn fp-btn-sm fp-btn-primary" type="button" data-hint="next"><span>Next</span></button>
<button class="fp-icon-btn is-sm" type="button" data-hint="skip" title="Skip the tour" aria-label="Skip the tour">${icon('close', 14)}</button>
</span>
</section>`);
    app.mounts.main.appendChild(this.root);
    this.count = q(this.root, '.fp-hint-count');
    this.title = q(this.root, '.fp-hint-title');
    this.text = q(this.root, '.fp-hint-text');
    this.back = q<HTMLButtonElement>(this.root, '[data-hint="back"]');
    this.next = q(this.root, '[data-hint="next"] span');
    this.root.addEventListener('click', (e) => {
      const act = (e.target as HTMLElement).closest<HTMLElement>('[data-hint]')?.dataset.hint;
      if (act === 'back') this.go(this.step - 1);
      else if (act === 'next') { if (this.step >= STEPS.length - 1) this.finish(); else this.go(this.step + 1); }
      else if (act === 'skip') this.finish();
    });
  }

  get shown(): boolean { return this.open; }

  begin(): void {
    if (this.open || read() || anyDialogOpen()) return;
    this.open = true;
    setHidden(this.root, false);
    this.go(0);
  }

  hideTemporarily(): void {
    if (!this.open) return;
    this.light(null);
    setHidden(this.root, true);
    this.open = false;
  }

  private go(at: number): void {
    this.step = Math.max(0, Math.min(STEPS.length - 1, at));
    const s = STEPS[this.step];
    setText(this.count, `Step ${this.step + 1} of ${STEPS.length}`);
    setText(this.title, s.title);
    setText(this.text, s.text);
    setDisabled(this.back, this.step === 0);
    setText(this.next, this.step === STEPS.length - 1 ? 'Done' : 'Next');
    this.light(this.app.mounts.root.querySelector(s.target));
  }

  private light(target: Element | null): void {
    if (this.lit === target) return;
    if (this.lit) setClass(this.lit, 'is-hinted', false);
    this.lit = target;
    if (target) setClass(target, 'is-hinted', true);
  }

  private finish(): void {
    write();
    this.light(null);
    setHidden(this.root, true);
    this.open = false;
  }
}

export function installHints(app: App): void {
  const strip = new HintStrip(app);
  on('fp:site-loaded', () => { window.setTimeout(() => { if (app.state().activeId !== null) strip.begin(); }, 0); });
  on('fp:home', () => strip.hideTemporarily());
  on('fp:site-closed', () => { if (app.state().activeId === null) strip.hideTemporarily(); });
}
