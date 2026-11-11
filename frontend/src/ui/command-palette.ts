import { onLanguage, t } from '../i18n';
import type { Command, Commands } from './commands';
import { Dialog } from './dialogs';
import { el, q, setClass, setHidden, setText } from './dom';
import { icon } from './icons';

interface Entry { cmd: Command; row: HTMLElement; label: HTMLElement; group: HTMLElement; keys: HTMLElement; text: string; hay: string }

function subsequence(word: string, text: string): boolean {
  let at = 0;
  for (const ch of text) if (ch === word[at] && ++at === word.length) return true;
  return word.length === 0;
}

export class CommandPalette extends Dialog {
  private readonly input: HTMLInputElement;
  private readonly listEl: HTMLElement;
  private readonly none: HTMLElement;
  private readonly entries: Entry[] = [];
  private shown: Entry[] = [];
  private at = 0;

  constructor(private readonly commands: Commands) {
    super('Find a Command', 560, 'fp-palette-dlg');
    this.body.append(el(`<div class="fp-palette">
<input class="fp-input fp-palette-input" type="search" spellcheck="false" autocomplete="off" placeholder="Type what you want to do: open, reload, theme, shortcuts" aria-label="Search commands" aria-controls="fp-palette-list">
<div class="fp-palette-list" id="fp-palette-list" role="listbox" aria-label="Commands"><p class="fp-palette-none" hidden>No command matches. Try another word.</p></div>
</div>`));
    this.input = q<HTMLInputElement>(this.body, '.fp-palette-input');
    this.listEl = q(this.body, '.fp-palette-list');
    this.none = q(this.body, '.fp-palette-none');
    this.foot.hidden = true;
    for (const cmd of commands.all()) {
      const row = el(`<div class="fp-palette-row" role="option" aria-selected="false" hidden><span class="fp-palette-icon">${icon(cmd.icon ?? 'commandPalette', 14)}</span><span class="fp-palette-label"></span><span class="fp-palette-group"></span><kbd class="fp-palette-keys"></kbd></div>`);
      const entry: Entry = { cmd, row, label: q(row, '.fp-palette-label'), group: q(row, '.fp-palette-group'), keys: q(row, '.fp-palette-keys'), text: '', hay: '' };
      row.addEventListener('pointerdown', (e) => { e.preventDefault(); this.pick(entry); });
      row.addEventListener('pointermove', () => this.highlight(this.shown.indexOf(entry)));
      this.listEl.appendChild(row);
      this.entries.push(entry);
    }
    onLanguage(() => this.relabel());
    this.input.addEventListener('input', () => this.filter());
    this.input.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        if (this.shown.length) this.highlight((this.at + (e.key === 'ArrowDown' ? 1 : -1) + this.shown.length) % this.shown.length);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        const entry = this.shown[this.at];
        if (entry) this.pick(entry);
      }
    });
  }

  private relabel(): void {
    for (const en of this.entries) {
      en.text = t(this.commands.label(en.cmd));
      const group = t(en.cmd.group ?? '');
      en.hay = `${en.cmd.id} ${en.text} ${group} ${en.cmd.description ?? ''}`.toLowerCase();
      setText(en.label, en.text);
      setText(en.group, group);
      setText(en.keys, this.commands.keyLabel(en.cmd));
    }
  }

  show(): void {
    this.relabel();
    this.input.value = '';
    this.filter();
    this.open(this.input);
  }

  private score(en: Entry, words: string[]): number {
    if (!this.commands.enabled(en.cmd)) return -1;
    const label = en.text.toLowerCase();
    let total = 1;
    for (const w of words) {
      if (label.startsWith(w)) total += 6;
      else if (label.split(/\s+/).some((p) => p.startsWith(w))) total += 5;
      else if (label.includes(w)) total += 4;
      else if (en.hay.includes(w)) total += 2;
      else if (w.length > 1 && subsequence(w, label)) total += 1;
      else return -1;
    }
    return total;
  }

  private filter(): void {
    const words = this.input.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
    const scored = this.entries.map((en) => [en, this.score(en, words)] as const).filter(([, s]) => s >= 0);
    scored.sort((a, b) => b[1] - a[1] || this.entries.indexOf(a[0]) - this.entries.indexOf(b[0]));
    this.shown = scored.map(([en]) => en);
    const visible = new Set(this.shown);
    for (const en of this.entries) setHidden(en.row, !visible.has(en));
    let cursor: Element | null = this.none.nextElementSibling;
    for (const en of this.shown) {
      if (en.row === cursor) cursor = cursor.nextElementSibling;
      else this.listEl.insertBefore(en.row, cursor);
    }
    setHidden(this.none, this.shown.length > 0);
    this.listEl.scrollTop = 0;
    this.highlight(0);
  }

  private highlight(i: number): void {
    if (i < 0) return;
    this.at = i;
    this.shown.forEach((en, n) => {
      const on = n === i;
      setClass(en.row, 'is-on', on);
      en.row.setAttribute('aria-selected', String(on));
      if (on) en.row.scrollIntoView({ block: 'nearest' });
    });
  }

  private pick(en: Entry): void {
    this.close();
    this.commands.run(en.cmd.id);
  }
}
