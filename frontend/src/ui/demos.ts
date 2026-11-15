import { openBundled, openSample, type SampleResult } from '../api-demo';
import type { App } from '../app-api';
import { emit } from '../events';
import type { Command } from './commands';

export interface DemoInfo {
  id: string;
  title: string;
  line: string;
  picture: string;
  open: () => Promise<SampleResult>;
}

const BASE = `${import.meta.env.BASE_URL}demos/`;

export const DEMOS: readonly DemoInfo[] = [
  { id: 'lowlight', title: 'Lowlight', line: 'A planetarium studio with scroll effects and page components.', picture: `${BASE}lowlight/cover.webp`, open: () => openBundled('lowlight') },
  { id: 'looking-back', title: 'Looking Back', line: 'A photo essay on pictures of Earth from far away.', picture: `${BASE}looking-back/cover.webp`, open: () => openBundled('looking-back') },
  { id: 'harbour-ferries', title: 'Harbour Ferries', line: 'A ferry operator with a fare calculator, routes and search.', picture: `${BASE}harbour-ferries/cover.webp`, open: () => openBundled('harbour-ferries') },
  { id: 'northwind', title: 'Northwind Notes', line: 'A four page product site with problems for the checks to find.', picture: `${BASE}northwind/cover.webp`, open: openSample },
];

export const demoCommand = (d: DemoInfo): string => `demo-${d.id}`;

let opening: string | null = null;
const watchers = new Set<(id: string | null) => void>();

export function onDemoOpening(fn: (id: string | null) => void): void {
  watchers.add(fn);
}

function setOpening(id: string | null): void {
  opening = id;
  for (const fn of watchers) fn(id);
}

export async function openDemo(app: App, id: string): Promise<void> {
  const demo = DEMOS.find((d) => d.id === id);
  if (!demo) return;
  if (opening !== null) { emit('fp:notice', { kind: 'info', text: 'A demo is still opening.' }); return; }
  setOpening(id);
  emit('fp:notice', { kind: 'info', text: 'Opening the demo...' });
  try {
    const { site } = await demo.open();
    await app.refreshSites();
    await app.openSite(site.id);
  } catch (e) {
    emit('fp:notice', { kind: 'error', text: e instanceof Error && e.message ? e.message : 'The sample site could not be opened' });
  } finally {
    setOpening(null);
  }
}

export function demoCommands(app: App, engineUp: () => boolean): Command[] {
  return DEMOS.map((d) => ({
    id: demoCommand(d),
    label: d.title,
    icon: 'globe',
    group: 'Help',
    menu: 'Help',
    description: `Open the ${d.title} demo site`,
    mutates: true,
    enabled: () => engineUp() && opening === null,
    run: () => openDemo(app, d.id),
  }));
}
