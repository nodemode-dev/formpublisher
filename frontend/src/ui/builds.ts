import '../styles/package.css';
import { buildsApi, type BuildDetail, type BuildSummary, type CompareResult } from '../api-builds';
import type { App } from '../app-api';
import { emit, on } from '../events';
import { locale, onLanguage, t } from '../i18n';
import { confirmAction, Dialog } from './dialogs';
import { el, patchList, q, setAttr, setClass, setDisabled, setHidden, setText } from './dom';
import { icon } from './icons';
import { refuse } from './notice-step';

export function fmtBytes(n: number): string {
  if (!Number.isFinite(n) || n < 0) return '-';
  if (n < 1024) return `${n} B`;
  const units = ['KB', 'MB', 'GB'];
  let v = n / 1024;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i += 1; }
  return `${v >= 100 ? Math.round(v) : v.toFixed(1)} ${units[i]}`;
}

export function fmtDate(iso: string): string {
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return '-';
  try {
    return new Intl.DateTimeFormat(locale(), { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(t));
  } catch {
    return iso;
  }
}

export function fmtCount(n: number, one: string, many: string): string {
  return n === 1 ? `1 ${one}` : `${n} ${many}`;
}

export async function copyText(text: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text);
    emit('fp:notice', { kind: 'ok', text: 'Copied' });
  } catch {
    emit('fp:notice', { kind: 'error', text: 'Copy is not available here' });
  }
}

let libraryOpener: ((id: string) => void) | null = null;

export function setLibraryOpener(fn: (id: string) => void): void { libraryOpener = fn; }

export function showInLibrary(id: string): void { libraryOpener?.(id); }

const message = (e: unknown): string => (e instanceof Error && e.message ? e.message : 'Request failed');

class InspectDialog extends Dialog {
  private readonly fields: Record<string, HTMLElement>;
  private readonly list: HTMLElement;
  private readonly empty: HTMLElement;
  private seq = 0;

  constructor() {
    super('Build', 660, 'fp-pkg-dlg');
    this.body.appendChild(el(`<div class="fp-pkg-wrap"><div class="fp-pkg-info">
<span class="fp-pkg-k">Site</span><span class="fp-pkg-v" data-f="site" translate="no"></span>
<span class="fp-pkg-k">Revision</span><span class="fp-pkg-v is-mono" data-f="revision" translate="no"></span>
<span class="fp-pkg-k">Build id</span><span class="fp-pkg-v is-mono" data-f="id" translate="no"></span>
<span class="fp-pkg-k">SHA-256</span><span class="fp-pkg-v is-mono" data-f="sha" translate="no"></span>
<span class="fp-pkg-k">Built</span><span class="fp-pkg-v" data-f="date" translate="no"></span>
<span class="fp-pkg-k">Size</span><span class="fp-pkg-v" data-f="size" translate="no"></span>
</div>
<div class="fp-pkg-files"><div class="fp-pkg-frow is-head"><span>File</span><span>Size</span><span>SHA-256</span></div><div class="fp-pkg-flist"></div><div class="fp-pkg-fnone" hidden>No files</div></div></div>`));
    this.fields = {};
    for (const n of Array.from(this.body.querySelectorAll<HTMLElement>('[data-f]'))) this.fields[n.dataset.f ?? ''] = n;
    this.list = q(this.body, '.fp-pkg-flist');
    this.empty = q(this.body, '.fp-pkg-fnone');
    this.button('Close', 'ghost', () => this.close());
  }

  async show(summary: BuildSummary, siteName: string): Promise<void> {
    const seq = ++this.seq;
    this.fill(summary, siteName, []);
    this.open();
    try {
      const d = await buildsApi.detail(summary.id);
      if (seq === this.seq) this.fill(d, siteName || d.siteName, d.fileList);
    } catch (e) {
      if (seq === this.seq) refuse(e, message(e), summary.id);
    }
  }

