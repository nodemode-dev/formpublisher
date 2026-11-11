import type { RouteInfo, Site } from './api';

export type EngineState = 'unknown' | 'ok' | 'down';
export type Pane = 'strip' | 'props' | 'bottom';
export type BottomTab = 'problems' | 'console' | 'network';

export interface OpenTab {
  id: string;
  name: string;
}

export interface AppState {
  readonly sites: readonly Site[];
  readonly open: readonly OpenTab[];
  readonly activeId: string | null;
  readonly site: Site | null;
  readonly routes: readonly RouteInfo[];
  readonly route: string | null;
  readonly engine: EngineState;
  readonly engineVersion: string;
}

export interface Mounts {
  readonly root: HTMLElement;
  readonly titlebar: HTMLElement;
  readonly menubar: HTMLElement;
  readonly titleTools: HTMLElement;
  readonly tabs: HTMLElement;
  readonly options: HTMLElement;
  readonly main: HTMLElement;
  readonly strip: HTMLElement;
  readonly stage: HTMLElement;
  readonly bottom: HTMLElement;
  readonly inspector: HTMLElement;
  readonly statusLeft: HTMLElement;
  readonly statusRight: HTMLElement;
  readonly overlay: HTMLElement;
  readonly toast: HTMLElement;
}

export interface App {
  readonly mounts: Mounts;
  readonly ready: Promise<void>;
  state(): AppState;
  openSite(id: string): Promise<void>;
  closeSite(id: string): void;
  deactivate(): void;
  selectRoute(path: string): void;
  refreshSites(): Promise<void>;
  importZip(file: File): Promise<Site>;
  importFolder(path: string): Promise<Site>;
  importFromFormWeb(): Promise<Site | null>;
  pickZip(): void;
  pickFolder(): Promise<string | null>;
  togglePane(pane: Pane, force?: boolean): void;
  showBottomTab(tab: BottomTab): void;
}
