export interface Site {
  id: string;
  name: string;
  source: string;
  kind: string;
  importedAt: string;
  routeCount: number | null;
  size: number | null;
  revisions: number;
}

export interface RouteInfo {
  path: string;
  page: string;
  locale?: string;
  item?: string;
  stylesheet?: string;
}

export interface Health {
  ok: boolean;
  version: string;
}

export type LiveEvent =
  | { type: 'site.imported'; id?: string; [k: string]: unknown }
  | { type: 'site.removed'; id?: string; [k: string]: unknown }
  | { type: 'settings.changed'; [k: string]: unknown };

export type LiveState = 'connecting' | 'open' | 'closed';

export interface FormWebImport {
  site: Site | null;
  message: string;
}

const STATUS_CODES: Record<number, string> = {
  0: 'unreachable',
  400: 'invalid',
  401: 'unauthorized',
  403: 'forbidden',
  404: 'not-found',
  409: 'conflict',
  413: 'too-large',
  415: 'unsupported',
  422: 'unprocessable',
  500: 'internal',
};

export class ApiError extends Error {
  readonly code: string;

  constructor(message: string, readonly status: number, code?: string) {
    super(message);
    this.code = code || STATUS_CODES[status] || (status >= 500 ? 'internal' : 'invalid');
  }
}

type Json = Record<string, unknown>;

const isObj = (v: unknown): v is Json => typeof v === 'object' && v !== null && !Array.isArray(v);
const str = (v: unknown): string => (typeof v === 'string' ? v : typeof v === 'number' ? String(v) : '');
const num = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null);

function sourceLabel(v: unknown): string {
  if (typeof v === 'string') return v;
  if (isObj(v) && str(v.url).startsWith('receive:')) return 'FormWeb';
  if (isObj(v)) return str(v.path) || str(v.url) || str(v.name) || str(v.kind) || str(v.type);
  return '';
}

export function toSite(raw: unknown): Site | null {
  if (!isObj(raw)) return null;
  const id = str(raw.id) || str(raw.site_id);
  if (!id) return null;
  const routes = raw.routes ?? raw.route_count ?? raw.routeCount;
  return {
    id,
    name: str(raw.name) || str(raw.title) || str(raw.slug) || id,
    source: sourceLabel(raw.source),
    kind: isObj(raw.source) ? (isObj(raw.source.fpub) ? 'fpub' : str(raw.source.kind)) : '',
    importedAt: str(raw.imported_at) || str(raw.importedAt) || str(raw.created_at) || str(raw.createdAt),
    routeCount: Array.isArray(routes) ? routes.length : num(routes),
    size: num(raw.size) ?? num(raw.size_bytes) ?? num(raw.bytes) ?? num(raw.sizeBytes),
    revisions: Array.isArray(raw.revisions) ? raw.revisions.length : 0,
  };
}

export function toRoute(raw: unknown): RouteInfo | null {
  if (typeof raw === 'string') return { path: raw, page: '' };
  if (!isObj(raw)) return null;
  const path = str(raw.path) || str(raw.route);
  if (!path) return null;
  return { path, page: str(raw.page) || str(raw.file), locale: str(raw.locale) || undefined, item: str(raw.item) || undefined, stylesheet: str(raw.stylesheet) || undefined };
}

function listOf(raw: unknown, key: string): unknown[] {
  if (Array.isArray(raw)) return raw;
  if (isObj(raw) && Array.isArray(raw[key])) return raw[key] as unknown[];
  return [];
}

async function failure(res: Response): Promise<ApiError> {
  let message = `${res.status} ${res.statusText}`.trim();
  let code = '';
  try {
    const body = (await res.json()) as unknown;
    if (isObj(body)) {
      code = str(body.code);
      const d = body.detail ?? body.message ?? body.error;
      if (typeof d === 'string' && d) message = d;
      else if (Array.isArray(d) && d.length && isObj(d[0]) && typeof d[0].msg === 'string') message = d[0].msg;
    }
  } catch {
    message = message || 'Request failed';
  }
  return new ApiError(message, res.status, code);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, init);
  } catch {
    throw new ApiError('The engine is not reachable', 0);
  }
  if (!res.ok) throw await failure(res);
  if (res.status === 204) return undefined as T;
  const type = res.headers.get('content-type') ?? '';
  return (type.includes('json') ? await res.json() : await res.text()) as T;
}