  private fill(b: BuildSummary, siteName: string, files: BuildDetail['fileList']): void {
    setText(this.fields.site, siteName || b.site);
    setText(this.fields.revision, b.revision || '-');
    setText(this.fields.id, b.id);
    setText(this.fields.sha, b.sha256 || '-');
    setText(this.fields.date, fmtDate(b.created));
    setText(this.fields.size, `${fmtBytes(b.size)}, ${t(fmtCount(b.files, 'file', 'files'))}`);
    setHidden(this.empty, files.length > 0 || b.files > 0);
    patchList(this.list, files, {
      key: (f) => f.path,
      create: (f) => {
        const n = el('<div class="fp-pkg-frow"><span class="fp-pkg-fpath" translate="no"></span><span class="fp-pkg-fsize" translate="no"></span><span class="fp-pkg-fsha" translate="no"></span></div>');
        this.fillFile(n, f);
        return n;
      },
      update: (n, f) => this.fillFile(n, f),
    });
  }

  private fillFile(n: HTMLElement, f: { path: string; sha256: string; size: number }): void {
    setText(q(n, '.fp-pkg-fpath'), f.path);
    setAttr(n, 'title', f.path);
    setText(q(n, '.fp-pkg-fsize'), fmtBytes(f.size));
    setText(q(n, '.fp-pkg-fsha'), f.sha256.slice(0, 16));
  }
}

class CompareDialog extends Dialog {
  private readonly sum: HTMLElement;
  private readonly head: HTMLElement;
  private readonly list: HTMLElement;
  private readonly none: HTMLElement;
  private readonly results = new Map<string, CompareResult>();
  private seq = 0;

  constructor() {
    super('Compare builds', 660, 'fp-pkg-dlg');
    this.body.appendChild(el(`<div class="fp-pkg-wrap"><div class="fp-pkg-cmp-head"><span class="fp-pkg-id" data-s="a" translate="no"></span>${icon('compare', 14)}<span class="fp-pkg-id" data-s="b" translate="no"></span></div>
<div class="fp-pkg-sum"></div>
<div class="fp-pkg-files"><div class="fp-pkg-flist fp-pkg-clist"></div><div class="fp-pkg-fnone" hidden>No differences. The two builds hold the same files.</div></div></div>`));
    this.head = q(this.body, '.fp-pkg-cmp-head');
    this.sum = q(this.body, '.fp-pkg-sum');
    this.list = q(this.body, '.fp-pkg-clist');
    this.none = q(this.body, '.fp-pkg-fnone');
    this.button('Close', 'ghost', () => this.close());
  }

  async show(a: string, b: string): Promise<void> {
    const seq = ++this.seq;
    const pair = `${a}:${b}`;
    const known = this.results.get(pair);
    setText(q(this.head, '[data-s="a"]'), a);
    setText(q(this.head, '[data-s="b"]'), b);
    if (known) this.fill(known);
    else {
      setText(this.sum, 'Comparing');
      setHidden(this.none, true);
      if (!this.isOpen) this.fill(null);
    }
    this.open();
    try {
      const r = await buildsApi.compare(a, b);
      if (seq !== this.seq) return;
      this.results.set(pair, r);
      this.fill(r);
    } catch (e) {
      if (seq !== this.seq) return;
      setText(this.sum, message(e));
    }
  }

  private fill(r: CompareResult | null): void {
    if (!r) {
      patchList(this.list, [], { key: () => '', create: () => el('<div></div>'), update: () => undefined });
      return;
    }
    setText(this.sum, `${r.added.length} added, ${r.removed.length} removed, ${r.changed.length} changed, ${r.same} unchanged`);
    const rows: Array<{ kind: 'added' | 'removed' | 'changed'; path: string; note: string }> = [
      ...r.added.map((p) => ({ kind: 'added' as const, path: p, note: '' })),
      ...r.removed.map((p) => ({ kind: 'removed' as const, path: p, note: '' })),
      ...r.changed.map((c) => ({ kind: 'changed' as const, path: c.path, note: `${fmtBytes(c.a.size)} to ${fmtBytes(c.b.size)}` })),
    ];
    setHidden(this.none, rows.length > 0);
    patchList(this.list, rows, {
      key: (x) => `${x.kind}:${x.path}`,
      create: (x) => {
        const n = el('<div class="fp-pkg-crow"><span class="fp-pkg-tag"></span><span class="fp-pkg-fpath" translate="no"></span><span class="fp-pkg-fsize" translate="no"></span></div>');
        this.fillRow(n, x);
        return n;
      },
      update: (n, x) => this.fillRow(n, x),
    });
  }

