import '../styles/package.css';
import '../styles/publish.css';
import { buildsApi, type BuildSummary } from '../api-builds';
import { publishApi, type NginxCheck, type PreparedCommand, type PreparedTarget, type TargetInfo } from '../api-publish';
import type { App } from '../app-api';
import { emit, on } from '../events';
import { t } from '../i18n';
import { copyText, fmtCount, fmtDate } from './builds';
import { confirmAction, Dialog } from './dialogs';
import { el, patchList, q, setAttr, setClass, setDisabled, setHidden, setText } from './dom';
import { icon } from './icons';
import { refuseStep } from './notice-step';
import { toast } from './toast';

type Tone = '' | 'ok' | 'error';

interface Verdict { text: string; tone: Tone; problems: string[]; nginx?: { text: string; tone: Tone }; at?: string }

function verdictOf(ok: boolean, problems: string[], nginx: NginxCheck | null, at: string): Verdict {
  return ok ? { text: 'Verified. Every file matches.', tone: 'ok', problems: [], nginx: nginxLine(nginx), at } : { text: 'Verification failed.', tone: 'error', problems, nginx: nginxLine(nginx), at };
}

function nginxLine(n: NginxCheck | null): { text: string; tone: Tone } | undefined {
  if (!n) return undefined;
  if (!n.ran) return { text: 'nginx is not installed here, so nginx -t did not run.', tone: '' };
  if (n.ok) return { text: n.version ? `nginx -t passed with nginx ${n.version}.` : 'nginx -t passed.', tone: 'ok' };
  const first = n.output.split('\n').find((l) => l.includes('[emerg]') || l.includes('[alert]')) ?? n.output.split('\n')[0] ?? '';
  return { text: `nginx -t failed: ${first.replace(/^nginx:\s*/, '')}`, tone: 'error' };
}

interface Memo {
  picked: Set<string>;
  includeModel: boolean;
  results: Map<string, PreparedTarget>;
  verdicts: Map<string, Verdict>;
}

const PICKS_KEY = 'formpublisher.publish.picks';
const MODEL_KEY = 'formpublisher.publish.model';
const SKELETONS = 6;

function readModel(): boolean {
  try { return localStorage.getItem(MODEL_KEY) === '1'; } catch { return false; }
}

function writeModel(on: boolean): void {
  try { localStorage.setItem(MODEL_KEY, on ? '1' : '0'); } catch { return; }
}

const message = (e: unknown): string => (e instanceof Error && e.message ? e.message : 'Request failed');

function say(node: HTMLElement, text: string, tone: Tone): void {
  setText(node, text);
  setAttr(node, 'title', text);
  setClass(node, 'is-ok', tone === 'ok');
  setClass(node, 'is-error', tone === 'error');
}

function readPicks(): string[] {
  try {
    const raw = JSON.parse(localStorage.getItem(PICKS_KEY) || '[]') as unknown;
    return Array.isArray(raw) ? raw.filter((v): v is string => typeof v === 'string') : [];
  } catch {
    return [];
  }
}

function writePicks(ids: string[]): void {
  try { localStorage.setItem(PICKS_KEY, JSON.stringify(ids)); } catch { return; }
}

const skeletonCard = (): string => `<div class="fp-pub-target is-skeleton" aria-hidden="true"><span></span><span class="fp-pub-tname">&nbsp;</span><span class="fp-pub-tdesc">&nbsp;</span></div>`;

const field = (node: Element, name: string): HTMLElement => q(node, `[data-f="${name}"]`);

class PublishSheet extends Dialog {
  private site = '';
  private builds: BuildSummary[] = [];
  private buildId = '';
  private targets: TargetInfo[] = [];
  private targetsLoaded = false;
  private busy = false;
  private seq = 0;
  private readonly memos = new Map<string, Memo>();
  private readonly f: Record<string, HTMLElement> = {};
  private readonly buildSel: HTMLSelectElement;
  private readonly buildNowBtn: HTMLButtonElement;
  private readonly allBtn: HTMLButtonElement;
  private readonly tlist: HTMLElement;
  private readonly skeleton: HTMLElement;
  private readonly rlist: HTMLElement;
  private readonly none: HTMLElement;
  private readonly bar: HTMLElement;
  private readonly closeBtn: HTMLButtonElement;
  private readonly prepareBtn: HTMLButtonElement;

