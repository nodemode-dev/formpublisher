import '../styles/trash.css';
import { ApiError } from '../api';
import { OriginUnknownError, TRASH_ROOT, trashApi, type TrashEntry, type TrashKind } from '../api-trash';
import type { App } from '../app-api';
import { emit, on } from '../events';
import { confirmAction, Dialog } from './dialogs';
import { el, patchList, q, setAttr, setClass, setDisabled, setHidden, setText } from './dom';
import { icon } from './icons';
import { fmtBytes, fmtDate } from './builds';

const KIND_LABEL: Record<TrashKind, string> = { site: 'Site', build: 'Build', key: 'Key', prepared: 'Prepared folder' };
const KIND_ICON: Record<TrashKind, string> = { site: 'globe', build: 'package', key: 'key', prepared: 'publish' };
const LIVE = new Set(['site.removed', 'site.imported', 'builds.removed', 'builds.created', 'keys.removed', 'keys.created', 'publish.removed', 'publish.prepared']);

const message = (e: unknown): string => (e instanceof Error && e.message ? e.message : 'Request failed');

const SITE_ID = /^[a-z0-9][a-z0-9-]{0,100}$/;
const HEX12 = /^[0-9a-f]{12}$/;
const HEX16 = /^[0-9a-f]{16}$/;

function shapeError(kind: TrashKind, name: string): string {
  const parts = name.split('/');
  if (kind === 'site') return parts.length === 1 && SITE_ID.test(name) ? '' : 'A site name uses lowercase letters, digits and hyphens, and starts with a letter or a digit.';
  if (kind === 'key') return HEX16.test(name.replace(/\.pem$/, '')) ? '' : 'A key name is 16 characters from 0 to 9 and a to f.';
  if (kind === 'build') return parts.length === 2 && SITE_ID.test(parts[0]) && HEX12.test(parts[1]) ? '' : 'A build goes at <site>/<build id>, where the build id is 12 characters from 0 to 9 and a to f.';
  return parts.length === 3 && SITE_ID.test(parts[0]) && HEX12.test(parts[1]) && SITE_ID.test(parts[2]) ? '' : 'A prepared folder goes at <site>/<build id>/<target>.';
}

class OriginDialog extends Dialog {
  private readonly lead = el('<p class="fp-note"></p>');
  private readonly prefix = el('<span class="fp-tr-prefix" translate="no"></span>');
  private readonly input = el<HTMLInputElement>('<input class="fp-input is-mono" type="text" spellcheck="false" autocomplete="off" aria-label="Name" placeholder="For example a site id or a build path" translate="no">');
  private readonly error = el('<p class="fp-tr-origin-error" role="alert"></p>');
  private readonly ok: HTMLButtonElement;
  private item: TrashEntry | null = null;
  private busy = false;
  private resolve: ((v: boolean) => void) | null = null;

  constructor() {
    super('Where does it go', 460, 'fp-tr-dlg');
    const row = el('<div class="fp-tr-origin"></div>');
    row.append(this.prefix, this.input);
    this.body.append(this.lead, row, this.error);
    this.button('Cancel', 'ghost', () => this.close());
    this.ok = this.button('Restore', 'primary', () => { void this.submit(); });
    this.input.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); void this.submit(); } });
    this.input.addEventListener('input', () => setText(this.error, ''));
    this.onClose = () => { const r = this.resolve; this.resolve = null; r?.(false); };
  }

  ask(item: TrashEntry): Promise<boolean> {
    this.item = item;
    setText(this.lead, `${item.label} could not be placed on its own. Its folder is fixed by its kind (${KIND_LABEL[item.kind]}); type the name it should have there.`);
    setText(this.prefix, `${TRASH_ROOT[item.kind]}/`);
    this.input.value = '';
    setText(this.error, '');
    this.open(this.input);
    return new Promise((r) => { this.resolve = r; });
  }

  private async submit(): Promise<void> {
    const item = this.item;
    const name = this.input.value.trim().replace(/^\/+/, '');
    if (!item || this.busy) return;
    if (!name) { setText(this.error, 'Type a name.'); this.input.focus(); return; }
    const shape = shapeError(item.kind, name);
    if (shape) { setText(this.error, shape); this.input.focus(); return; }
    const origin = `${TRASH_ROOT[item.kind]}/${item.kind === 'key' && !name.endsWith('.pem') ? `${name}.pem` : name}`;
    this.busy = true;
    setDisabled(this.ok, true);
    setText(this.error, '');
    try {
      await trashApi.restore(item.entry, origin);
      const r = this.resolve;
      this.resolve = null;
      this.close();
      r?.(true);
    } catch (e) {
      setText(this.error, message(e));
      this.input.focus();
    }
    this.busy = false;
    setDisabled(this.ok, false);
  }
}

