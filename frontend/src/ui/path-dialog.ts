import { el, q } from './dom';
import { icon } from './icons';

export function askPath(overlay: HTMLElement): Promise<string | null> {
  return new Promise((resolve) => {
    const prior = document.activeElement as HTMLElement | null;
    const scrim = el(`<div class="fp-scrim"><div class="fp-dialog" role="dialog" aria-modal="true" aria-label="Open folder"><div class="fp-dialog-head"><span class="fp-dialog-title">Open folder</span><button class="fp-icon-btn is-sm" type="button" data-act="cancel" aria-label="Close" title="Close">${icon('close', 14)}</button></div><div class="fp-dialog-body"><label class="fp-dialog-label" for="fp-path-input">Folder path on this computer</label><input id="fp-path-input" class="fp-input is-mono" type="text" spellcheck="false" autocomplete="off" translate="no" placeholder="/path/to/publication"><div class="fp-dialog-error" role="alert"></div></div><div class="fp-dialog-foot"><button class="fp-btn" type="button" data-act="cancel">Cancel</button><button class="fp-btn fp-btn-primary" type="button" data-act="ok">Open</button></div></div></div>`);
    const input = q<HTMLInputElement>(scrim, 'input');
    const error = q(scrim, '.fp-dialog-error');
    const finish = (value: string | null): void => {
      scrim.remove();
      prior?.focus();
      resolve(value);
    };
    const submit = (): void => {
      const value = input.value.trim();
      if (!value) { error.textContent = 'Enter a folder path.'; input.focus(); return; }
      finish(value);
    };
    scrim.addEventListener('click', (e) => {
      const t = e.target as HTMLElement;
      if (t === scrim || t.closest('[data-act="cancel"]')) finish(null);
      else if (t.closest('[data-act="ok"]')) submit();
    });
    scrim.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') { e.preventDefault(); finish(null); }
      else if (e.key === 'Enter' && e.target === input) { e.preventDefault(); submit(); }
    });
    overlay.append(scrim);
    input.focus();
  });
}