  private fillRow(n: HTMLElement, x: { kind: string; path: string; note: string }): void {
    const tag = q(n, '.fp-pkg-tag');
    setText(tag, x.kind === 'added' ? 'Added' : x.kind === 'removed' ? 'Removed' : 'Changed');
    setClass(tag, 'is-added', x.kind === 'added');
    setClass(tag, 'is-removed', x.kind === 'removed');
    setClass(tag, 'is-changed', x.kind === 'changed');
    setText(q(n, '.fp-pkg-fpath'), x.path);
    setAttr(n, 'title', x.path);
    setText(q(n, '.fp-pkg-fsize'), x.note);
  }
}

export class BuildsPage {
  private readonly skeleton: HTMLElement;
  private readonly empty: HTMLElement;
  private readonly list: HTMLElement;
  private readonly compareBtn: HTMLButtonElement;
  private builds: BuildSummary[] = [];
  private picked: string[] = [];
  private loaded = false;
  private seq = 0;
  private inspect: InspectDialog | null = null;
  private compare: CompareDialog | null = null;

  constructor(private readonly app: App, private readonly host: HTMLElement, private readonly confirm: typeof confirmAction = confirmAction) {
    host.appendChild(el(`<div class="fp-home-head"><div><h1 class="fp-home-title">Builds</h1><p class="fp-home-sub">Packages you have built, newest first.</p></div>
<div class="fp-home-head-actions fp-bl-tools"><span class="fp-bl-hint">Choose two builds to compare</span><button class="fp-btn" type="button" data-b="compare" disabled>${icon('compare', 14)}<span>Compare</span></button></div></div>`));
    host.appendChild(el(`<div class="fp-bl">
<div class="fp-bl-row is-head"><span></span><span>Site</span><span>Build</span><span>Built</span><span>Size</span><span>Signed</span><span></span></div>
<div class="fp-bl-row is-skeleton" aria-hidden="true"><span></span><span>&nbsp;</span><span></span><span></span><span></span><span></span><span></span></div>
<div class="fp-bl-empty" hidden><span class="fp-empty-icon">${icon('package', 20)}</span><div class="fp-empty-title">No builds yet</div><div class="fp-empty-text">Open a site and choose Package Site to build one.</div></div>
<div class="fp-bl-list"></div>
</div>`));
    this.skeleton = q(host, '.is-skeleton');
    this.empty = q(host, '.fp-bl-empty');
    this.list = q(host, '.fp-bl-list');
    this.compareBtn = q<HTMLButtonElement>(host, '[data-b="compare"]');
    this.wire();
    onLanguage(() => this.paint());
  }

  async refresh(): Promise<void> {
    const seq = ++this.seq;
    try {
      const rows = await buildsApi.list();
      if (seq !== this.seq) return;
      this.builds = rows;
      this.loaded = true;
      this.paint();
    } catch (e) {
      if (seq !== this.seq) return;
      this.loaded = true;
      this.paint();
      if (!this.host.hidden) emit('fp:notice', { kind: 'error', text: message(e) });
    }
  }

  async reveal(id: string): Promise<void> {
    await this.refresh();
    const row = Array.from(this.list.children).find((n) => (n as HTMLElement).dataset.key === id);
    if (!row) return;
    row.scrollIntoView({ block: 'nearest' });
    row.classList.add('is-hot');
    window.setTimeout(() => row.classList.remove('is-hot'), 1800);
  }

  private siteName(id: string): string {
    return this.app.state().sites.find((s) => s.id === id)?.name ?? id;
  }

