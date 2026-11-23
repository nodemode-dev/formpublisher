import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { TemplatesSheet } from '../../../src/ui/templates-sheet';
import type { App } from '../../../src/app-api';

interface Call { method: string; url: string; body: string | null }
type Answer = { status: number; body?: unknown };
let calls: Call[] = [];
let routes: Map<string, Answer[]> = new Map();

function answer(method: string, url: string, ...a: Answer[]): void { routes.set(`${method} ${url}`, a); }

const flush = async (): Promise<void> => { for (let i = 0; i < 8; i += 1) await new Promise((r) => setTimeout(r, 0)); };

beforeEach(() => {
  document.body.innerHTML = '<div id="overlay-root"></div>';
  calls = [];
  routes = new Map();
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    const method = init?.method ?? 'GET';
    calls.push({ method, url, body: typeof init?.body === 'string' ? init.body : null });
    const list = routes.get(`${method} ${url}`);
    const a = !list || list.length === 0 ? { status: 404, body: { detail: 'no route' } } : list.length > 1 ? list.shift() as Answer : list[0];
    return new Response(JSON.stringify(a.body ?? {}), { status: a.status, headers: { 'content-type': 'application/json' } });
  }));
});

afterEach(() => { vi.unstubAllGlobals(); });

const BAKERY = { id: 'bakery', name: 'Bakery', description: 'A small shop site', bytes: 1048576, sha256: 'x', licence: 'MIT', credit: 'By Form', type: 'shop', preview: 'p.png' };
const DIARY = { id: 'diary', name: 'Diary', description: '', bytes: 3 * 1048576, sha256: 'y', licence: 'CC0', credit: '', type: 'blog', preview: null };
const FETCHED = { fetched: true, fetchedAt: '2026-05-01T10:00:00Z', items: [BAKERY, DIARY], notStartable: 1 };

function mount(folder: string | null = '/tmp/new'): { sheet: TemplatesSheet; app: { pickFolder: ReturnType<typeof vi.fn>; importFolder: ReturnType<typeof vi.fn> }; root: HTMLElement } {
  const app = { pickFolder: vi.fn(async () => folder), importFolder: vi.fn(async () => ({})) };
  const sheet = new TemplatesSheet(app as unknown as App);
  return { sheet, app, root: sheet.body };
}

const cards = (root: HTMLElement): HTMLElement[] => Array.from(root.querySelectorAll<HTMLElement>('.fp-tpl-list .fp-tpl-card'));
const t = (root: ParentNode, sel: string): string => root.querySelector(sel)?.textContent ?? '';
const btn = (root: ParentNode, sel: string): HTMLButtonElement => root.querySelector<HTMLButtonElement>(sel) as HTMLButtonElement;

