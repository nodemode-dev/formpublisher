import { ApiError } from './api';

export type PreviewTheme = 'auto' | 'dark' | 'light';
export type PreviewMotion = 'auto' | 'reduce';
export type PreviewThrottle = 'none' | 'fast' | 'slow';

export interface MountRequest {
  site: string;
  revision?: string;
  probe?: boolean;
  theme?: PreviewTheme;
  motion?: PreviewMotion;
  throttle?: PreviewThrottle;
}

export interface HostMount {
  url: string;
  generation: number;
  origin: string;
}

type Json = Record<string, unknown>;

const isObj = (v: unknown): v is Json => typeof v === 'object' && v !== null && !Array.isArray(v);

async function failure(res: Response): Promise<ApiError> {
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

function toMount(raw: unknown): HostMount | null {
  if (!isObj(raw)) return null;
  const body = isObj(raw.mount) ? raw.mount : raw;
  const url = typeof body.url === 'string' ? body.url : '';
  if (!url) return null;
  const gen = body.generation;
  let origin = typeof body.origin === 'string' ? body.origin : '';
  if (!origin) {
    try { origin = new URL(url).origin; } catch { return null; }
  }
  return { url, generation: typeof gen === 'number' ? gen : Number(gen) || 0, origin };
}

export const hostApi = {
  async mount(req: MountRequest): Promise<HostMount> {
    const raw = await request<unknown>('/api/host/mount', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(req),
    });
    const mount = toMount(raw);
    if (!mount) throw new ApiError('The engine returned an unexpected answer', 502);
    return mount;
  },
  async current(): Promise<HostMount | null> {
    return toMount(await request<unknown>('/api/host'));
  },
  async unmount(): Promise<void> {
    await request<unknown>('/api/host/mount', { method: 'DELETE' });
  },
};
