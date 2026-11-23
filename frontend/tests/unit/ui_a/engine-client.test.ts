import { describe, it, expect, vi, beforeEach } from 'vitest';
import { api, ApiError, toSite, toRoute } from '../../../src/api';

interface Call { url: string; init: RequestInit | undefined }

function engine(status: number, body: unknown, type = 'application/json'): Call[] {
  const calls: Call[] = [];
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    calls.push({ url, init });
    if (status === 204) return new Response(null, { status });
    const text = typeof body === 'string' ? body : JSON.stringify(body);
    return new Response(text, { status, headers: { 'content-type': type } });
  }));
  return calls;
}

function engineDown(): void {
  vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('connection refused'); }));
}

async function refusal(p: Promise<unknown>): Promise<ApiError> {
  try {
    await p;
  } catch (e) {
    if (e instanceof ApiError) return e;
    throw e;
  }
  throw new Error('expected a refusal');
}

beforeEach(() => {
  vi.unstubAllGlobals();
});

describe('site list from the engine', () => {
  it('lists every site the engine answers with, in order, keeping names and route counts', async () => {
    const calls = engine(200, { sites: [
      { id: 's1', name: 'Harbour', routes: ['/', '/about', '/fares'], size: 2048, revisions: [{}, {}] },
      { id: 's2', title: 'Blog', route_count: 7 },
    ] });
    const sites = await api.sites();
    expect(calls[0].url).toBe('/api/sites');
    expect(sites.map((s) => s.name)).toEqual(['Harbour', 'Blog']);
    expect(sites[0].routeCount).toBe(3);
    expect(sites[0].size).toBe(2048);
    expect(sites[0].revisions).toBe(2);
    expect(sites[1].routeCount).toBe(7);
    expect(sites[1].revisions).toBe(0);
  });

  it('accepts a bare array answer and drops entries that have no id', async () => {
    engine(200, [{ id: 'a' }, { name: 'no id' }, 'junk', null, { site_id: 'b', slug: 'bee' }]);
    const sites = await api.sites();
    expect(sites.map((s) => [s.id, s.name])).toEqual([['a', 'a'], ['b', 'bee']]);
  });

  it('shows an empty list when the engine answers with an unexpected shape', async () => {
    engine(200, { items: [{ id: 'x' }] });
    expect(await api.sites()).toEqual([]);
  });
});

describe('site mapping', () => {
  it('labels a site received from FormWeb as FormWeb and a packaged site as fpub', () => {
    expect(toSite({ id: 'r', source: { url: 'receive:abc' } })?.source).toBe('FormWeb');
    expect(toSite({ id: 'p', source: { fpub: { v: 1 }, path: '/tmp/a.fpub' } })?.kind).toBe('fpub');
    expect(toSite({ id: 'f', source: { kind: 'folder', path: '/srv/site' } })).toMatchObject({ source: '/srv/site', kind: 'folder' });
    expect(toSite({ id: 's', source: 'upload.zip' })).toMatchObject({ source: 'upload.zip', kind: '' });
  });

  it('reads the import time and size from any of the spellings the engine uses', () => {
    expect(toSite({ id: 'a', imported_at: '2026-01-02' })?.importedAt).toBe('2026-01-02');
    expect(toSite({ id: 'b', createdAt: '2026-03-04' })?.importedAt).toBe('2026-03-04');
    expect(toSite({ id: 'c', size_bytes: 10 })?.size).toBe(10);
    expect(toSite({ id: 'd', bytes: 11 })?.size).toBe(11);
    expect(toSite({ id: 'e', size: Number.NaN })?.size).toBeNull();
  });

  it('takes a numeric id as text and refuses non objects', () => {
    expect(toSite({ id: 42 })?.id).toBe('42');
    expect(toSite(['id'])).toBeNull();
    expect(toSite('s1')).toBeNull();
  });

  it('turns route strings and route objects into paths with their page files', () => {
    expect(toRoute('/about')).toEqual({ path: '/about', page: '' });
    expect(toRoute({ route: '/fr/', file: 'fr/index.html', locale: 'fr' })).toEqual({ path: '/fr/', page: 'fr/index.html', locale: 'fr', item: undefined, stylesheet: undefined });
    expect(toRoute({ page: 'x.html' })).toBeNull();
  });
});

