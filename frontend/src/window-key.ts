const HEADER = 'X-FormPublisher-Key';
const STORE = 'formpublisher-window-key';

let key = '';

function remembered(): string {
  try { return sessionStorage.getItem(STORE) ?? ''; } catch { return ''; }
}

function remember(value: string): void {
  try { sessionStorage.setItem(STORE, value); } catch { return; }
}

function engineApi(input: RequestInfo | URL): boolean {
  try {
    const url = new URL(typeof input === 'string' ? input : input instanceof URL ? input.href : input.url, location.href);
    return url.origin === location.origin && url.pathname.startsWith('/api/');
  } catch { return false; }
}

function attach(): void {
  const native = window.fetch.bind(window);
  window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
    if (!key || !engineApi(input)) return native(input, init);
    const headers = new Headers(init?.headers ?? (input instanceof Request ? input.headers : undefined));
    headers.set(HEADER, key);
    return native(input, { ...init, headers });
  };
}

async function keptKeyWorks(): Promise<boolean> {
  const kept = remembered();
  if (!kept) return false;
  try {
    const res = await fetch('/api/window/check', { method: 'POST', headers: { [HEADER]: kept } });
    return res.ok;
  } catch { return false; }
}

export async function loadWindowKey(): Promise<void> {
  const holder = window as unknown as { __FORMPUBLISHER_WINDOW_KEY?: unknown };
  const given = holder.__FORMPUBLISHER_WINDOW_KEY;
  delete holder.__FORMPUBLISHER_WINDOW_KEY;
  if (typeof given === 'string' && given) key = given;
  else if (await keptKeyWorks()) key = remembered();
  else {
    try {
      const res = await fetch('/api/window/key', { method: 'POST' });
      const body = res.ok ? await res.json() as { key?: unknown } : {};
      if (typeof body.key === 'string' && body.key) { key = body.key; remember(key); }
    } catch { key = ''; }
  }
  if (key) attach();
}

export const windowKey = (): string => key;
