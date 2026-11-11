import { ApiError } from './api';

type Json = Record<string, unknown>;

export interface BuildFile { path: string; sha256: string; size: number }

export interface BuildSummary {
  id: string;
  site: string;
  revision: string;
  created: string;
  size: number;
  files: number;
  signed: boolean;
  sha256: string;
}

export interface BuildDetail extends BuildSummary {
  siteName: string;
  fileList: BuildFile[];
  routes: number;
  checks: { errors: number; warnings: number; infos: number } | null;
}

export interface KeyInfo { id: string; name: string; fingerprint: string; created: string; encrypted: boolean }

export interface VerifyResult { valid: boolean; key: string; reason: string }

export interface ReproduceResult { same: boolean; sha256: string; expected: string }

export interface CompareSide { sha256: string; size: number }

export interface CompareResult {
  added: string[];
  removed: string[];
  changed: Array<{ path: string; a: CompareSide; b: CompareSide }>;
  same: number;
}

export interface CheckSummary { errors: number; warnings: number; infos: number; ran: boolean }

const isObj = (v: unknown): v is Json => typeof v === 'object' && v !== null && !Array.isArray(v);
const str = (v: unknown): string => (typeof v === 'string' ? v : typeof v === 'number' ? String(v) : '');
const num = (v: unknown): number => (typeof v === 'number' && Number.isFinite(v) ? v : 0);

