import { isMac } from './dom';

export interface Command {
  id: string;
  label: string | (() => string);
  keys?: string[];
  icon?: string;
  run: (params?: Record<string, unknown>) => unknown;
  enabled?: () => boolean;
  checked?: () => boolean;
  group?: string;
  menu?: string;
  description?: string;
  mutates?: boolean;
  risky?: boolean;
  native?: boolean;
}

export const SHORTCUTS_KEY = 'formpublisher_shortcuts';

const CODE_KEYS: Record<string, string> = {
  BracketLeft: '[', BracketRight: ']', Equal: '=', Minus: '-', NumpadAdd: '=', NumpadSubtract: '-', Backspace: 'Backspace', Delete: 'Delete',
  Enter: 'Enter', Escape: 'Escape', Space: 'Space', ArrowUp: 'Up', ArrowDown: 'Down', ArrowLeft: 'Left', ArrowRight: 'Right', Slash: '/', Tab: 'Tab',
  Period: '.', Comma: ',', Semicolon: ';', Quote: "'", Backquote: '`', Backslash: '\\',
};

const GLYPHS: Record<string, string> = {
  Mod: '⌘', Shift: '⇧', Alt: '⌥', Backspace: '⌫', Delete: '⌦', Enter: '↩',
  Up: '↑', Down: '↓', Left: '←', Right: '→', Escape: 'Esc',
};

export function comboOf(e: KeyboardEvent): string {
  const c = e.code;
  const key = c.startsWith('Key') ? c.slice(3) : c.startsWith('Digit') ? c.slice(5) : c.startsWith('Numpad') && /\d$/.test(c) ? c.slice(6) : CODE_KEYS[c] ?? e.key;
  const parts: string[] = [];
  if (e.altKey) parts.push('Alt');
  if (e.shiftKey) parts.push('Shift');
  if (isMac ? e.metaKey : e.ctrlKey) parts.push('Mod');
  parts.push(key);
  return parts.join('+');
}

export function formatKeys(combo: string): string {
  const parts = combo.split('+');
  if (isMac) return parts.map((p) => GLYPHS[p] ?? p).join('');
  return parts.map((p) => (p === 'Mod' ? 'Ctrl' : p)).join('+');
}

const OWNED_COMBOS = new Set([
  'Mod+Q', 'Shift+Mod+Q', 'Mod+W', 'Shift+Mod+W', 'Mod+T', 'Shift+Mod+T', 'Mod+N', 'Shift+Mod+N',
  'Mod+Tab', 'Shift+Mod+Tab', 'Alt+Tab', 'Alt+F4', 'Mod+Space', 'Mod+PageUp', 'Mod+PageDown', 'F11', 'F12',
  ...[1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => `Mod+${n}`),
  ...(isMac ? ['Mod+H', 'Mod+M', 'Alt+Mod+Space'] : ['Mod+Escape']),
]);

export function rejectCombo(combo: string): string | null {
  const parts = combo.split('+');
  const key = parts[parts.length - 1];
  const modded = parts.includes('Mod') || parts.includes('Alt');
  if (!modded && !/^F([1-9]|1[0-2])$/.test(key)) return 'Use Ctrl, Alt or Cmd together with the key.';
  if (OWNED_COMBOS.has(combo)) return 'The browser or system keeps that combination, so the app cannot use it.';
  return null;
}

function readOverrides(): Record<string, string[]> {
  try {
    const raw = JSON.parse(localStorage.getItem(SHORTCUTS_KEY) || '{}') as unknown;
    if (typeof raw !== 'object' || raw === null || Array.isArray(raw)) return {};
    const out: Record<string, string[]> = {};
    for (const [id, keys] of Object.entries(raw)) if (Array.isArray(keys) && keys.every((k) => typeof k === 'string')) out[id] = keys as string[];
    return out;
  } catch {
    return {};
  }
}

export class Commands {
  private readonly map = new Map<string, Command>();
  private readonly defaults = new Map<string, string[]>();
  private readonly stored = readOverrides();
  private readonly listeners = new Set<() => void>();
  onRun: ((cmd: Command) => void) | null = null;
  onError: ((cmd: Command, error: unknown) => void) | null = null;

