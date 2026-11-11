import { api } from '../api';
import type { App } from '../app-api';
import { emit, on } from '../events';
import { LANGUAGES, setLanguage, storedLanguage } from '../i18n';
import { VERSION } from '../version';
import { Dialog } from './dialogs';
import { el, escapeHtml, q, setAttr, setClass, setDisabled, setText, setValue } from './dom';
import { icon } from './icons';
import { applyDensity, applyTheme, readChoice, readDensity, saveChoice, setAccent, setTheme, THEMES, type Density } from './themes';

export type PrefsSection = 'general' | 'interface' | 'formweb' | 'about';

const SECTIONS: Array<[PrefsSection, string, string]> = [
  ['general', 'General', 'settings'],
  ['interface', 'Interface', 'sun'],
  ['formweb', 'FormWeb', 'link'],
  ['about', 'About', 'info'],
];

const ACCENTS = ['#f97316', '#ef4444', '#eab308', '#22c55e', '#14b8a6', '#3b82f6', '#8b5cf6', '#ec4899'];
const DENSITIES: Array<[Density, string]> = [['compact', 'Compact'], ['standard', 'Regular'], ['comfortable', 'Comfortable']];

const swatch = (id: string): string => {
  const p = THEMES[id];
  const v = p.vars;
  return `<button class="fp-swatch" type="button" data-theme="${id}" aria-pressed="false"><span class="fp-swatch-chip" style="--sw-a:${v['--bg-primary']};--sw-b:${v['--bg-tertiary']};--sw-c:${v['--text-primary']};--sw-d:${v['--border-light']}"><i></i><i></i><i></i></span><span class="fp-swatch-name">${escapeHtml(p.label)}</span></button>`;
};

export class Preferences extends Dialog {
  private readonly tabs: HTMLElement[];
  private readonly pages: HTMLElement[];
  private readonly themeBtns: HTMLButtonElement[];
  private readonly accentBtns: HTMLButtonElement[];
  private readonly densityBtns: HTMLButtonElement[];
  private readonly accentInput: HTMLInputElement;
  private readonly intensity: HTMLInputElement;
  private readonly intensityOut: HTMLElement;
  private readonly fwInput: HTMLInputElement;
  private readonly fwSave: HTMLButtonElement;
  private readonly fwTest: HTMLButtonElement;
  private readonly fwResult: HTMLElement;
  private readonly engineValue: HTMLElement;
  private readonly autoCheck: HTMLInputElement;
  private readonly autoBuild: HTMLInputElement;
  private saved = '';
  private section: PrefsSection = 'general';

