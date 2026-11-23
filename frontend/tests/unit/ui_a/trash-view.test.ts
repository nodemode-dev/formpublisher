import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { TrashPage } from '../../../src/ui/trash';
import type { App } from '../../../src/app-api';
import { emit } from '../../../src/events';

interface Call { method: string; url: string; body: string | null }
type Answer = { status: number; body?: unknown };

let calls: Call[] = [];
let routes: Map<string, Answer[]> = new Map();
let notices: { kind: string; text: string }[] = [];
const hosts: HTMLElement[] = [];
const noticeFn = (e: Event): void => { notices.push((e as CustomEvent<{ kind: string; text: string }>).detail); };

function answer(method: string, url: string, ...a: Answer[]): void {
  routes.set(`${method} ${url}`, a);
}

function reply(a: Answer): Response {
  if (a.status === 204) return new Response(null, { status: 204 });
  return new Response(JSON.stringify(a.body ?? {}), { status: a.status, headers: { 'content-type': 'application/json' } });
}

const flush = async (): Promise<void> => { for (let i = 0; i < 8; i += 1) await new Promise((r) => setTimeout(r, 0)); };

function mount(confirm: (...a: unknown[]) => Promise<boolean> = async () => true): { page: TrashPage; host: HTMLElement; app: { refreshSites: ReturnType<typeof vi.fn> } } {
  const host = document.createElement('div');
  document.body.appendChild(host);
  hosts.push(host);
  const app = { refreshSites: vi.fn(async () => undefined) };
  const page = new TrashPage(app as unknown as App, host, confirm as never);
  return { page, host, app };
}

const rows = (host: HTMLElement): HTMLElement[] => Array.from(host.querySelectorAll<HTMLElement>('.fp-tr-list .fp-tr-row'));
const cell = (row: HTMLElement, sel: string): string => row.querySelector(sel)?.textContent ?? '';
const sent = (method: string): Call[] => calls.filter((c) => c.method === method);

beforeEach(() => {
  document.body.innerHTML = '<div id="overlay-root"></div>';
  calls = [];
  routes = new Map();
  notices = [];
  document.addEventListener('fp:notice', noticeFn);
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    const method = init?.method ?? 'GET';
    calls.push({ method, url, body: typeof init?.body === 'string' ? init.body : null });
    const list = routes.get(`${method} ${url}`);
    if (!list || list.length === 0) return reply({ status: 404, body: { detail: 'no route' } });
    return reply(list.length > 1 ? list.shift() as Answer : list[0]);
  }));
});

afterEach(() => {
  document.removeEventListener('fp:notice', noticeFn);
  for (const h of hosts.splice(0)) h.hidden = true;
  vi.unstubAllGlobals();
});

const SITE = { entry: 'e1', kind: 'site', label: 'Bakery', origin: 'sites/bakery', moved: '', size: 500 };
const BUILD = { entry: 'e2', kind: 'build', label: 'Bakery build', origin: 'builds/bakery/0123456789ab', moved: '2026-05-01T10:00:00Z', size: 2048 };

