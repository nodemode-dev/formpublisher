import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { RevisionsView, RevisionsDialog } from '../../../src/ui/revisions';

type Answer = { status: number; body?: unknown };
let urls: string[] = [];
let routes: Map<string, Answer[]> = new Map();

function answer(url: string, ...a: Answer[]): void { routes.set(url, a); }

const flush = async (): Promise<void> => { for (let i = 0; i < 8; i += 1) await new Promise((r) => setTimeout(r, 0)); };

beforeEach(() => {
  document.body.innerHTML = '<div id="overlay-root"></div><div id="host"></div>';
  urls = [];
  routes = new Map();
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    urls.push(url);
    const list = routes.get(url);
    const a = !list || list.length === 0 ? { status: 404, body: { detail: 'no route' } } : list.length > 1 ? list.shift() as Answer : list[0];
    return new Response(JSON.stringify(a.body ?? {}), { status: a.status, headers: { 'content-type': 'application/json' } });
  }));
});

afterEach(() => { vi.unstubAllGlobals(); });

const host = (): HTMLElement => document.getElementById('host') as HTMLElement;
const items = (): HTMLElement[] => Array.from(host().querySelectorAll<HTMLElement>('.fp-rv-item'));
const diffRows = (): HTMLElement[] => Array.from(host().querySelectorAll<HTMLElement>('.fp-rv-row'));
const text = (sel: string, root: ParentNode = host()): string => root.querySelector(sel)?.textContent ?? '';
const msg = (): HTMLElement => host().querySelector<HTMLElement>('[data-f="empty"]') as HTMLElement;

const R2 = { revision: 'r2', at: '2026-05-02T10:00:00Z', files: 3, bytes: 10, routes: 2, latest: true, changes: { added: 1, removed: 0, changed: 2 } };
const R1 = { revision: 'r1', at: '2026-05-01T10:00:00Z', files: 1, bytes: 5, routes: 1, latest: false };
const DIFF = {
  from: 'r1', to: 'r2',
  added: [{ path: 'about.html', size: 2048, sha256: 'abcdef0123456789' }],
  removed: [],
  changed: [{ path: 'index.html', from: { size: 1024, sha256: '111111aaaa' }, to: { size: 2048, sha256: '222222bbbb' } }],
  routes: { added: ['/about'], removed: [], from: 1, to: 2 },
  summary: { added: 1, removed: 0, changed: 1, same: 0, identical: false },
};

