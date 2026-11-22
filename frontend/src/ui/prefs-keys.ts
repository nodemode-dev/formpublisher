import { buildsApi, type KeyInfo, type KeySecret } from '../api-builds';
import { on } from '../events';
import { locale, onLanguage } from '../i18n';
import { el, patchList, q, setAttr, setClass, setDisabled, setHidden, setText } from './dom';
import { icon } from './icons';
import { confirmRemoveKey, exportKeyDialog, importKeyDialog } from './key-transfer';

export const KEPT: Record<KeySecret, string> = { store: 'Password store', file: 'Private file', none: 'Verify only' };

type Tone = '' | 'ok' | 'error';

const message = (e: unknown): string => (e instanceof Error && e.message ? e.message : 'Request failed');

export const keysPanelHtml = (): string => `<section class="fp-prefs-group"><h3 class="fp-prefs-label">Your keys</h3>
<div class="fp-keys-box"><div class="fp-keys-list" role="list" aria-label="Signing keys"></div><div class="fp-keys-empty" hidden>No keys yet. Create one below or import one.</div></div>
<div class="fp-keys-foot"><span class="fp-keys-status" role="status" aria-live="polite"></span><button class="fp-btn fp-btn-sm" type="button" data-kact="import">${icon('download', 14)}<span>Import...</span></button></div>
</section>
<section class="fp-prefs-group"><h3 class="fp-prefs-label">New key</h3>
<div class="fp-keys-new"><input class="fp-input" data-k="name" placeholder="Key name" aria-label="Key name" autocomplete="off"><input class="fp-input fp-keys-pass" type="password" data-k="pass" placeholder="Passphrase (optional)" aria-label="New key passphrase" autocomplete="new-password"><button class="fp-btn" type="button" data-kact="create">${icon('plus', 14)}<span>Create key</span></button></div>
</section>`;

export class KeysPanel {
  private keys: KeyInfo[] = [];
  private loaded = false;
  private busy = false;
  private seq = 0;
  private readonly list: HTMLElement;
  private readonly empty: HTMLElement;
  private readonly status: HTMLElement;
  private readonly name: HTMLInputElement;
  private readonly pass: HTMLInputElement;
  private readonly createBtn: HTMLButtonElement;
  private readonly importBtn: HTMLButtonElement;

