import { api, ApiError, connectLive, type LiveEvent, type LiveState, type RouteInfo, type Site } from './api';
import type { App, AppState, BottomTab, EngineState, Mounts, OpenTab, Pane } from './app-api';
import { reserveDock } from './dock-adapter';
import { emit, type NoticeKind } from './events';
import { locale, onLanguage } from './i18n';
import { brandMark } from './ui/brand';
import { pickFormWebProject } from './ui/formweb-picker';
import { inTauri, mountOnce, q,setAttr, setClass, setDisabled, setHidden, setText, setTitle, setValue } from './ui/dom';
import { installHints } from './ui/hint-strip';
import { icon } from './ui/icons';
import { refuse } from './ui/notice-step';
import { openPackageSheet, installPackaging } from './ui/package-sheet';
import { installPanel, panelPagesHtml } from './ui/panel';
import { askPath } from './ui/path-dialog';
import { Preview, routeKey } from './ui/preview';
import { LayoutState } from './ui/resizers';
import { RouteList } from './ui/routes';
import { SiteTabs } from './ui/tabs';
import { applyTheme, nextToggleTheme, readChoice, setTheme } from './ui/themes';
import { Toolbar } from './ui/toolbar';
import { VERSION } from './version';

const TABS_KEY = 'formpublisher.tabs';

