import '../styles/package.css';
import { buildsApi, type BuildDetail, type CheckSummary, type KeyInfo, type KeySecret } from '../api-builds';
import type { App } from '../app-api';
import { emit, on } from '../events';
import { copyText, fmtBytes, fmtCount, showInLibrary } from './builds';
import { Dialog } from './dialogs';
import { el, q, setAttr, setClass, setDisabled, setHidden, setText } from './dom';
import { Dropdown, dropdownHtml, type DropdownOption } from './dropdown';
import { icon } from './icons';
import { exportKeyDialog, importKeyDialog } from './key-transfer';
import { refuse, refuseStep } from './notice-step';
import { runChecks } from './panel';
import { installPublish } from './publish-sheet';

type Tone = '' | 'ok' | 'warn' | 'error';

const KEPT: Record<KeySecret, string> = { store: 'Password store', file: 'Private file', none: 'Verify only' };

const KEY_LABEL = 'Signing key';

const noKeys = (any: boolean): DropdownOption => ({ value: '', label: any ? 'Choose a key' : 'No keys yet' });

const message = (e: unknown): string => (e instanceof Error && e.message ? e.message : 'Request failed');

function say(node: HTMLElement, text: string, tone: Tone): void {
  setText(node, text);
  setClass(node, 'is-ok', tone === 'ok');
  setClass(node, 'is-warn', tone === 'warn');
  setClass(node, 'is-error', tone === 'error');
}

class PackageSheet extends Dialog {
  private site = '';
  private revision = '';
  private build: BuildDetail | null = null;
  private keys: KeyInfo[] = [];
  private busy = false;
  private seq = 0;
  private readonly f: Record<string, HTMLElement> = {};
  private readonly keySel: Dropdown;
  private readonly pass: HTMLInputElement;
  private readonly newName: HTMLInputElement;
  private readonly newPass: HTMLInputElement;
  private readonly newBox: HTMLElement;
  private readonly checksBtn: HTMLButtonElement;
  private readonly reproBtn: HTMLButtonElement;
  private readonly signBtn: HTMLButtonElement;
  private readonly verifyBtn: HTMLButtonElement;
  private readonly createBtn: HTMLButtonElement;
  private readonly newBtn: HTMLButtonElement;
  private readonly copyBtn: HTMLButtonElement;
  private readonly exportBtn: HTMLButtonElement;
  private readonly importBtn: HTMLButtonElement;
  private readonly buildBtn: HTMLButtonElement;
  private readonly downloadBtn: HTMLButtonElement;
  private readonly libraryBtn: HTMLButtonElement;
  private readonly publishBtn: HTMLButtonElement;
  private readonly bar: HTMLElement;
  private readonly dot: HTMLElement;

