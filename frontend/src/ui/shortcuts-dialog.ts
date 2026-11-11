import '../styles/shortcuts.css';
import { onLanguage, t } from '../i18n';
import { comboOf, formatKeys, rejectCombo, type Command, type Commands } from './commands';
import { Dialog } from './dialogs';
import { el, q, setAttr, setClass, setDisabled, setText } from './dom';

const ORDER = ['File', 'Edit', 'View', 'Site', 'App', 'Help'];
const MODIFIERS = new Set(['Shift', 'Control', 'Alt', 'Meta', 'AltGraph', 'CapsLock']);
const HINT = 'Choose Change, then press the new keys.';
const RECORD_HINT = 'Press the new keys. Escape cancels, Backspace clears.';

interface Row { cmd: Command; label: HTMLElement; keys: HTMLElement; change: HTMLButtonElement; reset: HTMLButtonElement; node: HTMLElement }
interface Pending { row: Row; apply: () => void }

export class ShortcutsDialog extends Dialog {
  private readonly rows: Row[] = [];
  private readonly note: HTMLElement;
  private readonly replace: HTMLButtonElement;
  private readonly keep: HTMLButtonElement;
  private readonly resetAll: HTMLButtonElement;
  private recording: Row | null = null;
  private pending: Pending | null = null;

  constructor(private readonly commands: Commands) {
    super('Keyboard Shortcuts', 620, 'fp-shortcuts-dlg');
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
        const node = el('<div class="fp-shortcut-row"><span class="fp-shortcut-label"></span><kbd class="fp-shortcut-keys"></kbd><button class="fp-btn fp-btn-ghost fp-btn-sm fp-shortcut-change" type="button">Change</button><button class="fp-btn fp-btn-ghost fp-btn-sm fp-shortcut-reset" type="button">Reset</button></div>');
        const row: Row = { cmd, node, label: q(node, '.fp-shortcut-label'), keys: q(node, '.fp-shortcut-keys'), change: q(node, '.fp-shortcut-change'), reset: q(node, '.fp-shortcut-reset') };
        row.change.addEventListener('click', () => { if (this.recording === row) this.stop(); else this.record(row); });
        row.reset.addEventListener('click', () => this.resetRow(row));
        setAttr(row.change, 'aria-label', `Change shortcut: ${commands.label(cmd)}`);
        setAttr(row.reset, 'aria-label', `Reset shortcut: ${commands.label(cmd)}`);
        section.appendChild(node);
        this.rows.push(row);
      }
      list.appendChild(section);
    }
    this.body.appendChild(list);
    this.note = el('<span class="fp-shortcuts-note" role="status" aria-live="polite"></span>');
    this.foot.appendChild(this.note);
    this.replace = this.button('Replace', 'primary', () => this.confirm());
    this.keep = this.button('Cancel', '', () => this.dismiss());
    this.replace.hidden = true;
    this.keep.hidden = true;
    this.resetAll = this.button('Reset all', 'ghost', () => { this.stop(); this.dismiss(); commands.resetKeys(); this.say('All shortcuts are back to their defaults.'); });
    this.button('Close', 'primary', () => this.close());
    this.scrim.addEventListener('keydown', (e) => this.onKey(e), true);
    this.scrim.addEventListener('pointerdown', (e) => {
      if (this.recording && !this.recording.change.contains(e.target as Node)) this.stop();
    }, true);
    this.onClose = () => { this.stop(); this.dismiss(); };
    commands.onChange(() => this.paint());
    onLanguage(() => this.paint());
  }

  show(): void {
    this.say(HINT);
    this.paint();
    this.open();
  }

  private paint(): void {
    for (const r of this.rows) {
      const recording = this.recording === r;
      setText(r.label, t(this.commands.label(r.cmd)));
      const keys = this.commands.keyLabel(r.cmd);
      setText(r.keys, recording ? 'Press keys' : keys || '-');
      setClass(r.keys, 'is-none', !recording && !keys);
      setClass(r.keys, 'is-recording', recording);
      setText(r.change, recording ? 'Cancel' : 'Change');
      setDisabled(r.change, !!r.cmd.native);
      setClass(r.reset, 'is-off', !this.commands.isCustom(r.cmd.id));
      r.reset.tabIndex = this.commands.isCustom(r.cmd.id) ? 0 : -1;
    }
    setDisabled(this.resetAll, !this.rows.some((r) => this.commands.isCustom(r.cmd.id)));
  }

  private name(cmd: Command): string {
    return this.commands.label(cmd).replace(/(\.\.\.|…)$/, '');
  }

  private say(text: string, warn = false): void {
    setText(this.note, text);
    setClass(this.note, 'is-warn', warn);
  }

  private record(row: Row): void {
    this.dismiss();
    this.recording = row;
    this.say(RECORD_HINT);
    this.paint();
    row.change.focus();
  }

  private stop(): void {
    if (!this.recording) return;
    this.recording = null;
    this.paint();
  }

  private ask(row: Row, text: string, apply: () => void): void {
    this.pending = { row, apply };
    this.say(text, true);
    this.replace.hidden = false;
    this.keep.hidden = false;
    this.replace.focus();
  }

  private dismiss(): void {
    if (!this.pending) return;
    const row = this.pending.row;
    this.pending = null;
    this.replace.hidden = true;
    this.keep.hidden = true;
    this.say(HINT);
    row.change.focus();
  }

  private confirm(): void {
    const pending = this.pending;
    if (!pending) return;
    this.pending = null;
    this.replace.hidden = true;
    this.keep.hidden = true;
    pending.apply();
    pending.row.change.focus();
  }

  private resetRow(row: Row): void {
    this.stop();
    this.dismiss();
    const id = row.cmd.id;
    const combo = this.commands.defaultKeys(id)[0];
    const other = combo ? this.commands.owner(combo, id) : undefined;
    const done = (): void => { this.commands.resetKey(id); this.say(`${this.name(row.cmd)} is back to its default.`); };
    if (other && !other.native) this.ask(row, `${formatKeys(combo)} is used by ${this.name(other)}. Move it back to ${this.name(row.cmd)}?`, done);
    else done();
  }

  private onKey(e: KeyboardEvent): void {
    const row = this.recording;
    if (!row) {
      if (this.pending && e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); this.dismiss(); }
      return;
    }
    e.preventDefault();
    e.stopPropagation();
    if (e.repeat || e.isComposing || MODIFIERS.has(e.key)) return;
    const plain = !e.metaKey && !e.ctrlKey && !e.altKey && !e.shiftKey;
    if (e.key === 'Escape' && plain) { this.stop(); this.say(HINT); return; }
    const cmd = row.cmd;
    if (e.key === 'Backspace' && plain) {
      this.stop();
      this.commands.setKeys(cmd.id, []);
      this.say(`${this.name(cmd)} has no shortcut.`);
      return;
    }
    const combo = comboOf(e);
    const why = rejectCombo(combo);
    if (why) { this.say(why, true); return; }
    const other = this.commands.owner(combo, cmd.id);
    if (other?.native) { this.say('Text editing keys cannot be moved.', true); return; }
    this.stop();
    if (cmd.keys?.length === 1 && cmd.keys[0] === combo) { this.say(HINT); return; }
    const apply = (): void => { this.commands.setKeys(cmd.id, [combo]); this.say(`${this.name(cmd)} is now ${formatKeys(combo)}.`); };
    if (other) this.ask(row, `${formatKeys(combo)} is already used by ${this.name(other)}. Move it to ${this.name(cmd)}?`, apply);
    else apply();
  }
}
