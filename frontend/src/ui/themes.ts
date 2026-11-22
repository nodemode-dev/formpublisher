import { emit } from '../events';

export interface ThemeProfile { label: string; vars: Record<string, string>; light?: boolean }

export const THEMES: Record<string, ThemeProfile> = {
  'studio': { label: 'Studio Dark', vars: { '--bg-primary': '#111111', '--bg-secondary': '#17151b', '--bg-tertiary': '#222127', '--border-color': '#2a2a2a', '--border-light': '#34333a', '--text-primary': '#f7f7f7', '--text-secondary': '#a4a4a4', '--text-muted': '#8a8a8b', '--canvas-bg': '#1c1b1d', '--grid-color': '#5e5e60', '--bg-node': '#191919' } },
  'nodemode-dark': { label: 'NodeMode Dark', vars: { '--bg-primary': '#0a0a0a', '--bg-secondary': '#121218', '--bg-tertiary': '#1a1a24', '--border-color': '#2a2a35', '--border-light': '#3a3a48', '--text-primary': '#e8e8ee', '--text-secondary': '#a8a8b8', '--text-muted': '#838393', '--canvas-bg': '#0a0a0a', '--grid-color': 'rgba(255,255,255,0.04)', '--node-shadow': '0 6px 18px rgba(0,0,0,0.45)' } },
  'light': { label: 'Light', light: true, vars: { '--bg-primary': '#ecebe6', '--bg-secondary': '#f7f6f1', '--bg-tertiary': '#e2e0d8', '--bg-node': '#f4f3ed', '--border-color': '#d1cdc1', '--border-light': '#beb9aa', '--text-primary': '#26241d', '--text-secondary': '#4c4a40', '--text-muted': '#646256', '--canvas-bg': '#e7e5dd', '--grid-color': 'rgba(70,60,30,0.10)', '--node-shadow': '0 5px 14px rgba(96,90,70,0.15)' } },
  'github-dark': { label: 'GitHub Dark', vars: { '--bg-primary': '#0d1117', '--bg-secondary': '#161b22', '--bg-tertiary': '#21262d', '--border-color': '#30363d', '--border-light': '#3d444d', '--text-primary': '#e6edf3', '--text-secondary': '#9198a1', '--text-muted': '#878e98', '--canvas-bg': '#0d1117', '--grid-color': 'rgba(230,237,243,0.05)', '--node-shadow': '0 6px 18px rgba(0,0,0,0.5)' } },
  'midnight': { label: 'Midnight Blue', vars: { '--bg-primary': '#0b1020', '--bg-secondary': '#101830', '--bg-tertiary': '#182242', '--border-color': '#25325c', '--border-light': '#324274', '--text-primary': '#e4e9f7', '--text-secondary': '#9fabd0', '--text-muted': '#7f8bb3', '--canvas-bg': '#0b1020', '--grid-color': 'rgba(160,180,255,0.06)', '--node-shadow': '0 8px 22px rgba(0,0,20,0.55)' } },
  'forest': { label: 'Forest', vars: { '--bg-primary': '#0c130e', '--bg-secondary': '#121c15', '--bg-tertiary': '#1a281e', '--border-color': '#2a4030', '--border-light': '#375441', '--text-primary': '#e4efe7', '--text-secondary': '#a4bdac', '--text-muted': '#789381', '--canvas-bg': '#0c130e', '--grid-color': 'rgba(180,230,190,0.05)', '--node-shadow': '0 6px 18px rgba(0,10,0,0.5)' } },
  'ember': { label: 'Ember', vars: { '--bg-primary': '#140d0a', '--bg-secondary': '#1d1310', '--bg-tertiary': '#2a1c16', '--border-color': '#452e22', '--border-light': '#5a3d2e', '--text-primary': '#f2e8e2', '--text-secondary': '#c7ab9c', '--text-muted': '#9f8273', '--canvas-bg': '#140d0a', '--grid-color': 'rgba(255,200,160,0.05)', '--node-shadow': '0 6px 18px rgba(20,5,0,0.55)' } },
  'violet': { label: 'Violet Haze', vars: { '--bg-primary': '#100b1c', '--bg-secondary': '#171129', '--bg-tertiary': '#221a3c', '--border-color': '#382c5e', '--border-light': '#493b78', '--text-primary': '#ece6f9', '--text-secondary': '#b3a6d8', '--text-muted': '#8f82b6', '--canvas-bg': '#100b1c', '--grid-color': 'rgba(210,190,255,0.06)', '--node-shadow': '0 8px 22px rgba(10,0,30,0.55)' } },
  'slate': { label: 'Slate', vars: { '--bg-primary': '#101418', '--bg-secondary': '#171d23', '--bg-tertiary': '#212a32', '--border-color': '#32404c', '--border-light': '#415260', '--text-primary': '#e7edf2', '--text-secondary': '#a3b2bf', '--text-muted': '#8493a0', '--canvas-bg': '#101418', '--grid-color': 'rgba(200,220,240,0.05)', '--node-shadow': '0 6px 18px rgba(0,5,10,0.5)' } },
  'mono': { label: 'Mono Ink', vars: { '--bg-primary': '#0e0e0e', '--bg-secondary': '#161616', '--bg-tertiary': '#202020', '--border-color': '#333333', '--border-light': '#454545', '--text-primary': '#f0f0f0', '--text-secondary': '#ababab', '--text-muted': '#898989', '--canvas-bg': '#0e0e0e', '--grid-color': 'rgba(255,255,255,0.05)', '--node-shadow': '0 6px 18px rgba(0,0,0,0.5)' } },
  'sand': { label: 'Sand (light)', light: true, vars: { '--bg-primary': '#efe8da', '--bg-secondary': '#f8f3e9', '--bg-tertiary': '#e6dcc8', '--bg-node': '#f5efe2', '--border-color': '#d4c7ab', '--border-light': '#c2b28e', '--text-primary': '#2a2418', '--text-secondary': '#59503c', '--text-muted': '#695f49', '--canvas-bg': '#eae2d1', '--grid-color': 'rgba(80,60,10,0.10)', '--node-shadow': '0 5px 14px rgba(100,80,30,0.16)' } },
  'ocean': { label: 'Deep Ocean', vars: { '--bg-primary': '#06131c', '--bg-secondary': '#0a1c29', '--bg-tertiary': '#10293c', '--border-color': '#1d425e', '--border-light': '#285578', '--text-primary': '#e2eef7', '--text-secondary': '#96b6cc', '--text-muted': '#7394aa', '--canvas-bg': '#06131c', '--grid-color': 'rgba(150,210,255,0.06)', '--node-shadow': '0 8px 22px rgba(0,10,20,0.6)' } },
  'rose': { label: 'Rose Noir', vars: { '--bg-primary': '#170b10', '--bg-secondary': '#211117', '--bg-tertiary': '#301a22', '--border-color': '#4d2b38', '--border-light': '#653a49', '--text-primary': '#f5e7ec', '--text-secondary': '#cfa5b3', '--text-muted': '#a87e8d', '--canvas-bg': '#170b10', '--grid-color': 'rgba(255,190,215,0.05)', '--node-shadow': '0 6px 18px rgba(25,0,10,0.55)' } },
  'terminal': { label: 'Terminal Green', vars: { '--bg-primary': '#050d05', '--bg-secondary': '#0a140a', '--bg-tertiary': '#102010', '--border-color': '#1f3d1f', '--border-light': '#2b522b', '--text-primary': '#d8f5d8', '--text-secondary': '#8fce8f', '--text-muted': '#5d925d', '--canvas-bg': '#050d05', '--grid-color': 'rgba(120,255,120,0.06)', '--node-shadow': '0 6px 18px rgba(0,10,0,0.6)' } },
  'contrast': { label: 'High Contrast', vars: { '--bg-primary': '#000000', '--bg-secondary': '#0a0a0a', '--bg-tertiary': '#161616', '--border-color': '#555555', '--border-light': '#777777', '--text-primary': '#ffffff', '--text-secondary': '#d8d8d8', '--text-muted': '#9a9a9a', '--canvas-bg': '#000000', '--grid-color': 'rgba(255,255,255,0.10)', '--node-shadow': '0 0 0 1px #666' } },
};