  constructor(private readonly app: App) {
    super('Package site', 600, 'fp-pkg-dlg');
    this.body.appendChild(el(`<div class="fp-pkg-wrap"><div class="fp-pkg-info">
<span class="fp-pkg-k">Site</span><span class="fp-pkg-v" data-f="site" translate="no"></span>
<span class="fp-pkg-k">Revision</span><span class="fp-pkg-v is-mono" data-f="revision" translate="no"></span>
</div>
<section class="fp-pkg-sec">
<div class="fp-pkg-sec-h">Checks</div>
<div class="fp-pkg-line"><span class="fp-st-dot" data-f="dot"></span><span class="fp-pkg-grow" data-f="checks"></span><button class="fp-btn fp-btn-sm" type="button" data-a="checks">Run checks</button></div>
</section>
<section class="fp-pkg-sec">
<div class="fp-pkg-sec-h">Build</div>
<div class="fp-pkg-progress" aria-hidden="true"><i></i></div>
<div class="fp-pkg-info">
<span class="fp-pkg-k">Build id</span><span class="fp-pkg-v is-mono" data-f="id" translate="no"></span>
<span class="fp-pkg-k">SHA-256</span><span class="fp-pkg-v is-mono fp-pkg-sha"><span data-f="sha" translate="no"></span><button class="fp-icon-btn is-sm" type="button" data-a="copy" title="Copy SHA-256" aria-label="Copy SHA-256">${icon('copy', 14)}</button></span>
<span class="fp-pkg-k">Size</span><span class="fp-pkg-v" data-f="size" translate="no"></span>
<span class="fp-pkg-k">Files</span><span class="fp-pkg-v" data-f="files" translate="no"></span>
</div>
<div class="fp-pkg-line"><button class="fp-btn fp-btn-sm" type="button" data-a="repro">${icon('reload', 14)}<span>Reproduce</span></button><span class="fp-pkg-grow fp-pkg-res" data-f="repro" role="status"></span></div>
</section>
<section class="fp-pkg-sec">
<div class="fp-pkg-sec-h">Signature</div>
<div class="fp-pkg-line">${dropdownHtml({ cls: 'fp-select fp-pkg-grow', label: KEY_LABEL, data: { f: 'key' }, options: [noKeys(false)] })}<input class="fp-input fp-pkg-pass" type="password" data-f="pass" placeholder="Passphrase" aria-label="Passphrase" autocomplete="off"><button class="fp-btn fp-btn-sm" type="button" data-a="sign">${icon('key', 14)}<span>Sign</span></button></div>
<div class="fp-pkg-line"><button class="fp-btn fp-btn-ghost fp-btn-sm" type="button" data-a="newkey">${icon('plus', 14)}<span>New key</span></button><button class="fp-btn fp-btn-ghost fp-btn-sm" type="button" data-a="exportkey">Export...</button><button class="fp-btn fp-btn-ghost fp-btn-sm" type="button" data-a="importkey">Import...</button><span class="fp-pkg-grow fp-pkg-res" data-f="sign" role="status"></span></div>
<div class="fp-pkg-line fp-pkg-newkey" hidden><input class="fp-input fp-pkg-grow" data-f="newname" placeholder="Key name" aria-label="Key name" autocomplete="off"><input class="fp-input fp-pkg-pass" type="password" data-f="newpass" placeholder="Passphrase (optional)" aria-label="New key passphrase" autocomplete="new-password"><button class="fp-btn fp-btn-sm" type="button" data-a="create">Create key</button></div>
<div class="fp-pkg-line"><button class="fp-btn fp-btn-sm" type="button" data-a="verify">${icon('shield', 14)}<span>Verify</span></button><span class="fp-pkg-grow fp-pkg-res is-verify" data-f="verify" role="status"></span></div>
</section></div>`));
    for (const n of Array.from(this.body.querySelectorAll<HTMLElement>('[data-f]'))) this.f[n.dataset.f ?? ''] = n;
    this.keySel = new Dropdown(this.f.key as HTMLButtonElement, { label: KEY_LABEL, options: [noKeys(false)], change: () => this.sync() });
    this.pass = this.f.pass as HTMLInputElement;
    this.newName = this.f.newname as HTMLInputElement;
    this.newPass = this.f.newpass as HTMLInputElement;
    this.newBox = q(this.body, '.fp-pkg-newkey');
    this.bar = q(this.body, '.fp-pkg-progress');
    this.dot = this.f.dot;
    const btn = (a: string): HTMLButtonElement => q<HTMLButtonElement>(this.body, `[data-a="${a}"]`);
    this.checksBtn = btn('checks');
    this.reproBtn = btn('repro');
    this.signBtn = btn('sign');
    this.verifyBtn = btn('verify');
    this.createBtn = btn('create');
    this.newBtn = btn('newkey');
    this.copyBtn = btn('copy');
    this.exportBtn = btn('exportkey');
    this.importBtn = btn('importkey');
    this.button('Close', 'ghost', () => this.close());
    this.libraryBtn = this.button('Show in library', 'ghost', () => this.toLibrary());
    this.downloadBtn = this.button('Download', 'ghost', () => this.download());
    this.publishBtn = this.button('Publish', 'ghost', () => this.toPublish());
    this.buildBtn = this.button('Build', 'primary', () => { void this.runBuild(); });
    this.wire();
    this.sync();
  }

  async show(): Promise<void> {
    const id = this.app.state().activeId;
    if (!id) {
      emit('fp:notice', { kind: 'info', text: 'Open a site first' });
      return;
    }
    const name = this.app.state().site?.name ?? this.app.state().open.find((t) => t.id === id)?.name ?? id;
    if (id !== this.site) {
      this.site = id;
      this.revision = '';
      this.build = null;
      this.resetResult();
      this.paintChecks(null, true);
    }
    setText(this.f.site, name);
    setText(this.f.revision, this.revision || '-');
    this.sync();
    this.open(this.buildBtn);
    const seq = ++this.seq;
    try {
      const rev = await buildsApi.siteRevision(id);
      if (seq !== this.seq) return;
      if (rev !== this.revision) {
        this.revision = rev;
        this.build = null;
        this.resetResult();
      }
      setText(this.f.revision, rev || '-');
    } catch (e) {
      if (seq === this.seq) emit('fp:notice', { kind: 'error', text: message(e) });
    }
    await Promise.all([this.loadChecks(), this.loadKeys()]);
  }

  refreshFor(site: string): void {
    if (this.isOpen && site === this.site) void this.loadChecks();
  }

  siteClosed(site: string): void {
    if (site === this.site) {
      this.close();
      this.site = '';
      this.build = null;
      this.resetResult();
    }
  }

  private async loadChecks(): Promise<void> {
    if (!this.site || !this.revision) return;
    const site = this.site;
    try {
      const s = await buildsApi.checkSummary(site, this.revision);
      if (site === this.site) this.paintChecks(s, false);
    } catch {
      if (site === this.site) this.paintChecks(null, false);
    }
  }