const SHELL = `<div class="fp-app">
<header class="fp-titlebar">
<div class="fp-brand" role="button" tabindex="0" title="Home" data-act="home">${brandMark(20)}<span class="fp-brand-name" translate="no">formpublisher</span></div>
<nav class="fp-menubar" aria-label="Main menu"></nav>
<input class="fp-doc-title" value="" readonly aria-label="Site name" placeholder="No site open" spellcheck="false">
<div class="fp-title-tools">
<button class="fp-tt-btn" type="button" data-act="palette" title="Find a Command" aria-label="Find a Command">${icon('commandPalette', 16)}</button>
<button class="fp-tt-btn fp-theme-btn" type="button" data-act="theme" title="Switch theme" aria-label="Switch theme"><span class="fp-theme-to-light">${icon('sun', 16)}</span><span class="fp-theme-to-dark">${icon('moon', 16)}</span></button>
<button class="fp-tt-btn fp-dock-btn" type="button" data-act="dock" title="Agent Dock" aria-label="Agent Dock" aria-pressed="false">${icon('terminal', 16)}</button>
<button class="fp-tt-btn" type="button" data-act="preferences"title="Preferences" aria-label="Preferences">${icon('settings', 16)}</button>
</div>
</header>
<div class="fp-tabs" role="tablist" aria-label="Open sites"></div>
<div class="fp-options"><div class="fp-tb-field">${icon('link', 14)}<input class="fp-route-field" aria-label="Route" title="Route" placeholder="No route selected" spellcheck="false" autocomplete="off"></div></div>
<div class="fp-main">
<aside class="fp-strip-col" aria-label="Routes">
<div class="fp-strip-head"><span class="fp-strip-title">Routes</span><span class="fp-strip-count">0</span></div>
<div class="fp-strip-scroll"><div class="fp-route-list" role="listbox" aria-label="Routes"></div><p class="fp-strip-empty">Open a site to list its routes.</p></div>
</aside>
<div class="fp-resizer" data-edge="strip" role="separator" aria-orientation="vertical"></div>
<div class="fp-stage-col">
<main class="fp-stage">
<div class="fp-stage-layer fp-stage-empty"><div class="fp-empty">
<span class="fp-empty-icon">${icon('globe', 20)}</span>
<div class="fp-empty-title">Open a FormWeb site to see it here</div>
<div class="fp-empty-text">Open a site export or a publication folder, or take the site that is open in FormWeb. FormPublisher reads it and never changes it.</div>
<div class="fp-empty-actions">
<button class="fp-btn fp-btn-primary" type="button" data-act="open-zip">${icon('archive', 14)}<span>Open zip</span></button>
<button class="fp-btn" type="button" data-act="open-folder">${icon('folder', 14)}<span>Open folder</span></button>
<button class="fp-btn" type="button" data-act="import-formweb">${icon('download', 14)}<span>Import from FormWeb</span></button>
</div>
<div class="fp-empty-result" role="status" aria-live="polite"></div>
</div></div>
</main>
<section class="fp-bottom" aria-label="Panel">
<div class="fp-bottom-head" role="tablist" aria-label="Panel">
<button class="fp-bottom-tab" type="button" role="tab" aria-selected="true" data-tab="problems" title="Problems">${icon('alert', 14)}<span>Problems</span></button>
<button class="fp-bottom-tab" type="button" role="tab" aria-selected="false" data-tab="console" title="Console">${icon('terminal', 14)}<span>Console</span></button>
<button class="fp-bottom-tab" type="button" role="tab" aria-selected="false" data-tab="network" title="Network">${icon('globe', 14)}<span>Network</span></button>
<button class="fp-bottom-tab" type="button" role="tab" aria-selected="false" data-tab="revisions" title="Revisions">${icon('archive', 14)}<span>Revisions</span></button>
<button class="fp-icon-btn is-sm" type="button" data-act="toggle-bottom" title="Hide the panel" aria-label="Hide the panel">${icon('chevronDown', 14)}</button>
</div>
<div class="fp-bottom-body">
${panelPagesHtml()}
<div class="fp-bottom-page" data-page="revisions" role="tabpanel" hidden></div>
</div>
</section>
</div>
<div class="fp-resizer" data-edge="props" role="separator" aria-orientation="vertical"></div>
<aside class="fp-props-col" aria-label="Inspector">
<section class="fp-group" data-group="site">
<div class="fp-group-head"><span class="fp-group-title">Site</span></div>
<div class="fp-group-body">
<div class="fp-prop-row"><span class="fp-prop-label">Name</span><span class="fp-prop-value" data-field="name" translate="no">-</span></div>
<div class="fp-prop-row"><span class="fp-prop-label">Source</span><span class="fp-prop-value" data-field="source" translate="no">-</span></div>
<div class="fp-prop-row"><span class="fp-prop-label">Imported</span><span class="fp-prop-value" data-field="imported" translate="no">-</span></div>
<div class="fp-prop-row"><span class="fp-prop-label">Routes</span><span class="fp-prop-value is-mono" data-field="routes" translate="no">-</span></div>
<div class="fp-prop-row"><span class="fp-prop-label">Size</span><span class="fp-prop-value is-mono" data-field="size" translate="no">-</span></div>
</div>
</section>
</aside>
<button class="fp-props-hide fp-icon-btn is-sm" type="button" data-act="hide-props" title="Hide the inspector" aria-label="Hide the inspector">${icon('chevronRight', 14)}</button>
<button class="fp-props-tab" type="button" data-act="show-props" title="Show the inspector" aria-label="Show the inspector">${icon('chevronLeft', 14)}</button>
<button class="fp-strip-hide fp-icon-btn is-sm" type="button" data-act="hide-strip" title="Hide the routes" aria-label="Hide the routes">${icon('chevronLeft', 14)}</button>
<button class="fp-strip-tab" type="button" data-act="show-strip" title="Show the routes" aria-label="Show the routes">${icon('chevronRight', 14)}</button>
</div>
<footer class="fp-status">
<div class="fp-status-left"><span class="fp-st fp-st-engine"><span class="fp-st-dot"></span><span class="fp-st-engine-text">Checking the engine</span></span><span class="fp-st fp-st-routes">0 routes</span></div>
<div class="fp-status-right"><button class="fp-icon-btn is-sm" type="button" data-act="toggle-bottom" title="Show or hide the panel" aria-label="Show or hide the panel">${icon('terminal', 14)}</button><span class="fp-st fp-st-version" translate="no">v${VERSION}</span></div>
</footer>
<input class="fp-file-input" type="file" accept=".zip,.fweb,.fpub,application/zip" hidden tabindex="-1" aria-hidden="true">
</div>`;

let instance: App | null = null;

export function getApp(): App {
  if (!instance) throw new Error('the app has not started');
  return instance;
}

interface SavedTabs { open: OpenTab[]; active: string | null }

function loadTabs(): SavedTabs {
  try {
    const raw = JSON.parse(localStorage.getItem(TABS_KEY) || '{}') as Partial<SavedTabs>;
    const open = Array.isArray(raw.open) ? raw.open.filter((t): t is OpenTab => !!t && typeof t.id === 'string' && typeof t.name === 'string') : [];
    const active = typeof raw.active === 'string' && open.some((t) => t.id === raw.active) ? raw.active : null;
    return { open, active };
  } catch {
    return { open: [], active: null };
  }
}