export const DEFAULT_THEME = 'studio';
export const DEFAULT_ACCENT = '#5fe07a';
export const OLD_DEFAULT_ACCENT = '#aba0d3';
export const PREVIOUS_DEFAULT_ACCENT = '#f97316';
export const INK_ON_ACCENT = '#0b1a10';
export const DEFAULT_INTENSITY = 1;
export const STORAGE_KEY = 'nodemode_ui_settings';
export const ACCENT_MOVED_KEY = 'formpublisher.accentMoved';
export const APPEARANCE = 3;
export const LIGHT_INK_DEFAULT = '#2e6c3b';
const LIGHT_INK_TARGET = 4.5;
const SOFT_MAX = 0.3;

export interface ThemeChoice { theme: string; accentColor: string; intensity?: number }
export type Density = 'compact' | 'standard' | 'comfortable';

const clampIntensity = (v: unknown): number => (typeof v === 'number' && Number.isFinite(v) ? Math.min(1.5, Math.max(0, v)) : DEFAULT_INTENSITY);

function moveAccentOnce(): void {
  try {
    if (localStorage.getItem(ACCENT_MOVED_KEY)) return;
    const raw = localStorage.getItem(STORAGE_KEY);
    const saved = raw ? JSON.parse(raw) as { accentColor?: unknown } : null;
    if (saved && typeof saved.accentColor === 'string' && saved.accentColor.toLowerCase() === PREVIOUS_DEFAULT_ACCENT) {
      saved.accentColor = DEFAULT_ACCENT;
      localStorage.setItem(STORAGE_KEY, JSON.stringify(saved));
    }
    localStorage.setItem(ACCENT_MOVED_KEY, '1');
  } catch (e) {
    console.error('[theme] accent move failed:', e);
  }
}