describe('trash page lists what the engine holds', () => {
  it('shows one row per entry with its label, kind and size, and enables Empty Trash', async () => {
    answer('GET', '/api/trash', { status: 200, body: { entries: [SITE, BUILD] } });
    const { page, host } = mount();
    await page.refresh();
    const r = rows(host);
    expect(r.map((n) => cell(n, '.fp-tr-label'))).toEqual(['Bakery', 'Bakery build']);
    expect(r.map((n) => cell(n, '.fp-tr-kind'))).toEqual(['Site', 'Build']);
    expect(r.map((n) => cell(n, '.fp-tr-size'))).toEqual(['500 B', '2.0 KB']);
    expect(cell(r[0], '.fp-tr-moved')).toBe('-');
    expect(host.querySelector<HTMLElement>('.fp-tr-empty')?.hidden).toBe(true);
    expect(host.querySelector<HTMLElement>('.fp-tr-skel')?.hidden).toBe(true);
    expect(host.querySelector<HTMLButtonElement>('[data-t="empty"]')?.disabled).toBe(false);
  });

  it('keeps the skeleton until the first answer arrives', () => {
    const { host } = mount();
    expect(host.querySelector<HTMLElement>('.fp-tr-skel')?.hidden).toBe(false);
    expect(host.querySelector<HTMLElement>('.fp-tr-empty')?.hidden).toBe(true);
  });

  it('says the trash is empty and disables Empty Trash when the engine has nothing', async () => {
    answer('GET', '/api/trash', { status: 200, body: [] });
    const { page, host } = mount();
    await page.refresh();
    expect(rows(host)).toHaveLength(0);
    const empty = host.querySelector<HTMLElement>('.fp-tr-empty');
    expect(empty?.hidden).toBe(false);
    expect(empty?.textContent).toContain('Nothing in the trash');
    expect(host.querySelector<HTMLButtonElement>('[data-t="empty"]')?.disabled).toBe(true);
  });

  it('shows a refusal of the list as an error notice carrying the engine sentence', async () => {
    answer('GET', '/api/trash', { status: 500, body: { detail: 'The trash folder cannot be read' } });
    const { page } = mount();
    await page.refresh();
    expect(notices).toContainEqual({ kind: 'error', text: 'The trash folder cannot be read' });
  });

  it('patches the same row node in place when a live event brings the list again', async () => {
    answer('GET', '/api/trash', { status: 200, body: [SITE] }, { status: 200, body: [{ ...SITE, label: 'Bakery old', size: 3 * 1048576 }, BUILD] });
    const { page, host } = mount();
    await page.refresh();
    const before = rows(host)[0];
    emit('fp:live', { type: 'trash.changed' });
    await flush();
    const after = rows(host);
    expect(after).toHaveLength(2);
    expect(after[0]).toBe(before);
    expect(cell(before, '.fp-tr-label')).toBe('Bakery old');
    expect(cell(before, '.fp-tr-size')).toBe('3.0 MB');
  });

  it('ignores live events about other things', async () => {
    answer('GET', '/api/trash', { status: 200, body: [SITE] });
    const { page } = mount();
    await page.refresh();
    const n = calls.length;
    emit('fp:live', { type: 'routes.checked' });
    await flush();
    expect(calls.length).toBe(n);
  });
});

