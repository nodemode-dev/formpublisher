import '../styles/panel.css';
import type { App } from '../app-api';
import { fetchResults, postLive, siteRevision, startRun, type Problem, type Severity, type Tier } from '../api-checks';
import { emit, on, type ProbeMessage, type RouteStatus } from '../events';
import { onLanguage, t } from '../i18n';
import { el, patchList, q, setAttr, setClass, setDisabled, setHidden, setText } from './dom';
import { Dropdown, dropdownHtml, type DropdownOption } from './dropdown';
import { icon } from './icons';
import { refuse } from './notice-step';
import { openPreferences } from './preferences';
import { RevisionsView } from './revisions';

interface ConEntry { seq: number; level: 'error' | 'warn'; text: string; where: string }
interface NetEntry { seq: number; url: string; kind: string; status: number; failed: boolean; ms: number; bytes: number }

interface SiteData {
  con: ConEntry[];
  net: NetEntry[];
  live: Map<string, Problem>;
  remote: Problem[];
  failed: Problem | null;
  thumbs: Record<string, string>;
  ran: boolean;
  revision: string | null;
  path: string;
  seq: number;
  token: number;
  signature: string;
}

const CAP = 500;
const SEV_RANK: Record<Severity, number> = { error: 0, warning: 1, info: 2 };
const SEV_ICON: Record<Severity, string> = { error: 'close', warning: 'alert', info: 'info' };
const MAX_TEXT = 300;

const s = (v: unknown): string => (typeof v === 'string' ? v : typeof v === 'number' ? String(v) : '');
const n = (v: unknown): number => (typeof v === 'number' && Number.isFinite(v) ? v : 0);
const clip = (t: string): string => (t.length > MAX_TEXT ? `${t.slice(0, MAX_TEXT)}...` : t);

function hash(text: string): string {
  let h = 2166136261;
  for (let i = 0; i < text.length; i += 1) h = Math.imul(h ^ text.charCodeAt(i), 16777619);
  return (h >>> 0).toString(36);
}

function plural(count: number, one: string, many: string): string {
  return `${count} ${count === 1 ? one : many}`;
}

