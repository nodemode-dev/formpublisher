import '../styles/live.css';
import { publishApi, type LiveProblem, type LiveResult, type TargetInfo } from '../api-publish';
import { on } from '../events';
import { fmtDate } from './builds';
import { confirmAction } from './dialogs';
import { el, patchList, q, setAttr, setClass, setDisabled, setText, setValue } from './dom';
import { Dropdown, dropdownHtml, type DropdownOption } from './dropdown';
import { openHosting } from './hosting-sheet';
import { icon } from './icons';

const HOST_LABEL = 'Host';
const ANY_HOST: DropdownOption = { value: '', label: 'Not sure' };
const SHAPE = 'The address must be a domain name or an https address with no path, for example example.com.';
const EMPTY = "Give the site's public address, for example example.com.";
const SEVERITY: Record<LiveProblem['severity'], { label: string; icon: string }> = {
  error: { label: 'Error', icon: 'alert' },
  warning: { label: 'Warning', icon: 'alert' },
  info: { label: 'Info', icon: 'check' },
};

interface Memo { address: string; last: LiveResult | null; host: string | null; loaded: boolean }

type Row = LiveProblem & { key: string };

const message = (e: unknown): string => (e instanceof Error && e.message ? e.message : 'Request failed');

export function liveNames(value: string): [string, string] | null {
  const raw = value.trim().toLowerCase().replace(/^https?:\/\//, '').replace(/\/$/, '').replace(/:443$/, '').replace(/\.$/, '');
  if (!raw || /[\s/@\\?#:]/.test(raw) || !raw.includes('.')) return null;
  const bare = raw.startsWith('www.') && raw.split('.').length > 2 ? raw.slice(4) : raw;
  return [bare, `www.${bare}`];
}

export class LivePane {
  readonly node: HTMLElement;
  private site = '';
  private build = '';
  private prepared: string[] = [];
  private busy = false;
  private seq = 0;
  private readonly memos = new Map<string, Memo>();
  private readonly input: HTMLInputElement;
  private readonly hostSel: Dropdown;
  private readonly runBtn: HTMLButtonElement;
  private readonly status: HTMLElement;
  private readonly time: HTMLElement;
  private readonly empty: HTMLElement;
  private readonly sum: HTMLElement;
  private readonly sumText: HTMLElement;
  private readonly list: HTMLElement;

  constructor() {
    this.node = el(`<section class="fp-pkg-sec fp-live">
<div class="fp-pkg-sec-h">Live site</div>
<div class="fp-live-line"><label class="fp-live-field"><span class="fp-live-k">Address</span><input class="fp-input is-mono" data-f="address" type="text" inputmode="url" spellcheck="false" autocomplete="off" autocapitalize="off" placeholder="example.com" translate="no"></label><div class="fp-live-field"><span class="fp-live-k">Host</span>${dropdownHtml({ cls: 'fp-select fp-live-host', label: HOST_LABEL, data: { f: 'host' }, options: [ANY_HOST] })}</div></div>
<p class="fp-live-note">Reads your public site at the address you give. It uploads nothing and sends nothing else.</p>
<div class="fp-live-acts"><button class="fp-btn fp-btn-sm" type="button" data-a="live">${icon('globe', 14)}<span>Check the live site</span></button><span class="fp-pub-note fp-live-status" data-f="status" role="status"></span><span class="fp-pub-vtime" data-f="time" translate="no"></span></div>
<div class="fp-live-out">
<div class="fp-live-empty" data-f="empty">Not checked yet. Nothing is read until you press the button.</div>
<div class="fp-live-sum" data-f="sum" role="status"><span class="fp-live-sum-icon">${icon('check', 14)}</span><span data-f="sumtext"></span></div>
<ul class="fp-live-list" data-f="list"></ul>
</div>
</section>`);
    const f = (name: string): HTMLElement => q(this.node, `[data-f="${name}"]`);
    this.input = f('address') as HTMLInputElement;
    this.hostSel = new Dropdown(f('host') as HTMLButtonElement, { label: HOST_LABEL, options: [ANY_HOST], change: (v) => { const m = this.memo(); if (m) m.host = v; } });
    this.runBtn = q<HTMLButtonElement>(this.node, '[data-a="live"]');
    this.status = f('status');
    this.time = f('time');
    this.empty = f('empty');
    this.sum = f('sum');
    this.sumText = f('sumtext');
    this.list = f('list');
    this.runBtn.addEventListener('click', () => { void this.run(); });
    this.input.addEventListener('input', () => { const m = this.memo(); if (m) m.address = this.input.value; });
    this.input.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.metaKey && !e.ctrlKey) { e.preventDefault(); void this.run(); } });
    this.list.addEventListener('click', (e) => {
      const row = (e.target as HTMLElement).closest<HTMLElement>('[data-a="guide"]')?.closest<HTMLElement>('.fp-live-row');
      if (!row) return;
      openHosting(row.dataset.guide || undefined, row.dataset.topic || undefined);
    });
    on('fp:live', (ev) => {
      if (ev.type === 'live.checked' && ev.site === this.site && !this.busy) void this.load(true);
    });
    this.paint();
  }

  setTargets(targets: TargetInfo[]): void {
    this.hostSel.setOptions([ANY_HOST, ...targets.map((t) => ({ value: t.id, label: t.name }))]);
    this.paintHost();
  }

  context(site: string, build: string, prepared: string[]): void {
    const changed = site !== this.site;
    this.site = site;
    this.build = build;
    this.prepared = prepared;
    if (changed) {
      this.seq += 1;
      say(this.status, '', '');
    }
    this.paint();
    if (changed && site) void this.load(false);
  }

  private memo(): Memo | null {
    if (!this.site) return null;
    let m = this.memos.get(this.site);
    if (!m) {
      m = { address: '', last: null, host: null, loaded: false };
      this.memos.set(this.site, m);
    }
    return m;
  }

  private async load(force: boolean): Promise<void> {
    const site = this.site;
    const m = this.memo();
    if (!m || (m.loaded && !force)) return;
    const seq = this.seq;
    try {
      const got = await publishApi.liveStored(site);
      if (seq !== this.seq || site !== this.site) return;
      m.loaded = true;
      m.last = got.last;
      if (!m.address) m.address = got.last?.address || got.suggested;
      this.paint();
    } catch (e) {
      if (seq === this.seq && site === this.site) say(this.status, message(e), 'error');
    }
  }

  private paintHost(): void {
    const m = this.memo();
    const known = this.hostSel.options().map((o) => o.value);
    const guess = this.prepared.length === 1 ? this.prepared[0] : '';
    const want = m?.host ?? (m?.last?.target || guess);
    this.hostSel.set(known.includes(want) ? want : '');
  }

  private paint(): void {
    const m = this.memo();
    setValue(this.input, m?.address ?? '');
    setDisabled(this.input, this.busy || !this.site);
    this.hostSel.setDisabled(this.busy || !this.site);
    setDisabled(this.runBtn, this.busy || !this.site);
    setClass(this.node, 'is-busy', this.busy);
    this.paintHost();
    const last = m?.last ?? null;
    setText(this.time, last?.checkedAt ? fmtDate(last.checkedAt) : '');
    setClass(this.empty, 'is-gone', last !== null);
    setClass(this.sum, 'is-shown', last !== null);
    setClass(this.sum, 'is-ok', last?.ok === true);
    setClass(this.sum, 'is-bad', last !== null && !last.ok);
    const text = !last ? '' : last.ok ? `No warnings or errors at ${last.address}.` : `Errors: ${last.errors}. Warnings: ${last.warnings}.`;
    setText(this.sumText, text);
    const rows: Row[] = (last?.problems ?? []).map((p, i) => ({ ...p, key: `${i}:${p.code}:${p.severity}:${p.message}` }));
    patchList(this.list, rows, {
      key: (r) => r.key,
      create: (r) => this.row(r),
      update: () => undefined,
    });
  }

  private row(r: Row): HTMLElement {
    const sev = SEVERITY[r.severity];
    const li = el(`<li class="fp-live-row is-${r.severity}"><span class="fp-live-sev">${icon(sev.icon, 14)}<span class="fp-live-sev-t"><span class="fp-live-sev-l"></span><span class="is-size" aria-hidden="true">Error</span><span class="is-size" aria-hidden="true">Warning</span><span class="is-size" aria-hidden="true">Info</span></span></span><div class="fp-live-body"><div class="fp-live-msg"></div><div class="fp-live-fix"></div></div><button class="fp-btn fp-btn-ghost fp-btn-sm fp-live-guide" type="button" data-a="guide">${icon('book', 14)}<span>Read the guide</span></button></li>`);
    setText(q(li, '.fp-live-sev-l'), sev.label);
    setText(q(li, '.fp-live-msg'), r.message);
    setText(q(li, '.fp-live-fix'), r.fix);
    setClass(q(li, '.fp-live-fix'), 'is-empty', !r.fix);
    setClass(q(li, '.fp-live-guide'), 'is-info', r.severity === 'info');
    li.dataset.guide = r.guide;
    li.dataset.topic = r.guideTopic;
    setAttr(li, 'data-code', r.code);
    return li;
  }

  private async run(): Promise<void> {
    const m = this.memo();
    const site = this.site;
    if (!m || this.busy) return;
    const address = this.input.value.trim();
    const names = liveNames(address);
    if (!names) {
      say(this.status, address ? SHAPE : EMPTY, 'error');
      this.input.focus();
      return;
    }
    const ok = await confirmAction('Check the live site', `This reads ${names[0]} and ${names[1]} over the internet: their home pages, the build's redirects, a few of its files and one address that does not exist. It uploads nothing and sends nothing else.`, 'Check');
    if (!ok || site !== this.site) return;
    this.busy = true;
    say(this.status, 'Checking', '');
    this.paint();
    const host = this.hostSel.selected()?.value ?? '';
    try {
      const made = await publishApi.liveCheck(site, address, this.build || null, host || null);
      const memo = this.memos.get(site);
      if (memo) {
        memo.last = made;
        memo.loaded = true;
        memo.address = made.address;
      }
      if (site === this.site) say(this.status, '', '');
    } catch (e) {
      if (site === this.site) say(this.status, message(e), 'error');
    } finally {
      this.busy = false;
      this.paint();
      const out = this.list.parentElement;
      if (out && site === this.site) out.scrollTop = 0;
    }
  }
}

function say(node: HTMLElement, text: string, tone: '' | 'error'): void {
  setText(node, text);
  setAttr(node, 'title', text);
  setClass(node, 'is-error', tone === 'error');
}
