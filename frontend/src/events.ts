import type { Disposer } from './ui/dom';

export type NoticeKind = 'info' | 'ok' | 'error';

export interface FpEventMap {
  'fp:home': Record<string, never>;
  'fp:palette': { source: 'titlebar' | 'shortcut' };
  'fp:theme-toggle': { from: string; to: string };
  'fp:preferences': { source: 'titlebar' | 'shortcut' };
  'fp:new-tab': Record<string, never>;
  'fp:pick-folder': { resolve: (path: string | null) => void };
  'fp:site-opened': { id: string };
  'fp:site-closed': { id: string };
  'fp:site-loaded': { id: string };
  'fp:sites-changed': Record<string, never>;
  'fp:route-selected': { siteId: string; path: string };
  'fp:settings-changed': Record<string, never>;
  'fp:ui-settings-changed': { key: string };
  'fp:notice': { kind: NoticeKind; text: string };
  'fp:engine-state': { state: 'ok' | 'down' | 'unknown' };
}

export type FpEventName = keyof FpEventMap;

export function emit<K extends FpEventName>(name: K, detail: FpEventMap[K], cancelable = false): boolean {
  const ev = new CustomEvent<FpEventMap[K]>(name, { detail, cancelable });
  document.dispatchEvent(ev);
  return !ev.defaultPrevented;
}

export function on<K extends FpEventName>(name: K, handler: (detail: FpEventMap[K], event: CustomEvent<FpEventMap[K]>) => void): Disposer {
  const fn = (e: Event): void => handler((e as CustomEvent<FpEventMap[K]>).detail, e as CustomEvent<FpEventMap[K]>);
  document.addEventListener(name, fn);
  return () => document.removeEventListener(name, fn);
}