  private async loadKeys(): Promise<void> {
    try {
      this.keys = await buildsApi.keys();
    } catch {
      this.keys = [];
    }
    this.paintKeys(this.keySel.value);
  }

  private paintChecks(s: CheckSummary | null, pending: boolean): void {
    const none = !s || !s.ran;
    const text = pending ? '' : none ? 'Checks have not run for this revision' : `${fmtCount(s.errors, 'error', 'errors')}, ${fmtCount(s.warnings, 'warning', 'warnings')}, ${fmtCount(s.infos, 'note', 'notes')}`;
    setText(this.f.checks, text);
    setClass(this.dot, 'is-error', !none && s.errors > 0);
    setClass(this.dot, 'is-warn', !none && s.errors === 0 && s.warnings > 0);
    setClass(this.dot, 'is-ok', !none && s.errors === 0 && s.warnings === 0);
  }

  private paintKeys(keep: string): void {
    const items: DropdownOption[] = [noKeys(this.keys.length > 0), ...this.keys.map((k) => ({ value: k.id, label: `${k.name}  ${k.fingerprint.slice(0, 22)}`, detail: KEPT[k.secret], disabled: !k.canSign, literal: true }))];
    this.keySel.setOptions(items, items.some((k) => k.value === keep) ? keep : undefined);
    this.sync();
  }

  private resetResult(): void {
    setText(this.f.id, '-');
    setText(this.f.sha, '-');
    setText(this.f.size, '-');
    setText(this.f.files, '-');
    say(this.f.repro, '', '');
    say(this.f.sign, '', '');
    say(this.f.verify, '', '');
    this.sync();
  }

  private paintResult(b: BuildDetail): void {
    setText(this.f.id, b.id);
    setText(this.f.sha, b.sha256 || '-');
    setText(this.f.size, `${fmtBytes(b.size)} (${b.size} bytes)`);
    setText(this.f.files, String(b.files));
    this.sync();
  }

  private sync(): void {
    const has = this.build !== null;
    const key = this.keys.find((k) => k.id === this.keySel.value);
    setDisabled(this.buildBtn, this.busy || !this.site || !this.revision);
    setDisabled(this.checksBtn, this.busy || !this.site);
    setDisabled(this.reproBtn, this.busy || !has);
    setDisabled(this.signBtn, this.busy || !has || !key || !key.canSign);
    setDisabled(this.verifyBtn, this.busy || !has || !this.build?.signed);
    setDisabled(this.copyBtn, !has);
    setDisabled(this.downloadBtn, this.busy || !has);
    setDisabled(this.libraryBtn, !has);
    setDisabled(this.publishBtn, this.busy || !has);
    setDisabled(this.newBtn, this.busy);
    setDisabled(this.exportBtn, this.busy || !key || !key.canSign);
    setDisabled(this.importBtn, this.busy);
    setDisabled(this.createBtn, this.busy);
    setDisabled(this.pass, this.busy || !key || !key.encrypted);
    setAttr(this.pass, 'placeholder', key && !key.encrypted ? 'No passphrase' : 'Passphrase');
    setClass(this.bar, 'is-running', this.busy && this.running === 'build');
  }

  private running: '' | 'build' | 'other' = '';

  private async guard(kind: 'build' | 'other', fn: () => Promise<void>): Promise<void> {
    if (this.busy) return;
    this.busy = true;
    this.running = kind;
    this.sync();
    try {
      await fn();
    } finally {
      this.busy = false;
      this.running = '';
      this.sync();
    }
  }

  private async runBuild(): Promise<void> {
    await this.guard('build', async () => {
      say(this.f.repro, '', '');
      say(this.f.sign, '', '');
      say(this.f.verify, '', '');
      try {
        const made = await buildsApi.build(this.site, this.revision || undefined);
        this.build = await buildsApi.detail(made.id);
        this.paintResult(this.build);
        emit('fp:notice', { kind: 'ok', text: `Built ${made.id}` });
      } catch (e) {
        this.build = null;
        this.resetResult();
        refuse(e, message(e), this.site);
      }
    });
  }

  private async runReproduce(): Promise<void> {
    const b = this.build;
    if (!b) return;
    await this.guard('other', async () => {
      say(this.f.repro, 'Rebuilding', '');
      try {
        const r = await buildsApi.reproduce(b.id);
        if (r.same) say(this.f.repro, 'Reproduced. The rebuild has the same bytes.', 'ok');
        else say(this.f.repro, `Not reproduced. Expected ${r.expected.slice(0, 12)}, got ${r.sha256.slice(0, 12)}.`, 'error');
      } catch (e) {
        say(this.f.repro, message(e), 'error');
        refuseStep(e, b.id, () => { void this.runReproduce(); });
      }
    });
  }