  constructor(private readonly app: App) {
    super('Publish site', 680, 'fp-pub-dlg');
    this.body.appendChild(el(`<div class="fp-pub-wrap">
<section class="fp-pkg-sec">
<div class="fp-pkg-sec-h">Build</div>
<div class="fp-pkg-info"><span class="fp-pkg-k">Site</span><span class="fp-pkg-v" data-f="site" translate="no"></span></div>
<div class="fp-pkg-line"><select class="fp-select fp-pkg-grow fp-pub-build-sel" data-f="build" aria-label="Build"></select><button class="fp-btn fp-btn-sm" type="button" data-a="build">${icon('package', 14)}<span>Build now</span></button></div>
<div class="fp-pub-note" data-f="buildnote" role="status"></div>
</section>
<section class="fp-pkg-sec">
<div class="fp-pub-sec-head"><div class="fp-pkg-sec-h">Hosts</div><button class="fp-btn fp-btn-ghost fp-btn-sm" type="button" data-a="all">Select all</button></div>
<div class="fp-pub-targets" role="group" aria-label="Hosts">${Array.from({ length: SKELETONS }, skeletonCard).join('')}<div class="fp-pub-tlist" hidden></div></div>
<label class="fp-pub-model"><input type="checkbox" data-f="model"><span class="fp-pub-model-name">Keep FormWeb's model files</span><span class="fp-pub-model-desc">Hosts do not need them, so site.formweb.json and asset-access.json are left out unless you tick this.</span></label>
<div class="fp-pkg-progress" aria-hidden="true"><i></i></div>
<div class="fp-pub-note" data-f="prep" role="status"></div>
</section>
<section class="fp-pkg-sec">
<div class="fp-pkg-sec-h">Prepared folders</div>
<div class="fp-pub-results">
<div class="fp-pub-none">Nothing is prepared for this build yet. Tick the hosts you want and press Prepare. FormPublisher writes a folder and shows the commands to run. It never uploads anything.</div>
<div class="fp-pub-res-list"></div>
</div>
</section></div>`));
    for (const n of Array.from(this.body.querySelectorAll<HTMLElement>('[data-f]'))) this.f[n.dataset.f ?? ''] = n;
    this.buildSel = this.f.build as HTMLSelectElement;
    this.buildNowBtn = q<HTMLButtonElement>(this.body, '[data-a="build"]');
    this.allBtn = q<HTMLButtonElement>(this.body, '[data-a="all"]');
    this.tlist = q(this.body, '.fp-pub-tlist');
    this.skeleton = q(this.body, '.fp-pub-targets');
    this.rlist = q(this.body, '.fp-pub-res-list');
    this.none = q(this.body, '.fp-pub-none');
    this.bar = q(this.body, '.fp-pkg-progress');
    this.closeBtn = this.button('Close', 'ghost', () => this.close());
    this.prepareBtn = this.button('Prepare', 'primary', () => { void this.runPrepare(); });
    this.wire();
    this.sync();
  }

  async show(build?: string): Promise<void> {
    const id = this.app.state().activeId;
    if (!id) {
      emit('fp:notice', { kind: 'info', text: 'Open a site first' });
      return;
    }
    const name = this.app.state().site?.name ?? this.app.state().open.find((t) => t.id === id)?.name ?? id;
    if (id !== this.site) {
      this.site = id;
      this.builds = [];
      this.buildId = '';
      this.paintBuilds();
      this.paintAll();
    }
    setText(this.f.site, name);
    this.sync();
    this.open(this.prepareBtn.disabled ? this.closeBtn : this.prepareBtn);
    const seq = ++this.seq;
    await Promise.all([this.loadTargets(), this.loadBuilds(build, seq)]);
  }

  siteClosed(site: string): void {
    if (site !== this.site) return;
    this.close();
    this.site = '';
    this.builds = [];
    this.buildId = '';
    this.paintBuilds();
    this.paintAll();
  }

  private memo(): Memo | null {
    if (!this.buildId) return null;
    let m = this.memos.get(this.buildId);
    if (!m) {
      m = { picked: new Set(readPicks()), includeModel: readModel(), results: new Map(), verdicts: new Map() };
      this.memos.set(this.buildId, m);
    }
    return m;
  }

  private async loadTargets(): Promise<void> {
    if (this.targetsLoaded) return;
    try {
      this.targets = await publishApi.targets();
      this.targetsLoaded = true;
    } catch (e) {
      this.targets = [];
      say(this.f.prep, message(e), 'error');
    }
    this.paintTargets();
    this.paintResults();
    this.sync();
  }