class PassphraseDialog extends Dialog {
  private readonly lead = el('<p class="fp-note"></p>');
  private readonly input = el<HTMLInputElement>('<input class="fp-input" type="password" spellcheck="false" autocomplete="off" aria-label="Passphrase" placeholder="Passphrase">');
  private readonly error = el('<p class="fp-tr-origin-error" role="alert"></p>');
  private readonly ok: HTMLButtonElement;
  private item: TrashEntry | null = null;
  private busy = false;
  private resolve: ((v: boolean) => void) | null = null;

  constructor() {
    super('Passphrase needed', 460, 'fp-tr-dlg');
    this.body.append(this.lead, this.input, this.error);
    this.button('Cancel', 'ghost', () => this.close());
    this.ok = this.button('Restore', 'primary', () => { void this.submit(); });
    this.input.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); void this.submit(); } });
    this.input.addEventListener('input', () => setText(this.error, ''));
    this.onClose = () => { this.input.value = ''; const r = this.resolve; this.resolve = null; r?.(false); };
  }

  ask(item: TrashEntry): Promise<boolean> {
    this.item = item;
    setText(this.lead, `${item.label} is locked. Type its passphrase to restore it.`);
    this.input.value = '';
    setText(this.error, '');
    this.open(this.input);
    return new Promise((r) => { this.resolve = r; });
  }

  private async submit(): Promise<void> {
    const item = this.item;
    if (!item || this.busy) return;
    if (!this.input.value) { setText(this.error, 'Type the passphrase.'); this.input.focus(); return; }
    this.busy = true;
    setDisabled(this.ok, true);
    setText(this.error, '');
    try {
      await trashApi.restore(item.entry, undefined, this.input.value);
      this.input.value = '';
      const r = this.resolve;
      this.resolve = null;
      this.close();
      r?.(true);
    } catch (e) {
      this.input.value = '';
      setText(this.error, message(e));
      this.input.focus();
    }
    this.busy = false;
    setDisabled(this.ok, false);
  }
}

export class TrashPage {
  private readonly skeleton: HTMLElement;
  private readonly empty: HTMLElement;
  private readonly list: HTMLElement;
  private readonly emptyBtn: HTMLButtonElement;
  private entries: TrashEntry[] = [];
  private loaded = false;
  private seq = 0;
  private busy = false;
  private originDialog: OriginDialog | null = null;
  private passDialog: PassphraseDialog | null = null;

  constructor(private readonly app: App, private readonly host: HTMLElement) {
    host.appendChild(el(`<div class="fp-home-head"><div><h1 class="fp-home-title">Trash</h1><p class="fp-home-sub">Removed sites, builds, keys and prepared folders stay here until you delete them for good.</p></div>
<div class="fp-bl-tools"><button class="fp-btn" type="button" data-t="empty" disabled>${icon('trash', 14)}<span>Empty Trash</span></button></div></div>`));
    host.appendChild(el(`<div class="fp-tr">
<div class="fp-tr-row is-head"><span></span><span>Item</span><span>Kind</span><span>Moved</span><span>Size</span><span></span></div>
<div class="fp-tr-skel" aria-hidden="true"><div class="fp-tr-row is-skeleton"><span></span><span>&nbsp;</span><span></span><span></span><span></span><span></span></div><div class="fp-tr-row is-skeleton"><span></span><span>&nbsp;</span><span></span><span></span><span></span><span></span></div><div class="fp-tr-row is-skeleton"><span></span><span>&nbsp;</span><span></span><span></span><span></span><span></span></div></div>
<div class="fp-tr-empty" hidden><span class="fp-empty-icon">${icon('trash', 20)}</span><div class="fp-empty-title">Nothing in the trash</div><div class="fp-empty-text">Sites, builds, keys and prepared folders you remove show up here.</div></div>
<div class="fp-tr-list"></div>
</div>`));
    this.skeleton = q(host, '.fp-tr-skel');
    this.empty = q(host, '.fp-tr-empty');
    this.list = q(host, '.fp-tr-list');
    this.emptyBtn = q<HTMLButtonElement>(host, '[data-t="empty"]');
    this.wire();
  }

  async refresh(): Promise<void> {
    const seq = ++this.seq;
    try {
      const rows = await trashApi.list();
      if (seq !== this.seq) return;
      this.entries = rows;
      this.loaded = true;
      this.paint();
    } catch (e) {
      if (seq !== this.seq) return;
      this.loaded = true;
      this.paint();
      if (!this.host.hidden) emit('fp:notice', { kind: 'error', text: message(e) });
    }
  }

