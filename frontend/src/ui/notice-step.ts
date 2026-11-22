import { ApiError } from '../api';
import { trashApi, type TrashEntry } from '../api-trash';
import { emit } from '../events';
import { openPreferences } from './preferences';
import type { ToastAction } from './toast';

export interface StepHost {
  openTrash(): void;
  showCheck(): void;
  openManual(code?: string): void;
  refreshSites(): Promise<void>;
}

const TRASH_KIND: Record<string, 'site' | 'build'> = { 'build-missing': 'build', 'site-missing': 'site' };

export const STEP_CODES = new Set(['build-missing', 'site-missing', 'formweb-unreachable', 'check-running', 'core-missing', 'passphrase-wrong', 'passphrase-required']);

export function refuse(e: unknown, fallback: string, ref?: string, run?: () => void): void {
  const text = e instanceof Error && e.message ? e.message : fallback;
  emit('fp:notice', { kind: 'error', text, code: e instanceof ApiError ? e.code : undefined, ref, run });
}

export function refuseStep(e: unknown, ref?: string, run?: () => void): void {
  if (e instanceof ApiError && STEP_CODES.has(e.code)) refuse(e, 'Request failed', ref, run);
}

async function restoreFromNotice(item: TrashEntry, run: (() => void) | undefined, host: StepHost): Promise<void> {
  try {
    await trashApi.restore(item.entry);
  } catch (e) {
    host.openTrash();
    emit('fp:notice', { kind: 'error', text: e instanceof Error && e.message ? e.message : 'Request failed' });
    return;
  }
  emit('fp:notice', { kind: 'ok', text: `Restored ${item.label}` });
  if (item.kind === 'site') await host.refreshSites().catch(() => undefined);
  run?.();
}

export async function stepFor(code: string | undefined, ref: string | undefined, run: (() => void) | undefined, host: StepHost): Promise<ToastAction | undefined> {
  if (!code) return undefined;
  const kind = TRASH_KIND[code];
  if (kind) {
    if (!ref) return undefined;
    try {
      const rows = await trashApi.list();
      const found = rows.filter((r) => r.kind === kind && (r.label === ref || (r.origin ?? '').split('/').pop() === ref));
      if (found.length !== 1) return rows.some((r) => r.kind === kind && [r.entry, r.label, r.origin ?? ''].some((s) => s.includes(ref))) ? { label: 'Open the trash', run: () => host.openTrash() } : undefined;
      const item = found[0];
      return { label: 'Restore', run: () => { void restoreFromNotice(item, run, host); } };
    } catch {
      return undefined;
    }
  }
  if (code === 'formweb-unreachable') return run ? { label: 'Try again', run } : { label: 'Open Preferences', run: () => openPreferences('formweb') };
  if (code === 'check-running') return { label: 'Show the running check', run: () => host.showCheck() };
  if (code === 'core-missing') return { label: 'Open the manual', run: () => host.openManual(code) };
  if (code === 'passphrase-wrong' || code === 'passphrase-required') return run ? { label: 'Enter the passphrase', run } : undefined;
  return undefined;
}