  private async runSign(): Promise<void> {
    const b = this.build;
    const key = this.keys.find((k) => k.id === this.keySel.value);
    if (!b || !key) return;
    await this.guard('other', async () => {
      say(this.f.sign, 'Signing', '');
      try {
        await buildsApi.sign(b.id, key.id, this.pass.value);
        this.pass.value = '';
        this.build = await buildsApi.detail(b.id);
        say(this.f.sign, `Signed with ${key.name}.`, 'ok');
        say(this.f.verify, '', '');
      } catch (e) {
        this.pass.value = '';
        say(this.f.sign, message(e), 'error');
        refuseStep(e, b.id, () => this.pass.focus());
      }
    });
  }

  private async runVerify(): Promise<void> {
    const b = this.build;
    if (!b) return;
    await this.guard('other', async () => {
      say(this.f.verify, 'Verifying', '');
      try {
        const r = await buildsApi.verify(b.id);
        if (r.valid && r.known) say(this.f.verify, `Verified with your key ${r.signerName || r.key}.`, 'ok');
        else if (r.valid) say(this.f.verify, `Signed by a key you do not have. ${r.key}`, 'warn');
        else say(this.f.verify, `Invalid. ${r.reason || r.message || 'The signature does not match.'}`, 'error');
      } catch (e) {
        say(this.f.verify, message(e), 'error');
        refuseStep(e, b.id, () => { void this.runVerify(); });
      }
    });
  }

  private async runCreateKey(): Promise<void> {
    const name = this.newName.value.trim();
    if (!name) {
      say(this.f.sign, 'Give the key a name.', 'error');
      this.newName.focus();
      return;
    }
    await this.guard('other', async () => {
      try {
        const k = await buildsApi.createKey(name, this.newPass.value);
        this.newName.value = '';
        this.newPass.value = '';
        setHidden(this.newBox, true);
        this.keys = await buildsApi.keys();
        this.paintKeys(k.id);
        say(this.f.sign, `Created key ${k.name}.`, 'ok');
      } catch (e) {
        say(this.f.sign, message(e), 'error');
      }
    });
  }

  private async afterImport(id: string): Promise<void> {
    try {
      this.keys = await buildsApi.keys();
    } catch {
      return;
    }
    this.paintKeys(id);
  }

  private async runChecksNow(): Promise<void> {
    await this.guard('other', async () => {
      try {
        await runChecks(this.app, false);
      } catch (e) {
        refuse(e, message(e), this.site);
      }
      await this.loadChecks();
    });
  }

  private download(): void {
    if (!this.build) return;
    const a = document.createElement('a');
    a.href = buildsApi.downloadUrl(this.build.id);
    a.download = 'site.zip';
    a.rel = 'noopener';
    document.body.appendChild(a);
    a.click();
    a.remove();
  }

  private toPublish(): void {
    const id = this.build?.id;
    if (!id) return;
    this.close();
    emit('fp:publish', { source: 'package', build: id });
  }

  private toLibrary(): void {
    const id = this.build?.id;
    if (!id) return;
    this.close();
    showInLibrary(id);
  }

  private wire(): void {
    this.body.addEventListener('click', (e) => {
      const a = (e.target as HTMLElement).closest<HTMLElement>('[data-a]')?.dataset.a;
      if (!a) return;
      if (a === 'checks') void this.runChecksNow();
      else if (a === 'repro') void this.runReproduce();
      else if (a === 'sign') void this.runSign();
      else if (a === 'verify') void this.runVerify();
      else if (a === 'create') void this.runCreateKey();
      else if (a === 'copy' && this.build) void copyText(this.build.sha256);
      else if (a === 'exportkey') {
        const key = this.keys.find((k) => k.id === this.keySel.value);
        if (key?.canSign) exportKeyDialog(key);
      } else if (a === 'importkey') importKeyDialog((k) => { void this.afterImport(k.id); });
      else if (a === 'newkey') {
        setHidden(this.newBox, !this.newBox.hidden);
        if (!this.newBox.hidden) this.newName.focus();
      }
    });
    this.newName.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); void this.runCreateKey(); } });
    this.newPass.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); void this.runCreateKey(); } });
    this.pass.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); void this.runSign(); } });
  }
}

let sheet: PackageSheet | null = null;

export function installPackaging(app: App): void {
  sheet ??= new PackageSheet(app);
  installPublish(app);
  on('fp:live', (ev) => {
    if (ev.type === 'checks.done' && typeof ev.site === 'string') sheet?.refreshFor(ev.site);
  });
  on('fp:checks', (d) => sheet?.refreshFor(d.siteId));
  on('fp:site-closed', (d) => sheet?.siteClosed(d.id));
}

export function openPackageSheet(app: App): void {
  sheet ??= new PackageSheet(app);
  void sheet.show();
}