async function failure(res: Response): Promise<ApiError> {
  let message = `${res.status} ${res.statusText}`.trim();
  let code = '';
  try {
    const body = (await res.json()) as unknown;
    if (isObj(body)) {
      code = typeof body.code === 'string' ? body.code : '';
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

const body = (method: string, data: unknown): RequestInit => ({ method, headers: { 'content-type': 'application/json' }, body: JSON.stringify(data) });

const enc = encodeURIComponent;

function listOf(raw: unknown, key: string): unknown[] {
  if (Array.isArray(raw)) return raw;
  if (isObj(raw) && Array.isArray(raw[key])) return raw[key] as unknown[];
  return [];
}

function toFile(raw: unknown): BuildFile | null {
  if (!isObj(raw)) return null;
  const path = str(raw.path);
  return path ? { path, sha256: str(raw.sha256), size: num(raw.size) } : null;
}

function signedOf(v: unknown): boolean {
  if (typeof v === 'boolean') return v;
  if (typeof v === 'string') return v !== '';
  return isObj(v);
}

export function toBuild(raw: unknown): BuildSummary | null {
  if (!isObj(raw)) return null;
  const meta = isObj(raw.build) ? raw.build : raw;
  const pub = isObj(raw.publish) ? raw.publish : isObj(raw.publishJson) ? raw.publishJson : null;
  const id = str(meta.id);
  if (!id) return null;
  const pkg = pub && isObj(pub.package) ? pub.package : isObj(meta.package) ? meta.package : null;
  const files = Array.isArray(meta.files) ? meta.files.length : num(meta.files) || (pub && Array.isArray(pub.files) ? pub.files.length : 0);
  return {
    id,
    site: str(meta.site),
    revision: str(meta.revision),
    created: str(meta.created),
    size: num(meta.size) || (pkg ? num(pkg.size) : 0),
    files,
    signed: signedOf(meta.signed),
    sha256: str(meta.sha256) || (pkg ? str(pkg.sha256) : ''),
  };
}

export function toDetail(raw: unknown): BuildDetail | null {
  const base = toBuild(raw);
  if (!base || !isObj(raw)) return null;
  const pub = isObj(raw.publish) ? raw.publish : isObj(raw.publishJson) ? raw.publishJson : {};
  const siteInfo = isObj(pub.site) ? pub.site : {};
  const checks = isObj(pub.checks) ? pub.checks : null;
  return {
    ...base,
    siteName: str(siteInfo.name) || base.site,
    fileList: listOf(pub, 'files').map(toFile).filter((f): f is BuildFile => f !== null),
    routes: Array.isArray(pub.routes) ? pub.routes.length : 0,
    checks: checks ? { errors: num(checks.errors), warnings: num(checks.warnings), infos: num(checks.infos) } : null,
  };
}

function toKey(raw: unknown): KeyInfo | null {
  if (!isObj(raw)) return null;
  const id = str(raw.id);
  return id ? { id, name: str(raw.name) || id, fingerprint: str(raw.fingerprint), created: str(raw.created), encrypted: raw.encrypted === true } : null;
}

function toSide(raw: unknown): CompareSide {
  return isObj(raw) ? { sha256: str(raw.sha256), size: num(raw.size) } : { sha256: '', size: 0 };
}

function pathOf(raw: unknown): string {
  return isObj(raw) ? str(raw.path) : str(raw);
}

export const buildsApi = {
  async siteRevision(site: string): Promise<string> {
    const raw = await request<unknown>(`/api/sites/${enc(site)}`);
    const o = isObj(raw) && isObj(raw.site) ? raw.site : raw;
    if (!isObj(o)) return '';
    const list = Array.isArray(o.revisions) ? o.revisions.filter((r): r is string => typeof r === 'string') : [];
    return str(o.revision) || list[list.length - 1] || '';
  },
  async checkSummary(site: string, revision: string): Promise<CheckSummary | null> {
    try {
      const raw = await request<unknown>(`/api/checks/${enc(site)}/${enc(revision)}`);
      const s = isObj(raw) && isObj(raw.summary) ? raw.summary : null;
      if (!s) return null;
      return { errors: num(s.errors), warnings: num(s.warnings), infos: num(s.infos), ran: Array.isArray(s.ran) ? s.ran.length > 0 : s.ran === true };
    } catch (e) {
      if (e instanceof ApiError && (e.status === 404 || e.status === 0)) return null;
      throw e;
    }
  },
  async build(site: string, revision?: string): Promise<BuildSummary> {
    const raw = await request<unknown>('/api/builds', body('POST', revision ? { site, revision } : { site }));
    const b = toBuild(raw);
    if (!b) throw new ApiError('The engine returned an unexpected answer', 502);
    return b;
  },
  async list(): Promise<BuildSummary[]> {
    return listOf(await request<unknown>('/api/builds'), 'builds').map(toBuild).filter((b): b is BuildSummary => b !== null);
  },
  async detail(id: string): Promise<BuildDetail> {
    const d = toDetail(await request<unknown>(`/api/builds/${enc(id)}`));
    if (!d) throw new ApiError('The engine returned an unexpected answer', 502);
    return d;
  },
  async reproduce(id: string): Promise<ReproduceResult> {
    const raw = await request<unknown>(`/api/builds/${enc(id)}/reproduce`, { method: 'POST' });
    const o = isObj(raw) ? raw : {};
    return { same: o.same === true, sha256: str(o.sha256), expected: str(o.expected) };
  },
  async sign(id: string, key: string, passphrase: string): Promise<void> {
    await request<unknown>(`/api/builds/${enc(id)}/sign`, body('POST', passphrase ? { key, passphrase } : { key }));
  },
  async verify(id: string): Promise<VerifyResult> {
    const raw = await request<unknown>(`/api/builds/${enc(id)}/verify`, { method: 'POST' });
    const o = isObj(raw) ? raw : {};
    return { valid: o.valid === true, key: str(o.key), reason: str(o.reason) };
  },
  async compare(a: string, b: string): Promise<CompareResult> {
    const raw = await request<unknown>(`/api/builds/${enc(a)}/compare/${enc(b)}`);
    const o = isObj(raw) ? raw : {};
    return {
      added: listOf(o, 'added').map(pathOf).filter(Boolean),
      removed: listOf(o, 'removed').map(pathOf).filter(Boolean),
      changed: listOf(o, 'changed').filter(isObj).map((c) => ({ path: str(c.path), a: toSide(c.a), b: toSide(c.b) })).filter((c) => c.path !== ''),
      same: typeof o.same === 'number' ? o.same : Array.isArray(o.same) ? o.same.length : 0,
    };
  },
  remove: (id: string): Promise<void> => request<void>(`/api/builds/${enc(id)}`, { method: 'DELETE' }),
  downloadUrl: (id: string): string => `/api/builds/${enc(id)}/download`,
  fpubUrl: (id: string): string => `/api/builds/${enc(id)}/fpub`,
  async keys(): Promise<KeyInfo[]> {
    return listOf(await request<unknown>('/api/keys'), 'keys').map(toKey).filter((k): k is KeyInfo => k !== null);
  },
  async createKey(name: string, passphrase: string): Promise<KeyInfo> {
    const raw = await request<unknown>('/api/keys', body('POST', passphrase ? { name, passphrase } : { name }));
    const k = toKey(isObj(raw) && isObj(raw.key) ? raw.key : raw);
    if (!k) throw new ApiError('The engine returned an unexpected answer', 502);
    return k;
  },
};
