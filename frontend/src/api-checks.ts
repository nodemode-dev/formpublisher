import { ApiError } from './api';

export type Severity = 'error' | 'warning' | 'info';
export type Tier = 'static' | 'live' | 'deep';

export interface Problem {
  id: string;
  tier: Tier;
  severity: Severity;
  code: string;
  route: string;
  message: string;
  fix?: string;
  file?: string;
  line?: number;
  selector?: string;
  url?: string;
}

export interface CheckSummary {
  errors: number;
  warnings: number;
  infos: number;
  ran: boolean;
}

export interface CheckResults {
  problems: Problem[];
  summary: CheckSummary;
  thumbs: Record<string, string>;
}

type Json = Record<string, unknown>;

const isObj = (v: unknown): v is Json => typeof v === 'object' && v !== null && !Array.isArray(v);
const str = (v: unknown): string => (typeof v === 'string' ? v : typeof v === 'number' ? String(v) : '');
const count = (v: unknown): number => (typeof v === 'number' && Number.isFinite(v) ? v : 0);

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, init);
  } catch {
    throw new ApiError('The engine is not reachable', 0);
  }
  if (!res.ok) {
    let message = `${res.status} ${res.statusText}`.trim();
    let code = '';
    try {
      const body = (await res.json()) as unknown;
      if (isObj(body)) {
        code = typeof body.code === 'string' ? body.code : '';
        const d = body.detail ?? body.message ?? body.error;
        if (typeof d === 'string' && d) message = d;
      }
    } catch {
      message = message || 'Request failed';
    }
    throw new ApiError(message, res.status, code);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

const post = (body: unknown): RequestInit => ({ method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });

export function toProblem(raw: unknown): Problem | null {
  if (!isObj(raw)) return null;
  const id = str(raw.id);
  const code = str(raw.code);
  if (!id || !code) return null;
  const sev = str(raw.severity);
  const tier = str(raw.tier);
  const p: Problem = {
    id,
    code,
    tier: tier === 'live' || tier === 'deep' ? tier : 'static',
    severity: sev === 'error' || sev === 'info' ? sev : 'warning',
    route: str(raw.route) || '/',
    message: str(raw.message),
  };
  const fix = str(raw.fix);
  if (fix) p.fix = fix;
  const file = str(raw.file);
  if (file) p.file = file;
  if (typeof raw.line === 'number') p.line = raw.line;
  const selector = str(raw.selector);
  if (selector) p.selector = selector;
  const url = str(raw.url);
  if (url) p.url = url;
  return p;
}

function ranOf(v: unknown): boolean {
  if (Array.isArray(v)) return v.length > 0;
  if (isObj(v)) return Object.keys(v).length > 0;
  return Boolean(v);
}

export async function siteRevision(site: string): Promise<string> {
  const raw = await request<unknown>(`/api/sites/${encodeURIComponent(site)}`);
  const o = isObj(raw) && isObj(raw.site) ? raw.site : raw;
  if (!isObj(o)) return '';
  const direct = str(o.revision);
  if (direct) return direct;
  const list = Array.isArray(o.revisions) ? o.revisions.map(str).filter(Boolean) : [];
  return list[list.length - 1] ?? '';
}

export async function fetchResults(site: string, revision: string): Promise<CheckResults> {
  const raw = await request<unknown>(`/api/checks/${encodeURIComponent(site)}/${encodeURIComponent(revision)}`);
  const o = isObj(raw) ? raw : {};
  const problems = (Array.isArray(o.problems) ? o.problems : []).map(toProblem).filter((p): p is Problem => p !== null);
  const s = isObj(o.summary) ? o.summary : {};
  const thumbs: Record<string, string> = {};
  if (isObj(o.thumbs)) for (const [k, v] of Object.entries(o.thumbs)) if (typeof v === 'string') thumbs[k] = v;
  return { problems, summary: { errors: count(s.errors), warnings: count(s.warnings), infos: count(s.infos), ran: ranOf(s.ran) }, thumbs };
}

export async function startRun(site: string, revision: string, deep: boolean): Promise<string> {
  const raw = await request<unknown>('/api/checks/run', post({ site, revision, tiers: deep ? ['static', 'deep'] : ['static'] }));
  return isObj(raw) ? str(raw.run) : '';
}

export async function postLive(site: string, revision: string, problems: Problem[]): Promise<void> {
  await request<unknown>('/api/checks/live', post({ site, revision, problems }));
}