  constructor(private readonly app: App) {
    super('Preferences', 760, 'fp-prefs-dlg');
    const langs = LANGUAGES.map(([code, name]) => `<option value="${code}" translate="no">${escapeHtml(name)}</option>`).join('');
    const root = el(`<div class="fp-prefs">
<nav class="fp-prefs-nav" aria-label="Preferences sections">${SECTIONS.map(([id, label, ic]) => `<button class="fp-prefs-tab" type="button" data-sec="${id}">${icon(ic, 16)}<span>${label}</span></button>`).join('')}</nav>
<div class="fp-prefs-pages">
<section class="fp-prefs-page" data-sec="general">
<h3 class="fp-prefs-h">General</h3>
<div class="fp-pref-row"><div class="fp-pref-text"><div class="fp-pref-name">Language</div><div class="fp-pref-hint">The window reloads in the language you choose.</div></div><select class="fp-select" data-ctl="language" aria-label="Language">${langs}</select></div>
</section>
<section class="fp-prefs-page" data-sec="interface" hidden>
<h3 class="fp-prefs-h">Interface</h3>
<div class="fp-pref-block"><div class="fp-pref-name">Theme</div><div class="fp-swatches">${Object.keys(THEMES).map(swatch).join('')}</div></div>
<div class="fp-pref-row"><div class="fp-pref-text"><div class="fp-pref-name">Accent colour</div></div><div class="fp-accents">${ACCENTS.map((c) => `<button class="fp-accent" type="button" data-accent="${c}" style="--ac:${c}" aria-label="${c}" aria-pressed="false" translate="no"></button>`).join('')}<input class="fp-accent-input" type="color" data-ctl="accent" aria-label="Custom accent colour"></div></div>
<div class="fp-pref-row"><div class="fp-pref-text"><div class="fp-pref-name">Accent intensity</div></div><div class="fp-range"><input type="range" min="0" max="1.5" step="0.05" data-ctl="intensity" aria-label="Accent intensity"><span class="fp-range-out" translate="no"></span></div></div>
<div class="fp-pref-row"><div class="fp-pref-text"><div class="fp-pref-name">Density</div><div class="fp-pref-hint">How tall the bars and controls are.</div></div><div class="fp-seg fp-seg-wide" role="group" aria-label="Density">${DENSITIES.map(([id, label]) => `<button type="button" data-density="${id}" aria-pressed="false">${label}</button>`).join('')}</div></div>
</section>
<section class="fp-prefs-page" data-sec="formweb" hidden>
<h3 class="fp-prefs-h">FormWeb</h3>
<div class="fp-pref-block"><label class="fp-pref-name" for="fp-fw-url">FormWeb address</label><div class="fp-pref-hint">FormWeb runs on this computer, for example http://127.0.0.1:8240. Test saves a changed address first.</div>
<div class="fp-fw-row"><input id="fp-fw-url" class="fp-input is-mono" type="text" spellcheck="false" autocomplete="off" translate="no" placeholder="http://127.0.0.1:8240"><button class="fp-btn" type="button" data-act="fw-save">Save</button><button class="fp-btn" type="button" data-act="fw-test">Test</button></div>
<div class="fp-fw-result" role="status" aria-live="polite"></div></div>
<div class="fp-pref-row"><div class="fp-pref-text"><label class="fp-pref-name" for="fp-auto-check">Check a site when it arrives</label><div class="fp-pref-hint">Runs the static checks on each site FormWeb sends, so the problems are ready when you open it. Off by default.</div></div><input id="fp-auto-check" class="fp-pref-check" type="checkbox" data-ctl="auto-check"></div>
<div class="fp-pref-row"><div class="fp-pref-text"><label class="fp-pref-name" for="fp-auto-build">Build a site when it arrives</label><div class="fp-pref-hint">Builds the package as soon as a site arrives, after the checks when both are on. Off by default.</div></div><input id="fp-auto-build" class="fp-pref-check" type="checkbox" data-ctl="auto-build"></div>
</section>
<section class="fp-prefs-page" data-sec="about" hidden>
<h3 class="fp-prefs-h">About</h3>
<div class="fp-about-name" translate="no">formpublisher</div>
<div class="fp-about-by" translate="no">by nodemode.ai</div>
<div class="fp-about-rows">
<div class="fp-about-row"><span>Version</span><span translate="no">${VERSION}</span></div>
<div class="fp-about-row"><span>Engine</span><span translate="no" data-field="engine">-</span></div>
<div class="fp-about-row"><span>License</span><span translate="no">GPL-3.0-only</span></div>
<div class="fp-about-row"><span>Copyright</span><span translate="no">Copyright 2026 NodeAgentc, Inc.</span></div>
</div>
</section>
</div>
</div>`);
    this.body.appendChild(root);
    this.foot.hidden = true;
    this.tabs = Array.from(root.querySelectorAll<HTMLElement>('.fp-prefs-tab'));
    this.pages = Array.from(root.querySelectorAll<HTMLElement>('.fp-prefs-page'));
    this.themeBtns = Array.from(root.querySelectorAll<HTMLButtonElement>('.fp-swatch'));
    this.accentBtns = Array.from(root.querySelectorAll<HTMLButtonElement>('.fp-accent'));
    this.densityBtns = Array.from(root.querySelectorAll<HTMLButtonElement>('[data-density]'));
    this.accentInput = q<HTMLInputElement>(root, '[data-ctl="accent"]');
    this.intensity = q<HTMLInputElement>(root, '[data-ctl="intensity"]');
    this.intensityOut = q(root, '.fp-range-out');
    this.fwInput = q<HTMLInputElement>(root, '#fp-fw-url');
    this.fwSave = q<HTMLButtonElement>(root, '[data-act="fw-save"]');
    this.fwTest = q<HTMLButtonElement>(root, '[data-act="fw-test"]');
    this.fwResult = q(root, '.fp-fw-result');
    this.engineValue = q(root, '[data-field="engine"]');
    this.autoCheck = q<HTMLInputElement>(root, '[data-ctl="auto-check"]');
    this.autoBuild = q<HTMLInputElement>(root, '[data-ctl="auto-build"]');
    this.autoCheck.addEventListener('change', () => { void this.saveFlag('receive.autoCheck', this.autoCheck); });
    this.autoBuild.addEventListener('change', () => { void this.saveFlag('receive.autoBuild', this.autoBuild); });
    const lang = q<HTMLSelectElement>(root, '[data-ctl="language"]');
    lang.value = storedLanguage();

    root.addEventListener('click', (e) => {
      const target = e.target as HTMLElement;
      const tab = target.closest<HTMLElement>('.fp-prefs-tab');
      if (tab?.dataset.sec) { this.select(tab.dataset.sec as PrefsSection); return; }
      const theme = target.closest<HTMLElement>('.fp-swatch')?.dataset.theme;
      if (theme) { setTheme(theme); return; }
      const accent = target.closest<HTMLElement>('.fp-accent')?.dataset.accent;
      if (accent) { setAccent(accent); return; }
      const density = target.closest<HTMLElement>('[data-density]')?.dataset.density as Density | undefined;
      if (density) { applyDensity(density); emit('fp:ui-settings-changed', { key: 'density' }); return; }
      const act = target.closest<HTMLElement>('[data-act]')?.dataset.act;
      if (act === 'fw-save') void this.saveFormWeb();
      else if (act === 'fw-test') void this.testFormWeb();
    });
    lang.addEventListener('change', () => setLanguage(lang.value));
    this.accentInput.addEventListener('input', () => setAccent(this.accentInput.value));
    this.intensity.addEventListener('input', () => {
      const value = Number(this.intensity.value);
      saveChoice({ ...readChoice(), intensity: value });
      applyTheme();
      emit('fp:ui-settings-changed', { key: 'intensity' });
    });
    this.fwInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); void this.saveFormWeb(); } });
    this.tabs.forEach((tab, i) => tab.addEventListener('keydown', (e) => {
      if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
      e.preventDefault();
      const next = this.tabs[(i + (e.key === 'ArrowDown' ? 1 : -1) + this.tabs.length) % this.tabs.length];
      next.focus();
      this.select(next.dataset.sec as PrefsSection);
    }));
    on('fp:ui-settings-changed', () => { if (this.isOpen) this.sync(); });
    this.select('general');
  }

  show(section?: PrefsSection): void {
    if (section) this.select(section);
    this.sync();
    setText(this.engineValue, this.app.state().engineVersion || '-');
    this.open(this.tabs.find((t) => t.dataset.sec === this.section) ?? null);
    void this.loadFormWeb();
  }

  private select(section: PrefsSection): void {
    this.section = section;
    for (const t of this.tabs) {
      const on = t.dataset.sec === section;
      setClass(t, 'is-on', on);
      setAttr(t, 'aria-current', on ? 'page' : 'false');
    }
    for (const p of this.pages) p.hidden = p.dataset.sec !== section;
  }

  private sync(): void {
    const choice = readChoice();
    const density = readDensity();
    for (const b of this.themeBtns) {
      const on = b.dataset.theme === choice.theme;
      setClass(b, 'is-on', on);
      setAttr(b, 'aria-pressed', String(on));
    }
    for (const b of this.accentBtns) {
      const on = b.dataset.accent?.toLowerCase() === choice.accentColor.toLowerCase();
      setClass(b, 'is-on', on);
      setAttr(b, 'aria-pressed', String(on));
    }
    if (/^#[0-9a-f]{6}$/i.test(choice.accentColor)) setValue(this.accentInput, choice.accentColor.toLowerCase());
    const intensity = choice.intensity ?? 1;
    setValue(this.intensity, String(intensity));
    setText(this.intensityOut, `${Math.round(intensity * 100)}%`);
    for (const b of this.densityBtns) {
      const on = b.dataset.density === density;
      setClass(b, 'is-on', on);
      setAttr(b, 'aria-pressed', String(on));
    }
  }

  private result(text: string, error = false): void {
    setText(this.fwResult, text);
    setClass(this.fwResult, 'is-error', error);
  }

  private async loadFormWeb(): Promise<void> {
    try {
      const s = await api.settings();
      const url = typeof s.formwebUrl === 'string' ? s.formwebUrl : '';
      this.saved = url;
      setValue(this.fwInput, url);
      this.autoCheck.checked = s['receive.autoCheck'] === true;
      this.autoBuild.checked = s['receive.autoBuild'] === true;
    } catch {
      this.result('The engine is not reachable', true);
    }
  }

  private async saveFlag(key: 'receive.autoCheck' | 'receive.autoBuild', box: HTMLInputElement): Promise<void> {
    const wanted = box.checked;
    try {
      const s = await api.putSettings({ [key]: wanted });
      box.checked = s[key] === true;
      emit('fp:settings-changed', {});
    } catch (e) {
      box.checked = !wanted;
      emit('fp:notice', { kind: 'error', text: e instanceof Error ? e.message : 'Request failed' });
    }
  }

  private async saveFormWeb(): Promise<boolean> {
    const url = this.fwInput.value.trim();
    if (!url) { this.result('Enter the FormWeb address.', true); return false; }
    if (url === this.saved) { this.result('Saved.'); return true; }
    setDisabled(this.fwSave, true);
    setDisabled(this.fwTest, true);
    try {
      const s = await api.putSettings({ formwebUrl: url });
      this.saved = typeof s.formwebUrl === 'string' ? s.formwebUrl : url;
      setValue(this.fwInput, this.saved);
      this.result('Saved.');
      emit('fp:settings-changed', {});
      return true;
    } catch (e) {
      this.result(e instanceof Error ? e.message : 'Request failed', true);
      return false;
    } finally {
      setDisabled(this.fwSave, false);
      setDisabled(this.fwTest, false);
    }
  }

  private async testFormWeb(): Promise<void> {
    if (!(await this.saveFormWeb())) return;
    setDisabled(this.fwTest, true);
    this.result('Testing');
    try {
      const s = await api.formwebStatus();
      const url = typeof s.url === 'string' ? s.url : this.saved;
      if (s.reachable === true) {
        const ms = typeof s.latencyMs === 'number' ? s.latencyMs : 0;
        this.result(`FormWeb answered at ${url} in ${ms} ms`);
      } else {
        this.result(`FormWeb is not reachable at ${url}`, true);
      }
    } catch (e) {
      this.result(e instanceof Error ? e.message : 'Request failed', true);
    } finally {
      setDisabled(this.fwTest, false);
    }
  }
}
