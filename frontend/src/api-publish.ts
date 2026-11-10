import { ApiError } from './api';

type Json = Record<string, unknown>;

export interface TargetInfo { id: string; name: string; description: string; localTool: string }

export interface PreparedCommand { label: string; run: string; cwd: string }

export interface PreparedTarget {
  target: string;
  folder: string;
  files: string[];
  commands: PreparedCommand[];
  notes: string[];
  warnings: string[];
}

export interface VerifyReport { ok: boolean; checked: number; problems: string[] }

export interface RevealResult { path: string; opened: boolean }

const isObj = (v: unknown): v is Json => typeof v === 'object' && v !== null && !Array.isArray(v);
const str = (v: unknown): string => (typeof v === 'string' ? v : typeof v === 'number' ? String(v) : '');
const num = (v: unknown): number => (typeof v === 'number' && Number.isFinite(v) ? v : 0);
const enc = encodeURIComponent;

async function failure(res: Response): Promise<ApiError> {
  let message = `${res.status} ${res.statusText}`.trim();
  try {
    const body = (await res.json()) as unknown;
    if (isObj(body)) {
      const d = body.detail ?? body.message ?? body.error;
      if (typeof d === 'string' && d) message = d;
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

const body = (method: string, data: unknown): RequestInit => ({ method, headers: { 'content-type': 'application/json' }, body: JSON.stringify(data) });

function listOf(raw: unknown, key: string): unknown[] {
  if (Array.isArray(raw)) return raw;
  if (isObj(raw) && Array.isArray(raw[key])) return raw[key] as unknown[];
  return [];
}

function lines(raw: unknown): string[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((v) => (isObj(v) ? str(v.message) || str(v.text) || str(v.path) : str(v))).filter((s) => s !== '');
}

function toTarget(raw: unknown): TargetInfo | null {
  if (!isObj(raw)) return null;
  const id = str(raw.id);
  return id ? { id, name: str(raw.name) || id, description: str(raw.description), localTool: str(raw.localTool ?? raw.local_tool) } : null;
}

function toCommand(raw: unknown): PreparedCommand | null {
  if (typeof raw === 'string') return raw ? { label: '', run: raw, cwd: '' } : null;
  if (!isObj(raw)) return null;
  const run = str(raw.run) || str(raw.command);
  return run ? { label: str(raw.label), run, cwd: str(raw.cwd) } : null;
}

export function toPrepared(id: string, raw: unknown): PreparedTarget | null {
  if (!isObj(raw)) return null;
  return {
    target: str(raw.target) || id,
    folder: str(raw.folder) || str(raw.path),
    files: Array.isArray(raw.files) ? raw.files.map((f) => (isObj(f) ? str(f.path) : str(f))).filter((s) => s !== '') : [],
    commands: Array.isArray(raw.commands) ? raw.commands.map(toCommand).filter((c): c is PreparedCommand => c !== null) : [],
    notes: lines(raw.notes),
    warnings: lines(raw.warnings),
  };
}

function resultsOf(raw: unknown): PreparedTarget[] {
  const o = isObj(raw) ? raw : {};
  const src = o.results ?? o.prepared ?? o.targets ?? {};
  const out: PreparedTarget[] = [];
  if (Array.isArray(src)) {
    for (const item of src) {
      const t = toPrepared(isObj(item) ? str(item.target) || str(item.id) : '', item);
      if (t && t.target) out.push(t);
    }
  } else if (isObj(src)) {
    for (const [id, v] of Object.entries(src)) {
      const t = toPrepared(id, v);
      if (t) out.push({ ...t, target: id });
    }
  }
  return out;
}

export const publishApi = {
  async targets(): Promise<TargetInfo[]> {
    return listOf(await request<unknown>('/api/targets'), 'targets').map(toTarget).filter((t): t is TargetInfo => t !== null);
  },
  async prepare(build: string, targets: string[]): Promise<PreparedTarget[]> {
    return resultsOf(await request<unknown>('/api/publish/prepare', body('POST', { build, targets })));
  },
  async prepared(build: string): Promise<PreparedTarget[]> {
    try {
      return resultsOf(await request<unknown>(`/api/publish/${enc(build)}`));
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) return [];
      throw e;
    }
  },
  async reveal(build: string, target: string): Promise<RevealResult> {
    const raw = await request<unknown>(`/api/publish/${enc(build)}/${enc(target)}/reveal`, { method: 'POST' });
    const o = isObj(raw) ? raw : {};
    return { path: str(o.path) || str(o.folder), opened: o.opened === true };
  },
  async verify(build: string, target: string): Promise<VerifyReport> {
    const raw = await request<unknown>(`/api/publish/${enc(build)}/${enc(target)}/verify`, { method: 'POST' });
    const o = isObj(raw) ? raw : {};
    const raw2 = o.problems ?? o.errors ?? o.mismatches;
    const problems = Array.isArray(raw2)
      ? raw2.map((p) => (isObj(p) && str(p.path) && str(p.problem) ? `${str(p.path)}: ${str(p.problem)}` : isObj(p) ? str(p.message) || str(p.path) : str(p))).filter((s) => s !== '')
      : [];
    const checked = num(o.checked) || num(o.files) || (Array.isArray(o.files) ? o.files.length : 0);
    const ok = typeof o.ok === 'boolean' ? o.ok : typeof o.valid === 'boolean' ? o.valid : problems.length === 0;
    return { ok, checked, problems };
  },
  async remove(build: string, target: string): Promise<void> {
    await request<unknown>(`/api/publish/${enc(build)}/${enc(target)}`, { method: 'DELETE' });
  },
};
