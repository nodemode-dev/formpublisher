import '../styles/templates.css';
import { api } from '../api';
import type { App } from '../app-api';
import { templatesApi, type StartedSite, type TemplateItem, type TemplateList } from '../api-templates';
import { onLanguage } from '../i18n';
import { fmtCount, fmtDate } from './builds';
import { Dialog } from './dialogs';
import { el, inTauri, patchList, q, setDisabled, setHidden, setText } from './dom';
import { icon } from './icons';

const SKELETONS = 3;

const megabytes = (bytes: number): string => `${(bytes / 1048576).toFixed(1)} MB`;

async function openExternal(target: string): Promise<void> {
  if (inTauri()) {
    const { invoke } = await import('@tauri-apps/api/core');
    await invoke('plugin:shell|open', { path: target });
    return;
  }
  window.open(target, '_blank', 'noopener');
}

const skeleton = (): string => `<div class="fp-tpl-card is-skeleton" aria-hidden="true"><span class="fp-tpl-preview"></span><span class="fp-tpl-name">&nbsp;</span><span class="fp-tpl-desc">&nbsp;</span><span class="fp-tpl-meta"></span><span class="fp-tpl-credit"></span><span class="fp-btn fp-btn-sm fp-tpl-start">${icon('plus', 14)}<span>Start a site from this</span></span></div>`;

export class TemplatesSheet extends Dialog {
  private readonly list: HTMLElement;
  private readonly status: HTMLElement;
  private readonly said: HTMLElement;
  private readonly more: HTMLElement;
  private readonly getBtn: HTMLButtonElement;
  private readonly none: HTMLElement;
  private readonly done: HTMLElement;
  private started: StartedSite | null = null;
  private kept: TemplateList | null = null;
  private busy = false;

  constructor(private readonly app: App) {
    super('Templates', 760, 'fp-tpl-dlg');
    this.body.appendChild(el(`<div class="fp-tpl-wrap">
<p class="fp-tpl-intro">Start a site from a template, edit it in FormWeb, then check, package and publish it here. The list comes from the public formai-templates repository on GitHub. Nothing is fetched until you ask.</p>
<div class="fp-tpl-bar"><button class="fp-btn fp-btn-primary fp-btn-sm" type="button" data-a="get">${icon('download', 14)}<span data-f="getlabel">Get the templates</span></button><span class="fp-tpl-status" data-f="status" role="status"><span data-f="said"></span> <span data-f="more"></span></span></div>
<div class="fp-tpl-grid">${Array.from({ length: SKELETONS }, skeleton).join('')}<div class="fp-tpl-list" hidden></div></div>
<div class="fp-tpl-none"></div>
<section class="fp-tpl-done" aria-live="polite">
<div class="fp-tpl-done-text" data-f="done">Pick a template and press Start a site from this. You choose the folder the new FormWeb project goes into.</div>
<div class="fp-tpl-path" data-f="path" translate="no"></div>
<div class="fp-tpl-next">
<button class="fp-btn fp-btn-sm" type="button" data-a="edit" disabled>${icon('link', 14)}<span>Edit in FormWeb</span></button>
<button class="fp-btn fp-btn-sm" type="button" data-a="publish" disabled>${icon('publish', 14)}<span>Publish it</span></button>
</div>
<div class="fp-tpl-hint">Editing happens in FormWeb, which is free and in the same family; FormPublisher has no editor of its own. In FormWeb, choose File, Import .fweb or .fpub file, and pick the project above.</div>
</section>
</div>`));
    this.list = q(this.body, '.fp-tpl-list');
    this.status = q(this.body, '[data-f="status"]');
    this.said = q(this.status, '[data-f="said"]');
    this.more = q(this.status, '[data-f="more"]');
    this.getBtn = q<HTMLButtonElement>(this.body, '[data-a="get"]');
    this.none = q(this.body, '.fp-tpl-none');
    this.done = q(this.body, '.fp-tpl-done');
    this.button('Close', 'ghost', () => this.close());
    this.body.addEventListener('click', (e) => {
      const t = (e.target as HTMLElement).closest<HTMLElement>('[data-a]');
      if (!t) return;
      const action = t.dataset.a;
      if (action === 'get') void this.refresh();
      else if (action === 'start') void this.start(t.closest<HTMLElement>('[data-key]')?.dataset.key ?? '', t.closest<HTMLElement>('[data-key]')?.dataset.name ?? '');
      else if (action === 'edit') void this.edit();
      else if (action === 'publish') void this.publish();
    });
    onLanguage(() => { if (this.kept) this.sayKept(this.kept); });
  }

  async show(): Promise<void> {
    this.open(this.getBtn);
    try {
      this.paint(await templatesApi.kept());
    } catch (e) {
      this.say(e instanceof Error ? e.message : 'The kept list could not be read', true);
    }
  }

