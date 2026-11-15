import { ApiError, toSite, type Site } from './api';

export interface SampleResult { site: Site; created: boolean }

export const openSample = (): Promise<SampleResult> => openDemoRoute('/api/demo/sample');

export const openBundled = (id: string): Promise<SampleResult> => openDemoRoute(`/api/demo/open/${encodeURIComponent(id)}`);

async function openDemoRoute(route: string): Promise<SampleResult> {
  let res: Response;
  try {
    res = await fetch(route, { method: 'POST' });
  } catch {
    throw new ApiError('The engine is not reachable', 0);
  }
  let raw: unknown = null;
  try { raw = await res.json(); } catch { raw = null; }
  const body = (typeof raw === 'object' && raw !== null ? raw : {}) as Record<string, unknown>;
  if (!res.ok) {
    const detail = typeof body.detail === 'string' ? body.detail : `The sample site could not be opened (${res.status})`;
    throw new ApiError(detail, res.status);
  }
  const site = toSite(body.site);
  if (!site) throw new ApiError('The engine returned an unexpected answer', 502);
  return { site, created: body.created === true };
}
