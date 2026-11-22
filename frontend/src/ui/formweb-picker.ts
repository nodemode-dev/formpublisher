import '../styles/formweb-picker.css';
import type { FormWebProject } from '../api';
import { locale } from '../i18n';
import { Dialog } from './dialogs';
import { el, patchList, q, setAttr, setClass, setText } from './dom';

type Pick = string | null | undefined;

const keyOf = (p: FormWebProject): string => (p.open ? 'open' : `id:${p.id ?? p.name}`);

const savedAt = (iso: string): string => {
  const at = new Date(iso);
  if (Number.isNaN(at.getTime())) return '';
  try {
    return new Intl.DateTimeFormat(locale(), { dateStyle: 'medium', timeStyle: 'short' }).format(at);
  } catch {
    return at.toISOString().slice(0, 16).replace('T', ' ');
  }
};

class ProjectPicker extends Dialog {
  private readonly list: HTMLElement;
  private readonly state: HTMLElement;
  private resolve: ((v: Pick) => void) | null = null;
  private last: FormWebProject[] = [];
  private chosenKey: string | null = null;
  private seq = 0;

  constructor() {
    super('Import from FormWeb', 460, 'fp-fw-dlg');
    this.body.appendChild(el('<p class="fp-note">Choose the FormWeb project to import.</p>'));
    this.list = el('<div class="fp-fw-list" role="radiogroup" aria-label="Import from FormWeb"></div>');
    this.state = el('<div class="fp-fw-state" role="status" aria-live="polite"><span>Checking FormWeb</span></div>');
    this.body.append(this.list, this.state);
    this.list.addEventListener('change', (e) => {
      const key = (e.target as HTMLElement).closest<HTMLElement>('.fp-fw-row')?.dataset.key;
      if (key) this.chosenKey = key;
    });
    this.button('Cancel', 'ghost', () => this.finish(undefined));
    this.button('Import', 'primary', () => this.finish(this.chosen()));
    this.onClose = () => this.finish(undefined);
    this.list.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); this.finish(this.chosen()); }
    });
    this.list.addEventListener('dblclick', (e) => {
      if ((e.target as HTMLElement).closest('.fp-fw-row')) this.finish(this.chosen());
    });
  }

  ask(projects: FormWebProject[]): Promise<Pick> {
    this.finish(undefined);
    ++this.seq;
    this.chosenKey = null;
    this.fill(projects, false);
    this.open(this.list.querySelector<HTMLElement>('input:checked'));
    return new Promise((r) => { this.resolve = r; });
  }

  async askFresh(load: () => Promise<FormWebProject[]>): Promise<Pick> {
    this.finish(undefined);
    const seq = ++this.seq;
    if (this.last.length <= 1) {
      const fresh = await load().catch(() => [] as FormWebProject[]);
      if (seq !== this.seq) return undefined;
      this.last = fresh;
      if (fresh.length <= 1) return null;
      return this.ask(fresh);
    }
    this.chosenKey = null;
    this.fill(this.last, true);
    this.open(this.list.querySelector<HTMLElement>('input:checked'));
    const answer = new Promise<Pick>((r) => { this.resolve = r; });
    void load().catch(() => null).then((fresh) => {
      if (seq !== this.seq || !this.isOpen) return;
      if (fresh === null) { this.fill(this.last, false); return; }
      if (fresh.length === 0) { this.last = fresh; this.finish(null); return; }
      this.fill(fresh, false);
    });
    return answer;
  }

  private fill(projects: FormWebProject[], stale: boolean): void {
    this.last = projects.slice();
    const keys = projects.map(keyOf);
    if (this.chosenKey === null || !keys.includes(this.chosenKey)) this.chosenKey = keys[0] ?? null;
    patchList(this.list, this.last, {
      key: keyOf,
      create: (p) => {
        const node = el(`<label class="fp-fw-row"><input type="radio" name="fp-fw-project"><span class="fp-fw-text"><span class="fp-fw-name"></span><span class="fp-fw-meta"></span></span></label>`);
        this.paint(node, p);
        return node;
      },
      update: (node, p) => this.paint(node, p),
    });
    setClass(this.list, 'is-stale', stale);
    setClass(this.state, 'is-on', stale);
    setAttr(this.list, 'aria-busy', String(stale));
  }

  private paint(node: HTMLElement, p: FormWebProject): void {
    const input = q<HTMLInputElement>(node, 'input');
    const value = p.open ? '' : (p.id ?? '');
    if (input.value !== value) input.value = value;
    const on = keyOf(p) === this.chosenKey;
    if (input.checked !== on) input.checked = on;
    const name = q(node, '.fp-fw-name');
    if (p.name) setAttr(name, 'translate', 'no');
    else if (name.hasAttribute('translate')) name.removeAttribute('translate');
    setText(name, p.name || 'Unsaved site');
    const when = p.updatedAt ? savedAt(p.updatedAt) : '';
    setText(q(node, '.fp-fw-meta'), p.open ? 'Open in FormWeb' : when ? `Saved ${when}` : '');
  }

  private chosen(): Pick {
    const input = this.list.querySelector<HTMLInputElement>('input:checked');
    if (!input) return undefined;
    return input.value || null;
  }

  private finish(v: Pick): void {
    const r = this.resolve;
    this.resolve = null;
    if (this.isOpen) this.close();
    r?.(v);
  }
}

let picker: ProjectPicker | null = null;

export function pickFormWebProject(projects: FormWebProject[] | (() => Promise<FormWebProject[]>)): Promise<Pick> {
  picker ??= new ProjectPicker();
  return typeof projects === 'function' ? picker.askFresh(projects) : picker.ask(projects);
}