describe('templates sheet', () => {
  it('opens on the kept list and invites a first fetch when nothing was fetched yet', async () => {
    answer('GET', '/api/templates', { status: 200, body: { fetched: false, items: [] } });
    const { sheet, root } = mount();
    await sheet.show();
    expect(sheet.isOpen).toBe(true);
    expect(calls.map((c) => `${c.method} ${c.url}`)).toEqual(['GET /api/templates']);
    expect(t(root, '[data-f="getlabel"]')).toBe('Get the templates');
    expect(t(root, '.fp-tpl-none')).toBe('No list yet. Press Get the templates to read it.');
    expect(cards(root)).toHaveLength(0);
  });

  it('shows one card per startable template with name, size in megabytes and licence', async () => {
    answer('GET', '/api/templates', { status: 200, body: FETCHED });
    const { sheet, root } = mount();
    await sheet.show();
    const c = cards(root);
    expect(c.map((n) => t(n, '.fp-tpl-name'))).toEqual(['Bakery', 'Diary']);
    expect(t(c[0], '.fp-tpl-meta')).toBe('1.0 MB \u00b7 MIT');
    expect(t(c[1], '.fp-tpl-meta')).toBe('3.0 MB \u00b7 CC0');
    expect(t(c[1], '.fp-tpl-desc')).toBe('A whole FormWeb site with its pages and pictures.');
    expect(t(root, '[data-f="getlabel"]')).toBe('Check again');
    expect(root.querySelectorAll('.is-skeleton')).toHaveLength(0);
  });

  it('counts the whole sites and explains the library parts left out', async () => {
    answer('GET', '/api/templates', { status: 200, body: FETCHED });
    const { sheet, root } = mount();
    await sheet.show();
    expect(t(root, '[data-f="said"]')).toMatch(/: 2 whole sites\.$/);
    expect(t(root, '[data-f="more"]')).toBe("1 more is a part for FormWeb's own library, not a whole site, so it is not offered here.");
  });

  it('loads a preview picture only for templates that have one', async () => {
    answer('GET', '/api/templates', { status: 200, body: FETCHED });
    const { sheet, root } = mount();
    await sheet.show();
    const [a, b] = cards(root).map((n) => n.querySelector('img') as HTMLImageElement);
    expect(a.getAttribute('src')).toBe('/api/templates/preview?id=bakery');
    expect(b.hasAttribute('src')).toBe(false);
  });

  it('offers a type filter only for types present, and filtering hides the other cards', async () => {
    answer('GET', '/api/templates', { status: 200, body: FETCHED });
    const { sheet, root } = mount();
    await sheet.show();
    const chips = Array.from(root.querySelectorAll<HTMLButtonElement>('.fp-tpl-chip'));
    expect(chips.map((c) => c.textContent)).toEqual(['All', 'Blog', 'Shop window']);
    expect(chips[0].getAttribute('aria-pressed')).toBe('true');
    chips[1].click();
    expect(cards(root).map((n) => n.hidden)).toEqual([true, false]);
    expect(chips[1].getAttribute('aria-pressed')).toBe('true');
    chips[0].click();
    expect(cards(root).map((n) => n.hidden)).toEqual([false, false]);
  });

  it('Get the templates posts a fetch and patches the same card nodes in place', async () => {
    answer('GET', '/api/templates', { status: 200, body: FETCHED });
    answer('POST', '/api/templates/fetch', { status: 200, body: { ...FETCHED, items: [{ ...BAKERY, name: 'Bakery 2' }, DIARY], notStartable: 0 } });
    const { sheet, root } = mount();
    await sheet.show();
    const before = cards(root)[0];
    btn(root, '[data-a="get"]').click();
    await flush();
    expect(calls.at(-1)).toMatchObject({ method: 'POST', url: '/api/templates/fetch' });
    expect(cards(root)[0]).toBe(before);
    expect(t(before, '.fp-tpl-name')).toBe('Bakery 2');
    expect(t(root, '[data-f="more"]')).toBe('');
    expect(btn(root, '[data-a="get"]').disabled).toBe(false);
  });

  it('shows a refusal of the fetch as the engine sentence marked as an error', async () => {
    answer('GET', '/api/templates', { status: 200, body: { fetched: false, items: [] } });
    answer('POST', '/api/templates/fetch', { status: 502, body: { detail: 'The template list could not be downloaded' } });
    const { sheet, root } = mount();
    await sheet.show();
    btn(root, '[data-a="get"]').click();
    await flush();
    expect(t(root, '[data-f="said"]')).toBe('The template list could not be downloaded');
    expect(root.querySelector('[data-f="status"]')?.classList.contains('is-error')).toBe(true);
  });

  it('starting a template sends nothing when no folder is chosen', async () => {
    answer('GET', '/api/templates', { status: 200, body: FETCHED });
    const { sheet, root, app } = mount(null);
    await sheet.show();
    btn(cards(root)[0], '[data-a="start"]').click();
    await flush();
    expect(app.pickFolder).toHaveBeenCalledTimes(1);
    expect(calls.filter((c) => c.url === '/api/templates/start')).toHaveLength(0);
    expect(btn(root, '[data-a="publish"]').disabled).toBe(true);
  });

  it('starting a template posts its id and the chosen folder, then reports the project and enables the next steps', async () => {
    answer('GET', '/api/templates', { status: 200, body: FETCHED });
    answer('POST', '/api/templates/start', { status: 200, body: { template: 'bakery', name: 'Bakery', project: '/tmp/new/bakery.fweb', files: 12 } });
    const { sheet, root } = mount('/tmp/new');
    await sheet.show();
    btn(cards(root)[0], '[data-a="start"]').click();
    await flush();
    const start = calls.find((c) => c.url === '/api/templates/start') as Call;
    expect(start.method).toBe('POST');
    expect(JSON.parse(start.body ?? '{}')).toEqual({ template: 'bakery', folder: '/tmp/new' });
    expect(t(root, '[data-f="done"]')).toBe('Made a FormWeb project from Bakery (12 files).');
    expect(t(root, '[data-f="path"]')).toBe('/tmp/new/bakery.fweb');
    expect(btn(root, '[data-a="edit"]').disabled).toBe(false);
    expect(btn(root, '[data-a="publish"]').disabled).toBe(false);
  });

  it('Publish it closes the sheet and imports the new project folder', async () => {
    answer('GET', '/api/templates', { status: 200, body: FETCHED });
    answer('POST', '/api/templates/start', { status: 200, body: { template: 'diary', name: 'Diary', project: '/tmp/new/diary.fweb', files: 1 } });
    const { sheet, root, app } = mount();
    await sheet.show();
    btn(cards(root)[1], '[data-a="start"]').click();
    await flush();
    expect(t(root, '[data-f="done"]')).toBe('Made a FormWeb project from Diary (1 file).');
    btn(root, '[data-a="publish"]').click();
    await flush();
    expect(sheet.isOpen).toBe(false);
    expect(app.importFolder).toHaveBeenCalledWith('/tmp/new/diary.fweb');
  });

  it('a refused start shows the engine sentence and keeps the next steps disabled', async () => {
    answer('GET', '/api/templates', { status: 200, body: FETCHED });
    answer('POST', '/api/templates/start', { status: 409, body: { detail: 'The SHA-256 of the download does not match' } });
    const { sheet, root } = mount();
    await sheet.show();
    btn(cards(root)[0], '[data-a="start"]').click();
    await flush();
    expect(t(root, '[data-f="done"]')).toBe('The SHA-256 of the download does not match');
    expect(root.querySelector('.fp-tpl-done')?.classList.contains('is-error')).toBe(true);
    expect(t(root, '[data-f="path"]')).toBe('');
    expect(btn(root, '[data-a="edit"]').disabled).toBe(true);
    expect(btn(root, '[data-a="publish"]').disabled).toBe(true);
  });

  it('says the engine is not reachable when the kept list cannot be requested', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('network'); }));
    const { sheet, root } = mount();
    await sheet.show();
    expect(t(root, '[data-f="said"]')).toBe('The engine is not reachable');
    expect(root.querySelector('[data-f="status"]')?.classList.contains('is-error')).toBe(true);
  });
});
