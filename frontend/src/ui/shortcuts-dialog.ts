import { t } from '../i18n';
import type { Command, Commands } from './commands';
import { Dialog } from './dialogs';
import { el, q, setClass, setText } from './dom';

const ORDER = ['File', 'Edit', 'View', 'Site', 'App', 'Help'];

interface Row { cmd: Command; label: HTMLElement; keys: HTMLElement; node: HTMLElement }

export class ShortcutsDialog extends Dialog {
  private readonly rows: Row[] = [];

  constructor(private readonly commands: Commands) {
    super('Keyboard Shortcuts', 560, 'fp-shortcuts-dlg');
    const list = el('<div class="fp-shortcuts"></div>');
    const groups = new Map<string, Command[]>();
    for (const cmd of commands.all()) {
      const g = cmd.group ?? 'App';
      groups.set(g, [...(groups.get(g) ?? []), cmd]);
    }
    const names = [...groups.keys()].sort((a, b) => (ORDER.indexOf(a) + 1 || 99) - (ORDER.indexOf(b) + 1 || 99));
    for (const name of names) {
      const section = el('<section class="fp-shortcuts-group"><h3 class="fp-shortcuts-head"></h3></section>');
      setText(q(section, 'h3'), name);
      for (const cmd of groups.get(name) ?? []) {
        const node = el('<div class="fp-shortcut-row"><span class="fp-shortcut-label"></span><kbd class="fp-shortcut-keys"></kbd></div>');
        const row: Row = { cmd, node, label: q(node, '.fp-shortcut-label'), keys: q(node, '.fp-shortcut-keys') };
        section.appendChild(node);
        this.rows.push(row);
      }
      list.appendChild(section);
    }
    this.body.appendChild(list);
    this.button('Close', 'primary', () => this.close());
  }

  show(): void {
    for (const r of this.rows) {
      setText(r.label, t(this.commands.label(r.cmd)));
      const keys = this.commands.keyLabel(r.cmd);
      setText(r.keys, keys || '-');
      setClass(r.keys, 'is-none', !keys);
    }
    this.open();
  }
}