  add(...cmds: Command[]): void {
    for (const cmd of cmds) {
      if (this.map.has(cmd.id)) throw new Error(`duplicate command: ${cmd.id}`);
      this.map.set(cmd.id, cmd);
      this.defaults.set(cmd.id, [...(cmd.keys ?? [])]);
      const kept = this.stored[cmd.id];
      if (kept) cmd.keys = [...kept];
    }
  }

  get(id: string): Command | undefined { return this.map.get(id); }

  all(): Command[] { return [...this.map.values()]; }

  label(cmd: Command): string { return typeof cmd.label === 'function' ? cmd.label() : cmd.label; }

  enabled(cmd: Command): boolean { return cmd.enabled ? cmd.enabled() : true; }

  keyLabel(cmd: Command): string { const k = cmd.keys?.[0]; return k ? formatKeys(k) : ''; }

  forCombo(combo: string): Command | undefined {
    for (const cmd of this.map.values()) if (cmd.keys?.includes(combo)) return cmd;
    return undefined;
  }

  defaultKeys(id: string): string[] { return [...(this.defaults.get(id) ?? [])]; }

  isCustom(id: string): boolean { return Object.prototype.hasOwnProperty.call(this.stored, id); }

  owner(combo: string, except: string): Command | undefined {
    for (const cmd of this.map.values()) if (cmd.id !== except && cmd.keys?.includes(combo)) return cmd;
    return undefined;
  }

  onChange(fn: () => void): () => void {
    this.listeners.add(fn);
    return () => { this.listeners.delete(fn); };
  }

  setKeys(id: string, keys: string[]): void {
    const cmd = this.map.get(id);
    if (!cmd) return;
    for (const other of this.map.values()) {
      if (other === cmd || !other.keys) continue;
      const left = other.keys.filter((k) => !keys.includes(k));
      if (left.length !== other.keys.length) { other.keys = left; this.remember(other.id, left); }
    }
    cmd.keys = [...keys];
    this.remember(id, keys);
    this.persist();
  }

  resetKey(id: string): void {
    this.setKeys(id, this.defaultKeys(id));
  }

  resetKeys(): void {
    for (const key of Object.keys(this.stored)) delete this.stored[key];
    for (const [id, cmd] of this.map) cmd.keys = [...(this.defaults.get(id) ?? [])];
    this.persist();
  }

  private remember(id: string, keys: string[]): void {
    const base = this.defaults.get(id) ?? [];
    if (keys.length === base.length && keys.every((k, i) => k === base[i])) delete this.stored[id];
    else this.stored[id] = [...keys];
  }

  run(id: string, params?: Record<string, unknown>): boolean {
    const cmd = this.map.get(id);
    if (!cmd || !this.enabled(cmd)) return false;
    try {
      const out = cmd.run(params);
      if (out instanceof Promise) out.catch((error: unknown) => this.onError?.(cmd, error));
    } catch (error) {
      this.onError?.(cmd, error);
      return false;
    }
    this.onRun?.(cmd);
    return true;
  }

  private persist(): void {
    try { localStorage.setItem(SHORTCUTS_KEY, JSON.stringify(this.stored)); } catch { void 0; }
    for (const fn of this.listeners) fn();
  }
}

function typingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement || target.isContentEditable;
}

const MODIFIER_KEYS = new Set(['Shift', 'Control', 'Alt', 'Meta', 'AltGraph', 'CapsLock']);

export function installShortcuts(commands: Commands): () => void {
  const handler = (e: KeyboardEvent): void => {
    if (e.defaultPrevented || e.isComposing || MODIFIER_KEYS.has(e.key)) return;
    const combo = comboOf(e);
    const cmd = commands.forCombo(combo);
    if (!cmd || cmd.native) return;
    if (!combo.split('+').includes('Mod') && typingTarget(e.target)) return;
    e.preventDefault();
    if (e.repeat) return;
    commands.run(cmd.id);
  };
  document.addEventListener('keydown', handler);
  return () => document.removeEventListener('keydown', handler);
}
