import { ApiError } from './api';

type Json = Record<string, unknown>;

export type TrashKind = 'site' | 'build' | 'key' | 'prepared';

export interface TrashEntry {
  entry: string;
  kind: TrashKind;
  label: string;
  origin: string | null;
  moved: string;
  size: number;
}

const isObj = (v: unknown): v is Json => typeof v === 'object' && v !== null && !Array.isArray(v);
const str = (v: unknown): string => (typeof v === 'string' ? v : typeof v === 'number' ? String(v) : '');
const num = (v: unknown): number => (typeof v === 'number' && Number.isFinite(v) ? v : 0);

async function failure(res: Response): Promise<ApiError> {
  let message = `${res.status} ${res.statusText}`.trim();
  try {
    const body = (await res.json()) as unknown;
    if (isObj(body)) {
      const d = body.detail ?? body.message ?? body.error;
      if (typeof d === 'string' && d) message = d;
      else if (isObj(d) && typeof d.reason === 'string' && d.reason) message = d.reason;
      else if (Array.isArray(d) && d.length && isObj(d[0]) && typeof d[0].msg === 'string') message = d[0].msg;
    }
  } catch {
    message = message || 'Request failed';
  }
  return new ApiError(message, res.status);
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

const KINDS: TrashKind[] = ['site', 'build', 'key', 'prepared'];

function toEntry(raw: unknown): TrashEntry | null {
  if (!isObj(raw)) return null;
  const entry = str(raw.entry) || str(raw.name) || str(raw.id);
  if (!entry) return null;
  const kind = KINDS.find((k) => k === str(raw.kind)) ?? 'site';
  const origin = str(raw.origin);
  return {
    entry,
    kind,
    label: str(raw.label) || entry,
    origin: origin || null,
    moved: str(raw.moved) || str(raw.movedAt),
    size: num(raw.size),
  };
}

export const trashApi = {
  async list(): Promise<TrashEntry[]> {
    const raw = await request<unknown>('/api/trash');
    const rows = Array.isArray(raw) ? raw : isObj(raw) && Array.isArray(raw.entries) ? raw.entries : [];
    return rows.map(toEntry).filter((e): e is TrashEntry => e !== null);
  },
  async restore(entry: string): Promise<void> {
    await request<unknown>(`/api/trash/${encodeURIComponent(entry)}/restore`, { method: 'POST' });
  },
  async remove(entry: string): Promise<void> {
    await request<unknown>(`/api/trash/${encodeURIComponent(entry)}`, { method: 'DELETE' });
  },
  async empty(): Promise<void> {
    await request<unknown>('/api/trash', { method: 'DELETE' });
  },
};
