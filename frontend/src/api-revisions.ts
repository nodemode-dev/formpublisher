import { ApiError } from './api';

export interface RevisionChanges { added: number; removed: number; changed: number }

export interface RevisionRow {
  revision: string;
  at: string;
  files: number;
  bytes: number;
  routes: number;
  latest: boolean;
  changes: RevisionChanges | null;
}

export interface DiffRow {
  kind: 'added' | 'removed' | 'changed' | 'route-added' | 'route-removed';
  path: string;
  size: string;
  hash: string;
}

export interface RevisionDiff {
  from: string;
  to: string;
  rows: DiffRow[];
  added: number;
  removed: number;
  changed: number;
  same: number;
  routesFrom: number;
  routesTo: number;
  identical: boolean;
}

type Json = Record<string, unknown>;

const isObj = (v: unknown): v is Json => typeof v === 'object' && v !== null && !Array.isArray(v);
const str = (v: unknown): string => (typeof v === 'string' ? v : typeof v === 'number' ? String(v) : '');
const num = (v: unknown): number => (typeof v === 'number' && Number.isFinite(v) ? v : 0);

async function request(path: string): Promise<unknown> {
  let res: Response;
  try {
    res = await fetch(path);
  } catch {
    throw new ApiError('The engine is not reachable', 0);
  }
  if (!res.ok) {
    let message = `${res.status} ${res.statusText}`.trim();
    try {
      const body = (await res.json()) as unknown;
      if (isObj(body) && typeof body.detail === 'string' && body.detail) message = body.detail;
    } catch {
      message = message || 'Request failed';
    }
    throw new ApiError(message, res.status);
  }
  return (await res.json()) as unknown;
}

export function sizeLabel(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export async function fetchRevisions(site: string): Promise<RevisionRow[]> {
  const raw = await request(`/api/sites/${encodeURIComponent(site)}/revisions`);
  const list = isObj(raw) && Array.isArray(raw.revisions) ? raw.revisions : [];
  const out: RevisionRow[] = [];
  for (const item of list) {
    if (!isObj(item) || !str(item.revision)) continue;
    const ch = isObj(item.changes) ? { added: num(item.changes.added), removed: num(item.changes.removed), changed: num(item.changes.changed) } : null;
    out.push({ revision: str(item.revision), at: str(item.at), files: num(item.files), bytes: num(item.bytes), routes: num(item.routes), latest: item.latest === true, changes: ch });
  }
  return out;
}

const rowsOf = (v: unknown): Json[] => (Array.isArray(v) ? v.filter(isObj) : []);

export async function fetchDiff(site: string, from: string, to: string): Promise<RevisionDiff> {
  const raw = await request(`/api/sites/${encodeURIComponent(site)}/diff?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`);
  const o = isObj(raw) ? raw : {};
  const rows: DiffRow[] = [];
  for (const r of rowsOf(o.added)) rows.push({ kind: 'added', path: str(r.path), size: sizeLabel(num(r.size)), hash: str(r.sha256).slice(0, 10) });
  for (const r of rowsOf(o.removed)) rows.push({ kind: 'removed', path: str(r.path), size: sizeLabel(num(r.size)), hash: str(r.sha256).slice(0, 10) });
  for (const r of rowsOf(o.changed)) {
    const a = isObj(r.from) ? r.from : {};
    const b = isObj(r.to) ? r.to : {};
    rows.push({ kind: 'changed', path: str(r.path), size: `${sizeLabel(num(a.size))} to ${sizeLabel(num(b.size))}`, hash: `${str(a.sha256).slice(0, 6)} ${str(b.sha256).slice(0, 6)}` });
  }
  const routes = isObj(o.routes) ? o.routes : {};
  for (const p of Array.isArray(routes.added) ? routes.added : []) rows.push({ kind: 'route-added', path: str(p), size: '', hash: '' });
  for (const p of Array.isArray(routes.removed) ? routes.removed : []) rows.push({ kind: 'route-removed', path: str(p), size: '', hash: '' });
  const s = isObj(o.summary) ? o.summary : {};
  return {
    from: str(o.from),
    to: str(o.to),
    rows,
    added: num(s.added),
    removed: num(s.removed),
    changed: num(s.changed),
    same: num(s.same),
    routesFrom: num(routes.from),
    routesTo: num(routes.to),
    identical: s.identical === true,
  };
}