export function readChoice(): ThemeChoice {
  moveAccentOnce();
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const saved = JSON.parse(raw) as Partial<ThemeChoice> & { appearance?: number };
      if (saved.appearance === APPEARANCE) return { theme: saved.theme && THEMES[saved.theme] ? saved.theme : DEFAULT_THEME, accentColor: saved.accentColor || DEFAULT_ACCENT, intensity: clampIntensity(saved.intensity) };
      if (saved.appearance === 2) return { theme: saved.theme && THEMES[saved.theme] ? saved.theme : DEFAULT_THEME, accentColor: !saved.accentColor || saved.accentColor === OLD_DEFAULT_ACCENT ? DEFAULT_ACCENT : saved.accentColor, intensity: DEFAULT_INTENSITY };
    }
  } catch (e) {
    console.error('[theme] read failed:', e);
  }
  return { theme: DEFAULT_THEME, accentColor: DEFAULT_ACCENT, intensity: DEFAULT_INTENSITY };
}

export function saveChoice(choice: ThemeChoice): void {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...(raw ? JSON.parse(raw) : {}), ...choice, appearance: APPEARANCE }));
  } catch (e) {
    console.error('[theme] save failed:', e);
  }
}

export function readDensity(): Density {
  try {
    const d = (JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}') as { density?: unknown }).density;
    return d === 'compact' || d === 'comfortable' ? d : 'standard';
  } catch {
    return 'standard';
  }
}

export function applyDensity(d: Density): void {
  const root = document.documentElement;
  root.classList.toggle('fp-density-compact', d === 'compact');
  root.classList.toggle('fp-density-comfortable', d === 'comfortable');
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...(raw ? JSON.parse(raw) : {}), density: d }));
  } catch (e) {
    console.error('[theme] save failed:', e);
  }
}