describe('refusals from the engine become sentences', () => {
  it('uses the detail sentence of a refusal and names its status', async () => {
    engine(404, { detail: 'No site with that id' });
    const e = await refusal(api.site('missing'));
    expect(e.message).toBe('No site with that id');
    expect(e.status).toBe(404);
    expect(e.code).toBe('not-found');
  });

  it('uses the first validation message when the engine answers with a list of problems', async () => {
    engine(422, { detail: [{ loc: ['body', 'path'], msg: 'Field required' }, { msg: 'second' }] });
    const e = await refusal(api.importPath(''));
    expect(e.message).toBe('Field required');
    expect(e.code).toBe('unprocessable');
  });

  it('keeps the code the engine sends over the one implied by the status', async () => {
    engine(409, { detail: 'Already imported', code: 'duplicate-site' });
    const e = await refusal(api.importPath('/srv/site'));
    expect(e.code).toBe('duplicate-site');
    expect(e.message).toBe('Already imported');
  });

  it('says the engine is not reachable when the request cannot be sent', async () => {
    engineDown();
    const e = await refusal(api.sites());
    expect(e.message).toBe('The engine is not reachable');
    expect(e.status).toBe(0);
    expect(e.code).toBe('unreachable');
  });

  it('falls back to the status line when the refusal has no readable body', async () => {
    engine(503, 'gateway down', 'text/plain');
    const e = await refusal(api.settings());
    expect(e.message).toBe('503');
    expect(e.code).toBe('internal');
  });

  it('classifies unknown client errors as invalid and unknown server errors as internal', () => {
    expect(new ApiError('x', 418).code).toBe('invalid');
    expect(new ApiError('x', 599).code).toBe('internal');
    expect(new ApiError('x', 413).code).toBe('too-large');
    expect(new ApiError('x', 401).code).toBe('unauthorized');
  });

  it('refuses a site answer that carries no id instead of showing an empty site', async () => {
    engine(200, { site: { name: 'nameless' } });
    const e = await refusal(api.site('s1'));
    expect(e.message).toBe('The engine returned an unexpected answer');
    expect(e.status).toBe(502);
  });
});

describe('requests the client sends', () => {
  it('imports a folder by posting its path as JSON and returns the new site', async () => {
    const calls = engine(201, { site: { id: 'n1', name: 'New' } });
    const site = await api.importPath('/home/me/site');
    expect(calls[0].url).toBe('/api/sites/import');
    expect(calls[0].init?.method).toBe('POST');
    expect(JSON.parse(String(calls[0].init?.body))).toEqual({ path: '/home/me/site' });
    expect(new Headers(calls[0].init?.headers).get('content-type')).toBe('application/json');
    expect(site).toMatchObject({ id: 'n1', name: 'New' });
  });

  it('uploads a zip as a form field named file', async () => {
    const calls = engine(200, { id: 'z1' });
    const file = new File(['PK'], 'site.zip', { type: 'application/zip' });
    const site = await api.importZip(file);
    const body = calls[0].init?.body;
    expect(body).toBeInstanceOf(FormData);
    expect(((body as FormData).get('file') as File).name).toBe('site.zip');
    expect(site.id).toBe('z1');
  });

  it('removes a site with DELETE and escapes the id in the path', async () => {
    const calls = engine(204, null);
    await expect(api.removeSite('a b/c')).resolves.toBeUndefined();
    expect(calls[0].url).toBe('/api/sites/a%20b%2Fc');
    expect(calls[0].init?.method).toBe('DELETE');
  });

  it('asks for the routes of one site and lists them', async () => {
    const calls = engine(200, { routes: ['/', { path: '/blog', page: 'blog.html' }, 5] });
    const routes = await api.routes('s/1');
    expect(calls[0].url).toBe('/api/sites/s%2F1/routes');
    expect(routes.map((r) => r.path)).toEqual(['/', '/blog']);
  });

  it('saves settings with PUT and the patch as the body', async () => {
    const calls = engine(200, { theme: 'dark' });
    expect(await api.putSettings({ theme: 'dark' })).toEqual({ theme: 'dark' });
    expect(calls[0].init?.method).toBe('PUT');
    expect(JSON.parse(String(calls[0].init?.body))).toEqual({ theme: 'dark' });
  });

  it('imports the current FormWeb project with no body, or the named project as JSON', async () => {
    const calls = engine(200, { site: { id: 'fw' }, message: 'Imported' });
    expect(await api.formwebImportCurrent()).toMatchObject({ site: { id: 'fw' }, message: 'Imported' });
    expect(calls[0].init?.body).toBeUndefined();
    await api.formwebImportCurrent('proj-9');
    expect(JSON.parse(String(calls[1].init?.body))).toEqual({ project: 'proj-9' });
  });

  it('reports no site and the engine sentence when FormWeb has nothing open', async () => {
    engine(200, { site: null, message: 'No project is open in FormWeb' });
    expect(await api.formwebImportCurrent()).toEqual({ site: null, message: 'No project is open in FormWeb' });
  });

  it('lists FormWeb projects with open and saved flags only when they are exactly true', async () => {
    engine(200, { projects: [{ id: 'p1', name: 'One', updatedAt: 't', open: true, saved: 'yes' }, 'junk', { name: 'Two' }] });
    expect(await api.formwebProjects()).toEqual([
      { id: 'p1', name: 'One', updatedAt: 't', open: true, saved: false },
      { id: null, name: 'Two', updatedAt: '', open: false, saved: false },
    ]);
  });
});

describe('engine health', () => {
  it('is healthy when the engine says ok and reports its version', async () => {
    engine(200, { status: 'OK', version: '0.10.1' });
    expect(await api.health()).toEqual({ ok: true, version: '0.10.1' });
  });

  it('is not healthy when the engine reports a degraded status or ok false', async () => {
    engine(200, { status: 'degraded' });
    expect((await api.health()).ok).toBe(false);
    engine(200, { ok: false, status: 'ok' });
    expect((await api.health()).ok).toBe(false);
  });
});
