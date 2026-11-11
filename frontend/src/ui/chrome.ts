import '../styles/overlays.css';
import { api } from '../api';
import type { App } from '../app-api';
import { emit, on } from '../events';
import { CommandPalette } from './command-palette';
import { Commands, installShortcuts } from './commands';
import { confirmAction } from './dialogs';
import { inTauri } from './dom';
import { setLibraryOpener } from './builds';
import { Home } from './home';
import './icons-extra';
import { MenuBar, type MenuDef } from './menu';
import { stepFor, type StepHost } from './notice-step';
import { NativeMenus, wantsNativeMenus } from './native-menu';
import { openPackageSheet } from './package-sheet';
import { runChecks } from './panel';
import { Preferences, type PrefsSection } from './preferences';
import { ShortcutsDialog } from './shortcuts-dialog';
import { applyDensity, nextToggleTheme, readChoice, readDensity, setTheme, THEMES, type Density } from './themes';
import { toast } from './toast';

export const DOCS_URL = 'https://github.com/nodemode-dev/formpublisher/blob/main/docs/MANUAL.md';

export interface Chrome {
  readonly commands: Commands;
  readonly home: Home;
}

const editable = (): boolean => {
  const a = document.activeElement;
  return a instanceof HTMLInputElement || a instanceof HTMLTextAreaElement || (a instanceof HTMLElement && a.isContentEditable);
};

const hasSelection = (): boolean => {
  const a = document.activeElement;
  if (a instanceof HTMLInputElement || a instanceof HTMLTextAreaElement) return (a.selectionStart ?? 0) !== (a.selectionEnd ?? 0);
  return (window.getSelection()?.toString() ?? '') !== '';
};

async function openExternal(target: string): Promise<void> {
  if (inTauri()) {
    const { invoke } = await import('@tauri-apps/api/core');
    await invoke('plugin:shell|open', { path: target });
    return;
  }
  window.open(target, '_blank', 'noopener');
}