  private async loadBuilds(want: string | undefined, seq: number): Promise<void> {
    const site = this.site;
    let rows: BuildSummary[] = [];
    try {
      rows = (await buildsApi.list()).filter((b) => b.site === site);
    } catch (e) {
      if (seq === this.seq) say(this.f.buildnote, message(e), 'error');
    }
    if (seq !== this.seq || site !== this.site) return;
    rows.sort((a, b) => (Date.parse(b.created) || 0) - (Date.parse(a.created) || 0));
    this.builds = rows;
    const keep = want && rows.some((b) => b.id === want) ? want : rows.some((b) => b.id === this.buildId) ? this.buildId : (rows[0]?.id ?? '');
    this.buildId = keep;
    this.paintBuilds();
    this.paintAll();
    this.sync();
    if (keep) await this.loadPrepared(keep);
  }

  private async loadPrepared(build: string): Promise<void> {
    try {
      const rows = await publishApi.prepared(build);
      if (build !== this.buildId) return;
      const m = this.memo();
      if (!m) return;
      m.results = new Map(rows.map((r) => [r.target, r]));
      for (const id of Array.from(m.verdicts.keys())) if (!m.results.has(id)) m.verdicts.delete(id);
      if (!this.busy) {
        for (const r of rows) {
          if (r.verified) m.verdicts.set(r.target, verdictOf(r.verified.ok, r.verified.problems, r.verified.nginx, r.verified.at));
          else m.verdicts.delete(r.target);
        }
      }
      this.paintResults();
    } catch (e) {
      if (build === this.buildId) say(this.f.prep, message(e), 'error');
    }
  }

  private paintBuilds(): void {
    const items = this.builds.length ? this.builds.map((b) => ({ id: b.id, label: `${b.id}   ${fmtDate(b.created)}` })) : [{ id: '', label: t('No builds yet') }];
    patchList(this.buildSel, items, {
      key: (b) => b.id || '-',
      create: (b) => {
        const o = el<HTMLOptionElement>('<option></option>');
        o.value = b.id;
        if (b.id) o.translate = false;
        o.textContent = b.label;
        return o;
      },
      update: (n, b) => setText(n, b.label),
    });
    if (this.buildSel.value !== this.buildId) this.buildSel.value = this.buildId;
    say(this.f.buildnote, this.builds.length || !this.site ? '' : 'This site has no build yet. Build it first, then prepare it for a host.', '');
  }

  private paintTargets(): void {
    setHidden(this.tlist, !this.targetsLoaded);
    for (const n of Array.from(this.skeleton.querySelectorAll<HTMLElement>('.is-skeleton'))) setHidden(n, this.targetsLoaded);
    const m = this.memo();
    patchList(this.tlist, this.targets, {
      key: (t) => t.id,
      create: (tg) => {
        const node = el(`<label class="fp-pub-target"><input type="checkbox" data-pick><span class="fp-pub-tname" translate="no"></span><span class="fp-pub-tdesc"></span></label>`);
        setText(q(node, '.fp-pub-tname'), t(tg.name));
        setText(q(node, '.fp-pub-tdesc'), tg.description);
        setAttr(q(node, '[data-pick]'), 'aria-label', t(tg.name));
        return node;
      },
      update: (node, tg) => {
        const box = q<HTMLInputElement>(node, '[data-pick]');
        const on = m?.picked.has(tg.id) ?? false;
        if (box.checked !== on) box.checked = on;
        setClass(node, 'is-picked', on);
        setText(q(node, '.fp-pub-tname'), t(tg.name));
        setText(q(node, '.fp-pub-tdesc'), tg.description);
        setAttr(node, 'title', tg.localTool);
      },
    });
    const all = this.targets.length > 0 && this.targets.every((t) => m?.picked.has(t.id));
    setText(this.allBtn, all ? 'Select none' : 'Select all');
    const model = this.f.model as HTMLInputElement;
    const keep = m?.includeModel ?? false;
    if (model.checked !== keep) model.checked = keep;
  }

  private paintResults(): void {
    const m = this.memo();
    const rows = this.targets.map((t) => m?.results.get(t.id)).filter((r): r is PreparedTarget => r !== undefined);
    for (const r of m?.results.values() ?? []) if (!rows.includes(r)) rows.push(r);
    setHidden(this.none, rows.length > 0);
    patchList(this.rlist, rows, {
      key: (r) => r.target,
      create: (r) => this.resultNode(r),
      update: (node, r) => this.fillResult(node, r),
    });
  }