  constructor(root: HTMLElement, private readonly visible: () => boolean) {
    this.list = q(root, '.fp-keys-list');
    this.empty = q(root, '.fp-keys-empty');
    this.status = q(root, '.fp-keys-status');
    this.name = q<HTMLInputElement>(root, '[data-k="name"]');
    this.pass = q<HTMLInputElement>(root, '[data-k="pass"]');
    this.createBtn = q<HTMLButtonElement>(root, '[data-kact="create"]');
    this.importBtn = q<HTMLButtonElement>(root, '[data-kact="import"]');
    root.addEventListener('click', (e) => {
      const btn = (e.target as HTMLElement).closest<HTMLElement>('[data-kact]');
      const act = btn?.dataset.kact;
      if (!btn || !act) return;
      if (act === 'create') { void this.create(); return; }
      if (act === 'import') { importKeyDialog((k) => { this.say(`Imported key ${k.name}`, 'ok'); void this.refresh(); }); return; }
      const key = this.keys.find((k) => k.id === btn.closest<HTMLElement>('[data-key]')?.dataset.key);
      if (!key) return;
      if (act === 'export' && key.canSign) exportKeyDialog(key);
      else if (act === 'remove') void this.remove(key);
    });
    for (const input of [this.name, this.pass]) {
      input.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); void this.create(); } });
      input.addEventListener('input', () => { if (this.status.classList.contains('is-error')) this.say('', ''); });
    }
    on('fp:live', (ev) => { if (ev.type.startsWith('keys.') && this.visible()) void this.refresh(); });
    onLanguage(() => this.paint());
  }

  shown(): void {
    void this.refresh();
  }

  async refresh(): Promise<void> {
    const seq = ++this.seq;
    try {
      const rows = await buildsApi.keys();
      if (seq !== this.seq) return;
      this.keys = rows;
      this.loaded = true;
    } catch (e) {
      if (seq !== this.seq) return;
      this.say(message(e), 'error');
    }
    this.paint();
  }

  private date(iso: string): string {
    const d = new Date(iso);
    if (!iso || Number.isNaN(d.getTime())) return '-';
    try { return new Intl.DateTimeFormat(locale(), { dateStyle: 'medium' }).format(d); } catch { return d.toISOString().slice(0, 10); }
  }

  private paint(): void {
    patchList(this.list, this.keys, {
      key: (k) => k.id,
      create: (k) => {
        const node = el(`<div class="fp-key-row" role="listitem"><span class="fp-key-icon">${icon('key', 16)}</span><div class="fp-key-main"><span class="fp-key-name" translate="no"></span><span class="fp-key-meta"><span class="fp-key-fp" translate="no"></span><span class="fp-key-date"></span><span class="fp-key-kept"></span></span></div><button class="fp-btn fp-btn-sm fp-btn-ghost" type="button" data-kact="export">Export...</button><button class="fp-btn fp-btn-sm fp-btn-ghost fp-key-remove" type="button" data-kact="remove">Remove</button></div>`);
        this.paintRow(node, k);
        return node;
      },
      update: (node, k) => this.paintRow(node, k),
    });
    setHidden(this.empty, !this.loaded || this.keys.length > 0);
    this.sync();
  }

  private paintRow(node: HTMLElement, k: KeyInfo): void {
    setText(q(node, '.fp-key-name'), k.name);
    setText(q(node, '.fp-key-fp'), k.fingerprint.slice(0, 22));
    setAttr(q(node, '.fp-key-fp'), 'title', k.fingerprint);
    setText(q(node, '.fp-key-date'), `Created on ${this.date(k.created)}`);
    setText(q(node, '.fp-key-kept'), KEPT[k.secret]);
    setClass(node, 'is-verify-only', !k.canSign);
    const exp = q<HTMLButtonElement>(node, '[data-kact="export"]');
    setDisabled(exp, this.busy || !k.canSign);
    setAttr(exp, 'title', k.canSign ? 'Export key' : 'This key can verify but not sign: it has no private key here.');
    setDisabled(q<HTMLButtonElement>(node, '[data-kact="remove"]'), this.busy);
  }

  private sync(): void {
    setDisabled(this.createBtn, this.busy);
    setDisabled(this.importBtn, this.busy);
    for (const node of Array.from(this.list.children) as HTMLElement[]) {
      const k = this.keys.find((x) => x.id === node.dataset.key);
      if (k) this.paintRow(node, k);
    }
  }

  private say(text: string, tone: Tone): void {
    setText(this.status, text);
    setClass(this.status, 'is-ok', tone === 'ok');
    setClass(this.status, 'is-error', tone === 'error');
  }

  private async guard(fn: () => Promise<void>): Promise<void> {
    if (this.busy) return;
    this.busy = true;
    this.sync();
    try {
      await fn();
    } finally {
      this.busy = false;
      this.sync();
    }
  }

  private async create(): Promise<void> {
    const name = this.name.value.trim();
    if (!name) { this.say('Give the key a name.', 'error'); this.name.focus(); return; }
    await this.guard(async () => {
      try {
        const k = await buildsApi.createKey(name, this.pass.value);
        this.name.value = '';
        this.pass.value = '';
        this.say(`Created key ${k.name}.`, 'ok');
        await this.refresh();
      } catch (e) {
        this.pass.value = '';
        this.say(message(e), 'error');
      }
    });
  }

  private async remove(key: KeyInfo): Promise<void> {
    if (!(await confirmRemoveKey(key))) return;
    await this.guard(async () => {
      try {
        await buildsApi.removeKey(key.id);
        this.say(`Removed key ${key.name}.`, 'ok');
      } catch (e) {
        this.say(message(e), 'error');
      }
      await this.refresh();
    });
  }
}
