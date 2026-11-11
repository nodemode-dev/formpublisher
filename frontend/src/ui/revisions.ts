import '../styles/revisions.css';
import { fetchDiff, fetchRevisions, type DiffRow, type RevisionDiff, type RevisionRow } from '../api-revisions';
import { locale, onLanguage } from '../i18n';
import { Dialog } from './dialogs';
import { el, patchList, q, setAttr, setClass, setHidden, setText } from './dom';

const KIND_LABEL: Record<DiffRow['kind'], string> = {
  added: 'Added',
  removed: 'Removed',
  changed: 'Changed',
  'route-added': 'Route added',
  'route-removed': 'Route removed',
};

const filesText = (n: number): string => (n === 1 ? '1 file' : `${n} files`);
const revText = (n: number): string => (n === 1 ? '1 revision' : `${n} revisions`);

export const revisionsText = revText;

function when(row: RevisionRow): string {
  const t = Date.parse(row.at);
  if (Number.isNaN(t)) return row.revision;
  try {
    return new Date(t).toLocaleString(locale(), { dateStyle: 'medium', timeStyle: 'medium' });
  } catch {
    return row.at;
  }
}

function changeText(row: RevisionRow): string {
  return row.changes ? `+${row.changes.added} -${row.changes.removed} ~${row.changes.changed}` : '';
}

/** A revision list on the left and the diff of the chosen revision against the one before it on the right. Fixed regions, so nothing moves when data arrives. */
export class RevisionsView {
  readonly root: HTMLElement;
  private readonly list: HTMLElement;
  private readonly count: HTMLElement;
  private readonly listEmpty: HTMLElement;
  private readonly rows: HTMLElement;
  private readonly empty: HTMLElement;
  private readonly from: HTMLElement;
  private readonly to: HTMLElement;
  private readonly sum: Record<'added' | 'removed' | 'changed', HTMLElement>;
  private revisions: RevisionRow[] = [];
  private selected = '';
  private site: string | null = null;
  private token = 0;
  private diffToken = 0;