function hexToRgba(hex: string, alpha: number): string {
  const h = hex.replace('#', '');
  const full = h.length === 3 ? h.split('').map((c) => c + c).join('') : h;
  const n = parseInt(full.slice(0, 6), 16);
  if (Number.isNaN(n)) return hexToRgba(DEFAULT_ACCENT, alpha);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${alpha})`;
}

function onAccent(hex: string): string {
  const h = hex.replace('#', '');
  const full = h.length === 3 ? h.split('').map((c) => c + c).join('') : h;
  const n = parseInt(full.slice(0, 6), 16);
  if (Number.isNaN(n)) return INK_ON_ACCENT;
  const lin = (c: number): number => { const s = c / 255; return s <= 0.04045 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4); };
  const l = 0.2126 * lin((n >> 16) & 255) + 0.7152 * lin((n >> 8) & 255) + 0.0722 * lin(n & 255);
  return l > 0.2 ? INK_ON_ACCENT : '#ffffff';
}

const rgbOf = (hex: string): number[] | null => {
  const h = hex.replace('#', '');
  const full = h.length === 3 ? h.split('').map((c) => c + c).join('') : h;
  if (!/^[0-9a-f]{6}/i.test(full)) return null;
  const n = parseInt(full.slice(0, 6), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
};

const lum = (c: number[]): number => {
  const lin = (v: number): number => { const s = v / 255; return s <= 0.04045 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4); };
  return 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2]);
};

const contrast = (a: number[], b: number[]): number => { const x = lum(a); const y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };

const mixRgb = (a: number[], b: number[], t: number): number[] => a.map((v, i) => Math.round(v * (1 - t) + b[i] * t));

export function lightInk(accent: string): string {
  const a = rgbOf(accent);
  if (!a) return LIGHT_INK_DEFAULT;
  const surfaces: number[][] = [];
  for (const p of Object.values(THEMES)) {
    if (!p.light) continue;
    for (const k of ['--bg-primary', '--bg-secondary', '--bg-tertiary']) { const c = rgbOf(p.vars[k]); if (c) surfaces.push(c); }
    const node = rgbOf(p.vars['--bg-node'] || p.vars['--bg-secondary']);
    if (node) surfaces.push(mixRgb(node, a, SOFT_MAX));
  }
  for (let t = 0; t <= 1; t = Math.round((t + 0.02) * 100) / 100) {
    const c = mixRgb(a, [0, 0, 0], t);
    if (surfaces.every((s) => contrast(c, s) >= LIGHT_INK_TARGET)) return `#${c.map((v) => v.toString(16).padStart(2, '0')).join('')}`;
  }
  return '#000000';
}

export function applyTheme(choice: ThemeChoice = readChoice()): void {
  const root = document.documentElement;
  const theme = THEMES[choice.theme] || THEMES[DEFAULT_THEME];
  for (const [k, v] of Object.entries(theme.vars)) root.style.setProperty(k, v);
  document.body.classList.toggle('theme-light', !!theme.light);
  root.classList.remove('theme-light-pending');
  root.style.setProperty('--bg-node', theme.vars['--bg-node'] || theme.vars['--bg-secondary']);
  root.style.setProperty('--shadow-lg', theme.light ? '0 4px 14px rgba(96, 90, 70, 0.16)' : '0 8px 32px rgba(0, 0, 0, 0.5)');
  root.style.setProperty('--accent-color', choice.accentColor);
  root.style.setProperty('--accent-color-dim', choice.accentColor + '33');
  root.style.setProperty('--accent-color-hover', `color-mix(in srgb, ${choice.accentColor} 82%, #ffffff)`);
  root.style.setProperty('--text-on-accent', onAccent(choice.accentColor));
  root.style.setProperty('--accent-ink-light', lightInk(choice.accentColor));
  root.style.setProperty('--accent-intensity', String(clampIntensity(choice.intensity)));
  root.style.setProperty('--accent-tint',hexToRgba(choice.accentColor, 0.06));
  root.style.setProperty('--accent-tint-strong', hexToRgba(choice.accentColor, 0.10));
  root.style.background = theme.vars['--bg-primary'];
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme.vars['--bg-primary']);
}

export function setTheme(theme: string): void {
  const choice = { ...readChoice(), theme };
  saveChoice(choice);
  applyTheme(choice);
  emit('fp:ui-settings-changed', { key: 'theme' });
}

export function setAccent(accentColor: string): void {
  const choice = { ...readChoice(), accentColor };
  saveChoice(choice);
  applyTheme(choice);
  emit('fp:ui-settings-changed', { key: 'accentColor' });
}

export function isLightTheme(theme: string = readChoice().theme): boolean {
  return !!THEMES[theme]?.light;
}

export function nextToggleTheme(theme: string = readChoice().theme): string {
  return isLightTheme(theme) ? DEFAULT_THEME : 'light';
}
