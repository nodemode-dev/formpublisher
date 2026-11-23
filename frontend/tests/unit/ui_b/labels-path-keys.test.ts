import { describe, it, expect } from 'vitest';
import { RESERVE_KEYS, RESERVE_LABELS } from '../../../src/ui/reserve-labels';
import { LANGUAGES } from '../../../src/i18n';
import { askPath } from '../../../src/ui/path-dialog';
import { isChord, chordLabel, leaves, ownsEvent, keeps, contain, onMac } from '../../../src/dock/keys';

describe('reserved label widths cover every language', () => {
  it('lists every language of the language menu exactly once', () => {
    expect(RESERVE_LABELS.map(([c]) => c).sort()).toEqual(LANGUAGES.map(([c]) => c).sort());
  });

  it('the default language row repeats the keys word for word', () => {
    const en = RESERVE_LABELS.find(([c]) => c === 'en');
    expect(en?.[1]).toEqual(RESERVE_KEYS);
  });

  it.each(RESERVE_LABELS.map(([c, l]) => [c, l] as const))('language %s gives one non-empty label per key', (_c, labels) => {
    expect(labels.length).toBe(RESERVE_KEYS.length);
    expect(labels.filter((l) => l.trim() === '')).toEqual([]);
  });

  it.each(RESERVE_LABELS.map(([c, l]) => [c, l] as const))('language %s keeps the step numbers and the example address', (_c, labels) => {
    for (let n = 1; n <= 4; n += 1) {
      const i = RESERVE_KEYS.indexOf(`Step ${n} of 4`);
      expect(labels[i]).toContain(String(n));
      expect(labels[i]).toContain('4');
    }
    const addr = RESERVE_KEYS.findIndex((k) => k.includes('http://127.0.0.1:8240'));
    expect(labels[addr]).toContain('http://127.0.0.1:8240');
  });
});

function overlay(): HTMLElement {
  document.body.innerHTML = '<button id="before">x</button><div id="ov"></div>';
  return document.getElementById('ov') as HTMLElement;
}

describe('open folder dialog', () => {
  it('refuses an empty path with a sentence and stays open', async () => {
    const ov = overlay();
    let done = false;
    const p = askPath(ov).then((v) => { done = true; return v; });
    (ov.querySelector('[data-act="ok"]') as HTMLElement).click();
    await Promise.resolve();
    expect(ov.querySelector('[role="alert"]')?.textContent).toBe('Enter a folder path.');
    expect(ov.querySelector('[role="dialog"]')).not.toBeNull();
    expect(done).toBe(false);
    (ov.querySelector('[data-act="cancel"]') as HTMLElement).click();
    expect(await p).toBeNull();
  });

  it('a path of only spaces counts as empty', async () => {
    const ov = overlay();
    void askPath(ov);
    const input = ov.querySelector('input') as HTMLInputElement;
    input.value = '    ';
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true }));
    expect(ov.querySelector('[role="alert"]')?.textContent).toBe('Enter a folder path.');
  });

  it('returns the typed path without surrounding spaces and closes', async () => {
    const ov = overlay();
    const p = askPath(ov);
    const input = ov.querySelector('input') as HTMLInputElement;
    input.value = '  /tmp/site out  ';
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true }));
    expect(await p).toBe('/tmp/site out');
    expect(ov.querySelector('[role="dialog"]')).toBeNull();
  });

  it('Escape closes the dialog without a path', async () => {
    const ov = overlay();
    const p = askPath(ov);
    (ov.querySelector('input') as HTMLInputElement).dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true }));
    expect(await p).toBeNull();
    expect(ov.children.length).toBe(0);
  });

  it('puts the cursor in the path field when it opens', () => {
    const ov = overlay();
    void askPath(ov);
    expect(document.activeElement).toBe(ov.querySelector('input'));
  });
});

const key = (init: KeyboardEventInit): KeyboardEvent => new KeyboardEvent('keydown', { bubbles: true, cancelable: true, ...init });

describe('dock keyboard chord', () => {
  const mod = onMac() ? { metaKey: true } : { ctrlKey: true };

  it('the platform modifier with J opens the dock and the label names it', () => {
    expect(isChord({}, key({ code: 'KeyJ', ...mod }))).toBe(true);
    expect(chordLabel({})).toBe(onMac() ? 'Cmd+J' : 'Ctrl+J');
  });

  it('J with Shift or Alt, or another letter, is not the chord', () => {
    expect(isChord({}, key({ code: 'KeyJ', shiftKey: true, ...mod }))).toBe(false);
    expect(isChord({}, key({ code: 'KeyJ', altKey: true, ...mod }))).toBe(false);
    expect(isChord({}, key({ code: 'KeyK', ...mod }))).toBe(false);
    expect(isChord({}, key({ code: 'KeyJ' }))).toBe(false);
  });

  it('a host that defines its own chord and label is obeyed', () => {
    const a = { isDockChord: (e: KeyboardEvent) => e.key === 'F9', chordLabel: () => 'F9' };
    expect(isChord(a, key({ key: 'F9' }))).toBe(true);
    expect(isChord(a, key({ code: 'KeyJ', ...mod }))).toBe(false);
    expect(chordLabel(a)).toBe('F9');
  });

  it('keys the host asks to pass through leave the dock, others stay inside', () => {
    const a = { passKey: (e: KeyboardEvent) => e.key === 'F1' };
    expect(leaves(a, key({ key: 'F1' }))).toBe(true);
    expect(leaves(a, key({ key: 'a' }))).toBe(false);
  });

  it('typing inside the dock does not reach the page, the chord still does', () => {
    document.body.innerHTML = '<div class="ft-dock"><input id="i"></div>';
    const dock = document.querySelector('.ft-dock') as HTMLElement;
    contain(dock, {});
    let heard: string[] = [];
    const listen = (e: Event): void => { heard.push((e as KeyboardEvent).code || (e as KeyboardEvent).key); };
    document.body.addEventListener('keydown', listen);
    const input = document.getElementById('i') as HTMLInputElement;
    input.dispatchEvent(key({ key: 'a', code: 'KeyA' }));
    input.dispatchEvent(key({ code: 'KeyJ', ...mod }));
    document.body.removeEventListener('keydown', listen);
    expect(heard).toEqual(['KeyJ']);
    heard = [];
  });

  it('events aimed inside the dock belong to it, events elsewhere do not', () => {
    document.body.innerHTML = '<div class="ft-dock"><b id="in">x</b></div><b id="out">y</b>';
    const inside = key({ key: 'a' });
    (document.getElementById('in') as HTMLElement).dispatchEvent(inside);
    const outside = key({ key: 'a' });
    (document.getElementById('out') as HTMLElement).dispatchEvent(outside);
    expect(ownsEvent(inside)).toBe(true);
    expect(ownsEvent(outside)).toBe(false);
    expect(keeps({}, inside)).toBe(true);
    const chord = key({ code: 'KeyJ', ...mod });
    (document.getElementById('in') as HTMLElement).dispatchEvent(chord);
    expect(keeps({}, chord)).toBe(false);
  });
});