function formatSize(bytes: number | null): string {
  if (bytes === null) return '-';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

function formatDate(iso: string): string {
  if (!iso) return '-';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  try {
    return new Intl.DateTimeFormat(locale(), { dateStyle: 'medium', timeStyle: 'short' }).format(d);
  } catch {
    return iso;
  }
}

const routeCountText = (n: number): string => (n === 1 ? '1 route' : `${n} routes`);

export async function startApp(): Promise<App> {
  applyTheme();
  reserveDock();
  const host = document.getElementById('app') as HTMLElement;
  mountOnce(host, SHELL);
  const root = q(host, '.fp-app');
  const overlay = q(document, '#overlay-root');
  const toastRoot = q(document, '#toast-root');

  const mounts: Mounts = {
    root,
    titlebar: q(root, '.fp-titlebar'),
    menubar: q(root, '.fp-menubar'),
    titleTools: q(root, '.fp-title-tools'),
    tabs: q(root, '.fp-tabs'),
    options: q(root, '.fp-options'),
    main: q(root, '.fp-main'),
    strip: q(root, '.fp-strip-col'),
    stage: q(root, '.fp-stage'),
    bottom: q(root, '.fp-bottom'),
    inspector: q(root, '.fp-props-col'),
    statusLeft: q(root, '.fp-status-left'),
    statusRight: q(root, '.fp-status-right'),
    overlay,
    toast: toastRoot,
  };

  const docTitle = q<HTMLInputElement>(root, '.fp-doc-title');
  if (document.documentElement.classList.contains('has-overlay-titlebar')) {
    for (const part of [mounts.titlebar, mounts.menubar, mounts.titleTools, docTitle]) part.setAttribute('data-tauri-drag-region', '');
  }
  const stripCount = q(root, '.fp-strip-count');
  const stripEmpty = q(root, '.fp-strip-empty');
  const stageEmpty = q(root, '.fp-stage-empty');
  const emptyResult = q(root, '.fp-empty-result');
  const fileInput = q<HTMLInputElement>(root, '.fp-file-input');
  const engineDot = q(root, '.fp-st-engine .fp-st-dot');
  const engineText = q(root, '.fp-st-engine-text');
  const routesStatus = q(root, '.fp-st-routes');
  const importButtons = Array.from(root.querySelectorAll<HTMLButtonElement>('[data-act="open-zip"], [data-act="open-folder"], [data-act="import-formweb"]'));
  const field = (name: string): HTMLElement => q(root, `[data-field="${name}"]`);
  const bottomTabs = Array.from(root.querySelectorAll<HTMLElement>('.fp-bottom-tab'));
  const bottomPages = Array.from(root.querySelectorAll<HTMLElement>('.fp-bottom-page'));

  const layout = new LayoutState(root);
  layout.install(Array.from(root.querySelectorAll<HTMLElement>('.fp-resizer')));

  const saved = loadTabs();
  const st = {
    sites: [] as Site[],
    open: saved.open,
    activeId: saved.active,
    site: null as Site | null,
    routes: [] as RouteInfo[],
    route: null as string | null,
    engine: 'unknown' as EngineState,
    engineVersion: '',
    loading: false,
  };
  let loadSeq = 0;
  let busy = false;

  const persist = (): void => {
    try { localStorage.setItem(TABS_KEY, JSON.stringify({ open: st.open, active: st.activeId })); } catch { return; }
  };

  const notice = (kind: NoticeKind, text: string): void => { emit('fp:notice', { kind, text }); };

  const showResult = (kind: NoticeKind, text: string): void => {
    setText(emptyResult, text);
    setClass(emptyResult, 'is-error', kind === 'error');
    setClass(emptyResult, 'is-ok', kind === 'ok');
  };

  const tabStrip = new SiteTabs(mounts.tabs, {
    activate: (id) => { if (id !== st.activeId) void openSite(id); },
    close: (id) => closeSite(id),
    add: () => { if (emit('fp:new-tab', {}, true)) deactivate(); },
  });

  const routeList = new RouteList(q(root, '.fp-route-list'), { select: (path) => selectRoute(path) });

  const toolbar: Toolbar = new Toolbar(mounts.options, {
    navigate: (path) => preview.navigate(path),
    reload: () => preview.reload(),
    openBrowser: () => preview.openInBrowser(),
    packageSite: () => openPackageSheet(app),
    change: (state, kind) => { if (kind === 'view') preview.setView(state); else preview.setOptions(state); },
  });

  const preview: Preview = new Preview(mounts.stage, {
    path: (path, source) => {
      toolbar.setRoute(path);
      if (source !== 'frame') return;
      const key = routeKey(path);
      const hit = st.routes.find((r) => r.path === path) ?? st.routes.find((r) => routeKey(r.path) === key);
      if (hit) selectRoute(hit.path);
    },
    error: (text) => notice('error', text),
  }, toolbar.current());

  const activeName = (): string => st.site?.name ?? st.open.find((t) => t.id === st.activeId)?.name ?? '';

  const paintTabs = (): void => {
    tabStrip.render(st.open.map((t) => ({ id: t.id, title: t.name, active: t.id === st.activeId })));
  };

  const paintSite = (): void => {
    const has = st.activeId !== null;
    const name = activeName();
    setValue(docTitle, name);
    setHidden(stageEmpty, has);
    preview.setVisible(has);
    toolbar.setActive(has);
    preview.show(st.activeId, st.route);
    setText(field('name'), name || '-');
    setText(field('source'), st.site?.source || '-');
    setText(field('imported'), st.site ? formatDate(st.site.importedAt) : '-');
    const count = st.site?.routeCount ?? (st.activeId !== null && !st.loading ? st.routes.length : null);
    setText(field('routes'), count === null ? '-' : String(count));
    setText(field('size'), st.site ? formatSize(st.site.size) : '-');
  };

  onLanguage(() => { setText(field('imported'), st.site ? formatDate(st.site.importedAt) : '-'); });

  const paintRoutes = (): void => {
    routeList.setSite(st.activeId);
    routeList.render(st.routes, st.route);
    setText(stripCount, String(st.routes.length));
    const message = st.activeId === null ? 'Open a site to list its routes.' : st.routes.length > 0 ? '' : st.loading ? 'Loading routes' : 'This site has no routes.';
    setText(stripEmpty, message);
    setHidden(stripEmpty, message === '');
    setText(routesStatus, routeCountText(st.routes.length));
  };

  const paintEngine = (): void => {
    setClass(engineDot, 'is-ok', st.engine === 'ok');
    setClass(engineDot, 'is-error', st.engine === 'down');
    setText(engineText, st.engine === 'ok' ? 'Engine ready' : st.engine === 'down' ? 'Engine not reachable' : 'Checking the engine');
    setTitle(q(root, '.fp-st-engine'), st.engineVersion ? `Engine ${st.engineVersion}` : '');
  };

  const paintBusy = (): void => {
    for (const b of importButtons) setDisabled(b, busy);
  };

  const paintAll = (): void => {
    paintTabs();
    paintSite();
    paintRoutes();
    paintEngine();
    paintBusy();
  };

  const setEngine = (state: EngineState, version = st.engineVersion): void => {
    if (st.engine === state && st.engineVersion === version) return;
    const changed = st.engine !== state;
    st.engine = state;
    st.engineVersion = version;
    paintEngine();
    if (changed) emit('fp:engine-state', { state });
  };

  async function checkHealth(): Promise<void> {
    try {
      const h = await api.health();
      setEngine(h.ok ? 'ok' : 'down', h.version);
    } catch {
      setEngine('down');
    }
  }

  function selectRoute(path: string): void {
    if (!st.routes.some((r) => r.path === path) || st.route === path || st.activeId === null) return;
    st.route = path;
    paintSite();
    paintRoutes();
    emit('fp:route-selected', { siteId: st.activeId, path });
  }

  async function load(id: string): Promise<void> {
    const seq = ++loadSeq;
    st.loading = true;
    paintRoutes();
    try {
      const [site, routes] = await Promise.all([api.site(id), api.routes(id)]);
      if (seq !== loadSeq || st.activeId !== id) return;
      st.site = site;
      st.routes = routes;
      st.route = routes.find((r) => r.path === st.route)?.path ?? routes.find((r) => r.path === '/')?.path ?? routes[0]?.path ?? null;
      const tab = st.open.find((t) => t.id === id);
      if (tab && tab.name !== site.name) { tab.name = site.name; persist(); }
      st.loading = false;
      paintAll();
      emit('fp:site-loaded', { id });
    } catch (e) {
      if (seq !== loadSeq || st.activeId !== id) return;
      st.loading = false;
      if (e instanceof ApiError && e.status === 404) {
        closeSite(id);
        notice('error', 'That site is no longer available.');
        return;
      }
      st.routes = [];
      st.route = null;
      paintAll();
      if (e instanceof ApiError && e.status === 0) setEngine('down');
      notice('error', e instanceof Error ? e.message : 'Could not load the site');
    }
  }

  async function openSite(id: string): Promise<void> {
    const known = st.sites.find((s) => s.id === id);
    if (!st.open.some((t) => t.id === id)) st.open.push({ id, name: known?.name ?? id });
    const same = st.activeId === id;
    st.activeId = id;
    st.site = known ?? null;
    if (!same) {
      st.routes = [];
      st.route = null;
    }
    persist();
    showResult('info', '');
    paintAll();
    emit('fp:site-opened', { id });
    await load(id);
  }

  function deactivate(): void {
    loadSeq += 1;
    st.activeId = null;
    st.site = null;
    st.routes = [];
    st.route = null;
    st.loading = false;
    persist();
    paintAll();
  }

  function closeSite(id: string): void {
    const at = st.open.findIndex((t) => t.id === id);
    if (at < 0) return;
    st.open.splice(at, 1);
    emit('fp:site-closed', { id });
    if (st.activeId === id) {
      const next = st.open[at] ?? st.open[at - 1];
      if (next) { void openSite(next.id); return; }
      deactivate();
      return;
    }
    persist();
    paintTabs();
  }

  async function refreshSites(): Promise<void> {
    try {
      const list = await api.sites();
      st.sites = list;
      let changed = false;
      for (const tab of st.open) {
        const s = list.find((x) => x.id === tab.id);
        if (s && s.name !== tab.name) { tab.name = s.name; changed = true; }
      }
      const gone = st.open.filter((t) => !list.some((s) => s.id === t.id));
      for (const t of gone) closeSite(t.id);
      if (changed) { persist(); paintAll(); }
      emit('fp:sites-changed', {});
    } catch (e) {
      if (e instanceof ApiError && e.status === 0) setEngine('down');
    }
  }

  async function flow(run: () => Promise<Site | null>, fallback: string): Promise<Site | null> {
    if (busy) return null;
    busy = true;
    paintBusy();
    showResult('info', 'Importing');
    try {
      const site = await run();
      await refreshSites();
      if (site) {
        await openSite(site.id);
        notice('ok', site.revisions > 1 ? `Added a revision to ${site.name}` : `Imported ${site.name}`);
      } else {
        showResult('ok', fallback);
        notice('ok', fallback);
      }
      return site;
    } catch (e) {
      const text = e instanceof Error ? e.message : 'The import failed';
      showResult('error', text);
      refuse(e, text, undefined, () => { void flow(run, fallback); });
      if (e instanceof ApiError && e.status === 0) setEngine('down');
      return null;
    } finally {
      busy = false;
      paintBusy();
    }
  }

  const importZip = async (file: File): Promise<Site> => {
    const site = await flow(() => api.importZip(file), 'The site was imported.');
    if (!site) throw new Error('The import did not finish');
    return site;
  };

  const importFolder = async (path: string): Promise<Site> => {
    const site = await flow(() => api.importPath(path), 'The site was imported.');
    if (!site) throw new Error('The import did not finish');
    return site;
  };

  const importFromFormWeb = async (): Promise<Site | null> => {
    if (busy) return null;
    const picked = await pickFormWebProject(() => api.formwebProjects().catch(() => []));
    if (picked === undefined) return null;
    const project = picked;
    return flow(async () => (await api.formwebImportCurrent(project)).site, 'FormWeb import finished.');
  };

  const nativeFolder = async (): Promise<string | null | undefined> => {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      const picked = await invoke<string | string[] | null>('plugin:dialog|open', { options: { directory: true, multiple: false, title: 'Open Folder' } });
      if (Array.isArray(picked)) return picked[0] ?? null;
      return picked ?? null;
    } catch {
      return undefined;
    }
  };

  const pickFolder = (): Promise<string | null> => new Promise((resolve) => {
    if (inTauri()) {
      void nativeFolder().then((path) => {
        if (path !== undefined) resolve(path);
        else void askPath(overlay).then(resolve);
      });
      return;
    }
    const handled = !emit('fp:pick-folder', { resolve }, true);
    if (!handled) void askPath(overlay).then(resolve);
  });

  const pickZip = (): void => { fileInput.click(); };

  fileInput.addEventListener('change', () => {
    const file = fileInput.files?.[0];
    fileInput.value = '';
    if (file) void flow(() => api.importZip(file), 'The site was imported.');
  });

  function togglePane(pane: Pane, force?: boolean): void {
    const hide = force === undefined ? !layout.isHidden(pane) : !force;
    layout.setHidden(pane, hide);
  }

  function showBottomTab(tab: BottomTab): void {
    for (const b of bottomTabs) setAttr(b, 'aria-selected', String(b.dataset.tab === tab));
    for (const p of bottomPages) setHidden(p, p.dataset.page !== tab);
    layout.setHidden('bottom', false);
  }

  root.addEventListener('click', (e) => {
    const target = e.target as HTMLElement;
    const tab = target.closest<HTMLElement>('.fp-bottom-tab');
    if (tab?.dataset.tab) { showBottomTab(tab.dataset.tab as BottomTab); return; }
    const act = target.closest<HTMLElement>('[data-act]')?.dataset.act;
    if (!act) return;
    switch (act) {
      case 'home': emit('fp:home', {}); break;
      case 'palette': emit('fp:palette', { source: 'titlebar' }); break;
      case 'preferences': emit('fp:preferences', { source: 'titlebar' }); break;
      case 'theme': {
        const from = readChoice().theme;
        const to = nextToggleTheme(from);
        if (emit('fp:theme-toggle', { from, to }, true)) setTheme(to);
        break;
      }
      case 'open-zip': pickZip(); break;
      case 'open-folder': void pickFolder().then((path) => { if (path) void flow(() => api.importPath(path), 'The site was imported.'); }); break;
      case 'import-formweb': void importFromFormWeb(); break;
      case 'hide-props': togglePane('props', false); break;
      case 'show-props': togglePane('props', true); break;
      case 'hide-strip': togglePane('strip', false); break;
      case 'show-strip': togglePane('strip', true); break;
      case 'toggle-bottom': togglePane('bottom'); break;
      default: break;
    }
  });

  q(root, '.fp-brand').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); emit('fp:home', {}); }
  });

  const onLive = (event: LiveEvent): void => {
    emit('fp:live', event);
    if (event.type === 'site.imported') {
      void refreshSites().then(() => { if (typeof event.id === 'string' && event.id === st.activeId) void load(event.id).then(() => preview.reload()); });
    } else if (event.type === 'site.removed') {
      if (typeof event.id === 'string') closeSite(event.id);
      void refreshSites();
    } else if (event.type === 'settings.changed') {
      emit('fp:settings-changed', {});
    }
  };

  const onLiveState = (state: LiveState): void => {
    if (state === 'open') void checkHealth().then(() => refreshSites());
    else if (state === 'closed') setEngine('down');
  };

  paintAll();

  const first = Promise.all([checkHealth(), refreshSites()]).then(async () => {
    if (st.activeId !== null && st.open.some((t) => t.id === st.activeId)) await load(st.activeId);
  }).then(() => undefined, () => undefined);

  const app: App = {
    mounts,
    ready: first,
    state: (): AppState => ({
      sites: st.sites,
      open: st.open,
      activeId: st.activeId,
      site: st.site,
      routes: st.routes,
      route: st.route,
      engine: st.engine,
      engineVersion: st.engineVersion,
    }),
    openSite,
    closeSite,
    deactivate,
    selectRoute,
    refreshSites,
    importZip,
    importFolder,
    importFromFormWeb,
    pickZip,
    pickFolder,
    togglePane,
    showBottomTab,
    preview: () => ({ navigate: (path) => preview.navigate(path), reload: () => preview.reload() }),
  };

  connectLive(onLive, onLiveState);
  instance = app;
  installPanel(app);
  installPackaging(app);
  installHints(app);
  return app;
}
