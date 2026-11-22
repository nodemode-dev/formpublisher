import { buildsApi, type KeyInfo } from '../api-builds';
import { emit } from '../events';
import { Dialog } from './dialogs';
import { el, q, setHidden, setText } from './dom';

const MIN = 8;
const MAX_PEM = 16 * 1024;
const message = (e: unknown): string => (e instanceof Error && e.message ? e.message : 'Request failed');

class ExportKeyDialog extends Dialog {
  private readonly lead: HTMLElement;
  private readonly path: HTMLInputElement;
  private readonly currentBox: HTMLElement;
  private readonly current: HTMLInputElement;
  private readonly pass: HTMLInputElement;
  private readonly again: HTMLInputElement;
  private readonly error: HTMLElement;
  private readonly ok: HTMLButtonElement;
  private key: KeyInfo | null = null;
  private busy = false;

  constructor() {
    super('Export key', 460, 'fp-kt-dlg');
    this.body.appendChild(el(`<div class="fp-kt-form">
<p class="fp-note" data-k="lead"></p>
<label class="fp-dialog-label" for="fp-kt-path">File to write on this computer</label>
<input id="fp-kt-path" class="fp-input is-mono" type="text" spellcheck="false" autocomplete="off" translate="no" placeholder="/path/to/key.pem">
<div class="fp-kt-field" data-k="current" hidden><label class="fp-dialog-label" for="fp-kt-current">Passphrase of this key</label><input id="fp-kt-current" class="fp-input" type="password" autocomplete="off"></div>
<label class="fp-dialog-label" for="fp-kt-pass">Passphrase for the exported file (at least 8 characters)</label>
<input id="fp-kt-pass" class="fp-input" type="password" autocomplete="new-password">
<label class="fp-dialog-label" for="fp-kt-again">Type it again</label>
<input id="fp-kt-again" class="fp-input" type="password" autocomplete="new-password">
<div class="fp-dialog-error fp-kt-error" role="alert"></div>
</div>`));
    this.lead = q(this.body, '[data-k="lead"]');
    this.path = q<HTMLInputElement>(this.body, '#fp-kt-path');
    this.currentBox = q(this.body, '[data-k="current"]');
    this.current = q<HTMLInputElement>(this.body, '#fp-kt-current');
    this.pass = q<HTMLInputElement>(this.body, '#fp-kt-pass');
    this.again = q<HTMLInputElement>(this.body, '#fp-kt-again');
    this.error = q(this.body, '.fp-kt-error');
    this.button('Cancel', 'ghost', () => this.close());
    this.ok = this.button('Export', 'primary', () => { void this.submit(); });
    for (const input of [this.path, this.current, this.pass, this.again]) {
      input.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); void this.submit(); } });
      input.addEventListener('input', () => setText(this.error, ''));
    }
    this.onClose = () => this.wipe();
  }

  ask(key: KeyInfo): void {
    this.key = key;
    this.wipe();
    setText(this.error, '');
    setText(this.lead, `The private key of ${key.name} is written as a PEM file, encrypted with the passphrase you choose here. Keep the file and the passphrase apart.`);
    setHidden(this.currentBox, !key.encrypted);
    this.open(this.path);
  }

  private wipe(): void {
    this.current.value = '';
    this.pass.value = '';
    this.again.value = '';
  }

  private fail(text: string, focus: HTMLInputElement): void {
    setText(this.error, text);
    focus.focus();
  }

  private async submit(): Promise<void> {
    const key = this.key;
    if (!key || this.busy) return;
    const path = this.path.value.trim();
    if (!path || !/\.pem$/i.test(path)) { this.fail('Give the full path of the file to write, ending in .pem.', this.path); return; }
    if (key.encrypted && !this.current.value) { this.fail('This key needs a passphrase.', this.current); return; }
    if (this.pass.value.length < MIN) { this.fail('Choose a passphrase of at least 8 characters for the exported key.', this.pass); return; }
    if (this.pass.value !== this.again.value) { this.fail('The two passphrases differ.', this.again); return; }
    this.busy = true;
    this.ok.disabled = true;
    const pass = this.pass.value;
    const current = this.current.value;
    this.wipe();
    try {
      const file = await buildsApi.exportKey(key.id, path, pass, current);
      this.close();
      emit('fp:notice', { kind: 'ok', text: `Exported key ${key.name} to ${file}` });
    } catch (e) {
      this.fail(message(e), this.pass);
    } finally {
      this.busy = false;
      this.ok.disabled = false;
    }
  }
}

