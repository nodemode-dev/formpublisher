import '../styles/recent.css';
import { api, type Site } from '../api';
import { openSample } from '../api-demo';
import type { App } from '../app-api';
import { emit, on } from '../events';
import { locale } from '../i18n';
import { brandMark } from './brand';
import { BuildsPage } from './builds';
import type { Commands } from './commands';
import { anyDialogOpen } from './dialogs';
import { el, patchList, q, setAttr, setClass, setDisabled, setHidden, setText } from './dom';
import { icon } from './icons';
import { RevisionsDialog, revisionsText } from './revisions';
import { TrashPage } from './trash';

export type HomeView = 'start' | 'recent' | 'builds' | 'trash';
type View = HomeView;

const NAV_W_KEY = 'formpublisher.homeNav';
const NAV_HIDDEN_KEY = 'formpublisher.homeNavHidden';
const START_CARDS = 6;
const FW_POLL_MS = 15000;

function kindOf(source: string): string {
  if (!source) return 'Site';
  if (source === 'Bundled sample site') return 'Demo';
  if (/^https?:\/\//i.test(source)) return 'FormWeb';
  if (/\.zip$/i.test(source)) return 'Zip';
  return 'Folder';
}

function relative(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return '';
  const secs = Math.round((then - Date.now()) / 1000);
  const steps: Array<[Intl.RelativeTimeFormatUnit, number]> = [['year', 31536000], ['month', 2592000], ['day', 86400], ['hour', 3600], ['minute', 60]];
  try {
    const rtf = new Intl.RelativeTimeFormat(locale(), { numeric: 'auto' });
    for (const [unit, size] of steps) if (Math.abs(secs) >= size) return rtf.format(Math.round(secs / size), unit);
    return rtf.format(Math.abs(secs) < 45 ? 0 : Math.sign(secs), Math.abs(secs) < 45 ? 'second' : 'minute');
  } catch {
    return iso;
  }
}

const routeText = (n: number): string => (n === 1 ? '1 route' : `${n} routes`);

const arrivedText = (n: number): string => (n === 1 ? '1 new site arrived' : `${n} new sites arrived`);

const CARD_GRID = (cls: string, withEmpty: boolean): string => `<div class="fp-recent-note" data-note="${cls}"><button class="fp-btn fp-btn-sm" type="button" data-show disabled>Show</button><span class="fp-recent-note-text" role="status" aria-live="polite"></span></div>
<div class="fp-card-grid ${cls}">
<div class="fp-card is-skeleton" aria-hidden="true"><span class="fp-card-preview"></span><span class="fp-card-body"><span class="fp-card-name">&nbsp;</span><span class="fp-card-meta">&nbsp;</span><span class="fp-card-revs">&nbsp;</span></span></div>
${withEmpty ? `<div class="fp-card is-empty" hidden><span class="fp-card-preview is-blank">${icon('globe', 28)}</span><span class="fp-card-body"><span class="fp-card-name">No sites yet</span><span class="fp-card-meta">Open a zip, a folder or a site from FormWeb</span></span></div>` : ''}
<div class="fp-card-list"></div>
</div>`;

export class Home {
  readonly root: HTMLElement;
  private view: View = 'start';
  private loaded = false;
  private fwTimer = 0;
  private readonly hero: HTMLElement;
  private readonly counts: HTMLElement[];
  private readonly grids: Array<{ list: HTMLElement; skeleton: HTMLElement; empty: HTMLElement | null; note: HTMLElement; limit: number }>;
  private frozen: string[] | null = null;
  private readonly openBox: HTMLElement;
  private readonly openList: HTMLElement;
  private readonly fwDot: HTMLElement;
  private readonly fwText: HTMLElement;
  private readonly navItems: HTMLElement[];
  private readonly pages: HTMLElement[];
  private readonly builds: BuildsPage;
  private readonly trash: TrashPage;
  private revisions: RevisionsDialog | null = null;

  constructor(private readonly app: App, private readonly commands: Commands, visible: boolean) {
    this.root = el(`<section class="fp-home" aria-label="Home"${visible ? '' : ' hidden'}>
<nav class="fp-home-nav" aria-label="Home">
<div class="fp-home-brand">${brandMark(26)}<span class="fp-home-brand-text"><span class="fp-home-brand-name" translate="no">formpublisher</span><span class="fp-home-brand-by" translate="no">by nodemode.ai</span></span></div>
<button class="fp-home-nav-item is-active" type="button" data-v="start">${icon('home', 16)}<span>Start</span></button>
<button class="fp-home-nav-item" type="button" data-v="recent">${icon('globe', 16)}<span>Recent sites</span><span class="fp-badge is-count" data-count="sites">0</span></button>
<button class="fp-home-nav-item" type="button" data-v="builds">${icon('package', 16)}<span>Builds</span></button>
<button class="fp-home-nav-item" type="button" data-v="trash">${icon('trash', 16)}<span>Trash</span></button>
<div class="fp-home-open" hidden><div class="fp-home-nav-sep"></div><div class="fp-home-nav-title">Open sites</div><div class="fp-home-open-list"></div></div>
<div class="fp-home-nav-foot">
<button class="fp-home-nav-item" type="button" data-a="local" title="Your sites stay on this computer">${icon('cloudOff', 16)}<span>Local only</span></button>
<button class="fp-home-nav-item" type="button" data-a="prefs">${icon('settings', 16)}<span>Preferences</span></button>
</div>
</nav>
<div class="fp-home-resizer" role="separator" aria-orientation="vertical" aria-label="Resize the side panel"></div>
<button class="fp-home-nav-hide" type="button" title="Hide the side panel" aria-label="Hide the side panel">${icon('chevronLeft', 14)}</button>
<button class="fp-home-nav-show" type="button" title="Show the side panel" aria-label="Show the side panel">${icon('chevronRight', 14)}</button>
<div class="fp-home-main">
<div data-page="start">
<div class="fp-home-head"><div><h1 class="fp-home-title">Start</h1><p class="fp-home-sub">Open a FormWeb site to preview, check and package it.</p></div></div>
<div class="fp-home-hero" data-drop>
<span class="fp-home-hero-icon">${icon('archive', 26)}</span>
<div class="fp-home-hero-text">
<div class="fp-home-hero-title">Drop a site zip here</div>
<div class="fp-home-hero-sub">Drop a FormWeb site export (.zip), project (.fweb) or package (.fpub) anywhere on this box to import it. FormPublisher reads it and never changes it.</div>
<div class="fp-home-fw"><span class="fp-st-dot"></span><span class="fp-home-fw-text"></span></div>
</div>
<div class="fp-home-hero-actions">
<button class="fp-btn fp-btn-primary" type="button" data-cmd="file.open-zip">${icon('archive', 14)}<span>Open zip</span></button>
<button class="fp-btn" type="button" data-cmd="file.open-folder">${icon('folder', 14)}<span>Open folder</span></button>
<button class="fp-btn" type="button" data-cmd="file.import-formweb">${icon('download', 14)}<span>Import from FormWeb</span></button>
</div>
</div>
<section class="fp-home-section"><div class="fp-home-section-head"><h2 class="fp-home-section-title">Recent sites</h2><button class="fp-btn fp-btn-ghost fp-btn-sm" type="button" data-v="recent">See all</button></div>${CARD_GRID('fp-recent-grid', true)}</section>
<section class="fp-home-section"><div class="fp-home-section-head"><h2 class="fp-home-section-title">Demos</h2></div><div class="fp-card-grid"><button class="fp-card" type="button" data-demo="sample"><span class="fp-card-preview">${icon('publish', 28)}<span class="fp-badge fp-demo-badge">Demo</span></span><span class="fp-card-body"><span class="fp-card-name">FormPublisher demo</span><span class="fp-card-meta">Try it on a sample site</span></span></button></div></section>
</div>
<div data-page="recent" hidden><div class="fp-home-head"><div><h1 class="fp-home-title">Recent sites</h1><p class="fp-home-sub">Every site you have imported, newest first.</p></div></div>${CARD_GRID('fp-recent-full', true)}</div>
<div data-page="builds" hidden></div>
<div data-page="trash" hidden></div>
</div>
</section>`);
    this.hero = q(this.root, '.fp-home-hero');
    this.counts = Array.from(this.root.querySelectorAll<HTMLElement>('[data-count="sites"]'));
    this.grids = [
      { list: q(this.root, '.fp-recent-grid .fp-card-list'), skeleton: q(this.root, '.fp-recent-grid .is-skeleton'), empty: q(this.root, '.fp-recent-grid .is-empty'), note: q(this.root, '[data-note="fp-recent-grid"]'), limit: START_CARDS },
      { list: q(this.root, '.fp-recent-full .fp-card-list'), skeleton: q(this.root, '.fp-recent-full .is-skeleton'), empty: q(this.root, '.fp-recent-full .is-empty'), note: q(this.root, '[data-note="fp-recent-full"]'), limit: Infinity },
    ];
    this.openBox = q(this.root, '.fp-home-open');
    this.openList = q(this.root, '.fp-home-open-list');
    this.fwDot = q(this.root, '.fp-home-fw .fp-st-dot');
    this.fwText = q(this.root, '.fp-home-fw-text');
    this.navItems = Array.from(this.root.querySelectorAll<HTMLElement>('.fp-home-nav-item[data-v]'));
    this.pages = Array.from(this.root.querySelectorAll<HTMLElement>('[data-page]'));
    setText(this.fwText, 'Checking FormWeb');
    this.builds = new BuildsPage(this.app, q(this.root, '[data-page="builds"]'));
    this.trash = new TrashPage(this.app, q(this.root, '[data-page="trash"]'));
    document.getElementById('app')?.appendChild(this.root);
    this.restoreNav();
    this.wire();
    this.sidePanel();
    this.paint();
    if (visible) {
      this.lock(true);
      this.startPolling();
    }
  }

  get isOpen(): boolean { return !this.root.hidden; }

  show(view?: View): void {
    if (view) this.select(view);
    if (!this.isOpen) {
      this.root.hidden = false;
      this.lock(true);
      this.startPolling();
    }
    this.paint(true);
    this.navItems.find((n) => n.classList.contains('is-active'))?.focus({ preventScroll: true });
  }

  hide(): void {
    if (!this.isOpen) return;
    this.root.hidden = true;
    this.lock(false);
    window.clearInterval(this.fwTimer);
    this.fwTimer = 0;
  }

  private lock(on: boolean): void {
    for (const c of Array.from(this.app.mounts.root.children)) (c as HTMLElement).inert = on && !c.classList.contains('fp-titlebar');
  }

  setDragOver(over: boolean): void {
    setClass(this.hero, 'is-drag-over', over);
  }

  heroContains(target: EventTarget | null): boolean {
    return target instanceof Node && this.isOpen && this.view === 'start' && this.hero.contains(target);
  }

  private select(view: View): void {
    this.view = view;
    for (const p of this.pages) setHidden(p, p.dataset.page !== view);
    for (const n of this.navItems) setClass(n, 'is-active', n.dataset.v === view);
    this.paint(true);
    if (view === 'builds') void this.builds.refresh();
    if (view === 'trash') void this.trash.refresh();
  }

  async revealBuild(id: string): Promise<void> {
    this.show('builds');
    await this.builds.reveal(id);
  }

  private startPolling(): void {
    void this.refreshFormWeb();
    window.clearInterval(this.fwTimer);
    this.fwTimer = window.setInterval(() => { void this.refreshFormWeb(); }, FW_POLL_MS);
  }

  async refreshFormWeb(): Promise<void> {
    try {
      const s = await api.formwebStatus();
      const url = typeof s.url === 'string' ? s.url : '';
      const ok = s.reachable === true;
      setClass(this.fwDot, 'is-ok', ok);
      setClass(this.fwDot, 'is-error', !ok);
      setText(this.fwText, ok ? `FormWeb is running at ${url}` : `FormWeb is not reachable at ${url}`);
    } catch {
      setClass(this.fwDot, 'is-ok', false);
      setClass(this.fwDot, 'is-error', true);
      setText(this.fwText, 'The engine is not reachable');
    }
  }

  markLoaded(): void {
    if (!this.loaded) { this.loaded = true; this.paint(); }
  }

  private recentOnScreen(): boolean {
    return this.isOpen && this.loaded && (this.view === 'start' || this.view === 'recent');
  }

  paint(resort = false): void {
    const state = this.app.state();
    const sorted = [...state.sites].sort((a, b) => (Date.parse(b.importedAt) || 0) - (Date.parse(a.importedAt) || 0));
    for (const c of this.counts) setText(c, String(sorted.length));
    const on = this.recentOnScreen();
    if (!on || resort) this.frozen = null;
    if (on) this.frozen ??= sorted.map((s) => s.id);
    const held = this.frozen;
    const byId = new Map(sorted.map((s) => [s.id, s]));
    const fresh = held ? sorted.filter((s) => !held.includes(s.id)).length : 0;
    const sites = held ? held.filter((id) => byId.has(id)).map((id) => byId.get(id) as Site) : sorted;
    for (const g of this.grids) {
      setText(q(g.note, '.fp-recent-note-text'), fresh > 0 ? arrivedText(fresh) : '');
      setClass(g.note, 'is-on', fresh > 0);
      setDisabled(q<HTMLButtonElement>(g.note, '[data-show]'), fresh === 0);
      setHidden(g.skeleton, this.loaded);
      if (g.empty) setHidden(g.empty, !this.loaded || sites.length > 0);
      patchList<Site>(g.list, sites.slice(0, g.limit), {
        key: (s) => s.id,
        create: (s) => this.card(s),
        update: (node, s) => this.fillCard(node, s),
      });
    }
    setHidden(this.openBox, state.open.length === 0);
    patchList(this.openList, [...state.open], {
      key: (t) => t.id,
      create: (t) => {
        const b = el<HTMLButtonElement>(`<button class="fp-home-nav-item" type="button" data-open="${t.id}">${icon('globe', 16)}<span class="fp-home-open-name" translate="no"></span></button>`);
        setText(q(b, '.fp-home-open-name'), t.name);
        return b;
      },
      update: (node, t) => {
        setText(q(node, '.fp-home-open-name'), t.name);
        setClass(node, 'is-active', t.id === state.activeId);
      },
    });
  }

  private card(site: Site): HTMLElement {
    const node = el(`<button class="fp-card" type="button" data-site="${site.id.replace(/"/g, '')}"><span class="fp-card-preview">${icon('globe', 28)}<span class="fp-badge"></span></span><span class="fp-card-body"><span class="fp-card-name" translate="no"></span><span class="fp-card-meta"><span class="fp-card-routes"></span><span class="fp-card-dot">&middot;</span><span class="fp-card-time" translate="no"></span></span><span class="fp-card-revs"><span class="fp-card-revbtn" role="button" tabindex="0" data-revs title="Show what changed between revisions"></span></span></span></button>`);
    this.fillCard(node, site);
    return node;
  }

  private fillCard(node: HTMLElement, site: Site): void {
    const kind = kindOf(site.source);
    const badge = q(node, '.fp-badge');
    setText(badge, kind);
    setAttr(badge, 'translate', kind === 'FormWeb' ? 'no' : 'yes');
    setText(q(node, '.fp-card-name'), site.name);
    setText(q(node, '.fp-card-routes'), site.routeCount === null ? '-' : routeText(site.routeCount));
    setText(q(node, '.fp-card-time'), relative(site.importedAt));
    setAttr(node, 'title', site.source);
    setText(q(node, '.fp-card-revbtn'), revisionsText(site.revisions));
  }

  private showRevisions(siteId: string): void {
    const site = this.app.state().sites.find((s) => s.id === siteId);
    this.revisions ??= new RevisionsDialog();
    this.revisions.show(siteId, site?.name ?? siteId);
  }

  private async openDemo(card: HTMLElement): Promise<void> {
    if (card.getAttribute('aria-busy') === 'true') return;
    setAttr(card, 'aria-busy', 'true');
    try {
      const { site } = await openSample();
      await this.app.refreshSites();
      await this.app.openSite(site.id);
    } catch (e) {
      emit('fp:notice', { kind: 'error', text: e instanceof Error ? e.message : 'The sample site could not be opened' });
    } finally {
      setAttr(card, 'aria-busy', 'false');
    }
  }

  private restoreNav(): void {
    try {
      const w = localStorage.getItem(NAV_W_KEY);
      if (w && /^\d{3}px$/.test(w.trim())) this.root.style.setProperty('--fp-home-nav-w', w.trim());
      if (localStorage.getItem(NAV_HIDDEN_KEY) === '1') this.root.classList.add('is-nav-hidden');
    } catch { return; }
  }

  private sidePanel(): void {
    const root = this.root;
    const bar = q(root, '.fp-home-resizer');
    const save = (): void => {
      try {
        localStorage.setItem(NAV_W_KEY, root.style.getPropertyValue('--fp-home-nav-w') || '232px');
        localStorage.setItem(NAV_HIDDEN_KEY, root.classList.contains('is-nav-hidden') ? '1' : '0');
      } catch { return; }
    };
    q(root, '.fp-home-nav-hide').addEventListener('click', () => { setClass(root, 'is-nav-hidden', true); save(); });
    q(root, '.fp-home-nav-show').addEventListener('click', () => { setClass(root, 'is-nav-hidden', false); save(); });
    bar.addEventListener('pointerdown', (e) => {
      e.preventDefault();
      const x0 = e.clientX;
      const start = q(root, '.fp-home-nav').getBoundingClientRect().width || 232;
      bar.classList.add('is-dragging');
      const mv = (ev: PointerEvent): void => {
        const raw = start + ev.clientX - x0;
        const collapse = raw < 120;
        if (root.classList.contains('is-nav-hidden') !== collapse) setClass(root, 'is-nav-hidden', collapse);
        if (!collapse) root.style.setProperty('--fp-home-nav-w', `${Math.round(Math.max(180, Math.min(420, raw)))}px`);
      };
      const up = (): void => {
        bar.classList.remove('is-dragging');
        window.removeEventListener('pointermove', mv);
        window.removeEventListener('pointerup', up);
        save();
      };
      window.addEventListener('pointermove', mv);
      window.addEventListener('pointerup', up);
    });
  }

  private wire(): void {
    this.root.addEventListener('click', (e) => {
      const t = e.target as HTMLElement;
      const v = t.closest<HTMLElement>('[data-v]')?.dataset.v as View | undefined;
      if (v) { this.select(v); return; }
      if (t.closest('[data-show]')) { this.paint(true); return; }
      if (t.closest('[data-revs]')) {
        const owner = t.closest<HTMLElement>('[data-site]')?.dataset.site;
        if (owner) this.showRevisions(owner);
        return;
      }
      const demo = t.closest<HTMLElement>('[data-demo]');
      if (demo) { void this.openDemo(demo); return; }
      const cmd = t.closest<HTMLElement>('[data-cmd]')?.dataset.cmd;
      if (cmd) { this.commands.run(cmd); return; }
      const site = t.closest<HTMLElement>('[data-site]')?.dataset.site;
      if (site) { void this.app.openSite(site); return; }
      const open = t.closest<HTMLElement>('[data-open]')?.dataset.open;
      if (open) { void this.app.openSite(open); return; }
      if (t.closest('[data-a="prefs"]')) this.commands.run('app.preferences');
    });
    this.root.addEventListener('keydown', (e) => {
      const chip = (e.target as HTMLElement).closest<HTMLElement>('[data-revs]');
      if (!chip || (e.key !== 'Enter' && e.key !== ' ')) return;
      e.preventDefault();
      e.stopPropagation();
      const owner = chip.closest<HTMLElement>('[data-site]')?.dataset.site;
      if (owner) this.showRevisions(owner);
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.isOpen && !anyDialogOpen() && this.app.state().activeId !== null) { e.preventDefault(); this.hide(); }
    });
    on('fp:sites-changed', () => { this.loaded = true; this.paint(); });
    on('fp:engine-state', ({ state }) => {
      if (state === 'down') this.markLoaded();
      if (this.isOpen) void this.refreshFormWeb();
    });
    on('fp:settings-changed', () => { if (this.isOpen) void this.refreshFormWeb(); });
    on('fp:site-opened', () => { this.paint(); this.hide(); });
    on('fp:site-loaded', () => this.paint());
    on('fp:live', (ev) => { if (ev.type === 'sites.received') void this.app.refreshSites(); });
    on('fp:site-closed', () => {
      this.paint();
      queueMicrotask(() => { if (this.app.state().activeId === null) this.show(); });
    });
  }
}