describe('trash page actions send the right requests', () => {
  it('Restore posts to the entry restore address with no body and reloads the sites of a site entry', async () => {
    answer('GET', '/api/trash', { status: 200, body: [SITE] });
    answer('POST', '/api/trash/e1/restore', { status: 200, body: { ok: true } });
    const { page, host, app } = mount();
    await page.refresh();
    rows(host)[0].querySelector<HTMLButtonElement>('[data-t="restore"]')?.click();
    await flush();
    const post = sent('POST');
    expect(post).toHaveLength(1);
    expect(post[0].url).toBe('/api/trash/e1/restore');
    expect(post[0].body).toBeNull();
    expect(notices).toContainEqual({ kind: 'ok', text: 'Restored Bakery' });
    expect(app.refreshSites).toHaveBeenCalledTimes(1);
  });

  it('a restore refusal is shown as the engine sentence', async () => {
    answer('GET', '/api/trash', { status: 200, body: [BUILD] });
    answer('POST', '/api/trash/e2/restore', { status: 409, body: { detail: 'A build with that id already exists', code: 'exists' } });
    const { page, host, app } = mount();
    await page.refresh();
    rows(host)[0].querySelector<HTMLButtonElement>('[data-t="restore"]')?.click();
    await flush();
    expect(notices).toContainEqual({ kind: 'error', text: 'A build with that id already exists' });
    expect(app.refreshSites).not.toHaveBeenCalled();
  });

  it('Delete for good asks first and sends nothing when the answer is no', async () => {
    answer('GET', '/api/trash', { status: 200, body: [SITE] });
    const confirm = vi.fn(async () => false);
    const { page, host } = mount(confirm);
    await page.refresh();
    rows(host)[0].querySelector<HTMLButtonElement>('[data-t="delete"]')?.click();
    await flush();
    expect(confirm).toHaveBeenCalledTimes(1);
    expect(String((confirm.mock.calls[0] as unknown[])[1])).toContain('Bakery');
    expect(sent('DELETE')).toHaveLength(0);
  });

  it('Delete for good sends DELETE for that entry once confirmed', async () => {
    answer('GET', '/api/trash', { status: 200, body: [SITE] });
    answer('DELETE', '/api/trash/e1', { status: 204 });
    const { page, host } = mount();
    await page.refresh();
    rows(host)[0].querySelector<HTMLButtonElement>('[data-t="delete"]')?.click();
    await flush();
    expect(sent('DELETE').map((c) => c.url)).toEqual(['/api/trash/e1']);
    expect(notices).toContainEqual({ kind: 'ok', text: 'Deleted Bakery' });
  });

  it('Empty Trash sends DELETE to the whole trash once confirmed', async () => {
    answer('GET', '/api/trash', { status: 200, body: [SITE, BUILD] });
    answer('DELETE', '/api/trash', { status: 204 });
    const { page, host } = mount();
    await page.refresh();
    host.querySelector<HTMLButtonElement>('[data-t="empty"]')?.click();
    await flush();
    expect(sent('DELETE').map((c) => c.url)).toEqual(['/api/trash']);
    expect(notices).toContainEqual({ kind: 'ok', text: 'The trash is empty' });
  });

  it('escapes an entry id with a slash in the restore address', async () => {
    answer('GET', '/api/trash', { status: 200, body: [{ ...SITE, entry: 'a/b' }] });
    answer('POST', '/api/trash/a%2Fb/restore', { status: 200, body: {} });
    const { page, host } = mount();
    await page.refresh();
    rows(host)[0].querySelector<HTMLButtonElement>('[data-t="restore"]')?.click();
    await flush();
    expect(sent('POST')[0].url).toBe('/api/trash/a%2Fb/restore');
  });
});