  private paint(): void {
    setHidden(this.skeleton, this.loaded);
    setHidden(this.empty, !this.loaded || this.entries.length > 0);
    setDisabled(this.emptyBtn, this.entries.length === 0 || this.busy);
    patchList(this.list, this.entries, {
      key: (e) => e.entry,
      create: (e) => {
        const n = el(`<div class="fp-tr-row"><span class="fp-tr-ico"></span><span class="fp-tr-label" translate="no"></span><span class="fp-tr-kind"></span><span class="fp-tr-moved" translate="no"></span><span class="fp-tr-size" translate="no"></span><span class="fp-tr-acts"><button class="fp-icon-btn is-sm" type="button" data-t="restore" title="Restore" aria-label="Restore">${icon('undo', 14)}</button><button class="fp-icon-btn is-sm" type="button" data-t="delete" title="Delete for good" aria-label="Delete for good">${icon('trash', 14)}</button></span></div>`);
        this.fillRow(n, e);
        return n;
      },
      update: (n, e) => this.fillRow(n, e),
    });
  }

  private fillRow(n: HTMLElement, e: TrashEntry): void {
    const ico = q(n, '.fp-tr-ico');
    if (ico.dataset.kind !== e.kind) {
      ico.innerHTML = icon(KIND_ICON[e.kind], 16);
      ico.dataset.kind = e.kind;
    }
    setText(q(n, '.fp-tr-label'), e.label);
    setAttr(q(n, '.fp-tr-label'), 'title', e.origin ?? e.entry);
    setText(q(n, '.fp-tr-kind'), KIND_LABEL[e.kind]);
    setText(q(n, '.fp-tr-moved'), e.moved ? fmtDate(e.moved) : '-');
    setText(q(n, '.fp-tr-size'), fmtBytes(e.size));
  }

  private setBusy(on: boolean, row?: HTMLElement): void {
    this.busy = on;
    setDisabled(this.emptyBtn, on || this.entries.length === 0);
    if (row) setClass(row, 'is-busy', on);
  }

  private wire(): void {
    this.host.addEventListener('click', (ev) => {
      const t = (ev.target as HTMLElement).closest<HTMLElement>('[data-t]');
      if (!t || this.busy) return;
      const act = t.dataset.t;
      if (act === 'empty') { void this.emptyAll(); return; }
      const row = t.closest<HTMLElement>('.fp-tr-row');
      const item = this.entries.find((x) => x.entry === row?.dataset.key);
      if (!row || !item) return;
      if (act === 'restore') void this.restore(item, row);
      else if (act === 'delete') void this.remove(item, row);
    });
    on('fp:live', (ev) => {
      if ((LIVE.has(ev.type) || ev.type.startsWith('trash.')) && !this.host.hidden) void this.refresh();
    });
  }

  private async restore(item: TrashEntry, row: HTMLElement): Promise<void> {
    this.setBusy(true, row);
    try {
      let done = true;
      try {
        await trashApi.restore(item.entry);
      } catch (e) {
        if (e instanceof OriginUnknownError) {
          this.originDialog ??= new OriginDialog();
          done = await this.originDialog.ask(item);
        } else if (e instanceof ApiError && e.code === 'passphrase-required') {
          this.passDialog ??= new PassphraseDialog();
          done = await this.passDialog.ask(item);
        } else {
          throw e;
        }
      }
      if (done) {
        emit('fp:notice', { kind: 'ok', text: `Restored ${item.label}` });
        if (item.kind === 'site') await this.app.refreshSites();
      }
    } catch (e) {
      emit('fp:notice', { kind: 'error', text: message(e) });
    }
    this.setBusy(false, row);
    await this.refresh();
  }

  private async remove(item: TrashEntry, row: HTMLElement): Promise<void> {
    if (!(await confirmAction('Delete for good', `Delete ${item.label} for good? This cannot be undone.`, 'Delete', true))) return;
    this.setBusy(true, row);
    try {
      await trashApi.remove(item.entry);
      emit('fp:notice', { kind: 'ok', text: `Deleted ${item.label}` });
    } catch (e) {
      emit('fp:notice', { kind: 'error', text: message(e) });
    }
    this.setBusy(false, row);
    await this.refresh();
  }

  private async emptyAll(): Promise<void> {
    if (!(await confirmAction('Empty Trash', 'Delete everything in the trash for good? This cannot be undone.', 'Empty Trash', true))) return;
    this.setBusy(true);
    try {
      await trashApi.empty();
      emit('fp:notice', { kind: 'ok', text: 'The trash is empty' });
    } catch (e) {
      emit('fp:notice', { kind: 'error', text: message(e) });
    }
    this.setBusy(false);
    await this.refresh();
  }
}