describe('revisions view', () => {
  it('asks for nothing and says to open a site when no site is given', async () => {
    const v = new RevisionsView(host());
    await v.load(null);
    expect(urls).toEqual([]);
    expect(text('[data-f="list-empty"]')).toBe('Open a site to see its revisions.');
    expect(text('[data-f="count"]')).toBe('0');
  });

  it('lists the revisions of the site with file counts, changes and the latest badge', async () => {
    answer('/api/sites/bakery/revisions', { status: 200, body: { revisions: [R2, R1] } });
    answer('/api/sites/bakery/diff?from=r1&to=r2', { status: 200, body: DIFF });
    const v = new RevisionsView(host());
    await v.load('bakery');
    const list = items();
    expect(list.map((n) => n.title)).toEqual(['r2', 'r1']);
    expect(list.map((n) => text('.fp-rv-files', n))).toEqual(['3 files', '1 file']);
    expect(text('.fp-rv-chg', list[0])).toBe('+1 -0 ~2');
    expect(text('.fp-rv-chg', list[1])).toBe('');
    expect(list[0].querySelector<HTMLElement>('.fp-rv-latest')?.hidden).toBe(false);
    expect(list[1].querySelector<HTMLElement>('.fp-rv-latest')?.hidden).toBe(true);
    expect(text('[data-f="count"]')).toBe('2');
  });

  it('selects the newest revision and compares it with the one before', async () => {
    answer('/api/sites/bakery/revisions', { status: 200, body: { revisions: [R2, R1] } });
    answer('/api/sites/bakery/diff?from=r1&to=r2', { status: 200, body: DIFF });
    const v = new RevisionsView(host());
    await v.load('bakery');
    expect(urls).toContain('/api/sites/bakery/diff?from=r1&to=r2');
    expect(items()[0].getAttribute('aria-selected')).toBe('true');
    expect(items()[1].getAttribute('aria-selected')).toBe('false');
    expect(text('[data-f="from"]')).toBe('r1');
    expect(text('[data-f="to"]')).toBe('r2');
    expect(text('[data-f="added"]')).toBe('1 added');
    expect(text('[data-f="removed"]')).toBe('0 removed');
    expect(text('[data-f="changed"]')).toBe('1 changed');
  });

  it('shows each difference with its kind, path and sizes in kilobytes', async () => {
    answer('/api/sites/bakery/revisions', { status: 200, body: { revisions: [R2, R1] } });
    answer('/api/sites/bakery/diff?from=r1&to=r2', { status: 200, body: DIFF });
    const v = new RevisionsView(host());
    await v.load('bakery');
    const rows = diffRows().map((n) => [text('.fp-rv-kind', n), text('.fp-rv-path', n), text('.fp-rv-size', n), text('.fp-rv-hash', n)]);
    expect(rows).toEqual([
      ['Added', 'about.html', '2.0 KB', 'abcdef0123'],
      ['Changed', 'index.html', '1.0 KB to 2.0 KB', '111111 222222'],
      ['Route added', '/about', '', ''],
    ]);
    expect(msg().hidden).toBe(true);
  });

  it('says nothing changed when the engine reports identical revisions', async () => {
    answer('/api/sites/s/revisions', { status: 200, body: { revisions: [R2, R1] } });
    answer('/api/sites/s/diff?from=r1&to=r2', { status: 200, body: { from: 'r1', to: 'r2', summary: { identical: true } } });
    const v = new RevisionsView(host());
    await v.load('s');
    expect(msg().hidden).toBe(false);
    expect(msg().textContent).toBe('Nothing changed between these two revisions.');
  });

  it('explains that a single revision has nothing to compare and sends no diff request', async () => {
    answer('/api/sites/s/revisions', { status: 200, body: { revisions: [R2] } });
    const v = new RevisionsView(host());
    await v.load('s');
    expect(urls.some((u) => u.includes('/diff'))).toBe(false);
    expect(msg().textContent).toContain('Only one revision so far');
  });

  it('says no revisions yet when the site has none', async () => {
    answer('/api/sites/s/revisions', { status: 200, body: { revisions: [] } });
    const v = new RevisionsView(host());
    await v.load('s');
    expect(text('[data-f="list-empty"]')).toBe('No revisions yet.');
  });

  it('shows a refusal of the revision list as the engine sentence', async () => {
    answer('/api/sites/gone/revisions', { status: 404, body: { detail: 'No site with id gone' } });
    const v = new RevisionsView(host());
    await v.load('gone');
    expect(msg().hidden).toBe(false);
    expect(msg().textContent).toBe('No site with id gone');
  });

  it('shows a refusal of the comparison as the engine sentence', async () => {
    answer('/api/sites/s/revisions', { status: 200, body: { revisions: [R2, R1] } });
    answer('/api/sites/s/diff?from=r1&to=r2', { status: 410, body: { detail: 'The older revision was pruned' } });
    const v = new RevisionsView(host());
    await v.load('s');
    expect(msg().textContent).toBe('The older revision was pruned');
    expect(diffRows()).toHaveLength(0);
  });

  it('clicking the oldest revision selects it and says it is the first one', async () => {
    answer('/api/sites/s/revisions', { status: 200, body: { revisions: [R2, R1] } });
    answer('/api/sites/s/diff?from=r1&to=r2', { status: 200, body: DIFF });
    const v = new RevisionsView(host());
    await v.load('s');
    items()[1].click();
    await flush();
    expect(items()[1].getAttribute('aria-selected')).toBe('true');
    expect(items()[0].classList.contains('is-on')).toBe(false);
    expect(msg().textContent).toBe('This is the first revision, so there is nothing to compare it with.');
    expect(diffRows()).toHaveLength(0);
    expect(text('[data-f="to"]')).toBe('r1');
  });

  it('Arrow Down moves the selection to the next revision', async () => {
    answer('/api/sites/s/revisions', { status: 200, body: { revisions: [R2, R1] } });
    answer('/api/sites/s/diff?from=r1&to=r2', { status: 200, body: DIFF });
    const v = new RevisionsView(host());
    await v.load('s');
    items()[0].dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }));
    await flush();
    expect(items()[1].getAttribute('aria-selected')).toBe('true');
  });

  it('keeps the same list nodes when the site arrives again with a new revision on top', async () => {
    const R3 = { revision: 'r3', at: '2026-05-03T10:00:00Z', files: 4, bytes: 1, routes: 2, latest: true };
    answer('/api/sites/s/revisions', { status: 200, body: { revisions: [R2, R1] } }, { status: 200, body: { revisions: [R3, { ...R2, latest: false }, R1] } });
    answer('/api/sites/s/diff?from=r1&to=r2', { status: 200, body: DIFF });
    const v = new RevisionsView(host());
    await v.load('s');
    const [n2, n1] = items();
    await v.load('s');
    const after = items();
    expect(after.map((n) => n.title)).toEqual(['r3', 'r2', 'r1']);
    expect(after[1]).toBe(n2);
    expect(after[2]).toBe(n1);
    expect(n2.querySelector<HTMLElement>('.fp-rv-latest')?.hidden).toBe(true);
    expect(n2.getAttribute('aria-selected')).toBe('true');
  });

  it('the dialog titles itself with the site name and loads that site', async () => {
    answer('/api/sites/s/revisions', { status: 200, body: { revisions: [] } });
    const d = new RevisionsDialog();
    d.show('s', 'Bakery');
    await flush();
    expect(d.isOpen).toBe(true);
    expect(d.panel.getAttribute('aria-label')).toBe('Revisions of Bakery');
    expect(urls).toEqual(['/api/sites/s/revisions']);
    d.close();
  });
});
