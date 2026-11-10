import { ICONS } from './icons';

const L = (body: string): string => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">${body}</svg>`;

Object.assign(ICONS, {
  home: L('<path d="M4 11l8-6.5 8 6.5"/><path d="M6 9.5V19h12V9.5"/><path d="M10 19v-5h4v5"/>'),
  search: L('<circle cx="11" cy="11" r="6"/><path d="M20 20l-4.2-4.2"/>'),
  trash: L('<path d="M4.5 7h15M9.5 7V5h5v2M6.5 7l.8 12h9.4l.8-12M10 11v5M14 11v5"/>'),
  keyboard: L('<rect x="3" y="6.5" width="18" height="11" rx="2"/><path d="M7 10.5h.01M10 10.5h.01M13 10.5h.01M16 10.5h.01M8 14h8"/>'),
  cloudOff: L('<path d="M7 18h10a4 4 0 0 0 .8-7.9A5.5 5.5 0 0 0 7.2 8.6 4.8 4.8 0 0 0 7 18z"/><path d="M4 4l16 16"/>'),
  newWindow: L('<rect x="3.5" y="4.5" width="17" height="15" rx="2"/><path d="M3.5 9h17M12 12.5v4M10 14.5h4"/>'),
  reload: L('<path d="M19 12a7 7 0 1 1-2.1-5"/><path d="M19 4.5V8h-3.5"/>'),
  panelLeft: L('<rect x="3.5" y="4.5" width="17" height="15" rx="2"/><path d="M9.5 4.5v15"/>'),
  panelRight: L('<rect x="3.5" y="4.5" width="17" height="15" rx="2"/><path d="M14.5 4.5v15"/>'),
  panelBottom: L('<rect x="3.5" y="4.5" width="17" height="15" rx="2"/><path d="M3.5 14.5h17"/>'),
  undo: L('<path d="M9 7L4.5 11.5 9 16"/><path d="M4.5 11.5H15a4.5 4.5 0 0 1 0 9h-3"/>'),
  redo: L('<path d="M15 7l4.5 4.5L15 16"/><path d="M19.5 11.5H9a4.5 4.5 0 0 0 0 9h3"/>'),
  cut: L('<circle cx="7" cy="17" r="2.5"/><circle cx="17" cy="17" r="2.5"/><path d="M8.5 15L17 4.5M15.5 15L7 4.5"/>'),
  copy: L('<rect x="8.5" y="8.5" width="11" height="11" rx="2"/><path d="M15.5 8.5V6.5a2 2 0 0 0-2-2h-7a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h2"/>'),
  paste: L('<rect x="5" y="5.5" width="14" height="15" rx="2"/><path d="M9 5.5V4h6v1.5M9 11h6M9 14.5h4"/>'),
  selectAll: L('<rect x="4.5" y="4.5" width="15" height="15" rx="2" stroke-dasharray="2.5 2.5"/><path d="M8.5 12.5l2.5 2.5 4.5-5"/>'),
  book: L('<path d="M5 5.5A1.5 1.5 0 0 1 6.5 4H19v14.5H6.5A1.5 1.5 0 0 0 5 20z"/><path d="M5 20V5.5M9 8.5h6"/>'),
  upload: L('<path d="M12 15.5V4.5M7.5 9L12 4.5 16.5 9M5 19.5h14"/>'),
  density: L('<path d="M4 7h16M4 12h16M4 17h16"/>'),
  package: L('<path d="M12 3.5l8 4v9l-8 4-8-4v-9z"/><path d="M4 7.5l8 4 8-4M12 11.5v9M8 5.5l8 4"/>'),
  key: L('<circle cx="8" cy="15" r="3.5"/><path d="M10.5 12.5L19 4M15.5 7.5l2.5 2.5M13 10l2 2"/>'),
  shield: L('<path d="M12 3.5l7 2.5v5.5c0 4.2-2.8 7.4-7 9-4.2-1.6-7-4.8-7-9V6z"/><path d="M8.8 12l2.4 2.4 4-4.8"/>'),
  compare: L('<path d="M9 4.5v15M15 4.5v15"/><path d="M4.5 8.5L9 4.5l4.5 4M10.5 15.5l4.5 4 4.5-4"/>'),
});