function bytesLabel(b: number): string {
  if (b <= 0) return '';
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / 1024 / 1024).toFixed(1)} MB`;
}

const SEV_LABEL = 'Filter by severity';
const TIER_LABEL = 'Filter by tier';
const SEV_OPTIONS: DropdownOption[] = [{ value: 'all', label: 'All severities' }, { value: 'error', label: 'Errors' }, { value: 'warning', label: 'Warnings' }, { value: 'info', label: 'Info' }];
const TIER_OPTIONS: DropdownOption[] = [{ value: 'all', label: 'All tiers' }, { value: 'static', label: 'Static' }, { value: 'live', label: 'Live' }, { value: 'deep', label: 'Deep' }];

const page = (name: string, bar: string, head: string, empty: string, hidden: boolean): string =>
  `<div class="fp-bottom-page fp-pn-page" data-page="${name}" role="tabpanel"${hidden ? ' hidden' : ''}><div class="fp-pn-bar">${bar}</div>${head}<div class="fp-pn-body"><div class="fp-pn-list" role="rowgroup"></div><div class="fp-pn-empty">${empty}</div></div></div>`;

const CLEAR = `<span class="fp-pn-spacer"></span><button class="fp-btn fp-btn-sm fp-btn-ghost" type="button" data-act="clear">Clear</button>`;

export function panelPagesHtml(): string {
  const filters = `${dropdownHtml({ cls: 'fp-pn-select', label: SEV_LABEL, data: { f: 'sev' }, options: SEV_OPTIONS })}${dropdownHtml({ cls: 'fp-pn-select', label: TIER_LABEL, data: { f: 'tier' }, options: TIER_OPTIONS })}`;
  const problems = `${filters}<button class="fp-btn fp-btn-sm fp-pn-filter" type="button" aria-haspopup="menu" aria-expanded="false" title="Filter problems" aria-label="Filter problems" hidden>${icon('filter', 14)}<i class="fp-pn-dot" hidden></i></button><span class="fp-pn-progress" aria-live="polite"></span><span class="fp-pn-spacer"></span><button class="fp-btn fp-btn-sm" type="button" data-act="run" title="Run checks">${icon('check', 14)}<span>Run checks</span></button><button class="fp-btn fp-btn-sm" type="button" data-act="deep" title="Deep check">${icon('alert', 14)}<span>Deep check</span></button>`;
  const note = '<p class="fp-pn-note" title="The deep check loads the site as a browser would, including what it loads from other hosts.">The deep check loads the site as a browser would, including what it loads from other hosts.</p>';
  const nethead = '<div class="fp-pn-net fp-pn-nethead" aria-hidden="true"><span>URL</span><span>Kind</span><span>Status</span><span>Time</span><span>Size</span></div>';
  return page('problems', problems, note, 'No problems found yet.', false)
    + page('console', CLEAR, '', 'Nothing in the console yet.', true)
    + page('network', CLEAR, nethead, 'No network requests yet.', true);
}

class Panel {
  private readonly data = new Map<string, SiteData>();
  private readonly pages: Record<'problems' | 'console' | 'network', HTMLElement>;
  private readonly lists: Record<'problems' | 'console' | 'network', HTMLElement>;
  private readonly empties: Record<'problems' | 'console' | 'network', HTMLElement>;
  private readonly counts: Record<'problems' | 'console' | 'network', HTMLElement>;
  private readonly sevSel: Dropdown;
  private readonly tierSel: Dropdown;
  private readonly filterBtn: HTMLButtonElement;
  private readonly filterDot: HTMLElement;
  private filterMenu: HTMLElement | null = null;
  private readonly runBtn: HTMLButtonElement;
  private readonly deepBtn: HTMLButtonElement;
  private readonly progress: HTMLElement;
  private readonly status: HTMLElement;
  private readonly statusDot: HTMLElement;
  private readonly statusText: HTMLElement;
  private frame = 0;
  private liveTimer: number | undefined;
  private lastSent = 0;
  private pending = new Map<string, Map<string, Problem>>();
  private runs = new Set<string>();
  private deepRun = '';
  private deepTimer: number | undefined;
  private activeSite: string | null = null;
  private readonly revs: RevisionsView;
  private readonly revPage: HTMLElement;
  private readonly revCount: HTMLElement;

  constructor(private readonly app: App) {
    const root = app.mounts.bottom;
    const tab = (name: string): HTMLElement => q(root, `.fp-bottom-tab[data-tab="${name}"]`);
    const page = (name: string): HTMLElement => q(root, `.fp-bottom-page[data-page="${name}"]`);
    this.pages = { problems: page('problems'), console: page('console'), network: page('network') };
    this.lists = { problems: q(this.pages.problems, '.fp-pn-list'), console: q(this.pages.console, '.fp-pn-list'), network: q(this.pages.network, '.fp-pn-list') };
    this.empties = { problems: q(this.pages.problems, '.fp-pn-empty'), console: q(this.pages.console, '.fp-pn-empty'), network: q(this.pages.network, '.fp-pn-empty') };
    this.sevSel = new Dropdown(q<HTMLButtonElement>(this.pages.problems, '[data-f="sev"]'), { label: SEV_LABEL, options: SEV_OPTIONS, change: () => this.filterChanged() });
    this.tierSel = new Dropdown(q<HTMLButtonElement>(this.pages.problems, '[data-f="tier"]'), { label: TIER_LABEL, options: TIER_OPTIONS, change: () => this.filterChanged() });
    this.filterBtn = q(this.pages.problems, '.fp-pn-filter');
    this.filterDot = q(this.filterBtn, '.fp-pn-dot');
    this.runBtn = q(this.pages.problems, '[data-act="run"]');
    this.deepBtn = q(this.pages.problems, '[data-act="deep"]');
    this.progress = q(this.pages.problems, '.fp-pn-progress');
    const badge = (t: HTMLElement): HTMLElement => {
      const b = el(`<span class="fp-badge is-count fp-pn-count">0</span>`);
      t.append(b);
      return b;
    };
    this.counts = { problems: badge(tab('problems')), console: badge(tab('console')), network: badge(tab('network')) };
    this.revPage = page('revisions');
    this.revs = new RevisionsView(this.revPage);
    this.revCount = badge(tab('revisions'));
    new MutationObserver(() => this.refreshRevisions()).observe(this.revPage, { attributes: true, attributeFilter: ['hidden'] });
    this.status = el(`<span class="fp-st fp-st-problems" role="button" tabindex="0" title="Show problems"><span class="fp-st-dot"></span><span class="fp-st-text"></span></span>`);
    this.statusDot = q(this.status, '.fp-st-dot');
    this.statusText = q(this.status, '.fp-st-text');
    app.mounts.statusLeft.append(this.status);
    this.wire();
    this.watchBar();
    this.sync();
    this.paint();
  }

  private watchBar(): void {
    const refit = (): void => { this.syncFilter(); this.fitBar(); };
    new ResizeObserver(refit).observe(this.pages.problems);
    onLanguage(refit);
    document.fonts?.addEventListener('loadingdone', refit);
    this.filterBtn.addEventListener('click', () => { if (this.filterMenu) this.closeMenu(false); else this.openMenu(); });
    this.filterBtn.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowDown') { e.preventDefault(); if (!this.filterMenu) this.openMenu(); }
    });
    document.addEventListener('pointerdown', (e) => {
      const menu = this.filterMenu;
      if (menu && !menu.contains(e.target as Node) && !this.filterBtn.contains(e.target as Node)) this.closeMenu(false);
    }, true);
    window.addEventListener('blur', () => this.closeMenu(false));
    window.addEventListener('resize', () => this.closeMenu(false));
    this.syncFilter();
  }

  private filterChanged(): void {
    this.syncFilter();
    this.fitBar();
    this.schedule();
  }

  private syncFilter(): void {
    const label = `${t('Filter problems')}: ${t(this.sevSel.selected()?.label ?? '')}, ${t(this.tierSel.selected()?.label ?? '')}`;
    setAttr(this.filterBtn, 'title', label);
    setAttr(this.filterBtn, 'aria-label', label);
    setHidden(this.filterDot, this.sevSel.value === 'all' && this.tierSel.value === 'all');
  }

  private openMenu(): void {
    if (this.filterMenu) return;
    const menu = el('<div class="fp-menu fp-pn-filter-menu has-checks" role="menu" translate="no"></div>');
    let focus: HTMLElement | null = null;
    [this.sevSel, this.tierSel].forEach((sel, g) => {
      if (g) menu.append(el('<div class="fp-menu-sep" role="separator"></div>'));
      const name = t(sel === this.sevSel ? SEV_LABEL : TIER_LABEL);
      const group = el('<div class="fp-pn-menu-group" role="group"></div>');
      setAttr(group, 'aria-label', name);
      const head = el('<div class="fp-pn-menu-head" aria-hidden="true"></div>');
      setText(head, name);
      group.append(head);
      for (const o of sel.options()) {
        const item = el<HTMLButtonElement>(`<button class="fp-menu-item" role="menuitemradio" type="button" tabindex="-1"><span class="fp-menu-check">${icon('check', 14)}</span><span class="fp-menu-label"></span></button>`);
        item.dataset.f = sel === this.sevSel ? 'sev' : 'tier';
        item.dataset.v = o.value;
        setText(q(item, '.fp-menu-label'), t(o.label));
        const on = sel.value === o.value;
        setAttr(item, 'aria-checked', String(on));
        setClass(item, 'is-checked', on);
        if (on && !focus) focus = item;
        item.addEventListener('click', () => this.pickFilter(sel, o.value));
        group.append(item);
      }
      menu.append(group);
    });
    menu.addEventListener('keydown', (e) => this.menuKey(e, menu));
    menu.style.visibility = 'hidden';
    menu.style.maxHeight = `${Math.max(120, window.innerHeight - 8)}px`;
    document.getElementById('overlay-root')?.append(menu);
    const b = this.filterBtn.getBoundingClientRect();
    const w = menu.offsetWidth;
    const h = menu.offsetHeight;
    const below = b.bottom + 4;
    const top = below + h <= window.innerHeight - 4 ? below : Math.max(4, b.top - 4 - h);
    menu.style.left = `${Math.round(Math.max(4, Math.min(b.left, window.innerWidth - w - 4)))}px`;
    menu.style.top = `${Math.round(top)}px`;
    menu.style.visibility = '';
    this.filterMenu = menu;
    setAttr(this.filterBtn, 'aria-expanded', 'true');
    setClass(this.filterBtn, 'is-open', true);
    (focus as HTMLElement | null)?.focus();
  }

  private closeMenu(restore: boolean): void {
    const menu = this.filterMenu;
    if (!menu) return;
    this.filterMenu = null;
    menu.remove();
    setAttr(this.filterBtn, 'aria-expanded', 'false');
    setClass(this.filterBtn, 'is-open', false);
    if (restore && !this.filterBtn.hidden) this.filterBtn.focus();
  }

  private pickFilter(sel: Dropdown, value: string): void {
    if (sel.value !== value) {
      sel.set(value);
      this.filterChanged();
    }
    const menu = this.filterMenu;
    if (!menu) return;
    const f = sel === this.sevSel ? 'sev' : 'tier';
    for (const item of Array.from(menu.querySelectorAll<HTMLElement>(`[data-f="${f}"]`))) {
      const on = item.dataset.v === value;
      setAttr(item, 'aria-checked', String(on));
      setClass(item, 'is-checked', on);
    }
  }

  private menuKey(e: KeyboardEvent, menu: HTMLElement): void {
    const items = Array.from(menu.querySelectorAll<HTMLElement>('[role="menuitemradio"]'));
    const cur = items.indexOf(document.activeElement as HTMLElement);
    const go = (i: number): void => { e.preventDefault(); e.stopPropagation(); items[(i + items.length) % items.length]?.focus(); };
    switch (e.key) {
      case 'ArrowDown': go(cur + 1); break;
      case 'ArrowUp': go(cur <= 0 ? -1 : cur - 1); break;
      case 'Home': go(0); break;
      case 'End': go(-1); break;
      case 'Escape': e.preventDefault(); e.stopPropagation(); this.closeMenu(true); break;
      case 'Tab': this.closeMenu(true); break;
      default: break;
    }
  }

  private fitBar(): void {
    const page = this.pages.problems;
    if (page.hidden || !page.clientWidth) { this.closeMenu(false); return; }
    const kept = document.activeElement;
    const apply = (mode: 'full' | 'short' | 'compact'): void => {
      const short = mode === 'short';
      const word = t('All');
      setHidden(this.filterBtn, mode !== 'compact');
      for (const sel of [this.sevSel, this.tierSel]) {
        if (mode === 'compact') sel.close(false);
        setHidden(sel.button, mode === 'compact');
        const all = sel.options()[0];
        sel.setShorts(short ? new Map([[all.value, word]]) : null);
        const title = short && sel.value === all.value ? t(all.label) : '';
        if (title) setAttr(sel.button, 'title', title); else if (sel.button.hasAttribute('title')) sel.button.removeAttribute('title');
      }
    };
    const wrapped = (mode: 'full' | 'short' | 'compact'): boolean => {
      const row = mode === 'compact' ? [this.filterBtn, this.runBtn, this.deepBtn] : [this.sevSel.button, this.tierSel.button, this.runBtn, this.deepBtn];
      return row.some((c) => Math.abs(c.offsetTop - row[0].offsetTop) > 2);
    };
    const settle = (): void => {
      if (kept instanceof HTMLElement && kept.isConnected && !kept.hidden && document.activeElement !== kept && document.activeElement === document.body) kept.focus();
    };
    apply('full');
    if (!wrapped('full')) { this.closeMenu(false); settle(); return; }
    apply('short');
    if (!wrapped('short')) { this.closeMenu(false); settle(); return; }
    apply('compact');
    settle();
  }

  private wire(): void {
    const { console: con, network } = this.pages;
    this.runBtn.addEventListener('click', () => { void runChecks(this.app, false); });
    this.deepBtn.addEventListener('click', () => { void runChecks(this.app, true); });
    const openProblems = (): void => this.app.showBottomTab('problems');
    this.status.addEventListener('click', openProblems);
    this.status.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openProblems(); } });
    q(con, '[data-act="clear"]').addEventListener('click', () => { const d = this.cur(); if (d) { d.con = []; this.schedule(); } });
    q(network, '[data-act="clear"]').addEventListener('click', () => { const d = this.cur(); if (d) { d.net = []; this.schedule(); } });
    const pick = (row: HTMLElement | null): void => {
      const route = row?.dataset.route;
      if (route) this.app.selectRoute(this.routeFor(route));
    };
    this.lists.problems.addEventListener('click', (e) => pick((e.target as HTMLElement).closest<HTMLElement>('.fp-pn-row')));
    this.lists.problems.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pick((e.target as HTMLElement).closest<HTMLElement>('.fp-pn-row')); }
    });
    on('fp:sites-changed', () => this.schedule());
    on('fp:probe', (m) => this.probe(m));
    on('fp:site-opened', () => this.sync());
    on('fp:site-loaded', () => this.sync());
    on('fp:site-closed', () => this.sync());
    on('fp:home', () => this.sync());
    on('fp:live', (ev) => this.live(ev));
  }

  private id(): string | null {
    return this.app.state().activeId;
  }

  private cur(): SiteData | null {
    const id = this.id();
    return id ? this.get(id) : null;
  }

  private get(id: string): SiteData {
    let d = this.data.get(id);
    if (!d) {
      d = { con: [], net: [], live: new Map(), remote: [], failed: null, thumbs: {}, ran: false, revision: null, path: '/', seq: 0, token: 0, signature: '' };
      this.data.set(id, d);
    }
    return d;
  }

  sync(): void {
    const id = this.id();
    if (id !== this.activeSite) {
      this.activeSite = id;
      if (id) void this.load(id, null);
      this.refreshRevisions();
    }
    this.schedule();
  }

  private refreshRevisions(): void {
    if (!this.revPage.hidden) void this.revs.load(this.id());
  }

  private async load(id: string, revision: string | null): Promise<void> {
    const d = this.get(id);
    const token = ++d.token;
    try {
      const rev = revision ?? await siteRevision(id);
      if (token !== d.token) return;
      d.revision = rev;
      if (!rev) return;
      const r = await fetchResults(id, rev);
      if (token !== d.token) return;
      d.remote = r.problems;
      d.thumbs = r.thumbs;
      d.ran = r.summary.ran || r.problems.some((p) => p.tier !== 'live');
      this.schedule();
    } catch {
      return;
    }
  }

  private route(d: SiteData): string {
    return d.path || '/';
  }

  private probe(m: ProbeMessage): void {
    const d = this.get(m.siteId);
    let touched = true;
    switch (m.type) {
      case 'hello':
      case 'nav':
        d.path = s(m.path) || '/';
        touched = false;
        break;
      case 'console': {
        const level = m.level === 'error' ? 'error' : 'warn';
        const text = clip(s(m.text));
        this.pushCon(d, { seq: ++d.seq, level, text, where: this.route(d) });
        this.addLive(m.siteId, d, `console.${level}`, level === 'error' ? 'error' : 'warning', `live.console`, text, hash(text));
        break;
      }
      case 'error': {
        const text = clip(s(m.message));
        const line = n(m.line);
        const src = s(m.source);
        this.pushCon(d, { seq: ++d.seq, level: 'error', text, where: src ? `${src}${line ? `:${line}` : ''}` : this.route(d) });
        this.addLive(m.siteId, d, 'pageerror', 'error', 'live.pageerror', text, hash(text), src, line);
        break;
      }
      case 'request': {
        const status = n(m.status);
        const failed = m.ok === false || status >= 400 || status === 0;
        d.net.push({ seq: ++d.seq, url: s(m.url), kind: s(m.kind), status, failed, ms: n(m.ms), bytes: n(m.bytes) });
        if (d.net.length > CAP) d.net.splice(0, d.net.length - CAP);
        if (failed) {
          const url = s(m.url);
          this.addLive(m.siteId, d, 'request', 'error', 'live.request', `The request to ${url} failed${status ? ` with status ${status}` : ''}.`, hash(url), undefined, undefined, url);
        }
        break;
      }
      case 'cls': {
        const v = n(m.value);
        if (v >= 0.001) this.addLive(m.siteId, d, 'cls', v >= 0.1 ? 'error' : 'warning', 'live.cls', `Layout shift of ${v.toFixed(3)} on this page.`, '');
        break;
      }
      case 'overflow':
        if (n(m.clientWidth) > 0) this.addLive(m.siteId, d, 'overflow', 'error', 'live.overflow', `The page is ${n(m.scrollWidth)} px wide in a ${n(m.clientWidth)} px viewport.`, '');
        break;
      default:
        touched = false;
    }
    if (touched) this.schedule();
  }

  private pushCon(d: SiteData, e: ConEntry): void {
    d.con.push(e);
    if (d.con.length > CAP) d.con.splice(0, d.con.length - CAP);
  }

  private addLive(site: string, d: SiteData, kind: string, severity: Severity, code: string, message: string, key: string, file?: string, line?: number, url?: string): void {
    const route = this.route(d);
    const p: Problem = { id: `live:${kind}:${route}:${key}`, tier: 'live', severity, code, route, message };
    if (file) p.file = file;
    if (line) p.line = line;
    if (url) p.url = url;
    const prev = d.live.get(p.id);
    if (prev && prev.message === p.message && prev.severity === p.severity) return;
    d.live.set(p.id, p);
    let queue = this.pending.get(site);
    if (!queue) { queue = new Map(); this.pending.set(site, queue); }
    queue.set(p.id, p);
    this.armFlush();
  }

  private armFlush(): void {
    if (this.liveTimer !== undefined) return;
    const wait = Math.max(0, 1000 - (Date.now() - this.lastSent));
    this.liveTimer = window.setTimeout(() => { this.liveTimer = undefined; void this.flush(); }, wait);
  }

  private async flush(): Promise<void> {
    const batches = this.pending;
    this.pending = new Map();
    this.lastSent = Date.now();
    for (const [site, queue] of batches) {
      const d = this.get(site);
      try {
        if (!d.revision) d.revision = await siteRevision(site);
        if (d.revision) await postLive(site, d.revision, Array.from(queue.values()));
      } catch {
        continue;
      }
    }
  }

  private live(ev: { type: string; [key: string]: unknown }): void {
    if (ev.type === 'checks.progress') {
      const run = s(ev.run);
      if (run && this.deepRun && run !== this.deepRun) return;
      const done = n(ev.done);
      const total = n(ev.total);
      const width = n(ev.width);
      const prior = this.data.get(s(ev.site));
      if (prior?.failed) { prior.failed = null; this.schedule(); }
      setText(this.progress, `Checking ${done} of ${total}${ev.route ? ` ${s(ev.route)}` : ''}${width ? ` at ${width} px` : ''}`);
      return;
    }
    if (ev.type === 'checks.failed') {
      const site = s(ev.site);
      if (s(ev.run) === this.deepRun || (this.deepRun === 'pending' && site === this.id())) this.endDeep();
      const d = site ? this.data.get(site) : undefined;
      const why = s(ev.reason);
      if (d) d.failed = { id: 'deep:deep.failed:run', tier: 'deep', severity: 'error', code: 'deep.failed', route: '', message: why ? `The deep check could not finish: ${why}` : 'The check failed.' };
      if (!site || site === this.id()) setText(this.progress, 'The check failed.');
      this.schedule();
      return;
    }
    if (ev.type === 'checks.done') {
      const run = s(ev.run);
      if (run === this.deepRun) this.endDeep();
      setText(this.progress, '');
      const site = s(ev.site);
      const d = site ? this.data.get(site) : undefined;
      if (site && d) void this.load(site, s(ev.revision) || d.revision);
      return;
    }
    if (ev.type === 'site.imported' || ev.type === 'sites.received') {
      if (s(ev.id ?? ev.site) === this.id()) this.refreshRevisions();
    }
    if (ev.type === 'site.imported') {
      const id = s(ev.id);
      if (id && this.data.has(id)) {
        const d = this.get(id);
        d.revision = null;
        d.live.clear();
        d.failed = null;
        void this.load(id, null);
      }
    }
  }

  private endDeep(): void {
    this.deepRun = '';
    if (this.deepTimer !== undefined) window.clearTimeout(this.deepTimer);
    this.deepTimer = undefined;
    this.schedule();
  }

  async run(deep: boolean): Promise<void> {
    const id = this.id();
    if (!id) {
      emit('fp:notice', { kind: 'info', text: 'Open a site to run checks.' });
      return;
    }
    if (this.deepRun) return;
    const d = this.get(id);
    try {
      if (!d.revision) d.revision = await siteRevision(id);
      if (!d.revision) throw new Error('This site has no revision to check.');
      this.app.showBottomTab('problems');
      setText(this.progress, deep ? 'Starting the deep check' : 'Checking');
      if (deep) {
        d.failed = null;
        this.deepRun = 'pending';
        this.deepTimer = window.setTimeout(() => { this.endDeep(); setText(this.progress, ''); }, 15 * 60 * 1000);
        this.schedule();
      }
      const run = await startRun(id, d.revision, deep);
      if (deep && this.deepRun === 'pending') this.deepRun = run || 'pending';
      if (!deep) {
        await this.load(id, d.revision);
        setText(this.progress, '');
      }
    } catch (err) {
      if (deep) this.endDeep();
      setText(this.progress, '');
      refuse(err, 'The check failed.');
    }
  }

  private schedule(): void {
    if (this.frame) return;
    this.frame = requestAnimationFrame(() => { this.frame = 0; this.paint(); });
  }

  private merged(d: SiteData): Problem[] {
    const map = new Map<string, Problem>();
    for (const p of d.remote) map.set(p.id, p);
    for (const p of d.live.values()) map.set(p.id, p);
    if (d.failed) map.set(d.failed.id, d.failed);
    return Array.from(map.values()).sort((a, b) => SEV_RANK[a.severity] - SEV_RANK[b.severity] || a.route.localeCompare(b.route) || a.code.localeCompare(b.code) || a.id.localeCompare(b.id));
  }

  private paint(): void {
    const d = this.cur();
    const all = d ? this.merged(d) : [];
    const sev = this.sevSel.value;
    const tier = this.tierSel.value;
    const shown = all.filter((p) => (sev === 'all' || p.severity === sev) && (tier === 'all' || p.tier === (tier as Tier)));
    patchList(this.lists.problems, shown, {
      key: (p) => p.id,
      create: (p) => {
        const node = el(`<div class="fp-pn-row fp-pn-prob" role="row" tabindex="0"><span class="fp-pn-sev"></span><span class="fp-pn-code" translate="no"></span><span class="fp-pn-msg"></span><span class="fp-pn-route" translate="no"></span><span class="fp-pn-tier"></span></div>`);
        if (p.code === 'deep.unavailable') {
          const act = el<HTMLButtonElement>('<button class="fp-pn-act" type="button">Open Preferences</button>');
          act.addEventListener('click', (e) => { e.stopPropagation(); openPreferences('checks'); });
          act.addEventListener('keydown', (e) => e.stopPropagation());
          q(node, '.fp-pn-msg').after(act);
          node.classList.add('has-act');
        }
        this.paintProblem(node, p);
        return node;
      },
      update: (node, p) => this.paintProblem(node, p),
    });
    const stickCon = this.nearEnd(this.lists.console);
    const stickNet = this.nearEnd(this.lists.network);
    patchList(this.lists.console, d ? d.con : [], {
      key: (e) => String(e.seq),
      create: (e) => {
        const node = el(`<div class="fp-pn-row fp-pn-con" role="row"><span class="fp-pn-sev"></span><span class="fp-pn-msg" translate="no"></span><span class="fp-pn-route" translate="no"></span></div>`);
        const sevEl = q(node, '.fp-pn-sev');
        sevEl.innerHTML = icon(e.level === 'error' ? 'close' : 'alert', 14);
        sevEl.classList.add(e.level === 'error' ? 'is-error' : 'is-warning');
        setText(q(node, '.fp-pn-msg'), e.text);
        setAttr(node, 'title', e.text);
        setText(q(node, '.fp-pn-route'), e.where);
        return node;
      },
      update: () => undefined,
    });
    patchList(this.lists.network, d ? d.net : [], {
      key: (e) => String(e.seq),
      create: (e) => {
        const node = el(`<div class="fp-pn-row fp-pn-net" role="row"><span class="fp-pn-msg" translate="no"></span><span></span><span></span><span></span><span></span></div>`);
        const cells = node.children;
        setText(cells[0], e.url);
        setText(cells[1], e.kind);
        setText(cells[2], e.status ? String(e.status) : 'failed');
        setText(cells[3], e.ms ? `${Math.round(e.ms)} ms` : '');
        setText(cells[4], bytesLabel(e.bytes));
        setAttr(node, 'title', e.url);
        setClass(node, 'is-failed', e.failed);
        return node;
      },
      update: () => undefined,
    });
    this.paintCount('console', d ? d.con.length : 0, d ? d.con.some((e) => e.level === 'error') : false);
    this.paintCount('network', d ? d.net.length : 0, d ? d.net.some((e) => e.failed) : false);
    const errors = all.filter((p) => p.severity === 'error').length;
    const warnings = all.filter((p) => p.severity === 'warning').length;
    this.paintCount('problems', errors + warnings, errors > 0);
    const revs = this.id() ? this.app.state().sites.find((x) => x.id === this.id())?.revisions ?? 0 : 0;
    setText(this.revCount, String(revs));
    this.revCount.style.visibility = revs > 1 ? 'visible' : 'hidden';
    setText(this.statusText, `${plural(errors, 'error', 'errors')}, ${plural(warnings, 'warning', 'warnings')}`);
    setClass(this.statusDot, 'is-error', errors > 0);
    setClass(this.statusDot, 'is-warn', errors === 0 && warnings > 0);
    setClass(this.statusDot, 'is-ok', errors === 0 && warnings === 0 && Boolean(d?.ran));
    setText(this.empties.problems, all.length === 0 ? 'No problems found yet.' : 'No problems match the filters.');
    setHidden(this.empties.problems, shown.length > 0);
    setText(this.empties.console, 'Nothing in the console yet.');
    setHidden(this.empties.console, (d?.con.length ?? 0) > 0);
    setText(this.empties.network, 'No network requests yet.');
    setHidden(this.empties.network, (d?.net.length ?? 0) > 0);
    const busy = this.deepRun !== '';
    setDisabled(this.runBtn, !d || busy);
    setDisabled(this.deepBtn, !d || busy);
    if (stickCon) this.lists.console.scrollTop = this.lists.console.scrollHeight;
    if (stickNet) this.lists.network.scrollTop = this.lists.network.scrollHeight;
    if (d && this.id()) this.publish(this.id() as string, d, all);
  }

  private nearEnd(list: HTMLElement): boolean {
    return list.scrollHeight - list.scrollTop - list.clientHeight < 40;
  }

  private paintCount(which: 'problems' | 'console' | 'network', value: number, hot: boolean): void {
    const b = this.counts[which];
    setText(b, value > 999 ? '999+' : String(value));
    b.style.visibility = value > 0 ? 'visible' : 'hidden';
    setClass(b, 'is-hot', hot);
  }

  private paintProblem(node: HTMLElement, p: Problem): void {
    const sevEl = q(node, '.fp-pn-sev');
    if (sevEl.dataset.sev !== p.severity) {
      sevEl.innerHTML = icon(SEV_ICON[p.severity], 14);
      sevEl.dataset.sev = p.severity;
      sevEl.className = `fp-pn-sev is-${p.severity}`;
    }
    setText(q(node, '.fp-pn-code'), p.code);
    setText(q(node, '.fp-pn-msg'), p.message);
    setText(q(node, '.fp-pn-route'), p.route);
    setText(q(node, '.fp-pn-tier'), p.tier);
    setAttr(node, 'data-route', p.route);
    setAttr(node, 'title', p.fix ? `${p.message} · ${p.fix}` : p.message);
  }

  private routeFor(route: string): string {
    const norm = (p: string): string => p.replace(/^\/+/, '').replace(/(^|\/)index\.html?$/, '$1').replace(/\.html?$/, '').replace(/\/+$/, '');
    const want = norm(route);
    return this.app.state().routes.find((r) => norm(r.path) === want)?.path ?? route;
  }

  private publish(site: string, d: SiteData, all: Problem[]): void {
    if (!d.revision) return;
    const status: Record<string, RouteStatus> = {};
    if (d.ran) for (const r of this.app.state().routes) status[r.path] = 'ok';
    for (const p of all) {
      if (p === d.failed) continue;
      const at = this.routeFor(p.route);
      if (p.severity === 'error') status[at] = 'error';
      else if (p.severity === 'warning' && status[at] !== 'error') status[at] = 'warn';
      else if (!status[at]) status[at] = 'ok';
    }
    const thumbs: Record<string, string> = {};
    for (const [route, url] of Object.entries(d.thumbs)) thumbs[this.routeFor(route)] = url;
    const sig = JSON.stringify([d.revision, status, thumbs]);
    if (sig === d.signature) return;
    d.signature = sig;
    emit('fp:checks', { siteId: site, revision: d.revision, status, thumbs });
  }
}

let panel: Panel | null = null;

export function installPanel(app: App): void {
  if (panel) return;
  panel = new Panel(app);
}

export function runChecks(_app: App, deep: boolean): Promise<void> {
  return panel ? panel.run(deep) : Promise.resolve();
}
