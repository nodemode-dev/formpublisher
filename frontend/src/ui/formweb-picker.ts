import '../styles/formweb-picker.css';
import type { FormWebProject } from '../api';
import { locale } from '../i18n';
import { Dialog } from './dialogs';
import { el, q, setText } from './dom';

type Pick = string | null | undefined;

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
  private resolve: ((v: Pick) => void) | null = null;

  constructor() {
    super('Import from FormWeb', 460, 'fp-fw-dlg');
    this.body.appendChild(el('<p class="fp-note">Choose the FormWeb project to import.</p>'));
    this.list = el('<div class="fp-fw-list" role="radiogroup" aria-label="Import from FormWeb"></div>');
    this.body.appendChild(this.list);
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
    this.list.replaceChildren(...projects.map((p, i) => this.row(p, i === 0)));
    this.open(this.list.querySelector<HTMLElement>('input:checked'));
    return new Promise((r) => { this.resolve = r; });
  }

  private row(p: FormWebProject, first: boolean): HTMLElement {
    const node = el(`<label class="fp-fw-row"><input type="radio" name="fp-fw-project"><span class="fp-fw-text"><span class="fp-fw-name"></span><span class="fp-fw-meta"></span></span></label>`);
    const input = q<HTMLInputElement>(node, 'input');
    input.value = p.open ? '' : (p.id ?? '');
    input.checked = first;
    const name = q(node, '.fp-fw-name');
    if (p.name) { name.setAttribute('translate', 'no'); setText(name, p.name); } else setText(name, 'Unsaved site');
    const when = p.updatedAt ? savedAt(p.updatedAt) : '';
    setText(q(node, '.fp-fw-meta'), p.open ? 'Open in FormWeb' : when ? `Saved ${when}` : '');
    return node;
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

export function pickFormWebProject(projects: FormWebProject[]): Promise<Pick> {
  picker ??= new ProjectPicker();
  return picker.ask(projects);
}
