export const LANGUAGES: Array<[string, string]> = [
  ['en', 'English'], ['es', 'Español (España)'], ['es-MX', 'Español (México)'], ['pt-BR', 'Português (Brasil)'], ['fr', 'Français (France)'],
  ['fr-CA', 'Français (Canada)'], ['de', 'Deutsch'], ['it', 'Italiano'], ['nl', 'Nederlands'], ['da', 'Dansk'], ['fi', 'Suomi'], ['nb', 'Norsk bokmål'],
  ['sv', 'Svenska'], ['ru', 'Русский'], ['pl', 'Polski'], ['cs', 'Čeština'], ['hu', 'Magyar'], ['uk', 'Українська'], ['tr', 'Türkçe'],
  ['zh-Hans', '简体中文'], ['zh-Hant', '繁體中文'], ['ja', '日本語'], ['ko', '한국어'], ['id', 'Bahasa Indonesia'], ['th', 'ไทย'], ['vi', 'Tiếng Việt'],
];
const STORE = 'formpublisher_lang';
const ATTRS = ['title', 'placeholder', 'aria-label', 'alt'];
const SKIP = 'script, style, textarea, code, pre, kbd, [translate="no"], [contenteditable="true"]';
const keyParts = import.meta.glob<string[]>('./keys/*.json', { import: 'default' });
const localeParts = import.meta.glob<Record<string, string>>('./locales/*/*.json', { import: 'default' });

interface Tables { exact: Map<string, string>; patterns: Array<[RegExp, string]> }
interface Rec { en: string; shown: string }

let code = 'en';
let exact = new Map<string, string>();
let patterns: Array<[RegExp, string]> = [];
const cache = new Map<string, string | null>();
const textEn = new WeakMap<Text, Rec>();
const attrEn = new WeakMap<Element, Map<string, Rec>>();
const listeners = new Set<() => void>();
const titleEn = document.title;
let observer: MutationObserver | null = null;
let wanted = 'en';

export function language(): string { return code; }

export function onLanguage(fn: () => void): () => void {
  listeners.add(fn);
  return () => { listeners.delete(fn); };
}

export function locale(): string { return code === 'zh-Hans' ? 'zh-CN' : code === 'zh-Hant' ? 'zh-TW' : code; }

export function storedLanguage(): string {
  try { return localStorage.getItem(STORE) || 'en'; } catch { return 'en'; }
}

export async function setLanguage(next: string): Promise<void> {
  if (!LANGUAGES.some(([c]) => c === next)) return;
  wanted = next;
  try { localStorage.setItem(STORE, next); } catch {}
  let tables: Tables | null = null;
  if (next !== 'en') {
    try { tables = await loadTables(next); } catch { tables = null; }
    if (wanted !== next) return;
    if (!tables) {
      wanted = code;
      try { localStorage.setItem(STORE, code); } catch {}
      return;
    }
  }
  if (next === code) return;
  switchTo(next, tables);
}

function escape(s: string): string { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }

function plural(count: string, forms: string): string {
  const pick = new Map(forms.split(';').map((f) => f.split('=') as [string, string]));
  const cat = new Intl.PluralRules(locale()).select(Number(count.replace(/[^\d.]/g, '')) || 0);
  return pick.get(cat) ?? pick.get('other') ?? '';
}