  constructor(host: HTMLElement) {
    this.root = el(`<div class="fp-rv">
<div class="fp-rv-side"><div class="fp-rv-head"><span class="fp-rv-title">Revisions</span><span class="fp-badge is-count" data-f="count">0</span></div>
<div class="fp-rv-listbox"><div class="fp-rv-list" role="listbox" aria-label="Revisions"></div><div class="fp-rv-empty" data-f="list-empty"></div></div></div>
<div class="fp-rv-main"><div class="fp-rv-bar"><span class="fp-rv-lab">From</span><span class="fp-rv-stamp" data-f="from" translate="no">-</span><span class="fp-rv-lab">To</span><span class="fp-rv-stamp" data-f="to" translate="no">-</span><span class="fp-rv-spacer"></span><span class="fp-rv-sum is-added" data-f="added">0 added</span><span class="fp-rv-sum is-removed" data-f="removed">0 removed</span><span class="fp-rv-sum is-changed" data-f="changed">0 changed</span></div>
<div class="fp-rv-body"><div class="fp-rv-rows" role="rowgroup"></div><div class="fp-rv-empty" data-f="empty"></div></div></div>
</div>`);
    host.appendChild(this.root);
    this.list = q(this.root, '.fp-rv-list');
    this.count = q(this.root, '[data-f="count"]');
    this.listEmpty = q(this.root, '[data-f="list-empty"]');
    this.rows = q(this.root, '.fp-rv-rows');
    this.empty = q(this.root, '[data-f="empty"]');
    this.from = q(this.root, '[data-f="from"]');
    this.to = q(this.root, '[data-f="to"]');
    this.sum = { added: q(this.root, '[data-f="added"]'), removed: q(this.root, '[data-f="removed"]'), changed: q(this.root, '[data-f="changed"]') };
    setText(this.listEmpty, 'Open a site to see its revisions.');
    setText(this.empty, '');
    onLanguage(() => this.paintList());
    const pick = (node: HTMLElement | null): void => {
      const id = node?.dataset.key;
      if (id) void this.select(id);
    };
    this.list.addEventListener('click', (e) => pick((e.target as HTMLElement).closest<HTMLElement>('.fp-rv-item')));
    this.list.addEventListener('keydown', (e) => {
      const node = (e.target as HTMLElement).closest<HTMLElement>('.fp-rv-item');
      if (!node) return;
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pick(node); return; }
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        const next = e.key === 'ArrowDown' ? node.nextElementSibling : node.previousElementSibling;
        if (next instanceof HTMLElement) { next.focus(); pick(next); }
      }
    });
  }

  get siteId(): string | null { return this.site; }

  async load(site: string | null): Promise<void> {
    const token = ++this.token;
    if (site !== this.site) {
      this.site = site;
      this.revisions = [];
      this.selected = '';
      this.paintList();
      this.paintDiff(null, 'Loading revisions');
    }
    if (!site) { this.paintDiff(null, ''); return; }
    try {
      const rows = await fetchRevisions(site);
      if (token !== this.token) return;
      this.revisions = rows;
      if (!rows.some((r) => r.revision === this.selected)) this.selected = rows[0]?.revision ?? '';
      this.paintList();
      await this.showDiff(token);
    } catch (e) {
      if (token !== this.token) return;
      this.paintDiff(null, e instanceof Error && e.message ? e.message : 'The revisions could not be loaded');
    }
  }

  private async select(id: string): Promise<void> {
    if (id === this.selected) return;
    this.selected = id;
    this.paintList();
    await this.showDiff(this.token);
  }

  private async showDiff(token: number): Promise<void> {
    const site = this.site;
    const index = this.revisions.findIndex((r) => r.revision === this.selected);
    if (!site || index < 0) { this.paintDiff(null, ''); return; }
    const older = this.revisions[index + 1];
    if (!older) {
      this.paintDiff(null, this.revisions.length > 1 ? 'This is the first revision, so there is nothing to compare it with.' : 'Only one revision so far. When this site arrives again, what changed shows here.');
      setText(this.to, this.selected);
      return;
    }
    const mine = ++this.diffToken;
    try {
      const diff = await fetchDiff(site, older.revision, this.selected);
      if (token !== this.token || mine !== this.diffToken) return;
      this.paintDiff(diff, diff.identical && diff.rows.length === 0 ? 'Nothing changed between these two revisions.' : '');
    } catch (e) {
      if (token !== this.token || mine !== this.diffToken) return;
      this.paintDiff(null, e instanceof Error && e.message ? e.message : 'The revisions could not be loaded');
    }
  }

  private paintList(): void {
    setText(this.count, String(this.revisions.length));
    setText(this.listEmpty, this.site ? (this.revisions.length ? '' : 'No revisions yet.') : 'Open a site to see its revisions.');
    setHidden(this.listEmpty, this.revisions.length > 0);
    patchList<RevisionRow>(this.list, this.revisions, {
      key: (r) => r.revision,
      create: (r) => {
        const node = el(`<div class="fp-rv-item" role="option" tabindex="0"><span class="fp-rv-when" translate="no"></span><span class="fp-badge fp-rv-latest">Latest</span><span class="fp-rv-files"></span><span class="fp-rv-chg" translate="no"></span></div>`);
        this.fillItem(node, r);
        return node;
      },
      update: (node, r) => this.fillItem(node, r),
    });
  }

  private fillItem(node: HTMLElement, r: RevisionRow): void {
    setText(q(node, '.fp-rv-when'), when(r));
    setHidden(q(node, '.fp-rv-latest'), !r.latest);
    setText(q(node, '.fp-rv-files'), filesText(r.files));
    setText(q(node, '.fp-rv-chg'), changeText(r));
    const on = r.revision === this.selected;
    setClass(node, 'is-on', on);
    setAttr(node, 'aria-selected', String(on));
    setAttr(node, 'title', r.revision);
  }

  private paintDiff(diff: RevisionDiff | null, message: string): void {
    setText(this.from, diff ? diff.from : '-');
    setText(this.to, diff ? diff.to : this.selected || '-');
    setText(this.sum.added, `${diff ? diff.added : 0} added`);
    setText(this.sum.removed, `${diff ? diff.removed : 0} removed`);
    setText(this.sum.changed, `${diff ? diff.changed : 0} changed`);
    patchList<DiffRow>(this.rows, this.rowsOf(diff), {
      key: (r) => `${r.kind}:${r.path}`,
      create: (r) => {
        const node = el(`<div class="fp-rv-row" role="row"><span class="fp-rv-kind"></span><span class="fp-rv-path" translate="no"></span><span class="fp-rv-size" translate="no"></span><span class="fp-rv-hash" translate="no"></span></div>`);
        this.fillRow(node, r);
        return node;
      },
      update: (node, r) => this.fillRow(node, r),
    });
    setText(this.empty, message);
    setHidden(this.empty, message === '');
  }

  private rowsOf(diff: RevisionDiff | null): DiffRow[] {
    return diff ? diff.rows : [];
  }

  private fillRow(node: HTMLElement, r: DiffRow): void {
    const kind = q(node, '.fp-rv-kind');
    setText(kind, KIND_LABEL[r.kind]);
    setAttr(node, 'data-kind', r.kind);
    setText(q(node, '.fp-rv-path'), r.path);
    setAttr(node, 'title', r.path);
    setText(q(node, '.fp-rv-size'), r.size);
    setText(q(node, '.fp-rv-hash'), r.hash);
  }
}

export class RevisionsDialog extends Dialog {
  private readonly view: RevisionsView;

  constructor() {
    super('Revisions', 820, 'fp-rv-dlg');
    this.foot.hidden = true;
    this.view = new RevisionsView(this.body);
  }

  show(siteId: string, name: string): void {
    this.setTitle(`Revisions of ${name}`);
    this.open();
    void this.view.load(siteId);
  }
}
