import '../styles/hosting.css';
import guide from '../../../docs/HOSTING.md?raw';
import { Dialog } from './dialogs';
import { el, escapeHtml, q } from './dom';

export const HOSTING_PART: Record<string, string> = {
  'static-zip': 'static-zip',
  netlify: 'netlify',
  'cloudflare-pages': 'cloudflare-pages',
  vercel: 'vercel',
  'github-pages': 'github-pages',
  nginx: 'nginx-on-your-own-server',
};

const slug = (text: string): string => text.toLowerCase().replace(/[^a-z0-9 -]/g, '').trim().replace(/\s+/g, '-');

function inline(text: string): string {
  return escapeHtml(text)
    .replace(/`([^`]+)`/g, '<code translate="no">$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\[([^\]]+)\]\(#([a-z0-9-]+)\)/g, '<a href="#$2" data-part="$2">$1</a>')
    .replace(/\[([^\]]+)\]\(([A-Za-z0-9_-]+\.md)\)/g, '<a href="#" data-doc="$2">$1</a>')
    .replace(/\[([^\]]+)\]\([^)\s]+\)/g, '$1');
}

function table(rows: string[]): string {
  const cells = (row: string): string[] => row.replace(/^\||\|$/g, '').split('|').map((c) => c.trim());
  const codes = (cell: string): string => {
    const found = [...cell.matchAll(/`([a-z0-9.-]+)`/g)].map((m) => m[1]);
    return found.length && cell.replace(/`[a-z0-9.-]+`|[\s,]/g, '') === '' ? ` data-code="${found.join(' ')}"` : '';
  };
  const head = cells(rows[0]).map((c) => `<th>${inline(c)}</th>`).join('');
  const body = rows.slice(2).map((r) => { const row = cells(r); return `<tr${codes(row[0] ?? '')}>${row.map((c) => `<td>${inline(c)}</td>`).join('')}</tr>`; }).join('');
  return `<div class="fp-host-table"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}

const IMAGE_ROUTE = '/api/docs/images/';

function figure(line: string): string | null {
  const md = /^!\[([^\]]*)\]\(images\/([a-z0-9-]+\.webp)\)$/.exec(line.trim());
  const pic = md ? null : /^<picture><source media="\(prefers-color-scheme: dark\)" srcset="images\/([a-z0-9-]+\.webp)"><img alt="([^"]*)" src="images\/([a-z0-9-]+\.webp)"><\/picture>$/.exec(line.trim());
  if (!md && !pic) return /^(!\[|<picture>)/.test(line) ? '' : null;
  const alt = escapeHtml(md ? md[1] : pic![2]);
  const light = md ? md[2] : pic![3];
  const dark = md ? light.replace(/-light\.webp$/, '-dark.webp') : pic![1];
  const img = (name: string, cls: string): string => `<img class="${cls}" src="${IMAGE_ROUTE}${name}" alt="${alt}" width="1600" height="1000" loading="lazy" decoding="async">`;
  return `<figure class="fp-host-fig">${dark === light ? img(light, '') : img(dark, 'is-dark') + img(light, 'is-light')}</figure>`;
}

export function renderGuide(markdown: string, prefix = 'fp-host'): string {
  const lines = markdown.replace(/\r/g, '').split('\n');
  const out: string[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) { i += 1; continue; }
    if (line.startsWith('```')) {
      const code: string[] = [];
      for (i += 1; i < lines.length && !lines[i].startsWith('```'); i += 1) code.push(lines[i]);
      out.push(`<pre class="fp-host-code" translate="no">${escapeHtml(code.join('\n'))}</pre>`);
      i += 1;
      continue;
    }
    const heading = /^(#{1,3}) (.+)$/.exec(line);
    if (heading) {
      const level = heading[1].length;
      out.push(level === 1 ? '' : `<h${level} id="${prefix}-${slug(heading[2])}" class="fp-host-h${level}">${inline(heading[2])}</h${level}>`);
      i += 1;
      continue;
    }
    const fig = figure(line);
    if (fig !== null) {
      out.push(fig);
      i += 1;
      continue;
    }
    if (line.startsWith('|')) {
      const rows: string[] = [];
      for (; i < lines.length && lines[i].startsWith('|'); i += 1) rows.push(lines[i]);
      out.push(table(rows));
      continue;
    }
    const listed = /^(\d+\.|-) /.exec(line);
    if (listed) {
      const ordered = listed[1] !== '-';
      const items: string[] = [];
      for (; i < lines.length && /^(\d+\.|-) /.test(lines[i]); i += 1) {
        let item = inline(lines[i].replace(/^(\d+\.|-) /, ''));
        const sub: string[] = [];
        for (; i + 1 < lines.length && /^ {2,}- /.test(lines[i + 1]); i += 1) sub.push(`<li>${inline(lines[i + 1].replace(/^ +- /, ''))}</li>`);
        if (sub.length) item += `<ul>${sub.join('')}</ul>`;
        items.push(`<li>${item}</li>`);
      }
      out.push(ordered ? `<ol>${items.join('')}</ol>` : `<ul>${items.join('')}</ul>`);
      continue;
    }
    const para: string[] = [];
    for (; i < lines.length && lines[i].trim() && !/^(#|\||```|\d+\. |- |!\[|<picture>)/.test(lines[i]); i += 1) para.push(lines[i]);
    out.push(`<p>${inline(para.join(' '))}</p>`);
  }
  return out.join('');
}

export class HostingSheet extends Dialog {
  private readonly page: HTMLElement;

  constructor() {
    super('Host it yourself', 760, 'fp-host-dlg');
    this.page = document.createElement('article');
    this.page.className = 'fp-host-page';
    this.page.lang = 'en';
    this.page.setAttribute('translate', 'no');
    this.page.innerHTML = renderGuide(guide);
    this.body.appendChild(this.page);
    this.page.addEventListener('click', (e) => {
      const link = (e.target as HTMLElement).closest<HTMLAnchorElement>('a[data-part]');
      if (!link) return;
      e.preventDefault();
      this.jump(link.dataset.part ?? '');
    });
    this.foot.appendChild(el('<span class="fp-host-note">The guide is in English.</span>'));
    this.button('Close', 'primary', () => this.close());
  }

  show(part?: string): void {
    this.open(q(this.foot, '.fp-btn-primary'));
    this.jump(part ?? '');
  }

  private jump(part: string): void {
    const target = part ? this.page.querySelector<HTMLElement>(`#fp-host-${part}`) : null;
    this.body.scrollTop = target ? this.body.scrollTop + target.getBoundingClientRect().top - this.body.getBoundingClientRect().top : 0;
  }
}

let sheet: HostingSheet | null = null;

export function openHosting(part?: string): void {
  sheet ??= new HostingSheet();
  sheet.show(part);
}