const json = (method: string, body: unknown): RequestInit => ({ method, headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });

function siteOrThrow(raw: unknown): Site {
  const site = toSite(isObj(raw) && isObj(raw.site) ? raw.site : raw);
  if (!site) throw new ApiError('The engine returned an unexpected answer', 502);
  return site;
}

export const api = {
  async health(): Promise<Health> {
    const raw = await request<unknown>('/api/health');
    const o = isObj(raw) ? raw : {};
    const status = str(o.status).toLowerCase();
    return { ok: o.ok !== false && (status === '' || status === 'ok' || status === 'healthy'), version: str(o.version) };
  },
  settings: (): Promise<Json> => request<Json>('/api/settings'),
  putSettings: (patch: Json): Promise<Json> => request<Json>('/api/settings', json('PUT', patch)),
  async sites(): Promise<Site[]> {
    return listOf(await request<unknown>('/api/sites'), 'sites').map(toSite).filter((s): s is Site => s !== null);
  },
  async site(id: string): Promise<Site> {
    return siteOrThrow(await request<unknown>(`/api/sites/${encodeURIComponent(id)}`));
  },
  async routes(id: string): Promise<RouteInfo[]> {
    return listOf(await request<unknown>(`/api/sites/${encodeURIComponent(id)}/routes`), 'routes').map(toRoute).filter((r): r is RouteInfo => r !== null);
  },
  async importZip(file: File): Promise<Site> {
    const form = new FormData();
    form.append('file', file, file.name);
    return siteOrThrow(await request<unknown>('/api/sites/import', { method: 'POST', body: form }));
  },
  async importPath(path: string): Promise<Site> {
    return siteOrThrow(await request<unknown>('/api/sites/import', json('POST', { path })));
  },
  removeSite: (id: string): Promise<void> => request<void>(`/api/sites/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  formwebStatus: (): Promise<Json> => request<Json>('/api/formweb/status'),
  async formwebImportCurrent(): Promise<FormWebImport> {
    const raw = await request<unknown>('/api/formweb/import-current', { method: 'POST' });
    const site = toSite(isObj(raw) && isObj(raw.site) ? raw.site : raw);
    const message = isObj(raw) ? str(raw.message) : '';
    return { site, message };
  },
};

export interface LiveHandle { close(): void }

export function connectLive(onEvent: (event: LiveEvent) => void, onState: (state: LiveState) => void): LiveHandle {
  let socket: WebSocket | null = null;
  let timer: number | undefined;
  let attempt = 0;
  let stopped = false;

  const open = (): void => {
    if (stopped) return;
    onState('connecting');
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    let ws: WebSocket;
    try {
      ws = new WebSocket(`${proto}//${location.host}/api/live`);
    } catch {
      schedule();
      return;
    }
    socket = ws;
    ws.addEventListener('open', () => { attempt = 0; onState('open'); });
    ws.addEventListener('message', (e) => {
      try {
        const data = JSON.parse(String(e.data)) as unknown;
        if (isObj(data) && typeof data.type === 'string') onEvent(data as LiveEvent);
      } catch {
        return;
      }
    });
    ws.addEventListener('close', () => { if (socket === ws) { socket = null; onState('closed'); schedule(); } });
    ws.addEventListener('error', () => ws.close());
  };

  const schedule = (): void => {
    if (stopped || timer !== undefined) return;
    const wait = Math.min(8000, 500 * 2 ** attempt);
    attempt += 1;
    timer = window.setTimeout(() => { timer = undefined; open(); }, wait);
  };

  open();

  return {
    close(): void {
      stopped = true;
      if (timer !== undefined) window.clearTimeout(timer);
      socket?.close();
    },
  };
}