function lookup(en: string): string | null {
  const hit = cache.get(en);
  if (hit !== undefined) return hit;
  cache.set(en, null);
  let out = exact.get(en) ?? null;
  if (out === null) {
    for (const [re, tr] of patterns) {
      const m = re.exec(en);
      if (m) { out = tr.replace(/\{(\d+):([^{}]+)\}/g, (_, n: string, forms: string) => plural(m[Number(n) + 1] ?? '', forms)).replace(/\{(p?)(\d+)\}/g, (_, p: string, n: string) => { if (p) return ''; const v = m[Number(n) + 1] ?? ''; return lookup(v) ?? v; }); break; }
    }
  }
  if (out === null && /[:.]$/.test(en) && !en.endsWith('...')) {
    const base = lookup(en.slice(0, -1));
    if (base !== null) out = base + en.slice(-1);
  }
  if (out === null && /(\.\.\.|…)$/.test(en)) {
    const cut = en.endsWith('…') ? 1 : 3;
    const base = lookup(en.slice(0, -cut));
    if (base !== null) out = base + en.slice(-cut);
  }
  if (out === null && !/[.…:]$/.test(en)) {
    const dotted = exact.get(`${en}...`) ?? exact.get(`${en}…`);
    if (dotted) out = dotted.replace(/\s*(\.\.\.|…)$/, '');
  }
  const keyed = out === null ? /^([\s\S]+?) \(([^()]{1,24})\)$/.exec(en) : null;
  if (keyed && /^((Alt|Shift|Ctrl|Cmd|Mod|Option)\+)*(\S{1,9}|Left|Right|Up|Down|Space|Enter|Esc|Tab|Backspace|Delete)$/.test(keyed[2])) {
    const base = lookup(keyed[1]);
    if (base !== null) out = `${base} (${keyed[2]})`;
  }
  if (out === null && en.includes(' · ')) {
    const parts = en.split(' · ').map((p) => lookup(p));
    if (parts.some((p) => p !== null)) out = en.split(' · ').map((p, i) => parts[i] ?? p).join(' · ');
  }
  if (cache.size > 20000) cache.clear();
  cache.set(en, out);
  return out;
}

export function t(en: string): string {
  if (code === 'en') return en;
  const m = /^(\s*)([\s\S]*?)(\s*)$/.exec(en);
  if (!m || !m[2]) return en;
  const tr = lookup(m[2]);
  return tr === null ? en : m[1] + tr + m[3];
}

function skipped(node: Element | null): boolean {
  return !node || node.closest(SKIP) !== null;
}

function text(node: Text): void {
  const cur = node.data;
  if (textEn.get(node)?.shown === cur || !/\p{L}/u.test(cur) || skipped(node.parentElement)) return;
  const next = t(cur);
  if (next !== cur) { textEn.set(node, { en: cur, shown: next }); node.data = next; }
}

function attrs(node: Element): void {
  if (skipped(node)) return;
  for (const a of ATTRS) {
    const cur = node.getAttribute(a);
    if (!cur) continue;
    const mine = attrEn.get(node);
    if (mine?.get(a)?.shown === cur) continue;
    const next = t(cur);
    if (next !== cur) {
      const map = mine ?? new Map<string, Rec>();
      map.set(a, { en: cur, shown: next });
      attrEn.set(node, map);
      node.setAttribute(a, next);
    }
  }
}

function retext(node: Text): void {
  const raw = node.data;
  const rec = textEn.get(node);
  let en = raw;
  if (rec && rec.shown === raw) en = rec.en;
  else if (!/\p{L}/u.test(raw) || skipped(node.parentElement)) return;
  const next = code === 'en' ? en : t(en);
  if (next !== raw) node.data = next;
  if (next !== en) textEn.set(node, { en, shown: next }); else textEn.delete(node);
}

function reattrs(node: Element): void {
  if (skipped(node)) return;
  for (const a of ATTRS) {
    const raw = node.getAttribute(a);
    if (!raw) continue;
    const mine = attrEn.get(node);
    const rec = mine?.get(a);
    const en = rec && rec.shown === raw ? rec.en : raw;
    const next = code === 'en' ? en : t(en);
    if (next !== raw) node.setAttribute(a, next);
    if (next !== en) {
      const map = mine ?? new Map<string, Rec>();
      map.set(a, { en, shown: next });
      attrEn.set(node, map);
    } else mine?.delete(a);
  }
}

function rewalk(root: Element): void {
  if (skipped(root)) return;
  reattrs(root);
  const w = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
    acceptNode: (n) => (n.nodeType === Node.ELEMENT_NODE && (n as Element).matches(SKIP) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT),
  });
  for (let n = w.nextNode(); n; n = w.nextNode()) {
    if (n.nodeType === Node.TEXT_NODE) retext(n as Text); else reattrs(n as Element);
  }
}