  private paintAll(): void {
    this.paintTargets();
    this.paintResults();
  }

  private nameOf(id: string): string {
    const name = this.targets.find((x) => x.id === id)?.name;
    return name ? t(name) : id;
  }

  private resultNode(r: PreparedTarget): HTMLElement {
    const node = el(`<article class="fp-pub-res">
<div class="fp-pub-res-h"><span class="fp-pub-res-name" data-f="name" translate="no"></span><span class="fp-badge" data-f="count"></span><span class="fp-pkg-grow"></span><button class="fp-btn fp-btn-sm" type="button" data-a="verify">${icon('shield', 14)}<span>Verify</span></button><button class="fp-btn fp-btn-ghost fp-btn-sm" type="button" data-a="remove">${icon('trash', 14)}<span>Remove</span></button></div>
<div class="fp-pub-note fp-pub-left" data-f="left"></div>
<div class="fp-pub-sub">Folder</div>
<div class="fp-pub-path"><div class="fp-pub-code" data-f="folder" translate="no"></div><button class="fp-btn fp-btn-sm" type="button" data-a="reveal">${icon('folder', 14)}<span>Reveal</span></button><button class="fp-btn fp-btn-sm" type="button" data-a="path">${icon('copy', 14)}<span>Copy path</span></button></div>
<div class="fp-pub-sub" data-f="cmdh">Commands</div>
<ul class="fp-pub-list" data-f="cmds"></ul>
<div class="fp-pub-sub" data-f="noteh">Notes</div>
<ul class="fp-pub-list" data-f="notes"></ul>
<div class="fp-pub-sub" data-f="warnh">Warnings</div>
<ul class="fp-pub-list" data-f="warns"></ul>
<div class="fp-pub-vrow"><div class="fp-pkg-res" data-f="verdict" role="status"></div><span class="fp-pub-vtime" data-f="vtime" translate="no"></span></div>
<div class="fp-pkg-res fp-pub-nginx" data-f="nginx" role="status"></div>
<ul class="fp-pub-list" data-f="probs"></ul>
</article>`);
    this.fillResult(node, r);
    return node;
  }

  private fillResult(node: HTMLElement, r: PreparedTarget): void {
    setText(field(node, 'name'), this.nameOf(r.target));
    setText(field(node, 'count'), fmtCount(r.files.length, 'file', 'files'));
    setText(field(node, 'folder'), r.folder);
    setAttr(node, 'aria-label', this.nameOf(r.target));
    setText(field(node, 'left'), r.leftOut.length ? `Left out: ${r.leftOut.join(', ')}` : '');
    setHidden(field(node, 'left'), r.leftOut.length === 0);
    const list = (name: string, head: string, items: string[], cls: string): void => {
      const box = field(node, name);
      setHidden(field(node, head), items.length === 0);
      setHidden(box, items.length === 0);
      patchList(box, items.map((text, i) => ({ text, i })), {
        key: (it) => `${it.i}:${it.text}`,
        create: (it) => {
          const li = el(`<li class="fp-pub-line${cls}"></li>`);
          li.textContent = it.text;
          return li;
        },
        update: () => undefined,
      });
    };
    list('notes', 'noteh', r.notes, '');
    list('warns', 'warnh', r.warnings, ' is-warn');
    const cmds = field(node, 'cmds');
    setHidden(field(node, 'cmdh'), r.commands.length === 0);
    setHidden(cmds, r.commands.length === 0);
    patchList(cmds, r.commands.map((c, i) => ({ c, i })), {
      key: (it) => `${it.i}:${it.c.run}`,
      create: (it) => this.commandNode(it.c),
      update: () => undefined,
    });
    const v = this.memo()?.verdicts.get(r.target);
    say(field(node, 'verdict'), v?.text ?? '', v?.tone ?? '');
    setText(field(node, 'vtime'), v?.at ? fmtDate(v.at) : '');
    setHidden(field(node, 'nginx'), r.target !== 'nginx');
    say(field(node, 'nginx'), v?.nginx?.text ?? '', v?.nginx?.tone ?? '');
    const probs = field(node, 'probs');
    setHidden(probs, !v || v.problems.length === 0);
    patchList(probs, (v?.problems ?? []).map((text, i) => ({ text, i })), {
      key: (it) => `${it.i}:${it.text}`,
      create: (it) => {
        const li = el('<li class="fp-pub-line is-bad"></li>');
        li.textContent = it.text;
        return li;
      },
      update: () => undefined,
    });
    for (const b of Array.from(node.querySelectorAll<HTMLButtonElement>('button[data-a]'))) setDisabled(b, this.busy);
  }

