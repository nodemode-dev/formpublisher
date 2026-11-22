import { api } from '../api';
import { emit } from '../events';
import { inTauri, q, setClass, setDisabled, setText, setValue } from './dom';
import { icon } from './icons';

const KEY = 'checks.chromePath';
const WAIT = 700;
const ABSOLUTE = /^(\/|[A-Za-z]:[\\/]|\\\\)/;

const example = (): string => {
  const p = navigator.platform || navigator.userAgent;
  if (/Mac/.test(p)) return '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
  if (/Win/.test(p)) return 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
  return '/usr/bin/google-chrome';
};

const message = (e: unknown): string => (e instanceof Error && e.message ? e.message : 'Request failed');

export const checksPanelHtml = (): string => `<section class="fp-prefs-group"><h3 class="fp-prefs-label">Deep check</h3>
<div class="fp-pref-block"><label class="fp-pref-name" for="fp-chrome-path">Browser for the deep check</label><div class="fp-pref-hint">The deep check drives this browser. When the field is empty, it looks for Google Chrome, then Microsoft Edge, then the places browsers are usually installed.</div>
<div class="fp-path-row"><input id="fp-chrome-path" class="fp-input is-mono" type="text" spellcheck="false" autocomplete="off" translate="no" placeholder="${example()}"><button class="fp-btn" type="button" data-cact="browse">${icon('folder', 14)}<span>Browse...</span></button><button class="fp-btn" type="button" data-cact="clear">Clear</button></div>
<div class="fp-path-result" role="status" aria-live="polite"></div></div>
</section>`;

export class ChecksPanel {
  private saved = '';
  private timer = 0;
  private seq = 0;
  private readonly input: HTMLInputElement;
  private readonly result: HTMLElement;
  private readonly browseBtn: HTMLButtonElement;
  private readonly clearBtn: HTMLButtonElement;

  constructor(root: HTMLElement) {
    this.input = q<HTMLInputElement>(root, '#fp-chrome-path');
    this.result = q(root, '.fp-path-result');
    this.browseBtn = q<HTMLButtonElement>(root, '[data-cact="browse"]');
    this.clearBtn = q<HTMLButtonElement>(root, '[data-cact="clear"]');
    this.browseBtn.addEventListener('click', () => { void this.browse(); });
    this.clearBtn.addEventListener('click', () => { setValue(this.input, ''); void this.save(); });
    this.input.addEventListener('input', () => {
      this.say('', false);
      this.syncClear();
      window.clearTimeout(this.timer);
      this.timer = window.setTimeout(() => { void this.save(); }, WAIT);
    });
    this.input.addEventListener('change', () => { void this.save(); });
    this.input.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); void this.save(); } });
  }

  fill(settings: Record<string, unknown>): void {
    const value = typeof settings[KEY] === 'string' ? (settings[KEY] as string) : '';
    this.saved = value;
    if (document.activeElement !== this.input) setValue(this.input, value);
    this.syncClear();
  }

  private syncClear(): void {
    setDisabled(this.clearBtn, this.input.value === '' && this.saved === '');
  }

  private say(text: string, error: boolean): void {
    setText(this.result, text);
    setClass(this.result, 'is-error', error);
  }

  private async browse(): Promise<void> {
    if (!inTauri()) {
      this.input.focus();
      this.input.select();
      this.say('Type the full path of the browser program in the field.', false);
      return;
    }
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      const picked = await invoke<string | string[] | null>('plugin:dialog|open', { options: { directory: false, multiple: false, title: 'Choose the browser' } });
      const path = Array.isArray(picked) ? picked[0] ?? null : picked;
      if (!path) return;
      setValue(this.input, path);
      await this.save();
    } catch (e) {
      this.say(message(e), true);
    }
  }

  private async save(): Promise<void> {
    window.clearTimeout(this.timer);
    const value = this.input.value.trim();
    this.syncClear();
    if (value === this.saved) return;
    if (value && !ABSOLUTE.test(value)) { this.say('Give the full path of the browser program, starting from the top folder.', true); return; }
    const seq = ++this.seq;
    try {
      const s = await api.putSettings({ [KEY]: value || null });
      if (seq !== this.seq) return;
      this.saved = typeof s[KEY] === 'string' ? (s[KEY] as string) : '';
      if (this.input.value.trim() === value) setValue(this.input, this.saved);
      this.say(value ? 'Saved.' : 'Cleared. The deep check looks for a browser itself.', false);
      emit('fp:settings-changed', {});
    } catch (e) {
      if (seq === this.seq) this.say(message(e), true);
    }
    this.syncClear();
  }
}
