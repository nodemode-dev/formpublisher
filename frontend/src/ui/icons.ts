const L = (body: string): string => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">${body}</svg>`;

export const ICONS: Record<string, string> = {
  info: L('<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5M12 8v.01"/>'),
  plus: L('<path d="M12 5v14M5 12h14"/>'),
  close: L('<path d="M6 6l12 12M18 6L6 18"/>'),
  check: L('<path d="M5 12.5l4.5 4.5L19 7.5"/>'),
  alert: L('<path d="M12 4l9 15.5H3z"/><path d="M12 10v4.5M12 17.2v.01"/>'),
  commandPalette: L('<rect x="3.5" y="5.5" width="17" height="13" rx="2"/><path d="M7.5 10l2.5 2-2.5 2M12.5 14.5h4"/>'),
  sun: L('<circle cx="12" cy="12" r="3.8"/><path d="M12 3.5v2M12 18.5v2M3.5 12h2M18.5 12h2M6 6l1.4 1.4M16.6 16.6L18 18M6 18l1.4-1.4M16.6 7.4L18 6"/>'),
  moon: L('<path d="M19.5 14.5A7.5 7.5 0 0 1 9.5 4.5a7.5 7.5 0 1 0 10 10z"/>'),
  settings: L('<path d="M4 7h9M17 7h3M4 17h3M11 17h9"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/>'),
  link: L('<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>'),
  globe: L('<circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17M12 3.5c2.5 2.6 3.7 5.4 3.7 8.5s-1.2 5.9-3.7 8.5c-2.5-2.6-3.7-5.4-3.7-8.5S9.5 6.1 12 3.5z"/>'),
  folder: L('<path d="M3.5 7A1.5 1.5 0 0 1 5 5.5h4l2 2.5h8A1.5 1.5 0 0 1 20.5 9.5v8A1.5 1.5 0 0 1 19 19H5a1.5 1.5 0 0 1-1.5-1.5z"/>'),
  archive: L('<rect x="3.5" y="4.5" width="17" height="4" rx="1"/><path d="M5 8.5v9A1.5 1.5 0 0 0 6.5 19h11a1.5 1.5 0 0 0 1.5-1.5v-9M10 12.5h4"/>'),
  download: L('<path d="M12 4v11M7.5 10.5L12 15l4.5-4.5M5 19.5h14"/>'),
  chevronLeft: L('<path d="M14.5 6l-6 6 6 6"/>'),
  chevronRight: L('<path d="M9.5 6l6 6-6 6"/>'),
  chevronDown: L('<path d="M6 9.5l6 6 6-6"/>'),
  routes: L('<circle cx="6" cy="6.5" r="2"/><circle cx="6" cy="17.5" r="2"/><circle cx="18" cy="12" r="2"/><path d="M8 6.5h3a3 3 0 0 1 3 3v.5M8 17.5h3a3 3 0 0 0 3-3V14"/>'),
  terminal: L('<rect x="3.5" y="4.5" width="17" height="15" rx="2"/><path d="M7.5 9.5l3 2.5-3 2.5M12.5 15h4"/>'),
  filter: L('<path d="M4 5.5h16l-6.2 7.3v5.2l-3.6 1.8v-7z"/>'),
  publish: L('<path d="M12 15.5V4.5M7.5 9L12 4.5 16.5 9"/><path d="M5 14.5v3A2 2 0 0 0 7 19.5h10a2 2 0 0 0 2-2v-3"/>'),
};

export function icon(name: string, size = 16): string {
  const svg = ICONS[name] ?? ICONS.info;
  return `<span class="icon" style="width:${size}px;height:${size}px" aria-hidden="true">${svg}</span>`;
}

export function hasIcon(name: string): boolean {
  return Object.prototype.hasOwnProperty.call(ICONS, name);
}
