import '../styles/hosting.css';
import { Dialog } from './dialogs';
import { el, q } from './dom';
import { openHosting, renderGuide } from './hosting-sheet';

const PREFIX = 'fp-man';

async function load(): Promise<string | null> {
  try {
    const res = await fetch('/api/docs/manual', { headers: { Accept: 'text/markdown' } });
    return res.ok ? await res.text() : null;
  } catch {
    return null;
  }
}

export class ManualSheet extends Dialog {
  private readonly page: HTMLElement;
  private readonly failed: HTMLElement;
  private marked: HTMLElement | null = null;
  loaded = false;

  constructor() {
    super('Manual', 760, 'fp-host-dlg fp-man-dlg');
    this.failed = el('<p class="fp-man-failed" hidden>The manual could not be loaded.</p>');
    this.page = document.createElement('article');
    this.page.className = 'fp-host-page';
    this.page.lang = 'en';
    this.page.setAttribute('translate', 'no');
    this.body.append(this.failed, this.page);
    this.page.addEventListener('click', (e) => {
      const link = (e.target as HTMLElement).closest<HTMLAnchorElement>('a[data-part], a[data-doc]');
      if (!link) return;
      e.preventDefault();
      if (link.dataset.doc === 'HOSTING.md') { this.close(); openHosting(); return; }
      if (link.dataset.part) this.jump(link.dataset.part);
    });
    this.foot.appendChild(el('<span class="fp-host-note">The manual is in English.</span>'));
    this.button('Close', 'primary', () => this.close());
  }

  fill(markdown: string | null): void {
    if (this.loaded) return;
    this.failed.hidden = markdown !== null;
    if (markdown === null) return;
    this.page.innerHTML = renderGuide(markdown, PREFIX);
    this.loaded = true;
  }

  show(part?: string, code?: string): void {
    this.open(q(this.foot, '.fp-btn-primary'));
    this.jump(part ?? '', code);
  }

  private jump(part: string, code?: string): void {
    const heading = part ? this.page.querySelector<HTMLElement>(`#${PREFIX}-${CSS.escape(part)}`) : null;
    const after = (r: HTMLElement): boolean => !heading || (heading.compareDocumentPosition(r) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
    const row = code ? Array.from(this.page.querySelectorAll<HTMLElement>('tr[data-code]')).find((r) => after(r) && (r.dataset.code ?? '').split(' ').includes(code)) ?? null : null;
    this.marked?.classList.remove('is-target');
    this.marked = row;
    row?.classList.add('is-target');
    const target = row ?? heading;
    this.body.scrollTop = target ? this.body.scrollTop + target.getBoundingClientRect().top - this.body.getBoundingClientRect().top : 0;
  }
}

let sheet: ManualSheet | null = null;
let pending: Promise<string | null> | null = null;

export async function openManual(part?: string, code?: string): Promise<void> {
  sheet ??= new ManualSheet();
  if (!sheet.loaded && !sheet.isOpen) {
    pending ??= load();
    const markdown = await pending;
    pending = null;
    sheet.fill(markdown);
  }
  sheet.show(part, code);
}
