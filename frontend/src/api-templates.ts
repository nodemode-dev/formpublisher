import { ApiError } from './api';

type Json = Record<string, unknown>;

export interface TemplateItem {
  id: string;
  name: string;
  description: string;
  bytes: number;
  sha256: string;
  licence: string;
  credit: string;
  preview: string | null;
}

export interface TemplateList {
  fetched: boolean;
  fetchedAt: string;
  source: string;
  url: string;
  items: TemplateItem[];
  notStartable: number;
}

export interface StartedSite {
  template: string;
  name: string;
  project: string;
  files: number;
}

const isObj = (v: unknown): v is Json => typeof v === 'object' && v !== null && !Array.isArray(v);
const str = (v: unknown): string => (typeof v === 'string' ? v : '');
const num = (v: unknown): number => (typeof v === 'number' && Number.isFinite(v) ? v : 0);

async function request(path: string, init?: RequestInit): Promise<Json> {
  let res: Response;
  try {
    res = await fetch(path, init);
  } catch {
    throw new ApiError('The engine is not reachable', 0);
  }
  let body: unknown = null;
  try { body = await res.json(); } catch { body = null; }
  if (!res.ok) {
    const detail = isObj(body) ? str(body.detail) : '';
    throw new ApiError(detail || `${res.status} ${res.statusText}`.trim(), res.status, isObj(body) ? str(body.code) : '');
  }
  return isObj(body) ? body : {};
}

function toItem(raw: unknown): TemplateItem | null {
  if (!isObj(raw) || !str(raw.id)) return null;
  return { id: str(raw.id), name: str(raw.name), description: str(raw.description), bytes: num(raw.bytes), sha256: str(raw.sha256), licence: str(raw.licence), credit: str(raw.credit), preview: str(raw.preview) || null };
}

function toList(raw: Json): TemplateList {
  const items = Array.isArray(raw.items) ? raw.items.map(toItem).filter((i): i is TemplateItem => i !== null) : [];
  return { fetched: raw.fetched === true, fetchedAt: str(raw.fetchedAt), source: str(raw.source), url: str(raw.url), items, notStartable: num(raw.notStartable) };
}

export const templatesApi = {
  async kept(): Promise<TemplateList> { return toList(await request('/api/templates')); },
  async fetch(): Promise<TemplateList> { return toList(await request('/api/templates/fetch', { method: 'POST' })); },
  async start(template: string, folder: string): Promise<StartedSite> {
    const raw = await request('/api/templates/start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ template, folder }) });
    return { template: str(raw.template), name: str(raw.name), project: str(raw.project), files: num(raw.files) };
  },
  previewUrl(id: string): string { return `/api/templates/preview?id=${encodeURIComponent(id)}`; },
};
