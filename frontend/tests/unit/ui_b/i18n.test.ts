import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { LANGUAGES, language, setLanguage, t, locale, onLanguage } from '../../../src/i18n';

const ROOT = join(__dirname, '../../../src/i18n');
const PARTS = readdirSync(join(ROOT, 'keys')).filter((f) => f.endsWith('.json')).sort();
const OTHERS = LANGUAGES.map(([c]) => c).filter((c) => c !== 'en');

function keys(part: string): string[] {
  return JSON.parse(readFileSync(join(ROOT, 'keys', part), 'utf8')) as string[];
}

function table(lang: string, part: string): Record<string, string> | null {
  const p = join(ROOT, 'locales', lang, part);
  return existsSync(p) ? (JSON.parse(readFileSync(p, 'utf8')) as Record<string, string>) : null;
}

function answer(tbl: Record<string, string>, en: string, i: number): string | undefined {
  return tbl[String(i)] ?? tbl[en];
}

function holes(s: string): string[] {
  return [...new Set([...s.matchAll(/\{(\d+)(?::[^{}]*)?\}/g)].map((m) => m[1]))].sort();
}

describe('every language answers every key of the default language', () => {
  it.each(OTHERS)('language %s has a table for every key part', (lang) => {
    const missing = PARTS.filter((part) => table(lang, part) === null);
    expect(missing).toEqual([]);
  });

  it.each(OTHERS)('language %s has a non-empty answer for every key', (lang) => {
    const missing: string[] = [];
    for (const part of PARTS) {
      const tbl = table(lang, part);
      if (!tbl) continue;
      keys(part).forEach((en, i) => {
        const v = answer(tbl, en, i);
        if (typeof v !== 'string' || v.trim() === '') missing.push(`${part}: ${en}`);
      });
    }
    expect(missing.slice(0, 5)).toEqual([]);
  });

  it.each(OTHERS)('language %s keeps every numbered placeholder of the default text', (lang) => {
    const broken: string[] = [];
    for (const part of PARTS) {
      const tbl = table(lang, part);
      if (!tbl) continue;
      keys(part).forEach((en, i) => {
        const v = answer(tbl, en, i);
        if (typeof v !== 'string' || !/\{\d+\}/.test(en)) return;
        if (JSON.stringify(holes(v)) !== JSON.stringify(holes(en))) broken.push(`${part}: ${en} => ${v}`);
      });
    }
    expect(broken.slice(0, 5)).toEqual([]);
  });

  it('the default language key lists hold no duplicate text within one part', () => {
    const dupes: string[] = [];
    for (const part of PARTS) {
      const list = keys(part);
      const seen = new Set<string>();
      for (const k of list) { if (seen.has(k)) dupes.push(`${part}: ${k}`); seen.add(k); }
    }
    expect(dupes.slice(0, 5)).toEqual([]);
  });
});

describe('switching languages through the public functions', () => {
  it('starts in the default language and returns text unchanged', () => {
    expect(language()).toBe('en');
    expect(t('Home')).toBe('Home');
  });

  it('ignores a language that is not in the list', async () => {
    await setLanguage('xx-NOPE');
    expect(language()).toBe('en');
  });

  it('switches to German, translates known text, sets the page language and falls back for unknown text', async () => {
    const de = table('de', 'en.json') ?? {};
    const list = keys('en.json');
    const idx = list.indexOf('Home');
    const expected = answer(de, 'Home', idx);
    let heard = 0;
    const stop = onLanguage(() => { heard += 1; });
    document.body.innerHTML = '<p id="a">Home</p><code id="b">Home</code><p id="c" title="Preferences">x</p>';
    await setLanguage('de');
    stop();
    expect(language()).toBe('de');
    expect(heard).toBe(1);
    expect(document.documentElement.lang).toBe('de');
    expect(t('Home')).toBe(expected);
    expect(t('  Home  ')).toBe(`  ${expected}  `);
    expect(t('Zq unknown sentence that no table holds')).toBe('Zq unknown sentence that no table holds');
    expect(document.getElementById('a')?.textContent).toBe(expected);
    expect(document.getElementById('b')?.textContent).toBe('Home');
    expect(document.getElementById('c')?.getAttribute('title')).toBe(answer(de, 'Preferences', list.indexOf('Preferences')));
    expect(localStorage.getItem('formpublisher_lang')).toBe('de');
  });

  it('fills numbered placeholders of a pattern key with the runtime value', async () => {
    await setLanguage('de');
    const de = table('de', 'en.json') ?? {};
    const list = keys('en.json');
    const tr = answer(de, 'Engine {0}', list.indexOf('Engine {0}'));
    expect(typeof tr).toBe('string');
    expect(t('Engine 0.11.0')).toBe(String(tr).replace('{0}', '0.11.0'));
  });

  it('translates a known text followed by a colon by keeping the colon', async () => {
    await setLanguage('de');
    const de = table('de', 'en.json') ?? {};
    const tr = answer(de, 'Preferences', keys('en.json').indexOf('Preferences'));
    expect(t('Preferences:')).toBe(`${tr}:`);
  });

  it('maps the Chinese script codes to region locales', async () => {
    await setLanguage('zh-Hant');
    expect(language()).toBe('zh-Hant');
    expect(locale()).toBe('zh-TW');
    await setLanguage('zh-Hans');
    expect(locale()).toBe('zh-CN');
  });

  it('switching back to the default language restores the original text in the page', async () => {
    document.body.innerHTML = '<p id="a">Home</p>';
    await setLanguage('fr');
    expect(document.getElementById('a')?.textContent).not.toBe('Home');
    await setLanguage('en');
    expect(language()).toBe('en');
    expect(document.getElementById('a')?.textContent).toBe('Home');
    expect(t('Home')).toBe('Home');
  });
});