  private paint(): void {
    const ids = new Set(this.builds.map((b) => b.id));
    this.picked = this.picked.filter((id) => ids.has(id));
    setHidden(this.skeleton, this.loaded);
    setHidden(this.empty, !this.loaded || this.builds.length > 0);
    patchList(this.list, this.builds, {
      key: (b) => b.id,
      create: (b) => {
        const n = el(`<div class="fp-bl-row"><label class="fp-bl-pick"><input type="checkbox" data-b="pick" aria-label="Choose for comparison"></label><span class="fp-bl-site" translate="no"></span><span class="fp-bl-id" translate="no"></span><span class="fp-bl-date" translate="no"></span><span class="fp-bl-size" translate="no"></span><span class="fp-bl-sig"><span class="fp-badge"></span></span><span class="fp-bl-acts"><button class="fp-icon-btn is-sm" type="button" data-b="inspect" title="Inspect" aria-label="Inspect">${icon('search', 14)}</button><a class="fp-icon-btn is-sm" data-b="download" title="Download" aria-label="Download" download>${icon('download', 14)}</a><a class="fp-icon-btn is-sm" data-b="fpub" title="Save as .fpub" aria-label="Save as .fpub" download>${icon('archive', 14)}</a><button class="fp-icon-btn is-sm" type="button" data-b="delete" title="Delete" aria-label="Delete">${icon('trash', 14)}</button></span></div>`);
        this.fillRow(n, b);
        return n;
      },
      update: (n, b) => this.fillRow(n, b),
    });
    setDisabled(this.compareBtn, this.picked.length !== 2);
  }

  private fillRow(n: HTMLElement, b: BuildSummary): void {
    setText(q(n, '.fp-bl-site'), this.siteName(b.site));
    setText(q(n, '.fp-bl-id'), b.id);
    setText(q(n, '.fp-bl-date'), fmtDate(b.created));
    setText(q(n, '.fp-bl-size'), fmtBytes(b.size));
    const badge = q(n, '.fp-badge');
    setText(badge, b.signed ? 'Signed' : 'Unsigned');
    setClass(badge, 'is-signed', b.signed);
    setAttr(q(n, '[data-b="download"]'), 'href', buildsApi.downloadUrl(b.id));
    setAttr(q(n, '[data-b="fpub"]'), 'href', buildsApi.fpubUrl(b.id));
    setAttr(q(n, '[data-b="fpub"]'), 'download', `${b.site}-${b.id}.fpub`);
    const box = q<HTMLInputElement>(n, '[data-b="pick"]');
    const on = this.picked.includes(b.id);
    if (box.checked !== on) box.checked = on;
    setClass(n, 'is-picked', on);
  }

  private wire(): void {
    this.host.addEventListener('change', (e) => {
      const t = e.target as HTMLElement;
      if (!(t instanceof HTMLInputElement) || t.dataset.b !== 'pick') return;
      const id = t.closest<HTMLElement>('.fp-bl-row')?.dataset.key;
      if (!id) return;
      this.picked = this.picked.filter((x) => x !== id);
      if (t.checked) this.picked.push(id);
      if (this.picked.length > 2) this.picked = this.picked.slice(-2);
      this.paint();
    });
    this.host.addEventListener('click', (e) => {
      const t = (e.target as HTMLElement).closest<HTMLElement>('[data-b]');
      if (!t) return;
      const act = t.dataset.b;
      const id = t.closest<HTMLElement>('.fp-bl-row')?.dataset.key;
      if (act === 'compare') {
        if (this.picked.length !== 2) return;
        this.compare ??= new CompareDialog();
        const order = this.builds.map((b) => b.id);
        const [older, newer] = [...this.picked].sort((x, y) => order.indexOf(y) - order.indexOf(x));
        void this.compare.show(older, newer);
        return;
      }
      const b = this.builds.find((x) => x.id === id);
      if (!b) return;
      if (act === 'inspect') {
        this.inspect ??= new InspectDialog();
        void this.inspect.show(b, this.siteName(b.site));
      } else if (act === 'delete') {
        void this.remove(b);
      }
    });
    on('fp:live', (ev) => {
      if (ev.type === 'builds.created' || ev.type === 'builds.removed') void this.refresh();
    });
  }

  private async remove(b: BuildSummary): Promise<void> {
    if (!(await this.confirm('Delete build',`Move build ${b.id} to the trash? Its zip, record and signature stay in the trash folder of the data folder.`, 'Move to Trash', true))) return;
    try {
      await buildsApi.remove(b.id);
      emit('fp:notice', { kind: 'ok', text: `Moved build ${b.id} to the trash` });
    } catch (e) {
      refuse(e, message(e), b.id);
    }
    await this.refresh();
  }
}
