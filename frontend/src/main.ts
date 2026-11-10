import { initLanguage } from './i18n';
import { installChrome } from './ui/chrome';
import { revealApp } from './ui/dom';

const READY_CAP_MS = 900;

void initLanguage()
  .catch(() => undefined)
  .then(() => import('./app'))
  .then(async (m) => {
    const app = await m.startApp();
    installChrome(app);
    await Promise.race([app.ready, new Promise<void>((r) => window.setTimeout(r, READY_CAP_MS))]);
    revealApp();
  });