function walk(root: Node): void {
  if (root.nodeType === Node.TEXT_NODE) { text(root as Text); return; }
  if (root.nodeType !== Node.ELEMENT_NODE) return;
  const node = root as Element;
  if (skipped(node)) return;
  attrs(node);
  const w = document.createTreeWalker(node, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
    acceptNode: (n) => (n.nodeType === Node.ELEMENT_NODE && (n as Element).matches(SKIP) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT),
  });
  for (let n = w.nextNode(); n; n = w.nextNode()) {
    if (n.nodeType === Node.TEXT_NODE) text(n as Text); else attrs(n as Element);
  }
}

function add(into: Tables, en: string, tr: string | undefined): void {
  if (!tr || tr === en) return;
  if (!/\{\d+\}/.test(en)) { into.exact.set(en, tr); return; }
  const suffix = new Set([...en.matchAll(/[A-Za-z]\{(\d+)\}/g)].map((m) => m[1]));
  const fixed = suffix.size ? tr.replace(/\{(\d+)\}/g, (all, n: string) => (suffix.has(n) ? `{p${n}}` : all)) : tr;
  const re = new RegExp('^' + escape(en).replace(/\\\{\d+\\\}/g, '([\\s\\S]*?)') + '$');
  const had = into.patterns.findIndex(([r]) => r.source === re.source);
  if (had >= 0) into.patterns.splice(had, 1);
  into.patterns.push([re, fixed]);
}

async function loadTables(want: string): Promise<Tables | null> {
  if (want === 'en' || !LANGUAGES.some(([c]) => c === want)) return null;
  const parts = Object.keys(keyParts).map((path) => /\/([^/]+)\.json$/.exec(path)?.[1] ?? '').filter(Boolean).sort();
  const loaded = await Promise.all(parts.map(async (part) => {
    const tr = localeParts[`./locales/${want}/${part}.json`];
    if (!tr) return null;
    const [keys, values] = await Promise.all([keyParts[`./keys/${part}.json`](), tr()]);
    return [keys, values] as const;
  }));
  if (!loaded.some(Boolean)) return null;
  const out: Tables = { exact: new Map(), patterns: [] };
  for (const pair of loaded) if (pair) pair[0].forEach((en, i) => add(out, en, pair[1][String(i)] ?? pair[1][en]));
  out.patterns.sort((a, b) => b[0].source.length - a[0].source.length);
  return out;
}

function direct(lang: string): void {
  const root = document.documentElement;
  if (/^(ar|he|fa|ur)(-|$)/.test(lang)) root.dir = 'rtl';
  else if (root.hasAttribute('dir')) root.removeAttribute('dir');
}

function watch(): void {
  if (observer) return;
  observer = new MutationObserver((list) => {
    if (code === 'en') return;
    for (const m of list) {
      if (m.type === 'characterData') text(m.target as Text);
      else if (m.type === 'attributes') attrs(m.target as Element);
      else m.addedNodes.forEach(walk);
    }
  });
  observer.observe(document.body, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ATTRS });
}

function switchTo(next: string, tables: Tables | null): void {
  observer?.disconnect();
  observer?.takeRecords();
  exact = tables ? tables.exact : new Map();
  patterns = tables ? tables.patterns : [];
  cache.clear();
  code = next;
  const root = document.documentElement;
  root.lang = locale();
  direct(next);
  document.title = t(titleEn);
  rewalk(document.body);
  watch();
  observer?.takeRecords();
  observer?.observe(document.body, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ATTRS });
  for (const fn of listeners) {
    try { fn(); } catch {}
  }
}

export async function initLanguage(): Promise<void> {
  const want = storedLanguage();
  wanted = want;
  const tables = await loadTables(want);
  if (!tables) return;
  exact = tables.exact;
  patterns = tables.patterns;
  code = want;
  document.documentElement.lang = locale();
  direct(want);
  document.title = t(document.title);
  walk(document.body);
  watch();
}