export function installChrome(app: App): Chrome {
  const commands = new Commands();
  const notice = (kind: 'info' | 'ok' | 'error', text: string): void => { emit('fp:notice', { kind, text }); };
  const st = () => app.state();
  const hasSite = (): boolean => st().activeId !== null;
  const engineUp = (): boolean => st().engine !== 'down';
  const shown = (cls: string): boolean => !app.mounts.root.classList.contains(cls);
  const siteName = (): string => st().site?.name ?? st().open.find((t) => t.id === st().activeId)?.name ?? '';

  const home = new Home(app, commands, app.state().activeId === null);
  setLibraryOpener((id) => { void home.revealBuild(id); });
  let palette: CommandPalette | null = null;
  let prefs: Preferences | null = null;
  let shortcuts: ShortcutsDialog | null = null;

  const density = (id: string, label: string, value: Density, keys?: string[]) => ({
    id: `view.density-${id}`,
    label,
    keys,
    icon: 'density',
    group: 'View',
    menu: 'View',
    description: `Use the ${id} density for bars and controls`,
    checked: (): boolean => readDensity() === value,
    run: (): void => { applyDensity(value); emit('fp:ui-settings-changed', { key: 'density' }); },
  });

  const pane = (id: string, label: string, ic: string, keys: string[] | undefined, cls: string, which: 'strip' | 'props' | 'bottom', description: string) => ({
    id,
    label,
    keys,
    icon: ic,
    group: 'View',
    menu: 'View',
    description,
    checked: (): boolean => shown(cls),
    run: (): void => app.togglePane(which),
  });

  const tab = (id: string, label: string, ic: string, which: 'problems' | 'console' | 'network') => ({
    id,
    label,
    icon: ic,
    group: 'View',
    menu: 'View',
    description: `Show the ${which} tab of the bottom panel`,
    run: (): void => app.showBottomTab(which),
  });

  commands.add(
    { id: 'file.open-zip', label: 'Open Zip...', keys: ['Mod+O'], icon: 'archive', group: 'File', menu: 'File', description: 'Import a FormWeb site export (.zip), project (.fweb) or package (.fpub)', mutates: true, enabled: engineUp, run: () => app.pickZip() },
    {
      id: 'file.open-folder', label: 'Open Folder...', keys: ['Shift+Mod+O'], icon: 'folder', group: 'File', menu: 'File', description: 'Import a publication folder', mutates: true, enabled: engineUp,
      run: async () => {
        const path = await app.pickFolder();
        if (path) await app.importFolder(path).catch(() => undefined);
      },
    },
    { id: 'file.import-formweb', label: 'Import from FormWeb...', icon: 'download', group: 'File', menu: 'File', description: 'Import the site that is open in FormWeb', mutates: true, enabled: engineUp, run: async () => { await app.importFromFormWeb(); } },
    { id: 'file.new-window', label: 'New Window', keys: ['Shift+Mod+N'], icon: 'newWindow', group: 'File', menu: 'File', description: 'Open another FormPublisher window',
      run: async () => {
        if (!inTauri()) { window.open(window.location.href, '_blank'); return; }
        const { invoke } = await import('@tauri-apps/api/core');
        await invoke('open_window', { path: '/', title: 'FormPublisher' });
      } },
    { id: 'file.close-tab', label: 'Close Tab', keys: ['Mod+W'], icon: 'close', group: 'File', menu: 'File', description: 'Close the open site tab', enabled: hasSite, run: () => { const id = st().activeId; if (id) app.closeSite(id); } },

    { id: 'edit.undo', label: 'Undo', keys: ['Mod+Z'], icon: 'undo', group: 'Edit', menu: 'Edit', description: 'Undo in the focused field', native: true, enabled: editable, run: () => document.execCommand('undo') },
    { id: 'edit.redo', label: 'Redo', keys: ['Shift+Mod+Z'], icon: 'redo', group: 'Edit', menu: 'Edit', description: 'Redo in the focused field', native: true, enabled: editable, run: () => document.execCommand('redo') },
    { id: 'edit.cut', label: 'Cut', keys: ['Mod+X'], icon: 'cut', group: 'Edit', menu: 'Edit', description: 'Cut the selected text', native: true, enabled: () => editable() && hasSelection(), run: () => document.execCommand('cut') },
    { id: 'edit.copy', label: 'Copy', keys: ['Mod+C'], icon: 'copy', group: 'Edit', menu: 'Edit', description: 'Copy the selected text', native: true, enabled: hasSelection, run: () => document.execCommand('copy') },
    {
      id: 'edit.paste', label: 'Paste', keys: ['Mod+V'], icon: 'paste', group: 'Edit', menu: 'Edit', description: 'Paste text from the clipboard', native: true, enabled: editable,
      run: async () => {
        const text = await navigator.clipboard.readText();
        if (text) document.execCommand('insertText', false, text);
      },
    },
    {
      id: 'edit.select-all', label: 'Select All', keys: ['Mod+A'], icon: 'selectAll', group: 'Edit', menu: 'Edit', description: 'Select all text in the focused field', native: true,
      run: () => {
        const a = document.activeElement;
        if (a instanceof HTMLInputElement || a instanceof HTMLTextAreaElement) a.select();
        else document.execCommand('selectAll');
      },
    },

    { id: 'view.home', label: 'Home', keys: ['Alt+Mod+H'], icon: 'home', group: 'View', menu: 'View', description: 'Show the Home page', run: () => home.show('start') },
    { id: 'view.builds', label: 'Builds', icon: 'package', group: 'View', menu: 'View', description: 'Show the library of builds on the Home page', run: () => home.show('builds') },
    { id: 'view.palette', label: 'Find a Command...', keys: ['Shift+Mod+P'], icon: 'commandPalette', group: 'View', menu: 'View', description: 'Search every command', run: () => { palette ??= new CommandPalette(commands); palette.show(); } },
    { id: 'view.theme', label: 'Toggle Theme', icon: 'sun', group: 'View', menu: 'View', description: 'Switch between the dark and light theme',
      run: (params) => {
        const to = typeof params?.to === 'string' && THEMES[params.to] ? params.to : nextToggleTheme(readChoice().theme);
        setTheme(to);
      } },
    density('compact', 'Compact', 'compact'),
    density('regular', 'Regular', 'standard'),
    density('comfortable', 'Comfortable', 'comfortable'),
    pane('view.toggle-routes', 'Routes', 'panelLeft', ['Mod+['], 'is-strip-hidden', 'strip', 'Show or hide the routes list'),
    pane('view.toggle-inspector', 'Inspector', 'panelRight', ['Mod+]'], 'is-props-hidden', 'props', 'Show or hide the inspector'),
    pane('view.toggle-bottom', 'Bottom Panel', 'panelBottom', undefined, 'is-bottom-hidden', 'bottom', 'Show or hide the bottom panel'),
    tab('view.problems', 'Problems', 'alert', 'problems'),
    tab('view.console', 'Console', 'terminal', 'console'),
    tab('view.network', 'Network', 'globe', 'network'),

    { id: 'site.package', label: 'Package Site...', keys: ['Shift+Mod+B'], icon: 'package', group: 'Site', menu: 'File', description: 'Build, sign and verify a package of the open site', enabled: () => hasSite() && engineUp(), run: () => openPackageSheet(app) },
    { id: 'publish.open', label: 'Publish Site...', icon: 'publish', group: 'Site', menu: 'File', description: 'Prepare a folder and the commands for each host', enabled: () => hasSite() && engineUp(), run: () => { emit('fp:publish', { source: 'palette' }); } },
    { id: 'site.check', label: 'Run Checks', icon: 'check', group: 'Site', menu: 'Site', description: 'Run the static checks on the open site', enabled: () => hasSite() && engineUp(), run: () => runChecks(app, false) },
    { id: 'site.check-deep', label: 'Run Deep Checks', icon: 'check', group: 'Site', menu: 'Site', description: 'Run the static and deep checks in a headless browser', enabled: () => hasSite() && engineUp(), run: () => runChecks(app, true) },
    {
      id: 'site.reload-routes', label: 'Reload Routes', keys: ['Mod+R'], icon: 'reload', group: 'Site', menu: 'Site', description: 'Read the routes of the open site again', enabled: () => hasSite() && engineUp(),
      run: async () => {
        const id = st().activeId;
        if (!id) return;
        let done = false;
        const off = on('fp:site-loaded', (d) => { if (d.id === id) done = true; });
        await app.openSite(id);
        off();
        if (done) notice('ok', 'Routes reloaded');
      },
    },
    {
      id: 'site.remove', label: 'Remove Site...', icon: 'trash', group: 'Site', menu: 'Site', description: 'Move the open site to the trash folder', mutates: true, risky: true, enabled: () => hasSite() && engineUp(),
      run: async () => {
        const id = st().activeId;
        if (!id) return;
        const name = siteName() || id;
        if (!(await confirmAction('Remove Site', `Move ${name} to the trash? The site stays in the trash folder of the data folder.`, 'Move to Trash', true))) return;
        await api.removeSite(id);
        await app.refreshSites();
        notice('ok', `Moved ${name} to the trash`);
      },
    },
    {
      id: 'site.reveal-folder', label: 'Reveal Site Folder', icon: 'folder', group: 'Site', menu: 'Site', description: 'Show the open site in the file manager', enabled: () => inTauri() && hasSite(),
      run: async () => {
        const id = st().activeId;
        if (!id) return;
        const dir = String((await api.settings()).home ?? '');
        if (!dir) throw new Error('The data folder is not known');
        const sep = dir.includes('\\') ? '\\' : '/';
        const { invoke } = await import('@tauri-apps/api/core');
        try {
          await invoke('reveal_path', { path: [dir.replace(/[\\/]+$/, ''), 'sites', id].join(sep) });
        } catch (e) {
          throw new Error(typeof e === 'string' ? e : e instanceof Error ? e.message : 'The folder could not be shown');
        }
      },
    },

    { id: 'app.preferences', label: 'Preferences...', keys: ['Mod+,'], icon: 'settings', group: 'App', menu: 'File', description: 'Open Preferences', run: (params) => { prefs ??= new Preferences(app); prefs.show(typeof params?.section === 'string' ? (params.section as PrefsSection) : undefined); } },

    { id: 'help.shortcuts', label: 'Keyboard Shortcuts', keys: ['Mod+/'], icon: 'keyboard', group: 'Help', menu: 'Help', description: 'List every command with its keys', run: () => { shortcuts ??= new ShortcutsDialog(commands); shortcuts.show(); } },
    { id: 'help.about', label: 'About formpublisher', icon: 'info', group: 'Help', menu: 'Help', description: 'Version, license and copyright', run: () => commands.run('app.preferences', { section: 'about' }) },
    { id: 'help.docs', label: 'Documentation', icon: 'book', group: 'Help', menu: 'Help', description: 'Open the manual on GitHub', run: () => openExternal(DOCS_URL) },
  );

  commands.onError = (_cmd, error) => notice('error', error instanceof Error && error.message ? error.message : 'Request failed');

  const menuDefs = (native: boolean): MenuDef[] => [
    { label: 'File', items: ['file.open-zip', 'file.open-folder', 'file.import-formweb', '-', 'file.new-window', 'file.close-tab', '-', 'site.package', 'publish.open', ...(native ? [] : ['-', 'app.preferences'])] },
    { label: 'Edit', items: ['edit.undo', 'edit.redo', '-', 'edit.cut', 'edit.copy', 'edit.paste', 'edit.select-all'] },
    { label: 'View', items: ['view.home', 'view.builds', 'view.palette', '-', 'view.theme', { label: 'Density', items: ['view.density-compact', 'view.density-regular', 'view.density-comfortable'] }, '-', 'view.toggle-routes', 'view.toggle-inspector', 'view.toggle-bottom', '-', 'view.problems', 'view.console', 'view.network'] },
    { label: 'Site', items: ['site.check', 'site.check-deep', '-', 'site.reload-routes', 'site.reveal-folder', '-', 'site.remove'] },
    { label: 'Help', items: ['help.shortcuts', 'help.docs', '-', 'help.about'] },
  ];

  const inWindow = (): void => { new MenuBar(app.mounts.menubar, commands, menuDefs(false)); };
  if (wantsNativeMenus()) {
    new NativeMenus(commands, () => menuDefs(true), 'app.preferences').build().catch(() => {
      document.documentElement.classList.remove('has-native-menus');
      inWindow();
    });
  } else {
    inWindow();
  }

  installShortcuts(commands);

  on('fp:palette', () => { commands.run('view.palette'); });
  on('fp:preferences', () => { commands.run('app.preferences'); });
  on('fp:home', () => { commands.run('view.home'); });
  on('fp:theme-toggle', (detail, ev) => { ev.preventDefault(); commands.run('view.theme', { to: detail.to }); });
  on('fp:new-tab', (_d, ev) => { ev.preventDefault(); home.show('start'); });
  const stepHost: StepHost = {
    openTrash: () => {
      document.querySelectorAll<HTMLElement>('#overlay-root .fp-scrim:not([hidden]) [data-close]').forEach((b) => b.click());
      home.show('trash');
    },
    showCheck: () => app.showBottomTab('problems'),
    openManual: () => { void openExternal(`${DOCS_URL}#error-codes`); },
    refreshSites: () => app.refreshSites(),
  };
  on('fp:notice', ({ kind, text, code, ref, run }) => {
    if (kind !== 'error' || !code) { toast(text, kind); return; }
    void stepFor(code, ref, run, stepHost).then((action) => { toast(text, kind, action); });
  });

  const hasFiles = (e: DragEvent): boolean => !!e.dataTransfer && Array.from(e.dataTransfer.types).includes('Files');
  document.addEventListener('dragover', (e) => {
    if (!hasFiles(e)) return;
    e.preventDefault();
    if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy';
    home.setDragOver(home.heroContains(e.target));
  });
  document.addEventListener('dragleave', (e) => { if (!e.relatedTarget) home.setDragOver(false); });
  document.addEventListener('drop', (e) => {
    if (!hasFiles(e)) return;
    e.preventDefault();
    home.setDragOver(false);
    const zips = Array.from(e.dataTransfer?.files ?? []).filter((f) => /\.(zip|fweb|fpub)$/i.test(f.name));
    if (!zips.length) { notice('error', 'Only .zip site exports, .fweb projects or .fpub packages can be imported by dropping.'); return; }
    void (async () => {
      for (const file of zips) {
        try { await app.importZip(file); } catch { continue; }
      }
    })();
  });

  return { commands, home };
}