class ImportKeyDialog extends Dialog {
  private readonly file: HTMLInputElement;
  private readonly name: HTMLInputElement;
  private readonly pass: HTMLInputElement;
  private readonly error: HTMLElement;
  private readonly ok: HTMLButtonElement;
  private busy = false;
  private done: ((k: KeyInfo) => void) | null = null;

  constructor() {
    super('Import key', 460, 'fp-kt-dlg');
    this.body.appendChild(el(`<div class="fp-kt-form">
<p class="fp-note">Add a signing key from a PEM private key file, such as one exported from FormPublisher. Its secret goes into the system password store, or a file only you can read.</p>
<label class="fp-dialog-label" for="fp-kt-file">PEM file</label>
<input id="fp-kt-file" class="fp-input" type="file" accept=".pem,application/x-pem-file,text/plain">
<label class="fp-dialog-label" for="fp-kt-name">Key name (optional)</label>
<input id="fp-kt-name" class="fp-input" type="text" autocomplete="off">
<label class="fp-dialog-label" for="fp-kt-ipass">Passphrase of the file, when it has one</label>
<input id="fp-kt-ipass" class="fp-input" type="password" autocomplete="off">
<div class="fp-dialog-error fp-kt-error" role="alert"></div>
</div>`));
    this.file = q<HTMLInputElement>(this.body, '#fp-kt-file');
    this.name = q<HTMLInputElement>(this.body, '#fp-kt-name');
    this.pass = q<HTMLInputElement>(this.body, '#fp-kt-ipass');
    this.error = q(this.body, '.fp-kt-error');
    this.button('Cancel', 'ghost', () => this.close());
    this.ok = this.button('Import', 'primary', () => { void this.submit(); });
    for (const input of [this.name, this.pass]) {
      input.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); void this.submit(); } });
    }
    for (const input of [this.file, this.name, this.pass]) input.addEventListener('input', () => setText(this.error, ''));
    this.onClose = () => this.wipe();
  }

  ask(done: (k: KeyInfo) => void): void {
    this.done = done;
    this.wipe();
    this.name.value = '';
    setText(this.error, '');
    this.open(this.file);
  }

  private wipe(): void {
    this.pass.value = '';
    this.file.value = '';
  }

  private async submit(): Promise<void> {
    if (this.busy) return;
    const chosen = this.file.files?.[0];
    if (!chosen) { setText(this.error, 'Choose a PEM file.'); this.file.focus(); return; }
    if (chosen.size > MAX_PEM) { setText(this.error, 'That is not a PEM private key FormPublisher can read.'); this.file.focus(); return; }
    this.busy = true;
    this.ok.disabled = true;
    const pass = this.pass.value;
    this.pass.value = '';
    try {
      const k = await buildsApi.importKey(await chosen.text(), pass, this.name.value.trim());
      this.file.value = '';
      this.close();
      emit('fp:notice', { kind: 'ok', text: `Imported key ${k.name}` });
      this.done?.(k);
    } catch (e) {
      setText(this.error, message(e));
      this.pass.focus();
    } finally {
      this.busy = false;
      this.ok.disabled = false;
    }
  }
}

let exporter: ExportKeyDialog | null = null;
let importer: ImportKeyDialog | null = null;

export function exportKeyDialog(key: KeyInfo): void {
  exporter ??= new ExportKeyDialog();
  exporter.ask(key);
}

export function importKeyDialog(done: (k: KeyInfo) => void): void {
  importer ??= new ImportKeyDialog();
  importer.ask(done);
}