  private say(text: string, bad = false, more = ''): void {
    this.kept = null;
    setText(this.said, text);
    setText(this.more, more);
    this.status.classList.toggle('is-error', bad);
  }

  private paint(data: TemplateList): void {
    setText(q(this.body, '[data-f="getlabel"]'), data.fetched ? 'Check again' : 'Get the templates');
    setText(this.none, data.fetched ? '' : 'No list yet. Press Get the templates to read it.');
    if (!data.fetched) { this.say(''); return; }
    q(this.body, '.fp-tpl-grid').querySelectorAll('.is-skeleton').forEach((n) => n.remove());
    setHidden(this.list, false);
    this.sayKept(data);
    patchList(this.list, data.items, {
      key: (item) => item.id,
      create: (item) => this.card(item),
      update: (node, item) => this.fill(node, item),
    });
  }

  private sayKept(data: TemplateList): void {
    const others = data.notStartable === 1
      ? "1 more is a part for FormWeb's own library, not a whole site, so it is not offered here."
      : data.notStartable ? `${data.notStartable} more are parts for FormWeb's own library, not whole sites, so they are not offered here.` : '';
    this.say(`Kept list from ${fmtDate(data.fetchedAt)}: ${fmtCount(data.items.length, 'whole site', 'whole sites')}.`, false, others);
    this.kept = data;
  }

  private card(item: TemplateItem): HTMLElement {
    const node = el(`<article class="fp-tpl-card" data-key=""><span class="fp-tpl-preview"><img alt="" width="320" height="180" decoding="async" draggable="false"></span><span class="fp-tpl-name" translate="no"></span><span class="fp-tpl-desc"></span><span class="fp-tpl-meta"></span><span class="fp-tpl-credit"></span><button class="fp-btn fp-btn-sm fp-tpl-start" type="button" data-a="start">${icon('plus', 14)}<span>Start a site from this</span></button></article>`);
    const img = q<HTMLImageElement>(node, 'img');
    img.addEventListener('load', () => img.classList.add('is-loaded'));
    this.fill(node, item);
    return node;
  }

  private fill(node: HTMLElement, item: TemplateItem): void {
    node.dataset.key = item.id;
    node.dataset.name = item.name;
    setText(q(node, '.fp-tpl-name'), item.name);
    setText(q(node, '.fp-tpl-desc'), item.description || 'A whole FormWeb site with its pages and pictures.');
    setText(q(node, '.fp-tpl-meta'), `${megabytes(item.bytes)} · ${item.licence}`);
    setText(q(node, '.fp-tpl-credit'), item.credit);
    const img = q<HTMLImageElement>(node, 'img');
    const src = item.preview ? templatesApi.previewUrl(item.id) : '';
    if (img.dataset.src !== src) {
      img.dataset.src = src;
      img.classList.remove('is-loaded');
      if (src) img.src = src; else img.removeAttribute('src');
    }
  }

  private async refresh(): Promise<void> {
    if (this.busy) return;
    this.busy = true;
    setDisabled(this.getBtn, true);
    this.say('Reading the list');
    try {
      this.paint(await templatesApi.fetch());
    } catch (e) {
      this.say(e instanceof Error ? e.message : 'The list could not be read', true);
    } finally {
      this.busy = false;
      setDisabled(this.getBtn, false);
    }
  }

  private async start(id: string, name: string): Promise<void> {
    if (this.busy || !id) return;
    const folder = await this.app.pickFolder();
    if (!folder) return;
    this.busy = true;
    this.done.classList.remove('is-error');
    setText(q(this.done, '[data-f="done"]'), `Downloading ${name} and checking its SHA-256`);
    try {
      this.started = await templatesApi.start(id, folder);
      setText(q(this.done, '[data-f="done"]'), `Made a FormWeb project from ${name} (${fmtCount(this.started.files, 'file', 'files')}).`);
      setText(q(this.done, '[data-f="path"]'), this.started.project);
    } catch (e) {
      this.started = null;
      this.done.classList.add('is-error');
      setText(q(this.done, '[data-f="done"]'), e instanceof Error ? e.message : 'The site could not be started');
      setText(q(this.done, '[data-f="path"]'), '');
    } finally {
      this.busy = false;
      setDisabled(q<HTMLButtonElement>(this.done, '[data-a="edit"]'), this.started === null);
      setDisabled(q<HTMLButtonElement>(this.done, '[data-a="publish"]'), this.started === null);
    }
  }

  private async edit(): Promise<void> {
    const settings = await api.settings().catch(() => ({} as Record<string, unknown>));
    const url = typeof settings.formwebUrl === 'string' && settings.formwebUrl ? settings.formwebUrl : 'http://127.0.0.1:8240';
    await openExternal(url);
  }

  private async publish(): Promise<void> {
    if (!this.started) return;
    const project = this.started.project;
    this.close();
    await this.app.importFolder(project).catch(() => undefined);
  }
}