  private commandNode(c: PreparedCommand): HTMLElement {
    const li = el(`<li class="fp-pub-cmd"><span class="fp-pub-cmd-label" data-f="label"></span><div class="fp-pub-code" data-f="run" translate="no"></div><button class="fp-icon-btn is-sm" type="button" data-a="copycmd" title="Copy command" aria-label="Copy command">${icon('copy', 14)}</button></li>`);
    setText(field(li, 'label'), c.label);
    if (c.cwd) li.title = c.cwd;
    setText(field(li, 'run'), c.run);
    li.dataset.run = c.run;
    return li;
  }

  private sync(): void {
    const m = this.memo();
    const any = m !== null && this.targets.some((t) => m.picked.has(t.id));
    setDisabled(this.prepareBtn, this.busy || !this.buildId || !any);
    setDisabled(this.buildNowBtn, this.busy || !this.site);
    setDisabled(this.allBtn, this.busy || !this.buildId || !this.targets.length);
    this.buildSel.disabled = this.busy || !this.builds.length;
    for (const b of Array.from(this.rlist.querySelectorAll<HTMLButtonElement>('button[data-a]'))) setDisabled(b, this.busy);
    for (const box of Array.from(this.tlist.querySelectorAll<HTMLInputElement>('[data-pick]'))) setDisabled(box, this.busy || !this.buildId);
    setDisabled(this.f.model as HTMLInputElement, this.busy || !this.buildId);
    setClass(this.bar, 'is-running', this.busy);
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

  private async runBuild(): Promise<void> {
    if (!this.site) return;
    await this.guard(async () => {
      say(this.f.buildnote, 'Building', '');
      try {
        const made = await buildsApi.build(this.site);
        const rows = (await buildsApi.list()).filter((b) => b.site === this.site);
        rows.sort((a, b) => (Date.parse(b.created) || 0) - (Date.parse(a.created) || 0));
        this.builds = rows;
        this.buildId = made.id;
        this.paintBuilds();
        this.paintAll();
        emit('fp:notice', { kind: 'ok', text: `Built ${made.id}` });
        await this.loadPrepared(made.id);
      } catch (e) {
        say(this.f.buildnote, message(e), 'error');
        refuseStep(e, this.site);
      }
    });
  }

  private async runPrepare(): Promise<void> {
    const m = this.memo();
    const build = this.buildId;
    if (!m || !build) return;
    const ids = this.targets.filter((t) => m.picked.has(t.id)).map((t) => t.id);
    if (!ids.length) {
      say(this.f.prep, 'Tick at least one host first.', 'error');
      return;
    }
    await this.guard(async () => {
      say(this.f.prep, 'Preparing', '');
      try {
        const rows = await publishApi.prepare(build, ids, m.includeModel);
        const memo = this.memos.get(build);
        if (!memo) return;
        for (const r of rows) {
          memo.results.set(r.target, r);
          memo.verdicts.delete(r.target);
        }
        if (build === this.buildId) this.paintResults();
        const names = rows.map((r) => this.nameOf(r.target)).join(', ');
        say(this.f.prep, `Prepared ${names}`, 'ok');
      } catch (e) {
        say(this.f.prep, message(e), 'error');
        refuseStep(e, build, () => { void this.runPrepare(); });
      }
    });
  }

  private async runVerify(target: string): Promise<void> {
    const build = this.buildId;
    const memo = this.memos.get(build);
    if (!memo) return;
    await this.guard(async () => {
      memo.verdicts.set(target, { text: 'Verifying', tone: '', problems: [] });
      this.paintResults();
      try {
        const r = await publishApi.verify(build, target);
        memo.verdicts.set(target, verdictOf(r.ok, r.problems, r.nginx, r.at));
      } catch (e) {
        memo.verdicts.set(target, { text: message(e), tone: 'error', problems: [] });
      }
      if (build === this.buildId) this.paintResults();
    });
  }

  private async runRemove(target: string): Promise<void> {
    const build = this.buildId;
    const memo = this.memos.get(build);
    if (!memo) return;
    const name = this.nameOf(target);
    const ok = await confirmAction('Remove prepared folder', `Move the prepared ${name} folder to the trash? You can prepare it again at any time.`, 'Remove', true);
    if (!ok) return;
    await this.guard(async () => {
      try {
        await publishApi.remove(build, target);
        memo.results.delete(target);
        memo.verdicts.delete(target);
        if (build === this.buildId) this.paintResults();
        if (!this.scrim.contains(document.activeElement) || document.activeElement === document.body) this.panel.focus();
        emit('fp:notice', { kind: 'ok', text: `Moved the ${name} folder to the trash` });
      } catch (e) {
        emit('fp:notice', { kind: 'error', text: message(e) });
      }
    });
  }

  private async runReveal(target: string): Promise<void> {
    const build = this.buildId;
    const folder = this.memos.get(build)?.results.get(target)?.folder ?? '';
    try {
      const r = await publishApi.reveal(build, target);
      if (!r.opened) {
        await copyText(r.path || folder);
        emit('fp:notice', { kind: 'info', text: 'This system cannot open folders from here. The path was copied.' });
      }
    } catch (e) {
      emit('fp:notice', { kind: 'error', text: message(e) });
    }
  }

  private pick(id: string, on: boolean): void {
    const m = this.memo();
    if (!m) return;
    if (on) m.picked.add(id); else m.picked.delete(id);
    writePicks(Array.from(m.picked));
    this.paintTargets();
    this.sync();
  }

  private wire(): void {
    this.body.addEventListener('click', (e) => {
      const t = e.target as HTMLElement;
      const a = t.closest<HTMLElement>('[data-a]')?.dataset.a;
      if (!a) return;
      const target = t.closest<HTMLElement>('.fp-pub-res')?.dataset.key ?? '';
      if (a === 'build') void this.runBuild();
      else if (a === 'all') {
        const m = this.memo();
        if (!m) return;
        const all = this.targets.every((x) => m.picked.has(x.id));
        m.picked = new Set(all ? [] : this.targets.map((x) => x.id));
        writePicks(Array.from(m.picked));
        this.paintTargets();
        this.sync();
      } else if (a === 'verify' && target) void this.runVerify(target);
      else if (a === 'remove' && target) void this.runRemove(target);
      else if (a === 'reveal' && target) void this.runReveal(target);
      else if (a === 'path' && target) void copyText(this.memo()?.results.get(target)?.folder ?? '');
      else if (a === 'copycmd') void copyText(t.closest<HTMLElement>('.fp-pub-cmd')?.dataset.run ?? '');
    });
    this.tlist.addEventListener('change', (e) => {
      const box = e.target as HTMLInputElement;
      const id = box.closest<HTMLElement>('.fp-pub-target')?.dataset.key;
      if (id) this.pick(id, box.checked);
    });
    this.f.model.addEventListener('change', () => {
      const m = this.memo();
      if (!m) return;
      m.includeModel = (this.f.model as HTMLInputElement).checked;
      writeModel(m.includeModel);
    });
    this.buildSel.addEventListener('change', () => {
      this.buildId = this.buildSel.value;
      this.paintAll();
      this.sync();
      if (this.buildId) void this.loadPrepared(this.buildId);
    });
    this.body.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && !this.prepareBtn.disabled) { e.preventDefault(); void this.runPrepare(); }
    });
  }
}

let sheet: PublishSheet | null = null;
let installed = false;

export function openPublishSheet(app: App, build?: string): void {
  sheet ??= new PublishSheet(app);
  void sheet.show(build);
}

export function installPublish(app: App): void {
  if (installed) return;
  installed = true;
  on('fp:publish', (d) => openPublishSheet(app, d.build));
  on('fp:site-closed', (d) => sheet?.siteClosed(d.id));
  on('fp:live', (ev) => {
    if (ev.type !== 'sites.received') return;
    const id = typeof ev.site === 'string' ? ev.site : typeof ev.id === 'string' ? ev.id : '';
    const name = typeof ev.name === 'string' && ev.name ? ev.name : typeof ev.siteName === 'string' ? ev.siteName : '';
    const open = (): void => {
      if (!id) return;
      void app.refreshSites().then(() => app.openSite(id));
    };
    toast(name ? `Received ${name} from FormWeb` : 'Received a site from FormWeb', 'ok', id ? { label: 'Open', run: open } : undefined);
  });
}