describe('restore dialog when the engine cannot place an item', () => {
  async function openDialog(item: Record<string, unknown>, refusal: Record<string, unknown>): Promise<{ scrim: HTMLElement; input: HTMLInputElement; ok: HTMLButtonElement; host: HTMLElement }> {
    answer('GET', '/api/trash', { status: 200, body: [item] });
    answer('POST', `/api/trash/${String(item.entry)}/restore`, { status: 409, body: refusal });
    const { page, host } = mount();
    await page.refresh();
    rows(host)[0].querySelector<HTMLButtonElement>('[data-t="restore"]')?.click();
    await flush();
    const scrim = document.querySelector<HTMLElement>('#overlay-root .fp-scrim') as HTMLElement;
    const ok = Array.from(scrim.querySelectorAll<HTMLButtonElement>('.fp-dlg-foot button')).find((b) => b.textContent === 'Restore') as HTMLButtonElement;
    return { scrim, input: scrim.querySelector<HTMLInputElement>('input[type="text"]') as HTMLInputElement, ok, host };
  }

  it('opens a dialog naming the item and the folder its kind lives in', async () => {
    const { scrim } = await openDialog({ ...SITE, origin: null }, { detail: 'Origin unknown', code: 'origin-unknown' });
    expect(scrim.hidden).toBe(false);
    expect(scrim.querySelector('.fp-note')?.textContent).toContain('Bakery could not be placed on its own');
    expect(scrim.querySelector('.fp-tr-prefix')?.textContent).toBe('sites/');
  });

  it('refuses an empty name without sending a request', async () => {
    const { scrim, ok } = await openDialog({ ...SITE, origin: null }, { detail: 'Origin unknown', code: 'origin-unknown' });
    const before = sent('POST').length;
    ok.click();
    await flush();
    expect(scrim.querySelector('.fp-tr-origin-error')?.textContent).toBe('Type a name.');
    expect(sent('POST').length).toBe(before);
  });

  it('refuses a site name with capitals or spaces with the naming rule, before any request', async () => {
    const { scrim, input, ok } = await openDialog({ ...SITE, origin: null }, { detail: 'Origin unknown', code: 'origin-unknown' });
    const before = sent('POST').length;
    input.value = 'My Bakery';
    ok.click();
    await flush();
    expect(scrim.querySelector('.fp-tr-origin-error')?.textContent).toContain('lowercase letters, digits and hyphens');
    expect(sent('POST').length).toBe(before);
  });

  it('refuses a build path whose id is not 12 hex characters', async () => {
    const { scrim, input, ok } = await openDialog({ ...BUILD, origin: null }, { detail: 'Origin unknown', code: 'origin-unknown' });
    expect(scrim.querySelector('.fp-tr-prefix')?.textContent).toBe('builds/');
    input.value = 'bakery/xyz';
    ok.click();
    await flush();
    expect(scrim.querySelector('.fp-tr-origin-error')?.textContent).toContain('12 characters from 0 to 9 and a to f');
  });

  it('sends the typed name under its kind folder as the origin and closes on success', async () => {
    const { scrim, input, ok } = await openDialog({ ...SITE, origin: null }, { detail: 'Origin unknown', code: 'origin-unknown' });
    routes.set('POST /api/trash/e1/restore', [{ status: 200, body: {} }]);
    input.value = '  /bakery-2 ';
    ok.click();
    await flush();
    const last = sent('POST').at(-1) as Call;
    expect(JSON.parse(last.body ?? '{}')).toEqual({ origin: 'sites/bakery-2' });
    expect(scrim.hidden).toBe(true);
    expect(notices).toContainEqual({ kind: 'ok', text: 'Restored Bakery' });
  });

  it('a locked key asks for its passphrase and refuses an empty one before sending', async () => {
    const key = { entry: 'k1', kind: 'key', label: 'Signing key', origin: 'keys/0123456789abcdef.pem', moved: '', size: 1 };
    const { scrim, ok } = await openDialog(key, { detail: 'Locked', code: 'passphrase-required' });
    expect(scrim.querySelector('.fp-note')?.textContent).toContain('Signing key is locked');
    const before = sent('POST').length;
    ok.click();
    await flush();
    const errs = Array.from(scrim.querySelectorAll('.fp-tr-origin-error')).map((n) => n.textContent);
    expect(errs).toContain('Type the passphrase.');
    expect(sent('POST').length).toBe(before);
  });

  it('a wrong passphrase is shown as the engine sentence and the field is cleared', async () => {
    const key = { entry: 'k1', kind: 'key', label: 'Signing key', origin: 'keys/0123456789abcdef.pem', moved: '', size: 1 };
    const { scrim, ok } = await openDialog(key, { detail: 'Locked', code: 'passphrase-required' });
    routes.set('POST /api/trash/k1/restore', [{ status: 403, body: { detail: 'That passphrase does not open the key', code: 'passphrase-wrong' } }]);
    const pass = scrim.querySelector<HTMLInputElement>('input[type="password"]') as HTMLInputElement;
    pass.value = 'guess';
    ok.click();
    await flush();
    expect(JSON.parse(sent('POST').at(-1)?.body ?? '{}')).toEqual({ passphrase: 'guess' });
    const errs = Array.from(scrim.querySelectorAll('.fp-tr-origin-error')).map((n) => n.textContent);
    expect(errs).toContain('That passphrase does not open the key');
    expect(pass.value).toBe('');
    expect(scrim.hidden).toBe(false);
  });
});
