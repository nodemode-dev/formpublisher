'use strict';
(() => {
  const config = JSON.parse(document.getElementById('fw-config')?.textContent || '{}');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const nodes = new Map(Array.from(document.querySelectorAll('[data-fw-id]')).map(node => [node.dataset.fwId, node]));
  const dialogs = new Map(Array.from(document.querySelectorAll('dialog[data-fw-overlay]')).map(node => [node.dataset.fwOverlay, node]));
  const query = new URLSearchParams(location.search);
  const memorySession = new Map();
  const readSession = key => { try { return sessionStorage.getItem(key) ?? memorySession.get(key) ?? null; } catch { return memorySession.get(key) ?? null; } };
  const writeSession = (key, value) => { memorySession.set(key, value); try { sessionStorage.setItem(key, value); } catch {} dispatchEvent(new Event('formweb-session')); };
  const conditions = entries => (entries || []).every(condition => {
    const value = condition.source === 'session' ? readSession(condition.key) : query.get(condition.key);
    if (condition.op === 'exists') return value !== null;
    if (condition.op === 'ne') return value !== String(condition.value ?? '');
    if (condition.op === 'contains') return (value || '').includes(String(condition.value ?? ''));
    return value === String(condition.value ?? '');
  });
  const resolve = (id, scope = '') => nodes.get(id + scope) || nodes.get(id);
  const conditionalNodes = [];
  addEventListener('formweb-session', () => { for (const entry of conditionalNodes) { const active = conditions(entry.record.conditions); entry.node.hidden = entry.authoredHidden || !active; if (active && !entry.active) for (const invoke of entry.load) invoke(true); entry.active = active; } });
  const text = (node, content) => {
    if (!node) return;
    let target = Array.from(node.childNodes).find(child => child.nodeType === Node.TEXT_NODE);
    if (target) target.data = content;
    else if (!node.children.length) node.textContent = content;
    else node.insertBefore(document.createTextNode(content), node.firstChild);
  };
  const applyPatch = (node, patch) => {
    if (!node) return;
    if (Object.hasOwn(patch, 'text')) text(node, patch.text);
    for (const [name, value] of Object.entries(patch.styles || {})) value === null ? node.style.removeProperty(name) : node.style.setProperty(name, String(value));
    for (const [name, value] of Object.entries(patch.attrs || {})) value === null ? node.removeAttribute(name) : node.setAttribute(name, String(value));
  };
  const variant = (root, name) => {
    if (!root) return;
    const metadata = config.nodes?.[root.dataset.fwNode];
    const definition = config.components?.definitions?.[metadata?.componentId];
    const changes = definition?.variants?.[name]?.nodes;
    if (!changes) return;
    const descendants = [root, ...root.querySelectorAll('[data-fw-node]')];
    const references = new Map(descendants.map(node => { const source = config.nodes?.[node.dataset.fwNode]?.componentSourceId || node.dataset.fwNode; return [config.nodes?.[source]?.attrs?.id, node.id]; }).filter(([source, target]) => source && target));
    const fragment = value => typeof value === 'string' && value.startsWith('#') && references.has(value.slice(1)) ? '#' + references.get(value.slice(1)) : value;
    const scopedPatch = patch => { const result = { ...patch, attrs: { ...patch.attrs } }; if (Object.hasOwn(result.attrs, 'href')) result.attrs.href = fragment(result.attrs.href); return result; };
    for (const node of descendants) {
      const source = config.nodes?.[node.dataset.fwNode]?.componentSourceId || node.dataset.fwNode;
      const baseline = config.nodes?.[source] || config.nodes?.[node.dataset.fwNode] || {};
      const baseStyles = { ...baseline.styles };
      for (const breakpoint of [...config.breakpoints || []].sort((a, b) => b.maxWidth - a.maxWidth)) if (breakpoint.maxWidth === 100000 || matchMedia(`(max-width:${breakpoint.maxWidth}px)`).matches) Object.assign(baseStyles, baseline.breakpoints?.[breakpoint.id] || {});
      const reset = { styles: {}, attrs: {} };
      for (const option of Object.values(definition.variants || {})) {
        const patch = option.nodes?.[source] || {};
        if (Object.hasOwn(patch, 'text')) reset.text = baseline.text || '';
        for (const key of Object.keys(patch.styles || {})) reset.styles[key] = baseStyles[key] ?? 'revert';
        for (const key of Object.keys(patch.attrs || {})) reset.attrs[key] = baseline.attrs?.[key] ?? null;
      }
      applyPatch(node, scopedPatch(reset));
      if (changes[source]) applyPatch(node, scopedPatch(changes[source]));
      const values = config.components?.instances?.[root.dataset.fwNode]?.props || {};
      for (const [key, prop] of Object.entries(definition.props || {})) {
        if (prop.target !== source) continue;
        const value = Object.hasOwn(values, key) ? values[key] : prop.default;
        if (value === undefined) continue;
        if (prop.field === 'text') text(node, String(value));
        else if (prop.field.startsWith('styles.')) node.style.setProperty(prop.field.slice(7), String(value));
        else if (prop.field.startsWith('attrs.')) node.setAttribute(prop.field.slice(6), String(prop.field === 'attrs.href' ? fragment(value) : value));
      }
    }
    root.dataset.fwVariant = name;
  };
  const timeline = (id, scope) => {
    const specification = config.behaviors?.timelines?.[id];
    const animations = [];
    for (const track of specification?.tracks || []) {
      const node = resolve(track.node, scope);
      if (!node) continue;
      if (reduced.matches || !node.animate) { applyPatch(node, { styles: track.keyframes.at(-1) || {} }); continue; }
      const frames = track.keyframes.map(frame => Object.fromEntries(Object.entries(frame).map(([key, value]) => [key.startsWith('--') ? key : key.replace(/-([a-z])/g, (_, letter) => letter.toUpperCase()), value])));
      animations.push(node.animate(frames, { duration: track.duration, delay: track.at ?? track.delay ?? 0, easing: track.easing || 'ease', iterations: specification.repeat || 1, fill: 'both' }));
    }
    return animations;
  };
  const priorFocus = new WeakMap();
  const closeDialog = dialog => { if (dialog?.open) { dialog.close(); priorFocus.get(dialog)?.focus(); } };
  const openDialog = dialog => { if (!dialog || dialog.open) return; priorFocus.set(dialog, document.activeElement); dialog.showModal(); };
  for (const dialog of dialogs.values()) {
    dialog.querySelector('[data-fw-close]')?.addEventListener('click', () => closeDialog(dialog));
    dialog.addEventListener('cancel', event => { if (dialog.dataset.fwDismissible === 'false') event.preventDefault(); });
    dialog.addEventListener('close', () => { if (dialog.dataset.fwSessionKey) writeSession(dialog.dataset.fwSessionKey, 'dismissed'); priorFocus.get(dialog)?.focus(); });
    dialog.addEventListener('click', event => { if (event.target === dialog && dialog.dataset.fwDismissible !== 'false') { const bounds = dialog.getBoundingClientRect(); if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) closeDialog(dialog); } });
  }
  for (const dialog of dialogs.values()) { const specification = config.behaviors?.overlays?.[dialog.dataset.fwOverlayKey]; if (specification?.initial && (!specification.sessionKey || readSession(specification.sessionKey) !== 'dismissed')) openDialog(dialog); }
  const run = (origin, action, record, active = true) => {
    if (!conditions(action.conditions)) return;
    const node = action.target ? resolve(action.target, record.scope) : origin;
    if (!node) return;
    if (action.action === 'toggle-class') action.trigger === 'hover' ? node.classList.toggle(action.className, active) : active && node.classList.toggle(action.className);
    if (action.action === 'navigate' && active) location.assign(action.url);
    if (action.action === 'fade-in' && active) {
      node.style.opacity = '1';
      if (!reduced.matches && node.animate) node.animate([{ opacity: 0, transform: 'translateY(12px)' }, { opacity: 1, transform: 'translateY(0)' }], { duration: action.duration ?? 300, easing: action.easing || 'ease-out' });
    }
    if (action.action === 'variant' && active) variant(node, action.variant);
    if (action.action === 'timeline' && active) timeline(action.timeline, record.scope);
    if (action.action === 'overlay-open' && active) openDialog(dialogs.get(action.overlay + (record.scope || '')) || dialogs.get(action.overlay));
    if (action.action === 'overlay-close' && active) closeDialog(dialogs.get(action.overlay + (record.scope || '')) || dialogs.get(action.overlay));
    if (action.action === 'analytics-event' && active) queueMicrotask(() => { const extra = action.experiment ? { experiment: action.experiment, variant: assignment[action.experiment] } : {}; if (!action.experiment || extra.variant) track(action.event, extra); });
  };
  for (const node of nodes.values()) {
    node.addEventListener('pointerdown', () => node.setAttribute('data-fw-press', ''));
    for (const event of ['pointerup', 'pointercancel', 'pointerleave', 'blur']) node.addEventListener(event, () => node.removeAttribute('data-fw-press'));
    node.addEventListener('keydown', event => { if (['Enter', ' '].includes(event.key)) node.setAttribute('data-fw-press', ''); });
    node.addEventListener('keyup', () => node.removeAttribute('data-fw-press'));
  }
  for (const record of config.records || []) {
    const node = nodes.get(record.id);
    if (!node) continue;
    const conditionEntry = { node, record, authoredHidden: node.hasAttribute('hidden'), active: conditions(record.conditions), load: [] };
    if (record.conditions?.length) { conditionalNodes.push(conditionEntry); node.hidden = conditionEntry.authoredHidden || !conditionEntry.active; }
    for (const action of [...record.interactions || [], ...record.actions || []]) {
      let executed = false;
      const invoke = active => { if (active && action.once && executed) return; if (!conditions(record.conditions)) return; run(node, action, record, active); if (active) executed = true; };
      if (action.trigger === 'click') node.addEventListener('click', () => invoke(true));
      if (action.trigger === 'press') node.addEventListener('pointerdown', () => invoke(true));
      if (action.trigger === 'hover') {
        node.addEventListener('pointerenter', () => invoke(true)); node.addEventListener('pointerleave', () => invoke(false));
        node.addEventListener('focusin', () => invoke(true)); node.addEventListener('focusout', () => invoke(false));
      }
      if (action.trigger === 'load') { conditionEntry.load.push(invoke); invoke(true); }
      if (action.trigger === 'scroll') {
        if (reduced.matches || !window.IntersectionObserver) { invoke(true); continue; }
        if (action.action === 'fade-in') node.style.opacity = '0';
        const observer = new IntersectionObserver(entries => { if (entries.some(entry => entry.isIntersecting)) { invoke(true); if (action.once !== false) observer.disconnect(); } }, { threshold: .1 });
        observer.observe(node);
      }
    }
  }
  for (const list of document.querySelectorAll('[data-fw-list]:not([data-fw-managed])')) {
    const rows = Array.from(list.children).filter(node => node.hasAttribute('data-fw-item'));
    const size = Math.max(1, Number(list.dataset.fwPageSize));
    const navigation = list.querySelector('[data-fw-pagination]');
    const output = navigation?.querySelector('[data-fw-page-output]');
    let page = 0;
    const refresh = () => { const count = Math.max(1, Math.ceil(rows.length / size)); rows.forEach((row, index) => { row.hidden = Math.floor(index / size) !== page; }); if (output) output.textContent = `${page + 1} / ${count}`; navigation?.querySelector('[data-fw-prev]')?.toggleAttribute('disabled', page === 0); navigation?.querySelector('[data-fw-next]')?.toggleAttribute('disabled', page + 1 >= count); };
    navigation?.querySelector('[data-fw-prev]')?.addEventListener('click', () => { page = Math.max(0, page - 1); refresh(); });
    navigation?.querySelector('[data-fw-next]')?.addEventListener('click', () => { page = Math.min(Math.ceil(rows.length / size) - 1, page + 1); refresh(); });
    refresh();
  }
  for (const form of document.querySelectorAll('form[data-fw-form]')) {
    const settings = config.forms?.forms?.[form.dataset.fwNode] || {};
    for (const field of form.querySelectorAll('[data-fw-track]')) field.value = query.get(field.dataset.fwTrack) || '';
    const status = form.querySelector('[data-fw-form-status]');
    const errors = new Map(Array.from(form.querySelectorAll('[data-fw-error]')).map(output => [output.dataset.fwError, output]));
    form.addEventListener('submit', async event => {
      event.preventDefault();
      if (!form.reportValidity()) return;
      const button = form.querySelector('[type=submit]');
      if (button) button.disabled = true;
      if (status) status.textContent = 'Sending...';
      for (const output of errors.values()) output.textContent = '';
      try {
        const fields = new FormData(form);
        const encoded = window.fwEncodeForm ? await window.fwEncodeForm(form, fields) : null;
        if (!encoded && Array.from(fields.values()).some(value => typeof value !== 'string')) throw Error('File uploads are unavailable');
        const response = await fetch(form.action, { method: 'POST', body: encoded ? encoded.body : new URLSearchParams(fields), headers: { Accept: 'application/json', ...(encoded ? { 'Content-Type': encoded.type } : {}) } });
        const result = await response.json();
        if (!response.ok) { for (const [name, message] of Object.entries(result.errors || {})) { const output = errors.get(name); if (output) output.textContent = String(message); } throw Error(result.detail || 'Submission failed'); }
        if (status) status.textContent = result.successMessage || settings.successMessage || 'Thank you. Your message has been received.';
        form.reset();
        for (const field of form.querySelectorAll('[data-fw-track]')) field.value = query.get(field.dataset.fwTrack) || '';
        const redirect = settings.successRedirect || result.successRedirect;
        if (redirect) location.assign(/^\/(?!\/)/.test(redirect) ? `${config.routePrefix || './'}${redirect.slice(1)}` : redirect);
      } catch (error) { if (status) status.textContent = settings.errorMessage || error.message || 'We could not send your message. Please try again.'; }
      finally { if (button) button.disabled = false; }
    });
  }
  const integration = config.integrations || {};
  const endpoint = integration.endpointBase?.replace(/\/$/, '');
  const parameters = new URLSearchParams(Object.entries(config.context || {}).filter(([, value]) => value !== null && value !== ''));
  let visitorToken = '', consentToken = '';
  const request = async (path, body) => {
    if (!endpoint) throw Error('Configure a backend provider endpoint first.');
    const headers = body === undefined ? {} : { 'Content-Type': 'application/json' };
    if (config.context?.previewToken) { if (visitorToken) headers['X-FormWeb-Visitor'] = visitorToken; if (consentToken) headers['X-FormWeb-Consent'] = consentToken; }
    const response = await fetch(`${endpoint}/api/runtime${path}?${parameters}`, { method: body === undefined ? 'GET' : 'POST', credentials: config.context?.previewToken ? 'omit' : 'include', headers, body: body === undefined ? undefined : JSON.stringify(body) });
    const result = await response.json();
    if (!response.ok) throw Error(typeof result.detail === 'string' ? result.detail : 'Backend provider unavailable.');
    if (config.context?.previewToken) { if (result.visitorToken) visitorToken = result.visitorToken; if (result.consentToken) consentToken = result.consentToken; if (path === '/member/logout') visitorToken = ''; if (path === '/consent' && body?.analytics === false) consentToken = ''; }
    return result;
  };
  const cartKey = `formweb-cart:${config.context?.site}`;
  const getCart = () => { try { return JSON.parse(readSession(cartKey) || '[]'); } catch { return []; } };
  const setCart = lines => { writeSession(cartKey, JSON.stringify(lines)); dispatchEvent(new Event('formweb-cart')); };
  const assignment = {};
  const track = async (name, extra = {}) => { if (readSession(`formweb-consent:${config.context?.site}`) !== 'true') return; try { await request('/event', { name, path: location.pathname, ...extra }); } catch {} };
  const assignExperiments = async () => {
    if (readSession(`formweb-consent:${config.context?.site}`) !== 'true') return;
    await Promise.all(Object.keys(integration.experiments || {}).map(async name => {
      try { const result = await request(`/experiment/${encodeURIComponent(name)}`); assignment[name] = result.variant; document.documentElement.setAttribute(`data-fw-experiment-${name}`, result.variant); writeSession(name, result.variant); } catch {}
    }));
  };
  for (const widget of document.querySelectorAll('[data-fw-widget]')) {
    const specification = integration.widgets?.[widget.dataset.fwOwner] || {};
    const status = widget.querySelector('.fw-widget-status');
    const perform = async work => { try { await work(); } catch (error) { status.textContent = error.message; } };
    if (widget.dataset.fwWidget === 'fetch') perform(async () => { const result = await request(`/data/${encodeURIComponent(specification.source)}`); const data = result.data ?? result; const value = specification.field ? Object.hasOwn(data, specification.field) ? data[specification.field] : specification.field.split('.').reduce((value, key) => value?.[key], data) : data; const output = widget.querySelector('[data-fw-output]'); output.textContent = typeof value === 'string' ? value : JSON.stringify(value) ?? ''; status.textContent = ''; });
    if (widget.dataset.fwWidget === 'product') perform(async () => {
      const catalog = await request('/commerce/catalog');
      const products = catalog.products || catalog.data?.products || [];
      const product = products.find(product => product.id === specification.product) || products[0];
      if (!product) throw Error('No published product is available.');
      widget.querySelector('[data-fw-product-title]').textContent = product.title;
      const select = widget.querySelector('[data-fw-variant]');
      const available = variant => variant && variant.availableForSale !== false && !(variant.inventoryKnown && variant.quantityAvailable <= 0);
      for (const variant of product.variants || []) { const option = document.createElement('option'); option.value = variant.id; option.textContent = `${variant.title}${available(variant) ? '' : ' (sold out)'}`; option.disabled = !available(variant); select.append(option); }
      const first = product.variants?.find(available); if (first) select.value = first.id;
      const price = () => { const variant = product.variants?.find(variant => variant.id === select.value); const value = variant?.price; widget.querySelector('[data-fw-price]').textContent = typeof value === 'object' ? `${value.amount} ${value.currencyCode || ''}` : String(value ?? ''); widget.querySelector('[data-fw-add]').disabled = !available(variant); status.textContent = available(variant) ? 'Available. Availability is checked again at checkout.' : 'Sold out.'; };
      select.addEventListener('change', price); price();
      widget.querySelector('[data-fw-add]').addEventListener('click', () => { const variant = product.variants?.find(variant => variant.id === select.value); if (!available(variant)) return; const quantity = Math.max(1, Math.min(99, Number(widget.querySelector('[data-fw-quantity]').value) || 1)); const lines = getCart(); const existing = lines.find(line => line.variantId === select.value); const total = (existing?.quantity || 0) + quantity; if (variant.inventoryKnown && total > variant.quantityAvailable) { status.textContent = 'Requested quantity exceeds available inventory.'; return; } if (existing) existing.quantity = total; else lines.push({ variantId: select.value, quantity }); setCart(lines); status.textContent = 'Added to cart.'; });
    });
    if (widget.dataset.fwWidget === 'cart') { const refresh = () => { widget.querySelector('[data-fw-cart-count]').textContent = `${getCart().reduce((total, line) => total + line.quantity, 0)} items`; }; refresh(); addEventListener('formweb-cart', refresh); widget.querySelector('[data-fw-clear]').addEventListener('click', () => setCart([])); }
    if (widget.dataset.fwWidget === 'checkout') widget.querySelector('[data-fw-checkout]').addEventListener('click', () => perform(async () => { const result = await request('/commerce/cart', { lines: getCart() }); if (!result.checkoutUrl || !/^https:\/\//.test(result.checkoutUrl)) throw Error('Configured provider did not return a hosted checkout.'); location.assign(result.checkoutUrl); }));
    if (widget.dataset.fwWidget === 'member-login') {
      const form = widget.querySelector('[data-fw-member-form]');
      const credentials = () => Object.fromEntries(new FormData(form));
      form.addEventListener('submit', event => { event.preventDefault(); perform(async () => { const result = await request('/member/login', credentials()); status.textContent = 'Signed in.'; form.elements.password.value = ''; widget.dispatchEvent(new CustomEvent('formweb-member', { bubbles: true, detail: result })); }); });
      widget.querySelector('[data-fw-register]').addEventListener('click', () => perform(async () => { if (!form.reportValidity()) return; await request('/member/register', credentials()); status.textContent = 'Account created. You can sign in.'; form.elements.password.value = ''; }));
      widget.querySelector('[data-fw-logout]').addEventListener('click', () => perform(async () => { await request('/member/logout', {}); status.textContent = 'Signed out.'; widget.dispatchEvent(new CustomEvent('formweb-member', { bubbles: true })); }));
    }
    if (widget.dataset.fwWidget === 'member-gate') { const refresh = () => perform(async () => { const result = await request('/member/session'); widget.querySelector('[data-fw-output]').textContent = result.authenticated ? 'Authenticated member session.' : 'Sign in to access protected routes.'; }); refresh(); document.addEventListener('formweb-member', refresh); }
    if (widget.dataset.fwWidget === 'analytics-consent') for (const button of widget.querySelectorAll('[data-fw-consent]')) button.addEventListener('click', () => perform(async () => { const analytics = button.dataset.fwConsent === 'true'; await request('/consent', { analytics }); writeSession(`formweb-consent:${config.context?.site}`, String(analytics)); status.textContent = analytics ? 'Analytics allowed.' : 'Analytics declined.'; if (analytics) { await assignExperiments(); track('page-view'); } }));
  }
  assignExperiments();
  document.addEventListener('click', event => { if (event.target.closest('a,button')) track('click'); });
  track('page-view');
})();
'use strict';
(() => {
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const params = new URLSearchParams(location.search);
  const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: 'base' });
  const writeUrl = values => {
    const next = new URLSearchParams(location.search);
    for (const [key, value] of values) { if (value === '' || value === null) next.delete(key); else next.set(key, value); }
    const query = next.toString();
    try { history.replaceState(null, '', `${location.pathname}${query ? '?' + query : ''}${location.hash}`); } catch {}
  };

  for (const form of document.querySelectorAll('form[data-fw-facets]')) {
    const key = form.dataset.fwFacets;
    const list = Array.from(document.querySelectorAll('[data-fw-list][data-fw-managed]')).find(node => node.dataset.fwList === key);
    if (!list) continue;
    const entries = Array.from(list.children).filter(node => node.hasAttribute('data-fw-item')).map((row, index) => {
      let facets = {}, sorts = {};
      try { facets = JSON.parse(row.dataset.fwFacetData || '{}'); sorts = JSON.parse(row.dataset.fwSortData || '{}'); } catch {}
      return { row, index, facets, sorts };
    });
    const navigation = list.querySelector('[data-fw-pagination]');
    const output = navigation?.querySelector('[data-fw-page-output]');
    const size = Math.max(0, Number(list.dataset.fwPageSize) || 0);
    const status = form.querySelector('[data-fw-status]');
    const sortSelect = form.querySelector('[data-fw-sort]');
    const facetControls = Array.from(form.querySelectorAll('[data-fw-facet]'));
    const ranges = Array.from(form.querySelectorAll('[data-fw-range]'));
    const facetKeys = [...new Set(facetControls.map(control => control.dataset.fwFacet))];
    const rangeKeys = [...new Set(ranges.map(input => input.dataset.fwRange))];
    let page = 0;

    const read = () => {
      const state = {};
      for (const control of facetControls) {
        const name = control.dataset.fwFacet;
        if (control.type === 'checkbox') { if (control.checked) (state[name] ||= { kind: 'checkbox', values: [] }).values.push(control.value); }
        else if (control.value.trim()) state[name] = { kind: control.dataset.fwKind, value: control.value.trim() };
      }
      for (const input of ranges) if (input.value !== '') (state[input.dataset.fwRange] ||= { kind: 'range' })[input.dataset.fwBound] = input.value;
      return state;
    };
    const compareRange = (a, b) => (a !== '' && b !== '' && !Number.isNaN(Number(a)) && !Number.isNaN(Number(b))) ? Number(a) - Number(b) : (a < b ? -1 : a > b ? 1 : 0);
    const matches = (entry, state) => Object.entries(state).every(([name, rule]) => {
      const values = entry.facets[name] || [];
      if (rule.kind === 'checkbox') return rule.values.some(value => values.includes(value));
      if (rule.kind === 'select') return values.includes(rule.value);
      if (rule.kind === 'search') return rule.value.toLowerCase().split(/\s+/).every(term => (values[0] || '').includes(term));
      const value = values[0];
      if (value === undefined) return false;
      if (rule.min !== undefined && compareRange(value, rule.min) < 0) return false;
      if (rule.max !== undefined && compareRange(value, rule.max) > 0) return false;
      return true;
    });

    const apply = (persist = true) => {
      const state = read();
      const sort = sortSelect?.value || '';
      const direction = sortSelect?.selectedOptions[0]?.dataset.fwDirection === 'desc' ? -1 : 1;
      const ordered = entries.slice().sort((a, b) => {
        if (!sort) return a.index - b.index;
        const x = a.sorts[sort], y = b.sorts[sort];
        if ((x ?? null) === null && (y ?? null) === null) return a.index - b.index;
        if ((x ?? null) === null) return 1;
        if ((y ?? null) === null) return -1;
        const result = typeof x === 'number' && typeof y === 'number' ? x - y : collator.compare(String(x), String(y));
        return result * direction || a.index - b.index;
      });
      const current = Array.from(list.children).filter(node => node.hasAttribute('data-fw-item'));
      if (ordered.some((entry, index) => entry.row !== current[index])) for (const entry of ordered) list.insertBefore(entry.row, navigation);
      const hits = ordered.filter(entry => matches(entry, state));
      const pages = size ? Math.max(1, Math.ceil(hits.length / size)) : 1;
      page = Math.min(page, pages - 1);
      const shown = new Set(size ? hits.slice(page * size, page * size + size) : hits);
      for (const entry of entries) entry.row.hidden = !shown.has(entry);
      if (status) status.textContent = hits.length ? `${hits.length} of ${entries.length} results` : 'No results match your filters.';
      if (navigation) {
        navigation.hidden = size === 0 || hits.length <= size;
        if (output) output.textContent = `${page + 1} / ${pages}`;
        navigation.querySelector('[data-fw-prev]')?.toggleAttribute('disabled', page === 0);
        navigation.querySelector('[data-fw-next]')?.toggleAttribute('disabled', page + 1 >= pages);
      }
      if (!persist) return;
      const values = [];
      for (const name of facetKeys) {
        const rule = state[name];
        values.push([name, !rule ? '' : rule.kind === 'checkbox' ? rule.values.join(',') : rule.value]);
      }
      for (const name of rangeKeys) { values.push([`${name}-min`, state[name]?.min ?? '']); values.push([`${name}-max`, state[name]?.max ?? '']); }
      values.push(['sort', sort], ['page', page > 0 ? String(page + 1) : '']);
      writeUrl(values);
    };

    for (const control of facetControls) {
      const stored = params.get(control.dataset.fwFacet);
      if (stored === null) continue;
      if (control.type === 'checkbox') control.checked = stored.split(',').includes(control.value);
      else control.value = stored;
    }
    for (const input of ranges) { const stored = params.get(`${input.dataset.fwRange}-${input.dataset.fwBound}`); if (stored !== null) input.value = stored; }
    if (sortSelect && params.get('sort') !== null) sortSelect.value = params.get('sort');
    if (sortSelect && sortSelect.selectedIndex === -1) sortSelect.value = '';
    page = Math.max(0, (Number(params.get('page')) || 1) - 1);

    form.addEventListener('submit', event => event.preventDefault());
    form.addEventListener('input', () => { page = 0; apply(); });
    form.addEventListener('change', () => { page = 0; apply(); });
    form.querySelector('[data-fw-clear]')?.addEventListener('click', () => {
      for (const control of facetControls) { if (control.type === 'checkbox') control.checked = false; else control.value = ''; }
      for (const input of ranges) input.value = '';
      if (sortSelect) sortSelect.value = '';
      page = 0;
      apply();
    });
    navigation?.querySelector('[data-fw-prev]')?.addEventListener('click', () => { page = Math.max(0, page - 1); apply(); });
    navigation?.querySelector('[data-fw-next]')?.addEventListener('click', () => { page += 1; apply(); });
    apply(false);
  }

  for (const slider of document.querySelectorAll('[data-fw-slider]')) {
    const viewport = slider.querySelector('[data-fw-viewport]');
    const slides = Array.from(slider.querySelectorAll('[data-fw-slide]'));
    const dots = Array.from(slider.querySelectorAll('[data-fw-dot]'));
    const previous = slider.querySelector('[data-fw-prev]');
    const next = slider.querySelector('[data-fw-next]');
    const pause = slider.querySelector('[data-fw-pause]');
    if (!viewport || !slides.length) continue;
    const loop = slider.dataset.fwLoop === 'true';
    const interval = Math.max(2000, Number(slider.dataset.fwInterval) || 5000);
    const perView = () => Math.max(1, Number(getComputedStyle(slider).getPropertyValue('--fw-per-view')) || 1);
    const stops = () => Math.max(1, slides.length - Math.min(perView(), slides.length) + 1);
    const offset = index => slides[index].offsetLeft - slides[0].offsetLeft;
    let index = 0;
    let userPaused = false;
    let hovering = false;
    let timer = 0;

    const update = () => {
      const left = viewport.scrollLeft;
      let best = 0, distance = Infinity;
      for (let i = 0; i < slides.length; i += 1) { const gap = Math.abs(offset(i) - left); if (gap < distance) { distance = gap; best = i; } }
      index = Math.min(best, stops() - 1);
      const end = viewport.scrollWidth - viewport.clientWidth - 2;
      if (left >= end) index = stops() - 1;
      dots.forEach((dot, i) => { if (i === index) dot.setAttribute('aria-current', 'true'); else dot.removeAttribute('aria-current'); });
      if (!loop) { previous?.toggleAttribute('disabled', left <= 1); next?.toggleAttribute('disabled', left >= end); }
    };
    const go = target => {
      const count = stops();
      const wrapped = loop ? (target + count) % count : Math.max(0, Math.min(count - 1, target));
      viewport.scrollTo({ left: offset(wrapped), behavior: reduced.matches ? 'auto' : 'smooth' });
    };
    let frame = 0;
    viewport.addEventListener('scroll', () => { cancelAnimationFrame(frame); frame = requestAnimationFrame(update); }, { passive: true });
    previous?.addEventListener('click', () => go(index - 1));
    next?.addEventListener('click', () => go(index + 1));
    dots.forEach((dot, i) => dot.addEventListener('click', () => go(i)));
    viewport.addEventListener('keydown', event => {
      if (event.key === 'ArrowLeft') { event.preventDefault(); go(index - 1); }
      else if (event.key === 'ArrowRight') { event.preventDefault(); go(index + 1); }
      else if (event.key === 'Home') { event.preventDefault(); go(0); }
      else if (event.key === 'End') { event.preventDefault(); go(stops() - 1); }
    });

    const stop = () => { clearInterval(timer); timer = 0; };
    const start = () => {
      stop();
      if (slider.dataset.fwAutoplay !== 'true' || reduced.matches || userPaused || hovering || document.hidden) return;
      timer = setInterval(() => go(index + 1 >= stops() ? 0 : index + 1), interval);
    };
    if (slider.dataset.fwAutoplay === 'true') {
      slider.addEventListener('pointerenter', () => { hovering = true; start(); });
      slider.addEventListener('pointerleave', () => { hovering = false; start(); });
      slider.addEventListener('focusin', () => { hovering = true; start(); });
      slider.addEventListener('focusout', () => { hovering = false; start(); });
      document.addEventListener('visibilitychange', start);
      reduced.addEventListener?.('change', () => { if (pause) pause.hidden = reduced.matches; start(); });
      pause?.addEventListener('click', () => {
        userPaused = !userPaused;
        pause.setAttribute('aria-pressed', String(userPaused));
        pause.textContent = userPaused ? 'Play' : 'Pause';
        start();
      });
      if (pause) pause.hidden = reduced.matches;
    }
    addEventListener('resize', update);
    update();
    start();
  }

  let config = {};
  try { config = JSON.parse(document.getElementById('fw-config')?.textContent || '{}'); } catch {}
  const presets = {
    phone: { pattern: '\\+?[0-9][0-9 .\\-]{5,18}[0-9]', type: 'tel', inputMode: 'tel', autocomplete: 'tel', title: 'Enter a valid phone number' },
    postal: { pattern: '[A-Za-z0-9][A-Za-z0-9 \\-]{2,9}', autocomplete: 'postal-code', title: 'Enter a valid postal code' },
    email: { type: 'email', inputMode: 'email', autocomplete: 'email', title: 'Enter a valid email address' }
  };
  const limitFor = (form, name) => Math.min(2 * 1024 * 1024, Number(config.forms?.forms?.[form.dataset.fwNode]?.constraints?.[name]?.maxSize) || 2 * 1024 * 1024);

  for (const form of document.querySelectorAll('form')) {
    const rules = config.forms?.forms?.[form.dataset.fwNode]?.constraints || {};
    for (const [name, rule] of Object.entries(rules)) {
      const preset = presets[rule.preset];
      if (!preset) continue;
      for (const control of form.querySelectorAll('input[name], textarea[name]')) {
        if (control.name !== name) continue;
        if (preset.pattern && !control.pattern) control.pattern = preset.pattern;
        if (preset.type && control.tagName === 'INPUT' && control.type === 'text') control.type = preset.type;
        if (preset.inputMode) control.inputMode = preset.inputMode;
        if (preset.autocomplete && !control.autocomplete) control.autocomplete = preset.autocomplete;
        if (!control.title) control.title = preset.title;
      }
    }

    const steps = Array.from(form.querySelectorAll('[data-fw-step]')).sort((a, b) => Number(a.dataset.fwStep) - Number(b.dataset.fwStep));
    const nav = form.querySelector('[data-fw-step-nav]');
    if (steps.length < 2 || !nav) continue;
    const back = nav.querySelector('[data-fw-step-prev]');
    const forward = nav.querySelector('[data-fw-step-next]');
    const output = nav.querySelector('[data-fw-step-output]');
    const submitters = Array.from(form.querySelectorAll('[type=submit]')).filter(button => !steps.some(step => step.contains(button)));
    const fieldsOf = step => Array.from(step.querySelectorAll('input, select, textarea'));
    let index = 0;
    const show = (target, focus) => {
      index = target;
      steps.forEach((step, i) => { step.hidden = i !== index; });
      back.disabled = index === 0;
      forward.hidden = index === steps.length - 1;
      for (const button of submitters) button.hidden = index !== steps.length - 1;
      const title = steps[index].dataset.fwStepTitle;
      output.textContent = `Step ${index + 1} of ${steps.length}${title ? ': ' + title : ''}`;
      if (focus) fieldsOf(steps[index]).find(control => control.type !== 'hidden')?.focus();
    };
    const valid = i => {
      const bad = fieldsOf(steps[i]).find(control => !control.checkValidity());
      if (!bad) return true;
      show(i, false);
      bad.reportValidity();
      bad.focus();
      return false;
    };
    back.addEventListener('click', () => show(Math.max(0, index - 1), true));
    forward.addEventListener('click', () => { if (valid(index)) show(index + 1, true); });
    form.addEventListener('submit', event => {
      if (index < steps.length - 1) {
        event.preventDefault();
        event.stopImmediatePropagation();
        if (valid(index)) show(index + 1, true);
        return;
      }
      for (let i = 0; i < steps.length; i += 1) {
        if (!valid(i)) { event.preventDefault(); event.stopImmediatePropagation(); return; }
      }
      show(steps.length - 1, false);
    }, true);
    form.addEventListener('reset', () => show(0, false));
    form.setAttribute('data-fw-ready', '');
    show(0, false);
  }

  window.fwEncodeForm = async (form, fields) => {
    const entries = Array.from(fields.entries());
    if (!entries.some(([, value]) => typeof value !== 'string')) return null;
    const real = entries.filter(([, value]) => typeof value !== 'string' && value.size > 0);
    if (!real.length) {
      const plain = new URLSearchParams();
      for (const [name, value] of entries) if (typeof value === 'string') plain.append(name, value);
      return { body: plain, type: 'application/x-www-form-urlencoded;charset=UTF-8' };
    }
    const read = file => new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = () => reject(Error('The file could not be read.'));
      reader.onload = () => resolve(String(reader.result).split(',')[1] || '');
      reader.readAsDataURL(file);
    });
    const body = {};
    let total = 0;
    for (const [name, value] of entries) {
      let item = value;
      if (typeof value !== 'string') {
        if (value.size === 0) continue;
        total += value.size;
        if (value.size > limitFor(form, name) || total > 3 * 1024 * 1024) throw Error('The attached files are too large.');
        item = { name: value.name, type: value.type, size: value.size, data: await read(value) };
      }
      body[name] = name in body ? [].concat(body[name], item) : item;
    }
    return { body: JSON.stringify(body), type: 'application/json' };
  };
})();

(() => {
  document.addEventListener('click', event => {
    const button = event.target.closest && event.target.closest('[data-fw-embed-load]');
    const gate = button && button.closest('[data-fw-embed-gate]');
    if (!gate) return;
    const src = gate.dataset.fwEmbedSrc || '';
    if (gate.dataset.fwEmbedKind === 'x') {
      const quote = document.createElement('blockquote');
      quote.className = 'twitter-tweet';
      const link = document.createElement('a');
      link.href = src;
      link.textContent = src;
      quote.append(link);
      gate.replaceWith(quote);
      if (!document.getElementById('twitter-wjs')) { const script = document.createElement('script'); script.id = 'twitter-wjs'; script.async = true; script.src = 'https://platform.x.com/widgets.js'; document.head.append(script); }
      else if (window.twttr && window.twttr.widgets) window.twttr.widgets.load(quote.parentNode);
      return;
    }
    const frame = document.createElement('iframe');
    frame.src = src;
    frame.title = gate.dataset.fwEmbedTitle || 'Embedded media';
    frame.setAttribute('data-fw-embed-frame', '');
    frame.setAttribute('referrerpolicy', 'strict-origin-when-cross-origin');
    frame.setAttribute('allow', 'autoplay; encrypted-media; fullscreen; picture-in-picture; clipboard-write');
    frame.allowFullscreen = true;
    frame.setAttribute('style', gate.dataset.fwEmbedStyle || 'width:100%;border:0;display:block');
    gate.replaceWith(frame);
    frame.focus({ preventScroll: true });
  });
})();
// Scroll and pointer effects (FW-185). An element opts in with data-fw-effect: parallax, scroll, mouse, marquee or
// cursor, and data-fw-effect-speed sets the strength. Motion uses the CSS translate, scale and opacity properties, so
// an element's own transform is left alone. With reduced motion, nothing moves: marquees stay still and cursors stay
// native. One scroll listener and one pointer listener drive every element through requestAnimationFrame.
(() => {
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const all = [...document.querySelectorAll('[data-fw-effect]')];
  if (!all.length) return;
  const speed = (el, fallback) => { const n = parseFloat(el.getAttribute('data-fw-effect-speed') || ''); return Number.isFinite(n) ? n : fallback; };
  const kind = el => el.getAttribute('data-fw-effect');
  const scrolled = all.filter(el => kind(el) === 'parallax' || kind(el) === 'scroll');
  const moved = all.filter(el => kind(el) === 'mouse');
  if (!reduced) {
    let queued = false;
    const frame = () => {
      queued = false;
      const view = innerHeight;
      for (const el of scrolled) {
        const box = el.getBoundingClientRect();
        if (box.bottom < -view || box.top > view * 2) continue;
        if (kind(el) === 'parallax') {
          el.style.translate = `0 ${Math.round(((box.top + box.height / 2) - view / 2) * -speed(el, 0.3))}px`;
        } else {
          const progress = Math.min(1, Math.max(0, (view - box.top) / (view * 0.6)));
          el.style.opacity = String(0.15 + 0.85 * progress);
          el.style.translate = `0 ${Math.round((1 - progress) * 80 * speed(el, 1))}px`;
          el.style.scale = String(0.92 + 0.08 * progress);
        }
      }
    };
    const queue = () => { if (!queued) { queued = true; requestAnimationFrame(frame); } };
    // The first frame runs now, not on the next animation frame, so the starting positions are set before first paint
    // wherever the deferred script runs ahead of it.
    if (scrolled.length) { addEventListener('scroll', queue, { passive: true }); addEventListener('resize', queue); frame(); }
    if (moved.length) {
      let x = 0, y = 0, pending = false;
      addEventListener('pointermove', event => {
        x = event.clientX / innerWidth - 0.5; y = event.clientY / innerHeight - 0.5;
        if (pending) return;
        pending = true;
        requestAnimationFrame(() => { pending = false; for (const el of moved) { const s = 40 * speed(el, 1); el.style.translate = `${Math.round(x * s)}px ${Math.round(y * s)}px`; } });
      }, { passive: true });
    }
  }
  for (const el of all.filter(el => kind(el) === 'marquee')) {
    if (reduced || el.querySelector(':scope > .fw-marquee-track')) continue;
    const track = document.createElement('div');
    track.className = 'fw-marquee-track';
    const gap = getComputedStyle(el).columnGap;
    track.style.cssText = `display:flex;width:max-content;gap:${gap === 'normal' ? '48px' : gap};padding-right:${gap === 'normal' ? '48px' : gap}`;
    while (el.firstChild) track.append(el.firstChild);
    const copy = track.cloneNode(true);
    copy.setAttribute('aria-hidden', 'true');
    for (const node of copy.querySelectorAll('[id]')) node.removeAttribute('id');
    const rail = document.createElement('div');
    rail.className = 'fw-marquee-rail';
    rail.style.cssText = 'display:flex;width:max-content';
    rail.append(track, copy);
    el.style.overflow = 'hidden';
    el.style.display = 'block';
    el.append(rail);
    const width = track.getBoundingClientRect().width || 600;
    const animation = rail.animate([{ transform: 'translateX(0)' }, { transform: 'translateX(-50%)' }], { duration: (width / Math.max(10, 60 * speed(el, 1))) * 1000, iterations: Infinity });
    el.addEventListener('pointerenter', () => animation.pause());
    el.addEventListener('pointerleave', () => animation.play());
  }
  for (const el of all.filter(el => kind(el) === 'cursor')) {
    if (reduced || matchMedia('(pointer: coarse)').matches) continue;
    const dot = document.createElement('div');
    const size = Math.round(28 * speed(el, 1));
    dot.setAttribute('aria-hidden', 'true');
    dot.style.cssText = `position:fixed;left:0;top:0;width:${size}px;height:${size}px;margin:${-size / 2}px 0 0 ${-size / 2}px;border-radius:50%;background:${getComputedStyle(el).color};opacity:0;pointer-events:none;transition:opacity .15s;z-index:2147483000`;
    document.body.append(dot);
    el.style.cursor = 'none';
    el.addEventListener('pointermove', event => { dot.style.translate = `${event.clientX}px ${event.clientY}px`; dot.style.opacity = '1'; });
    el.addEventListener('pointerleave', () => { dot.style.opacity = '0'; });
  }
})();
(() => {
  'use strict';
  let config = {};
  try { config = JSON.parse(document.getElementById('fw-config')?.textContent || '{}'); } catch {}
  const motion = config.motion;
  if (!motion || typeof motion !== 'object') return;
  const html = document.documentElement;
  const reduced = html.classList.contains('fw-r') || matchMedia('(prefers-reduced-motion: reduce)').matches;
  const SAFE = /^(opacity|transform|translate|scale|rotate|filter|backdrop-filter|clip-path|color|background-color|border-color|box-shadow|--.+)$/;
  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
  const kebab = k => (k.startsWith('--') ? k : k.replace(/[A-Z]/g, c => '-' + c.toLowerCase()));
  const camel = k => (k.startsWith('--') ? k : k.replace(/-([a-z])/g, (_, c) => c.toUpperCase()));
  const all = (id, root = document) => {
    const sel = `[data-fw-node="${CSS.escape(String(id))}"]`;
    const found = [...root.querySelectorAll(sel)];
    return root !== document && root.matches(sel) ? [root, ...found] : found;
  };
  const ready = fn => { if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', fn, { once: true }); else fn(); };
  const entries = map => Object.entries(map && typeof map === 'object' ? map : {});

  const bezier = (x1, y1, x2, y2) => {
    const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
    const cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
    const sx = t => ((ax * t + bx) * t + cx) * t;
    const sy = t => ((ay * t + by) * t + cy) * t;
    const dx = t => (3 * ax * t + 2 * bx) * t + cx;
    return x => {
      if (x <= 0) return 0;
      if (x >= 1) return 1;
      let t = x;
      for (let i = 0; i < 8; i++) { const e = sx(t) - x; if (Math.abs(e) < 1e-6) return sy(t); const d = dx(t); if (Math.abs(d) < 1e-6) break; t -= e / d; }
      let lo = 0, hi = 1;
      t = x;
      for (let i = 0; i < 24; i++) { const e = sx(t); if (Math.abs(e - x) < 1e-6) break; if (e < x) lo = t; else hi = t; t = (lo + hi) / 2; }
      return sy(t);
    };
  };
  const spring = (stiffness, damping) => {
    const w0 = Math.sqrt(stiffness), z = damping / (2 * w0);
    let raw;
    let settle;
    if (z < 1) {
      const wd = w0 * Math.sqrt(1 - z * z);
      settle = Math.min(6 / (z * w0), 20);
      raw = s => 1 - Math.exp(-z * w0 * s) * (Math.cos(wd * s) + (z * w0 / wd) * Math.sin(wd * s));
    } else if (z === 1) {
      settle = Math.min(8 / w0, 20);
      raw = s => 1 - Math.exp(-w0 * s) * (1 + w0 * s);
    } else {
      const q = Math.sqrt(z * z - 1), r1 = -w0 * (z - q), r2 = -w0 * (z + q);
      settle = Math.min(6 / -r1, 20);
      raw = s => 1 - (r2 * Math.exp(r1 * s) - r1 * Math.exp(r2 * s)) / (r2 - r1);
    }
    const end = raw(settle);
    return t => (t <= 0 ? 0 : t >= 1 ? 1 : raw(t * settle) + (1 - end) * t);
  };
  const KEYWORDS = { linear: [0, 0, 1, 1], ease: [0.25, 0.1, 0.25, 1], 'ease-in': [0.42, 0, 1, 1], 'ease-out': [0, 0, 0.58, 1], 'ease-in-out': [0.42, 0, 0.58, 1] };
  const easings = new Map();
  const easing = name => {
    const key = String(name || 'linear').trim();
    let fn = easings.get(key);
    if (fn) return fn;
    const args = (/\(([^)]*)\)/.exec(key)?.[1] || '').split(',').map(Number);
    if (key === 'linear') fn = t => t;
    else if (KEYWORDS[key]) fn = bezier(...KEYWORDS[key]);
    else if (key.startsWith('cubic-bezier') && args.length === 4 && args.every(Number.isFinite)) fn = bezier(...args);
    else if (key.startsWith('spring') && args.length === 2 && args.every(Number.isFinite) && args[0] > 0 && args[1] > 0) fn = spring(args[0], args[1]);
    else fn = t => t;
    easings.set(key, fn);
    return fn;
  };
  const LINEAR_OK = typeof CSS !== 'undefined' && CSS.supports?.('animation-timing-function', 'linear(0, 1)');
  const cssEasing = name => {
    const key = String(name || 'ease').trim();
    if (KEYWORDS[key] || key.startsWith('cubic-bezier')) return key;
    if (key === 'linear') return 'linear';
    if (key.startsWith('spring') && LINEAR_OK) {
      const fn = easing(key);
      const points = [];
      for (let i = 0; i <= 40; i++) points.push((Math.round(fn(i / 40) * 1000) / 1000).toString());
      return `linear(${points.join(',')})`;
    }
    return 'ease-out';
  };

  const subs = new Set();
  let raf = 0, lastTime = 0;
  const tick = now => {
    raf = 0;
    if (document.hidden || !subs.size) { lastTime = 0; return; }
    const dt = lastTime ? Math.min(now - lastTime, 100) : 16;
    lastTime = now;
    for (const fn of subs) fn(now, dt);
    if (subs.size) raf = requestAnimationFrame(tick); else lastTime = 0;
  };
  const kick = () => { if (!raf && subs.size && !document.hidden) raf = requestAnimationFrame(tick); };
  const onFrame = fn => { subs.add(fn); kick(); return () => { subs.delete(fn); }; };
  document.addEventListener('visibilitychange', () => { lastTime = 0; kick(); });

  const hex = s => s.replace(/#([0-9a-f]{8}|[0-9a-f]{6}|[0-9a-f]{4}|[0-9a-f]{3})\b/gi, (_, h) => {
    if (h.length < 6) h = [...h].map(c => c + c).join('');
    const n = i => parseInt(h.slice(i, i + 2), 16);
    return h.length === 8 ? `rgba(${n(0)}, ${n(2)}, ${n(4)}, ${Math.round(n(6) / 255 * 1000) / 1000})` : `rgb(${n(0)}, ${n(2)}, ${n(4)})`;
  });
  const parsed = new Map();
  const parse = str => {
    let p = parsed.get(str);
    if (p) return p;
    p = { parts: [], nums: [], units: [] };
    const re = /(-?(?:\d+\.?\d*|\.\d+)(?:e[-+]?\d+)?)([a-z%]*)/gi;
    const s = hex(str);
    let last = 0, m;
    while ((m = re.exec(s))) { p.parts.push(s.slice(last, m.index)); p.nums.push(parseFloat(m[1])); p.units.push(m[2]); last = m.index + m[0].length; }
    p.parts.push(s.slice(last));
    parsed.set(str, p);
    return p;
  };
  const round = v => Math.round(v * 1000) / 1000;
  const interpolate = (a, b, t) => {
    a = String(a); b = String(b);
    if (a === b) return a;
    const pa = parse(a), pb = parse(b);
    const n = pa.nums.length;
    let ok = n === pb.nums.length && n > 0 && pa.parts.every((s, i) => s === pb.parts[i]);
    const units = [];
    for (let i = 0; ok && i < n; i++) {
      const ua = pa.units[i], ub = pb.units[i];
      if (ua === ub) units.push(ua);
      else if (pa.nums[i] === 0 && ua === '') units.push(ub);
      else if (pb.nums[i] === 0 && ub === '') units.push(ua);
      else ok = false;
    }
    if (!ok) return t < 0.5 ? a : b;
    let out = pa.parts[0];
    for (let i = 0; i < n; i++) out += round(pa.nums[i] + (pb.nums[i] - pa.nums[i]) * t) + units[i] + pa.parts[i + 1];
    return out;
  };
  const applyStyles = (el, styles) => {
    for (const [k, v] of entries(styles)) { const key = kebab(k); if (SAFE.test(key)) el.style.setProperty(key, String(v)); }
  };
  const frameStyles = styles => {
    const out = {};
    for (const [k, v] of entries(styles)) if (SAFE.test(kebab(k))) out[camel(k)] = String(v);
    return out;
  };
  const styleKeys = styles => Object.keys(styles || {}).map(kebab).filter(k => SAFE.test(k));

  const pools = new Map();
  const watch = (el, threshold, margin, fn) => {
    const key = threshold + '|' + margin;
    let pool = pools.get(key);
    if (!pool) {
      pool = { map: new Map() };
      let io;
      try { io = new IntersectionObserver(list => { for (const e of list) for (const f of [...(pool.map.get(e.target) || [])]) f(e); }, { threshold, rootMargin: margin }); }
      catch { io = new IntersectionObserver(list => { for (const e of list) for (const f of [...(pool.map.get(e.target) || [])]) f(e); }, { threshold, rootMargin: '0px' }); }
      pool.io = io;
      pools.set(key, pool);
    }
    let fns = pool.map.get(el);
    if (!fns) { fns = []; pool.map.set(el, fns); pool.io.observe(el); }
    fns.push(fn);
    return () => {
      const l = pool.map.get(el);
      if (!l) return;
      const i = l.indexOf(fn);
      if (i >= 0) l.splice(i, 1);
      if (!l.length) { pool.map.delete(el); pool.io.unobserve(el); }
    };
  };
  const whenIn = (el, cfg, run, threshold = 0.15) => {
    if (cfg.trigger === 'load') { ready(run); return; }
    const stop = watch(el, clamp(Number(cfg.threshold ?? threshold), 0, 1), cfg.rootMargin || '0px', e => { if (e.isIntersecting) { stop(); run(); } });
  };

  const authoredOf = list => {
    const root = html.classList.contains('fw-m');
    const els = list.map(l => l.el);
    const held = els.map(el => el.style.getPropertyValue('transition'));
    for (const el of els) el.style.setProperty('transition', 'none');
    if (root) html.classList.remove('fw-m');
    const out = list.map(({ el, keys }) => { const cs = getComputedStyle(el); return keys.map(k => cs.getPropertyValue(k).trim()); });
    if (root) { html.classList.add('fw-m'); if (els[0]) getComputedStyle(els[0]).opacity; }
    els.forEach((el, i) => { if (held[i]) el.style.setProperty('transition', held[i]); else el.style.removeProperty('transition'); });
    return out;
  };
  const toFrame = (keys, values) => { const o = {}; keys.forEach((k, i) => { if (values[i]) o[camel(k)] = values[i]; }); return o; };

  const scrollJobs = { id: 0 };
  for (const type of ['wheel', 'touchstart', 'keydown']) addEventListener(type, () => { scrollJobs.id++; }, { passive: true });
  const glide = (target, duration, easingName) => new Promise(resolve => {
    const job = ++scrollJobs.id;
    const from = scrollY;
    if (reduced || !(duration > 0) || Math.abs(target - from) < 1) { scrollTo({ top: target, behavior: 'instant' }); resolve(); return; }
    const ease = easing(easingName);
    let start = -1;
    const stop = onFrame(now => {
      if (job !== scrollJobs.id) { stop(); resolve(); return; }
      if (start < 0) start = now;
      const t = Math.min(1, (now - start) / duration);
      scrollTo({ top: from + (target - from) * ease(t), behavior: 'instant' });
      if (t >= 1) { stop(); resolve(); }
    });
  });

  const sceneStates = new Map();
  const sceneProgress = id => sceneStates.get(id)?.[0]?.s || 0;
  const sceneOf = element => {
    for (let n = element instanceof Element ? element : null; n; n = n.parentElement) {
      const key = n.getAttribute('data-fw-node');
      if (key && sceneStates.has(key)) return key;
    }
    return null;
  };
  const progressSubs = new Map();
  const onProgress = (scene, fn) => {
    if (typeof fn !== 'function') return () => {};
    let set = progressSubs.get(scene);
    if (!set) { set = new Set(); progressSubs.set(scene, set); }
    set.add(fn);
    return () => { set.delete(fn); };
  };
  const scrollToNode = (id, duration, easingName) => {
    const el = all(id)[0];
    if (!el) return Promise.resolve();
    const margin = parseFloat(getComputedStyle(el).scrollMarginTop) || 0;
    return glide(el.getBoundingClientRect().top + scrollY - margin, duration, easingName);
  };
  const scrollToScene = (id, progress, duration, easingName) => {
    const s = sceneStates.get(id)?.[0];
    if (!s) return scrollToNode(id, duration, easingName);
    s.measure();
    const r = s.el.getBoundingClientRect();
    const span = Math.max(0, r.height - s.stageH);
    return glide(r.top + scrollY - s.offset + clamp(Number(progress) || 0, 0, 1) * span, duration, easingName);
  };

  const sampleProps = keyframes => {
    const props = new Map();
    for (const kf of [...(keyframes || [])].sort((a, b) => a.at - b.at)) {
      for (const [k, v] of entries(kf.styles)) {
        const key = kebab(k);
        if (!SAFE.test(key)) continue;
        if (!props.has(key)) props.set(key, []);
        props.get(key).push({ at: Number(kf.at) || 0, v: String(v) });
      }
    }
    return props;
  };
  const sample = (props, p, ease) => {
    const out = [];
    for (const [key, arr] of props) {
      let v;
      const last = arr.length - 1;
      if (p <= arr[0].at) v = arr[0].v;
      else if (p >= arr[last].at) v = arr[last].v;
      else {
        let i = 0;
        while (i < last - 1 && arr[i + 1].at <= p) i++;
        const span = arr[i + 1].at - arr[i].at;
        v = interpolate(arr[i].v, arr[i + 1].v, span > 0 ? ease((p - arr[i].at) / span) : 1);
      }
      out.push(key, v);
    }
    return out;
  };
  const written = new WeakMap();
  const put = (el, key, v) => {
    let m = written.get(el);
    if (!m) { m = new Map(); written.set(el, m); }
    if (m.get(key) !== v) { m.set(key, v); el.style.setProperty(key, v); }
  };

  const initReveals = () => {
    const groups = [];
    for (const [id, cfg] of entries(motion.reveals)) {
      const keys = styleKeys(cfg.from);
      if (!keys.length) continue;
      for (const el of all(id)) groups.push({ el, cfg, keys, shown: false, anims: [], done: [] });
    }
    if (reduced || !groups.length) return;
    const pending = [];
    let queued = false;
    const flush = () => {
      queued = false;
      const batch = pending.splice(0).filter(g => !g.shown);
      if (!batch.length) return;
      const jobs = [];
      for (const g of batch) { g.shown = true; for (const el of g.cfg.children ? [...g.el.children] : [g.el]) jobs.push({ g, el, keys: g.keys }); }
      const authored = authoredOf(jobs);
      const idx = new Map();
      jobs.forEach((j, i) => {
        const n = idx.get(j.g) || 0;
        idx.set(j.g, n + 1);
        const c = j.g.cfg;
        const to = toFrame(j.keys, authored[i]);
        const anim = j.el.animate([frameStyles(c.from), to], { duration: Number(c.duration ?? 600), delay: Number(c.delay || 0) + n * Number(c.stagger || 0), easing: cssEasing(c.easing || 'ease-out'), fill: 'both' });
        j.g.anims.push(anim);
        j.g.done.push(j);
        anim.onfinish = () => {
          j.el.dataset.fwIn = '';
          j.keys.forEach((k, ki) => { if (authored[i][ki]) j.el.style.setProperty(k, authored[i][ki]); });
          anim.cancel();
        };
      });
    };
    const arm = g => { pending.push(g); if (!queued) { queued = true; queueMicrotask(flush); } };
    const reset = g => {
      for (const a of g.anims) a.cancel();
      for (const j of g.done) { delete j.el.dataset.fwIn; for (const k of j.keys) j.el.style.removeProperty(k); }
      g.anims = []; g.done = []; g.shown = false;
    };
    for (const g of groups) {
      const c = g.cfg;
      if (c.trigger === 'load') { ready(() => arm(g)); continue; }
      const once = c.once !== false;
      const stop = watch(g.el, clamp(Number(c.threshold ?? 0.15), 0, 1), c.rootMargin || '0px', e => {
        if (e.isIntersecting) { if (!g.shown) arm(g); if (once) stop(); }
        else if (!once && g.shown) reset(g);
      });
    }
  };

  const initScenes = () => {
    const list = [];
    for (const [id, cfg] of entries(motion.scenes)) {
      const states = [];
      for (const el of all(id)) {
        const stage = cfg.stage ? all(cfg.stage, el).find(n => n !== el) || null : null;
        const s = {
          id, cfg, el, stage, offset: 0, stageH: 0, s: 0, prev: 0, applied: -1, init: false,
          tracks: (cfg.tracks || []).map(t => ({ items: all(t.node, el), props: sampleProps(t.keyframes), ease: easing(t.easing || 'linear') })),
          dist: (cfg.distribute || []).map(d => ({ parents: all(d.parent, el), props: sampleProps(d.keyframes), stagger: Number(d.stagger || 0), ease: easing(d.easing || 'linear') })),
          measure() {
            this.stageH = stage ? stage.getBoundingClientRect().height : innerHeight;
            this.offset = stage ? parseFloat(getComputedStyle(stage).top) || 0 : 0;
          }
        };
        s.measure();
        states.push(s);
        list.push(s);
      }
      if (states.length) sceneStates.set(id, states);
    }
    if (!list.length) return;
    if (reduced) {
      for (const s of list) if (s.cfg.progressVar) s.el.style.setProperty('--fw-progress', String(s.cfg.reducedAt ?? 1));
      return;
    }
    let dirty = true, stopFrame = null;
    const frame = (now, dt) => {
      dirty = false;
      let busy = false;
      const live = [];
      for (const s of list) {
        const r = s.el.getBoundingClientRect();
        if (r.bottom >= -innerHeight && r.top <= innerHeight * 2) live.push(s, r.top, r.height);
      }
      for (let i = 0; i < live.length; i += 3) {
        const s = live[i], span = live[i + 2] - s.stageH;
        const raw = span > 0 ? clamp((s.offset - live[i + 1]) / span, 0, 1) : 0;
        const tau = Number(s.cfg.smoothing || 0);
        if (!s.init) { s.init = true; s.s = s.prev = raw; }
        else if (tau > 0) s.s += (raw - s.s) * (1 - Math.exp(-dt / tau));
        else s.s = raw;
        if (Math.abs(raw - s.s) < 5e-4) s.s = raw; else busy = true;
        if (s.s !== s.applied) {
          s.applied = s.s;
          for (const t of s.tracks) { const vals = sample(t.props, s.s, t.ease); for (const el of t.items) for (let k = 0; k < vals.length; k += 2) put(el, vals[k], vals[k + 1]); }
          for (const d of s.dist) {
            for (const parent of d.parents) {
              const kids = parent.children, n = kids.length, den = Math.max(1 - (n - 1) * d.stagger, 0.01);
              for (let c = 0; c < n; c++) { const vals = sample(d.props, clamp((s.s - c * d.stagger) / den, 0, 1), d.ease); for (let k = 0; k < vals.length; k += 2) put(kids[c], vals[k], vals[k + 1]); }
            }
          }
          if (s.cfg.progressVar) put(s.el, '--fw-progress', s.s.toFixed(4));
          if (progressSubs.get(s.id)?.size && sceneStates.get(s.id)?.[0] === s) for (const fn of [...progressSubs.get(s.id)]) fn(s.s);
        }
        for (const m of s.cfg.markers || []) if (s.prev < m.at && s.s >= m.at) document.dispatchEvent(new CustomEvent('formweb-motion-action', { detail: { action: m.action, origin: s.el } }));
        s.prev = s.s;
      }
      if (!busy && !dirty && stopFrame) { stopFrame(); stopFrame = null; }
    };
    const wake = () => { dirty = true; if (!stopFrame) stopFrame = onFrame(frame); };
    addEventListener('scroll', wake, { passive: true });
    addEventListener('resize', wake);
    const ro = new ResizeObserver(() => { for (const s of list) s.measure(); wake(); });
    for (const s of list) { ro.observe(s.el); if (s.stage) ro.observe(s.stage); }
    frame(performance.now(), 16);
    wake();
  };

  const initLoops = () => {
    if (reduced) return;
    const marquees = [];
    for (const [id, cfg] of entries(motion.loops)) {
      for (const el of all(id)) {
        const type = cfg.type;
        const duration = Number(cfg.duration || 0);
        if (type === 'marquee') {
          const track = el.querySelector(':scope > .fw-track');
          if (!track || track.dataset.fwCloned) continue;
          const originals = [...track.children];
          if (!originals.length) continue;
          track.dataset.fwCloned = '';
          for (const child of originals) {
            const copy = child.cloneNode(true);
            copy.setAttribute('aria-hidden', 'true');
            copy.setAttribute('inert', '');
            copy.removeAttribute('id');
            for (const n of copy.querySelectorAll('[id]')) n.removeAttribute('id');
            track.append(copy);
          }
          marquees.push({ el, track, cfg, first: originals[0], clone: track.children[originals.length], anim: null, hover: false, off: false });
        } else if (type === 'spin') {
          el.animate([{ rotate: '0deg' }, { rotate: `${Number(cfg.amount ?? 360)}deg` }], { duration: clamp(duration || 8000, 100, 120000), iterations: Infinity, easing: 'linear' });
        } else if (type === 'float') {
          el.animate([{ translate: '0 0' }, { translate: `0 ${-Number(cfg.amount ?? 12)}px` }], { duration: clamp(duration || 4000, 100, 120000), iterations: Infinity, direction: 'alternate', easing: 'ease-in-out' });
        } else if (type === 'keyframes' && Array.isArray(cfg.keyframes) && cfg.keyframes.length > 1) {
          const frames = cfg.keyframes.map(k => ({ ...frameStyles(k.styles), offset: clamp(Number(k.at ?? k.offset ?? 0), 0, 1) }));
          el.animate(frames, { duration: clamp(duration || 2000, 100, 120000), easing: cssEasing(cfg.easing || 'linear'), iterations: cfg.iterations === 'infinite' || cfg.iterations == null ? Infinity : Number(cfg.iterations) });
        }
      }
    }
    if (!marquees.length) return;
    const retime = list => {
      const reads = list.map(m => {
        const vertical = m.cfg.direction === 'up' || m.cfg.direction === 'down';
        const a = m.first, b = m.clone;
        let dist = vertical ? b.offsetTop - a.offsetTop : b.offsetLeft - a.offsetLeft;
        if (!(dist > 0)) dist = (vertical ? m.track.offsetHeight : m.track.offsetWidth) / 2;
        return { m, vertical, dist };
      });
      for (const { m, vertical, dist } of reads) {
        if (!(dist > 0)) continue;
        const reverse = m.cfg.direction === 'right' || m.cfg.direction === 'down';
        const at = v => (vertical ? `0 ${v}px` : `${v}px 0`);
        const frames = [{ translate: at(reverse ? -dist : 0) }, { translate: at(reverse ? 0 : -dist) }];
        const duration = dist / clamp(Number(m.cfg.speed || 40), 1, 2000) * 1000;
        if (!m.anim) { m.anim = m.track.animate(frames, { duration, iterations: Infinity, easing: 'linear' }); sync(m); continue; }
        const progress = m.anim.effect.getComputedTiming().progress || 0;
        m.anim.effect.setKeyframes(frames);
        m.anim.effect.updateTiming({ duration });
        m.anim.currentTime = progress * duration;
      }
    };
    const sync = m => { if (!m.anim) return; if (m.hover || m.off) m.anim.pause(); else m.anim.play(); };
    for (const m of marquees) {
      if (m.cfg.pauseOnHover) {
        m.el.addEventListener('pointerenter', e => { if (e.pointerType === 'mouse') { m.hover = true; sync(m); } });
        m.el.addEventListener('pointerleave', () => { m.hover = false; sync(m); });
      }
      if (m.cfg.pauseOffscreen) watch(m.el, 0, '0px', e => { m.off = !e.isIntersecting; sync(m); });
    }
    retime(marquees);
    const ro = new ResizeObserver(() => retime(marquees));
    for (const m of marquees) ro.observe(m.track);
    if (document.fonts?.ready) document.fonts.ready.then(() => retime(marquees));
  };

  const NUMBER = /(\d{1,3}(?:([,  ])\d{3})+|\d+)(\.\d+)?/;
  const initCounters = () => {
    for (const [id, cfg] of entries(motion.counters)) {
      for (const el of all(id)) {
        const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
        let node, m;
        while ((node = walker.nextNode())) { m = NUMBER.exec(node.data); if (m) break; }
        if (!m) continue;
        const from = Number(cfg.from || 0), to = Number(cfg.to ?? 0), decimals = clamp(Number(cfg.decimals || 0), 0, 8);
        const sep = m[2] || '';
        const prefix = node.data.slice(0, m.index), suffix = node.data.slice(m.index + m[0].length);
        const format = v => {
          const [int, frac] = Math.abs(v).toFixed(decimals).split('.');
          const body = sep ? int.replace(/\B(?=(\d{3})+(?!\d))/g, sep) : int;
          return (v < 0 ? '-' : '') + body + (frac ? '.' + frac : '');
        };
        let update = v => { const next = prefix + format(v) + suffix; if (node.data !== next) node.data = next; };
        if (!el.style.minWidth) { const range = document.createRange(); range.selectNodeContents(el); const width = Math.ceil(range.getBoundingClientRect().width); if (width) el.style.minWidth = width + 'px'; }
        if (reduced) { update(to); continue; }
        if (cfg.odometer) {
          const template = format(Math.max(Math.abs(from), Math.abs(to)));
          const root = document.createElement('span');
          const cols = document.createElement('span');
          const label = document.createElement('span');
          const pre = document.createTextNode(prefix), post = document.createTextNode(suffix);
          cols.setAttribute('aria-hidden', 'true');
          label.style.cssText = 'position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap';
          label.textContent = prefix + format(to) + suffix;
          const strips = [...template].map(ch => {
            const col = document.createElement('span');
            if (!/\d/.test(ch)) { col.append(document.createTextNode(ch)); cols.append(col); return { col, digit: false, text: col.firstChild, ch }; }
            col.style.cssText = 'display:inline-block;height:1lh;overflow:hidden;vertical-align:text-bottom';
            const strip = document.createElement('span');
            strip.style.cssText = 'display:block;transition:translate 160ms ease-out;translate:0 -10lh';
            for (let d = 0; d <= 10; d++) { const cell = document.createElement('span'); cell.style.cssText = 'display:block;height:1lh'; cell.textContent = d < 10 ? String(d) : ''; strip.append(cell); }
            col.append(strip);
            cols.append(col);
            return { col, strip, digit: true };
          });
          root.append(pre, cols, label, post);
          node.replaceWith(root);
          let shown = '';
          update = v => {
            const s = format(v).padStart(strips.length, ' ');
            if (s === shown) return;
            shown = s;
            strips.forEach((c, i) => {
              if (c.digit) c.strip.style.translate = `0 ${s[i] === ' ' ? -10 : -Number(s[i])}lh`;
              else { const t = /\d| /.test(s[i]) ? '' : s[i]; if (c.text.data !== t) c.text.data = t; }
            });
          };
        }
        update(from);
        const ease = easing('ease-out'), duration = Math.max(1, Number(cfg.duration ?? 1200));
        whenIn(el, cfg, () => {
          let start = -1;
          const stop = onFrame(now => {
            if (start < 0) start = now;
            const t = Math.min(1, (now - start) / duration);
            update(t >= 1 ? to : from + (to - from) * ease(t));
            if (t >= 1) stop();
          });
        }, 0.3);
      }
    }
  };

  const initText = () => {
    const jobs = [];
    for (const [id, cfg] of entries(motion.text)) for (const el of all(id)) jobs.push({ el, cfg });
    if (!jobs.length) return;
    if (reduced) return;
    const splits = jobs.filter(j => j.cfg.type === 'split');
    const plans = splits.map(({ el, cfg }) => {
      const sel = cfg.by === 'chars' ? '.fw-c' : '.fw-w';
      const parts = [...el.querySelectorAll(sel)];
      const keys = styleKeys(cfg.from);
      return { el, cfg, parts, keys };
    }).filter(p => p.parts.length && p.keys.length);
    const authored = plans.map(p => authoredOfPart(p));
    plans.forEach((p, i) => {
      const to = toFrame(p.keys, authored[i]);
      for (const part of p.parts) applyStyles(part, p.cfg.from);
      whenIn(p.el, p.cfg, () => {
        let groups;
        if (p.cfg.by === 'lines') {
          const rows = new Map();
          for (const part of p.parts) { const top = Math.round(part.offsetTop); if (!rows.has(top)) rows.set(top, []); rows.get(top).push(part); }
          groups = [...rows.entries()].sort((a, b) => a[0] - b[0]).map(r => r[1]);
        } else groups = p.parts.map(x => [x]);
        groups.forEach((group, gi) => {
          for (const part of group) {
            const anim = part.animate([frameStyles(p.cfg.from), to], { duration: Number(p.cfg.duration ?? 500), delay: gi * Number(p.cfg.stagger || 0), easing: cssEasing(p.cfg.easing || 'ease-out'), fill: 'both' });
            anim.onfinish = () => { for (const k of p.keys) part.style.removeProperty(k); anim.cancel(); };
          }
        });
      });
    });
    for (const { el, cfg } of jobs.filter(j => j.cfg.type === 'typewriter')) {
      const chars = [...el.querySelectorAll('.fw-c')];
      if (!chars.length) continue;
      for (const c of chars) c.style.visibility = 'hidden';
      let caret = null;
      if (cfg.cursor) {
        caret = document.createElement('span');
        caret.setAttribute('aria-hidden', 'true');
        caret.style.cssText = 'display:inline-block;width:0;height:1em;vertical-align:text-bottom;box-shadow:0 0 0 1px currentColor;visibility:hidden';
        chars[0].before(caret);
      }
      whenIn(el, cfg, () => {
        const speed = Math.max(1, Number(cfg.speed ?? 30));
        let start = -1, shown = 0;
        if (caret) {
          caret.style.visibility = '';
          caret.animate([{ opacity: 1 }, { opacity: 1, offset: 0.5 }, { opacity: 0, offset: 0.5 }, { opacity: 0 }], { duration: 1000, iterations: Infinity });
        }
        const stop = onFrame(now => {
          if (start < 0) start = now;
          const want = Math.min(chars.length, Math.floor((now - start) / speed) + 1);
          if (want === shown) return;
          for (; shown < want; shown++) chars[shown].style.visibility = '';
          if (caret) chars[shown - 1].after(caret);
          if (shown >= chars.length) stop();
        });
      });
    }
    for (const { el, cfg } of jobs.filter(j => j.cfg.type === 'ghost')) {
      const input = el.matches('input,textarea') ? el : el.querySelector('input,textarea');
      const strings = (cfg.strings || []).map(String).filter(Boolean);
      if (!input || !strings.length) continue;
      const original = input.getAttribute('placeholder') || '';
      const speed = Number(cfg.speed ?? 60), erase = Number(cfg.erase ?? 30), hold = Number(cfg.hold ?? 1500);
      let index = 0, count = 0, phase = 'type', timer = 0, visible = false;
      const busy = () => document.activeElement === input || input.value !== '' || !visible || document.hidden;
      const step = () => {
        timer = 0;
        if (busy()) { if (input.value !== '' || document.activeElement === input) input.setAttribute('placeholder', original); return; }
        const s = strings[index];
        let wait = speed;
        if (phase === 'type') { count++; if (count >= s.length) { phase = 'hold'; wait = hold; } }
        else if (phase === 'hold') { phase = 'erase'; wait = erase; }
        else { count--; wait = erase; if (count <= 0) { phase = 'type'; index = (index + 1) % strings.length; wait = speed * 3; } }
        input.setAttribute('placeholder', s.slice(0, Math.max(count, 0)));
        timer = setTimeout(step, wait);
      };
      const resume = () => { if (!timer && !busy()) timer = setTimeout(step, speed); };
      input.addEventListener('blur', resume);
      input.addEventListener('input', () => { if (input.value === '') resume(); });
      document.addEventListener('visibilitychange', resume);
      watch(el, 0, '0px', e => { visible = e.isIntersecting; if (visible) resume(); });
    }
  };
  const authoredOfPart = p => {
    const cs = getComputedStyle(p.parts[0]);
    return p.keys.map(k => cs.getPropertyValue(k).trim());
  };

  globalThis.__formwebMotion = Object.freeze({ config, reduced, easing, onFrame, interpolate, applyStyles, sceneProgress, sceneOf, onProgress, scrollToScene, scrollToNode });

  initReveals();
  initScenes();
  initLoops();
  initCounters();
  initText();
})();
(() => {
  'use strict';
  const doc = document, root = doc.documentElement;
  let cfg = {};
  try { cfg = JSON.parse(doc.getElementById('fw-config')?.textContent || '{}'); } catch {}
  const motion = cfg.motion;
  if (!motion || typeof motion !== 'object') return;
  const M = globalThis.__formwebMotion || null;
  const reduced = M ? !!M.reduced : (root.classList.contains('fw-r') || matchMedia('(prefers-reduced-motion: reduce)').matches);
  const clamp = (v, lo, hi) => Math.min(Math.max(v, lo), hi);
  const guard = fn => { try { fn(); } catch {} };
  const subs = new Set();
  let raf = 0;
  const pump = () => { raf = 0; for (const fn of [...subs]) fn(); if (subs.size && !raf) raf = requestAnimationFrame(pump); };
  const onFrame = fn => { if (M && M.onFrame) return M.onFrame(fn); subs.add(fn); if (!raf) raf = requestAnimationFrame(pump); return () => subs.delete(fn); };
  const loop = step => {
    let off = null, dead = false, last = performance.now();
    const stop = () => { dead = true; if (off) { off(); off = null; } };
    const tick = () => { if (dead) return; const now = performance.now(), dt = Math.min(0.05, (now - last) / 1000); last = now; if (!step(dt)) stop(); };
    const unsub = onFrame(tick);
    off = dead ? (unsub(), null) : unsub;
    return stop;
  };
  const runner = step => { let stop = null; return () => { if (!stop) stop = loop(dt => { const go = step(dt); if (!go) stop = null; return go; }); }; };
  const eases = { linear: t => t, 'ease-in': t => t * t * t, 'ease-out': t => 1 - Math.pow(1 - t, 3), 'ease-in-out': t => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2 };
  const ease = name => (M && M.easing) ? M.easing(name || 'ease-in-out') : (eases[name] || eases['ease-in-out']);
  const esc = s => CSS.escape(String(s));
  const nodes = id => [...doc.querySelectorAll(`[data-fw-node="${esc(id)}"]`)];
  const find = (id, from) => {
    if (id === undefined || id === null || id === '') return null;
    const sel = `[data-fw-node="${esc(id)}"]`;
    for (let a = from; a; a = a.parentElement) { if (a.matches(sel)) return a; const hit = a.querySelector(sel); if (hit) return hit; }
    return doc.querySelector(sel);
  };
  let serial = 0;
  const ident = el => { while (!el.id) { const id = `fw-i${++serial}`; if (!doc.getElementById(id)) el.id = id; } return el.id; };
  const press = (el, fn) => {
    if (!el.matches('a[href],button,input,select,textarea,summary')) {
      if (!el.hasAttribute('role')) el.setAttribute('role', 'button');
      if (el.tabIndex < 0) el.tabIndex = 0;
      el.addEventListener('keydown', e => { if (e.target === el && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); fn(e); } });
    }
    el.addEventListener('click', fn);
  };
  const owned = new WeakSet();
  const hide = (el, on) => {
    if (on) { el.hidden = true; if (getComputedStyle(el).display !== 'none') { el.style.display = 'none'; owned.add(el); } }
    else { el.hidden = false; if (owned.has(el)) { el.style.display = ''; owned.delete(el); } }
  };
  const length = v => { const s = String(v === undefined || v === null ? '' : v).trim(); return /^\d*\.?\d+$/.test(s) ? `${s}px` : /^\d*\.?\d+(px|em|rem|vw|vh)$/.test(s) ? s : '1000px'; };

  const drag = (el, o) => {
    const back = o.flip && o.flip.back ? find(o.flip.back, el) : null;
    const nested = !!back && el.contains(back);
    const faces = back && !nested ? [el, back] : [el];
    const axis = o.axis || 'both';
    const friction = typeof o.friction === 'number' ? o.friction : 4;
    const bounce = typeof o.restitution === 'number' ? o.restitution : 0.4;
    const step = Number(o.keyboard) || 0;
    const inertia = !!o.inertia && !reduced;
    const spin = !!o.rotate && !reduced && axis === 'both';
    let x = 0, y = 0, rot = 0, vx = 0, vy = 0, spinning = 0, flipped = false, halt = null, grip = null;
    const bounds = () => !o.bounds ? null : o.bounds === 'parent' ? el.parentElement : find(o.bounds, el);
    const paint = () => { for (const f of faces) { f.style.translate = `${x}px ${y}px`; f.style.rotate = `${rot}deg`; } };
    const nudge = (dx, dy) => {
      if (axis === 'x') dy = 0; else if (axis === 'y') dx = 0;
      const hit = { x: false, y: false }, b = bounds();
      if (b) {
        const r = el.getBoundingClientRect(), p = b.getBoundingClientRect();
        const cx = Math.min(Math.max(dx, p.left - r.left), p.right - r.right), cy = Math.min(Math.max(dy, p.top - r.top), p.bottom - r.bottom);
        hit.x = Math.abs(cx - dx) > 0.01; hit.y = Math.abs(cy - dy) > 0.01; dx = cx; dy = cy;
      }
      x += dx; y += dy; paint();
      return hit;
    };
    const turn = on => {
      flipped = on;
      const t = reduced ? 'none' : 'transform 700ms ease';
      el.style.transition = t;
      el.style.transform = `perspective(1200px) rotateY(${on ? 180 : 0}deg)`;
      if (back) { back.style.transition = t; back.style.transform = nested ? 'rotateY(180deg)' : `perspective(1200px) rotateY(${on ? 360 : 180}deg)`; back.setAttribute('aria-hidden', String(!on)); }
    };
    const fling = () => {
      halt = loop(dt => {
        const k = Math.exp(-friction * dt);
        vx *= k; vy *= k; spinning *= k;
        const hit = nudge(vx * dt, vy * dt);
        if (hit.x) vx = -vx * bounce;
        if (hit.y) vy = -vy * bounce;
        rot += spinning * dt; paint();
        if (Math.hypot(vx, vy) < 6 && Math.abs(spinning) < 2) { halt = null; return false; }
        return true;
      });
    };
    const down = e => {
      if (e.button > 0) return;
      const inner = e.target.closest('a[href],button,input,select,textarea,[contenteditable]');
      if (inner && inner !== e.currentTarget && e.currentTarget.contains(inner)) return;
      if (halt) { halt(); halt = null; }
      const r = el.getBoundingClientRect();
      grip = { id: e.pointerId, px: e.clientX, py: e.clientY, sx: e.clientX, sy: e.clientY, gx: e.clientX - r.left - r.width / 2, gy: e.clientY - r.top - r.height / 2, inertia: (r.width * r.width + r.height * r.height) / 4 || 1, far: 0, live: false, t: performance.now(), vx: 0, vy: 0 };
      e.currentTarget.setPointerCapture(e.pointerId);
    };
    const move = e => {
      if (!grip || e.pointerId !== grip.id) return;
      const now = performance.now(), dt = Math.max(0.001, (now - grip.t) / 1000), dx = e.clientX - grip.px, dy = e.clientY - grip.py;
      grip.px = e.clientX; grip.py = e.clientY; grip.t = now;
      grip.far = Math.max(grip.far, Math.hypot(e.clientX - grip.sx, e.clientY - grip.sy));
      if (!grip.live) { if (grip.far < 4) return; grip.live = true; el.style.cursor = 'grabbing'; return; }
      nudge(dx, dy);
      grip.vx = 0.5 * (dx / dt) + 0.5 * grip.vx; grip.vy = 0.5 * (dy / dt) + 0.5 * grip.vy;
    };
    const up = e => {
      if (!grip || e.pointerId !== grip.id) return;
      const g = grip; grip = null; el.style.cursor = 'grab';
      if (!g.live) { if (e.type === 'pointerup' && back && o.flip) turn(!flipped); return; }
      if (!inertia || e.type === 'pointercancel') return;
      const idle = performance.now() - g.t > 90;
      vx = idle || axis === 'y' ? 0 : g.vx; vy = idle || axis === 'x' ? 0 : g.vy;
      if (Math.hypot(vx, vy) < 30) return;
      spinning = spin ? clamp((g.gx * vy - g.gy * vx) / g.inertia * 180 / Math.PI, -720, 720) : 0;
      fling();
    };
    const keys = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
    el.addEventListener('keydown', e => {
      if (e.target !== el) return;
      const d = keys[e.key];
      if (d && step) { e.preventDefault(); if (halt) { halt(); halt = null; } nudge(d[0] * step, d[1] * step); }
      else if ((e.key === 'Enter' || e.key === ' ') && back && o.flip) { e.preventDefault(); turn(!flipped); }
    });
    for (const f of faces) { f.addEventListener('pointerdown', down); f.addEventListener('pointermove', move); f.addEventListener('pointerup', up); f.addEventListener('pointercancel', up); f.style.touchAction = 'none'; f.style.cursor = 'grab'; f.style.userSelect = 'none'; }
    if (el.tabIndex < 0) el.tabIndex = 0;
    if (back) {
      for (const f of faces) { f.style.backfaceVisibility = 'hidden'; f.style.webkitBackfaceVisibility = 'hidden'; }
      if (nested) el.style.transformStyle = 'preserve-3d';
      el.style.transform = 'perspective(1200px) rotateY(0deg)';
      back.style.transform = nested ? 'rotateY(180deg)' : 'perspective(1200px) rotateY(180deg)';
      back.setAttribute('aria-hidden', 'true');
    }
  };

  const tilt = (el, o) => {
    if (reduced) return;
    const max = Number(o.max) || 8, spring = clamp(Number(o.spring) || 0.12, 0.01, 1), depth = length(o.perspective);
    let tx = 0, ty = 0, cx = 0, cy = 0;
    const start = runner(dt => {
      const k = 1 - Math.pow(1 - spring, dt * 60);
      cx += (tx - cx) * k; cy += (ty - cy) * k;
      const rest = !tx && !ty && Math.abs(cx) < 0.01 && Math.abs(cy) < 0.01;
      if (rest) { cx = cy = 0; el.style.transform = ''; return false; }
      el.style.transform = `perspective(${depth}) rotateX(${cx.toFixed(3)}deg) rotateY(${cy.toFixed(3)}deg)`;
      return Math.abs(tx - cx) > 0.01 || Math.abs(ty - cy) > 0.01;
    });
    const aim = e => {
      const r = el.getBoundingClientRect(), w = el.offsetWidth || r.width || 1, h = el.offsetHeight || r.height || 1;
      tx = clamp((e.clientY - r.top - r.height / 2) / (h / 2), -1, 1) * max;
      ty = -clamp((e.clientX - r.left - r.width / 2) / (w / 2), -1, 1) * max;
      start();
    };
    el.addEventListener('pointerenter', aim);
    el.addEventListener('pointermove', aim);
    el.addEventListener('pointerleave', () => { tx = ty = 0; start(); });
  };

  const follow = (el, o) => {
    if (reduced) return;
    const zone = find(o.within, el) || el.parentElement;
    if (!zone) return;
    const spring = clamp(Number(o.spring) || 0.18, 0.01, 1);
    let px = 0, py = 0, cx = 0, cy = 0, vis = 0, goal = 0, fresh = false;
    el.style.opacity = '0';
    const start = runner(dt => {
      const k = 1 - Math.pow(1 - spring, dt * 60), r = el.getBoundingClientRect();
      const tx = px - (r.left + r.width / 2 - cx), ty = py - (r.top + r.height / 2 - cy);
      if (fresh) { cx = tx; cy = ty; fresh = false; }
      cx += (tx - cx) * k; cy += (ty - cy) * k; vis += (goal - vis) * k;
      if (goal === 0 && vis < 0.005) { vis = 0; el.style.opacity = '0'; return false; }
      el.style.translate = `${cx.toFixed(2)}px ${cy.toFixed(2)}px`;
      el.style.opacity = vis.toFixed(3);
      el.style.scale = (0.9 + 0.1 * vis).toFixed(4);
      return goal === 0 || Math.abs(tx - cx) > 0.05 || Math.abs(ty - cy) > 0.05 || vis < 0.995;
    });
    const aim = e => { px = e.clientX; py = e.clientY; if (goal === 0) { if (vis < 0.05) fresh = true; goal = 1; } start(); };
    zone.addEventListener('pointerenter', aim);
    zone.addEventListener('pointermove', aim);
    zone.addEventListener('pointerleave', () => { goal = 0; start(); });
  };

  const proximity = list => {
    const seen = new Map();
    let pt = null, queued = false;
    const apply = () => {
      queued = false;
      for (const [el, radius] of list) {
        let n = 0;
        if (pt) { const r = el.getBoundingClientRect(); n = clamp(1 - Math.hypot(pt.x - r.left - r.width / 2, pt.y - r.top - r.height / 2) / radius, 0, 1); n = Math.round(n * 1000) / 1000; }
        if (seen.get(el) !== n) { seen.set(el, n); el.style.setProperty('--fw-near', String(n)); }
      }
    };
    const queue = () => { if (!queued) { queued = true; requestAnimationFrame(apply); } };
    for (const [el] of list) el.style.setProperty('--fw-near', '0');
    addEventListener('pointermove', e => { pt = { x: e.clientX, y: e.clientY }; queue(); }, { passive: true });
    root.addEventListener('pointerleave', () => { pt = null; queue(); });
  };

  const accordion = (host, o, items) => {
    const open = typeof o.initial === 'number' ? o.initial : -1;
    const set = (i, on) => {
      const { t, p } = items[i];
      t.setAttribute('aria-expanded', String(on));
      if (on) { p.setAttribute('data-fw-open', ''); p.removeAttribute('inert'); p.removeAttribute('aria-hidden'); }
      else { p.removeAttribute('data-fw-open'); p.setAttribute('inert', ''); p.setAttribute('aria-hidden', 'true'); }
    };
    items.forEach(({ t, p }, i) => {
      t.setAttribute('aria-controls', ident(p));
      set(i, p.hasAttribute('data-fw-open') || i === open);
      void p.offsetHeight;
      if (!reduced && parseFloat(getComputedStyle(p).transitionDuration) === 0) p.style.transition = 'grid-template-rows 300ms ease';
      press(t, () => {
        const on = t.getAttribute('aria-expanded') !== 'true';
        if (on && o.single) items.forEach((_, j) => { if (j !== i) set(j, false); });
        set(i, on);
      });
      t.addEventListener('keydown', e => {
        const to = e.key === 'ArrowDown' ? (i + 1) % items.length : e.key === 'ArrowUp' ? (i - 1 + items.length) % items.length : e.key === 'Home' ? 0 : e.key === 'End' ? items.length - 1 : -1;
        if (to >= 0 && e.target === t) { e.preventDefault(); items[to].t.focus(); }
      });
    });
  };

  const tabs = (host, o, items) => {
    let list = items[0].t.parentElement;
    while (list && !items.every(i => list.contains(i.t))) list = list.parentElement;
    if (list && !list.hasAttribute('role')) list.setAttribute('role', 'tablist');
    const ind = o.indicator ? find(o.indicator, host) : null;
    let cur = -1, ready = false;
    const place = () => {
      if (!ind || cur < 0) return;
      const tr = items[cur].t.getBoundingClientRect();
      if (!tr.width && !tr.height) return;
      const parent = ind.offsetParent || root, pr = parent.getBoundingClientRect(), iw = ind.offsetWidth || 1, ih = ind.offsetHeight || 1;
      const cx = pr.left + (parent.clientLeft || 0) + ind.offsetLeft + iw / 2, cy = pr.top + (parent.clientTop || 0) + ind.offsetTop + ih / 2;
      const a = items[0].t.getBoundingClientRect(), b = items[items.length - 1].t.getBoundingClientRect();
      const vertical = items.length > 1 && Math.abs(a.top - b.top) > Math.abs(a.left - b.left);
      const tx = vertical ? 0 : tr.left + tr.width / 2 - cx, ty = vertical ? tr.top + tr.height / 2 - cy : 0;
      const sx = vertical ? 1 : tr.width / iw, sy = vertical ? tr.height / ih : 1;
      if (!ready) ind.style.transition = 'none';
      ind.style.translate = `${tx.toFixed(2)}px ${ty.toFixed(2)}px`;
      ind.style.scale = `${sx.toFixed(4)} ${sy.toFixed(4)}`;
      if (!ready) { ready = true; void ind.offsetWidth; ind.style.transition = reduced ? 'none' : 'translate 300ms ease, scale 300ms ease'; }
    };
    const select = (i, focus) => {
      cur = i;
      items.forEach(({ t, p }, j) => { const on = j === i; t.setAttribute('aria-selected', String(on)); t.tabIndex = on ? 0 : -1; hide(p, !on); });
      if (focus) items[i].t.focus();
      place();
    };
    items.forEach(({ t, p }, i) => {
      t.setAttribute('role', 'tab'); p.setAttribute('role', 'tabpanel');
      t.setAttribute('aria-controls', ident(p)); p.setAttribute('aria-labelledby', ident(t));
      press(t, () => select(i, false));
      t.addEventListener('keydown', e => {
        const n = items.length, to = e.key === 'ArrowRight' || e.key === 'ArrowDown' ? (i + 1) % n : e.key === 'ArrowLeft' || e.key === 'ArrowUp' ? (i - 1 + n) % n : e.key === 'Home' ? 0 : e.key === 'End' ? n - 1 : -1;
        if (to >= 0) { e.preventDefault(); select(to, true); }
      });
    });
    select(clamp(typeof o.initial === 'number' ? o.initial : 0, 0, items.length - 1), false);
    if (ind) {
      if (typeof ResizeObserver === 'function' && list) new ResizeObserver(place).observe(list);
      addEventListener('resize', place);
      if (doc.fonts && doc.fonts.ready) doc.fonts.ready.then(place);
    }
  };

  const filter = (host, o) => {
    const box = find(o.items, host);
    const chips = (o.chips || []).map(c => ({ t: find(c.trigger, host), v: String(c.value) })).filter(c => c.t);
    if (!box || !chips.length) return;
    let cur = null;
    const apply = (val, animate) => {
      cur = val;
      const kids = [...box.children], before = new Map();
      if (animate && !reduced) for (const k of kids) if (!k.hidden) before.set(k, k.getBoundingClientRect());
      for (const k of kids) hide(k, !(val === 'all' || (k.getAttribute('data-fw-tags') || '').split(/\s+/).includes(val)));
      for (const c of chips) c.t.setAttribute('aria-pressed', String(c.v === val));
      if (!animate || reduced) return;
      for (const k of kids) {
        if (k.hidden) continue;
        const was = before.get(k), now = k.getBoundingClientRect();
        if (was) { const dx = was.left - now.left, dy = was.top - now.top; if (dx || dy) k.animate([{ transform: `translate(${dx}px,${dy}px)` }, { transform: 'none' }], { duration: 320, easing: 'cubic-bezier(.2,.7,.2,1)' }); }
        else k.animate([{ opacity: 0, transform: 'scale(.94)' }, { opacity: 1, transform: 'none' }], { duration: 260, easing: 'ease-out' });
      }
    };
    for (const c of chips) press(c.t, () => apply(cur === c.v && c.v !== 'all' ? 'all' : c.v, true));
    apply(String(o.initial === undefined ? 'all' : o.initial), false);
  };

  const disclosure = (host, o) => {
    if (o.type === 'filter') return filter(host, o);
    const items = (Array.isArray(o.items) ? o.items : []).map(i => ({ t: find(i.trigger, host), p: find(i.panel, host) })).filter(i => i.t && i.p);
    if (!items.length) return;
    if (o.type === 'accordion') accordion(host, o, items); else if (o.type === 'tabs') tabs(host, o, items);
  };

  const copying = new WeakMap();
  const firstText = el => { const w = doc.createTreeWalker(el, NodeFilter.SHOW_TEXT); let n; while ((n = w.nextNode())) if (n.data.trim()) return n; return null; };
  const feedback = (el, text, ms) => {
    let s = copying.get(el);
    if (s) clearTimeout(s.timer);
    else {
      const node = firstText(el);
      if (!node) return;
      const w = parseFloat(getComputedStyle(el).width) || el.getBoundingClientRect().width;
      s = { node, data: node.data, min: el.style.minWidth };
      copying.set(el, s);
      el.style.minWidth = `${w}px`;
    }
    s.node.data = text;
    s.timer = setTimeout(() => { s.node.data = s.data; el.style.minWidth = s.min; copying.delete(el); }, ms);
  };
  const clip = async text => {
    try { if (navigator.clipboard && navigator.clipboard.writeText) { await navigator.clipboard.writeText(text); return true; } } catch {}
    const ta = doc.createElement('textarea'), prev = doc.activeElement;
    ta.value = text; ta.setAttribute('readonly', ''); ta.setAttribute('aria-hidden', 'true');
    ta.style.cssText = 'position:fixed;top:0;left:0;opacity:0;pointer-events:none';
    doc.body.appendChild(ta); ta.select();
    let ok = false;
    try { ok = doc.execCommand('copy'); } catch {}
    ta.remove();
    if (prev && prev.focus) prev.focus({ preventScroll: true });
    return ok;
  };
  const copy = async (step, el, ctx) => {
    const src = step.from ? find(step.from, el) : null;
    const text = typeof step.text === 'string' ? step.text : src ? (src.matches('input,textarea,select') ? src.value : src.innerText || src.textContent) : (ctx.value || '');
    if (await clip(text) && step.feedback) feedback(el, String(step.feedback), Number.isFinite(step.duration) ? step.duration : 1600);
  };

  const glide = (y, ms, name) => new Promise(done => {
    const from = scrollY, fn = ease(name);
    let t = 0;
    loop(dt => { t += dt * 1000; const p = Math.min(1, t / ms); scrollTo({ top: from + (y - from) * fn(p), behavior: 'instant' }); if (p >= 1) { done(); return false; } return true; });
  });
  const toNode = async (step, el) => {
    const ms = Number.isFinite(step.duration) ? step.duration : 800;
    if (M) {
      try {
        if (typeof step.progress === 'number' && M.scrollToScene) return await M.scrollToScene(step.to, step.progress, ms, step.easing);
        if (M.scrollToNode) return await M.scrollToNode(step.to, ms, step.easing);
      } catch {}
    }
    const target = find(step.to, el);
    if (!target) return;
    const y = target.getBoundingClientRect().top + scrollY;
    if (reduced) scrollTo({ top: y, behavior: 'instant' });
    else if (Number.isFinite(step.duration)) await glide(y, ms, step.easing);
    else scrollTo({ top: y, behavior: 'smooth' });
  };

  const media = (step, el) => {
    let m = find(step.target, el);
    if (m && !(m instanceof HTMLMediaElement)) m = m.querySelector('video,audio');
    if (!m) return;
    const play = () => { const p = m.play(); if (p && p.catch) p.catch(() => {}); };
    if (step.command === 'play') play();
    else if (step.command === 'pause') m.pause();
    else if (step.command === 'toggle') { if (m.paused) play(); else m.pause(); }
    else if (step.command === 'restart') { m.currentTime = 0; play(); }
  };

  let box = null, source = null, opener = null, busy = false, closing = false;
  const largest = img => {
    const set = img.getAttribute('srcset');
    if (set) {
      let best = null, score = -1;
      for (const part of set.split(',')) { const [u, d] = part.trim().split(/\s+/); const s = d ? parseFloat(d) : 1; if (u && s > score) { score = s; best = u; } }
      if (best) return new URL(best, doc.baseURI).href;
    }
    return img.currentSrc || img.src;
  };
  const dialog = () => {
    if (box) return box;
    const d = doc.createElement('dialog'), im = doc.createElement('img');
    d.className = 'fw-lightbox'; d.setAttribute('aria-label', 'Image preview'); d.tabIndex = -1;
    d.style.cssText = 'position:fixed;inset:0;width:100%;height:100%;max-width:none;max-height:none;margin:0;padding:0;border:0;overflow:hidden;background:rgba(0,0,0,.88);cursor:zoom-out';
    im.style.cssText = 'position:absolute;inset:0;margin:auto;max-width:92vw;max-height:92vh;object-fit:contain';
    d.appendChild(im);
    d.addEventListener('click', () => shut());
    d.addEventListener('cancel', e => { e.preventDefault(); shut(); });
    doc.body.appendChild(d);
    return (box = d);
  };
  const fly = opening => {
    const im = box.firstChild;
    if (reduced || !source || !source.isConnected) return Promise.resolve();
    const a = source.getBoundingClientRect(), b = im.getBoundingClientRect();
    if (!a.width || !b.width || a.bottom < 0 || a.top > innerHeight) return Promise.resolve();
    const frames = [{ transformOrigin: '0 0', transform: `translate(${a.left - b.left}px,${a.top - b.top}px) scale(${a.width / b.width},${a.height / b.height})` }, { transformOrigin: '0 0', transform: 'none' }];
    if (!opening) frames.reverse();
    return im.animate(frames, { duration: 360, easing: 'cubic-bezier(.2,.8,.2,1)', fill: opening ? 'none' : 'forwards' }).finished.catch(() => {});
  };
  const shut = async () => {
    if (!box || !box.open || closing) return;
    closing = true;
    if (!reduced) { box.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 260, fill: 'forwards' }); await fly(false); }
    box.close();
    for (const a of box.getAnimations({ subtree: true })) a.cancel();
    closing = false;
    if (opener && opener.focus) opener.focus({ preventScroll: true });
  };
  const lightbox = async (step, el) => {
    const hit = find(step.target, el) || el;
    const img = hit.matches('img') ? hit : hit.querySelector('img');
    if (!img || busy || (box && box.open)) return;
    busy = true;
    try {
      const d = dialog(), im = d.firstChild, src = largest(img);
      im.alt = img.alt || '';
      if (im.getAttribute('src') !== src) im.src = src;
      try { await Promise.race([im.decode(), new Promise(r => setTimeout(r, 1500))]); } catch {}
      source = img;
      opener = doc.activeElement && doc.activeElement !== doc.body ? doc.activeElement : el;
      d.showModal();
      if (!reduced) d.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 240 });
      fly(true);
    } finally { busy = false; }
  };

  const themeKey = () => cfg.context && cfg.context.site ? `fw-theme-${cfg.context.site}` : 'fw-theme';
  const themers = new Set();
  const mark = () => { const dark = (root.getAttribute('data-theme') || (cfg.design && cfg.design.themes && cfg.design.themes.default) || 'dark') === 'dark'; for (const el of themers) el.setAttribute('aria-pressed', String(dark)); };
  const theme = () => {
    const now = root.getAttribute('data-theme') || (cfg.design && cfg.design.themes && cfg.design.themes.default) || 'dark';
    const next = now === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    try { localStorage.setItem(themeKey(), next); } catch {}
    mark();
  };

  const run = (step, el, ctx) => {
    if (!step || typeof step !== 'object') return;
    let out;
    switch (step.action) {
      case 'copy': out = copy(step, el, ctx); break;
      case 'scroll-to': out = toNode(step, el); break;
      case 'media': media(step, el); break;
      case 'lightbox': out = lightbox(step, el); break;
      case 'toggle-theme': theme(); break;
      default: {
        const handler = globalThis.__formwebActions && globalThis.__formwebActions[step.action];
        if (handler) out = handler(step, el, ctx);
      }
    }
    if (out && out.catch) out.catch(() => {});
  };
  globalThis.__formwebRun = run;

  const bind = (el, step) => {
    const go = ctx => run(step, el, ctx || {});
    if (step.action === 'toggle-theme') { themers.add(el); if (step.trigger !== 'click') el.setAttribute('aria-pressed', 'false'); }
    if (step.action === 'copy' && step.feedback) el.setAttribute('aria-live', 'polite');
    switch (step.trigger) {
      case 'click': press(el, e => { if (e.type === 'click' && el.matches('a,button')) e.preventDefault(); go(); }); break;
      case 'hover': el.addEventListener('pointerenter', e => { if (e.pointerType !== 'touch') go(); }); break;
      case 'change': el.addEventListener('change', () => go({ value: el.value })); break;
      case 'input': el.addEventListener('input', () => go({ value: el.value })); break;
      case 'submit': {
        const form = el.matches('form') ? el : el.closest('form') || el.querySelector('form');
        if (form) form.addEventListener('submit', e => { e.preventDefault(); const field = form.querySelector('input:not([type=submit]):not([type=button]),textarea,select'); go({ value: field ? field.value : '' }); });
        break;
      }
      case 'load': go(); break;
      case 'view': {
        if (typeof IntersectionObserver !== 'function') { go(); break; }
        const io = new IntersectionObserver(list => { if (list.some(i => i.isIntersecting)) { io.disconnect(); go(); } }, { threshold: 0.25 });
        io.observe(el);
        break;
      }
    }
  };

  const init = () => {
    const each = (kind, fn) => { const map = motion[kind]; if (map && typeof map === 'object') for (const [id, o] of Object.entries(map)) if (o && typeof o === 'object') nodes(id).forEach(el => guard(() => fn(el, o))); };
    each('drag', drag);
    const near = [];
    each('pointer', (el, o) => {
      if (o.type === 'tilt') tilt(el, o);
      else if (o.type === 'follow') follow(el, o);
      else if (o.type === 'proximity') near.push([el, Number(o.radius) > 0 ? Number(o.radius) : 200]);
    });
    if (near.length) guard(() => proximity(near));
    each('disclosure', disclosure);
    const acts = motion.actions;
    if (acts && typeof acts === 'object') {
      for (const [id, steps] of Object.entries(acts)) {
        if (!Array.isArray(steps)) continue;
        for (const el of nodes(id)) for (const step of steps) if (step && typeof step === 'object') guard(() => bind(el, step));
      }
      mark();
    }
    doc.addEventListener('formweb-motion-action', e => {
      const d = e.detail || {};
      const step = typeof d.action === 'string' ? { action: d.action, ...d } : d.action;
      const origin = typeof d.origin === 'string' ? nodes(d.origin)[0] : d.origin;
      guard(() => run(step, origin instanceof Element ? origin : doc.body, {}));
    });
  };
  if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', init, { once: true }); else init();
})();
(() => {
  'use strict';
  let config = {};
  try { config = JSON.parse(document.getElementById('fw-config')?.textContent || '{}'); } catch {}
  const spec = config.variables;
  if (!spec || typeof spec !== 'object') return;
  const doc = document, html = doc.documentElement;
  const own = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  const obj = m => (m && typeof m === 'object' && !Array.isArray(m) ? m : {});
  const entries = m => Object.entries(obj(m));
  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
  const defs = obj(spec.values), tables = obj(spec.tables), sources = obj(spec.formulas);
  const nodes = id => [...doc.querySelectorAll(`[data-fw-node="${CSS.escape(String(id))}"]`)];
  const ready = fn => { if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', fn, { once: true }); else fn(); };
  const guard = fn => { try { fn(); } catch {} };

  const fin = x => (Number.isFinite(x) ? x + 0 : 0);
  const DECIMAL = /^-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$/;
  const toNum = v => {
    if (typeof v === 'number') return fin(v);
    if (typeof v === 'boolean') return v ? 1 : 0;
    if (typeof v !== 'string') return 0;
    const s = v.trim();
    return DECIMAL.test(s) ? fin(parseFloat(s)) : 0;
  };
  const numText = x => {
    x = fin(x);
    if (Number.isInteger(x)) return Math.abs(x) < 1e21 ? x.toFixed(0) : BigInt(x).toString();
    const s = x.toFixed(10).replace(/0+$/, '').replace(/\.$/, '');
    return s === '-0' ? '0' : s;
  };
  const toText = v => (typeof v === 'string' ? v : typeof v === 'boolean' ? String(v) : typeof v === 'number' ? numText(v) : '');
  const truthy = v => (typeof v === 'string' ? v.length > 0 : typeof v === 'boolean' ? v : typeof v === 'number' ? v !== 0 : false);
  const coerce = (type, v) => {
    if (type === 'number') return toNum(v);
    if (type === 'boolean') return truthy(v);
    return toText(v);
  };
  const roundTo = (x, digits) => {
    const p = Math.pow(10, clamp(Math.trunc(fin(digits)), 0, 10));
    return fin(Math.sign(x) * Math.floor(Math.abs(x) * p + 0.5) / p);
  };
  const fixed = (x, d) => {
    if (x < 1e21) return x.toFixed(d);
    return BigInt(x).toString() + (d ? '.' + '0'.repeat(d) : '');
  };
  const format = (x, o) => {
    const d = clamp(Math.trunc(Number(o.decimals) || 0), 0, 10);
    const r = roundTo(fin(x), d);
    const parts = fixed(Math.abs(r), d).split('.');
    if (o.grouping) parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    return `${typeof o.prefix === 'string' ? o.prefix : ''}${r < 0 ? '-' : ''}${parts.join('.')}${typeof o.suffix === 'string' ? o.suffix : ''}`;
  };
  const cmpText = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

  const TOKEN_NUM = /\d+(?:\.\d+)?(?:[eE][+-]?\d+)?/y;
  const TOKEN_NAME = /[A-Za-z_][A-Za-z0-9_]*/y;
  const TOKEN_STR = /"[^"\\]*"/y;
  const TOKEN_OP = /\|\||&&|==|!=|<=|>=|[<>+\-*\/%^!(),]/y;
  const TOKEN_SPACE = /\s+/y;
  const lex = src => {
    const out = [];
    let i = 0;
    const at = (re) => { re.lastIndex = i; return re.exec(src); };
    while (i < src.length) {
      let m = at(TOKEN_SPACE);
      if (m) { i += m[0].length; continue; }
      if ((m = at(TOKEN_NUM))) out.push({ k: 'num', v: parseFloat(m[0]) });
      else if ((m = at(TOKEN_NAME))) out.push({ k: 'id', v: m[0] });
      else if ((m = at(TOKEN_STR))) out.push({ k: 'str', v: m[0].slice(1, -1) });
      else if ((m = at(TOKEN_OP))) out.push({ k: 'op', v: m[0] });
      else throw new Error('token');
      i += m[0].length;
    }
    return out;
  };

  const FUNCTIONS = new Set(['min', 'max', 'round', 'floor', 'ceil', 'abs', 'clamp', 'sum', 'lookup', 'if']);
  const parseFormula = src => {
    const t = lex(src);
    let p = 0;
    const isOp = v => p < t.length && t[p].k === 'op' && t[p].v === v;
    const eat = v => { if (!isOp(v)) throw new Error('expected'); p++; };
    const expr = () => or();
    const or = () => {
      let a = and();
      while (isOp('||')) { p++; a = { t: 'bin', o: '||', a, b: and() }; }
      return a;
    };
    const and = () => {
      let a = cmp();
      while (isOp('&&')) { p++; a = { t: 'bin', o: '&&', a, b: cmp() }; }
      return a;
    };
    const cmp = () => {
      const a = add();
      for (const o of ['==', '!=', '<=', '>=', '<', '>']) if (isOp(o)) { p++; return { t: 'bin', o, a, b: add() }; }
      return a;
    };
    const add = () => {
      let a = mul();
      while (isOp('+') || isOp('-')) { const o = t[p++].v; a = { t: 'bin', o, a, b: mul() }; }
      return a;
    };
    const mul = () => {
      let a = unary();
      while (isOp('*') || isOp('/') || isOp('%')) { const o = t[p++].v; a = { t: 'bin', o, a, b: unary() }; }
      return a;
    };
    const unary = () => {
      if (isOp('-')) { p++; return { t: 'neg', a: unary() }; }
      if (isOp('!')) { p++; return { t: 'not', a: unary() }; }
      return pow();
    };
    const pow = () => {
      const a = atom();
      if (isOp('^')) { p++; return { t: 'bin', o: '^', a, b: unary() }; }
      return a;
    };
    const atom = () => {
      const tok = t[p++];
      if (!tok) throw new Error('end');
      if (tok.k === 'num') return { t: 'lit', v: tok.v };
      if (tok.k === 'str') return { t: 'lit', v: tok.v };
      if (tok.k === 'op' && tok.v === '(') { const e = expr(); eat(')'); return e; }
      if (tok.k !== 'id') throw new Error('atom');
      if (tok.v === 'true') return { t: 'lit', v: true };
      if (tok.v === 'false') return { t: 'lit', v: false };
      if (isOp('(')) {
        if (!FUNCTIONS.has(tok.v)) throw new Error('function');
        p++;
        const args = [];
        if (!isOp(')')) { args.push(expr()); while (isOp(',')) { p++; args.push(expr()); } }
        eat(')');
        return { t: 'call', f: tok.v, args };
      }
      return own(tables, tok.v) ? { t: 'tbl', v: tok.v } : { t: 'var', v: tok.v };
    };
    const root = expr();
    if (p !== t.length) throw new Error('trailing');
    return root;
  };
  const compile = src => { try { return parseFormula(String(src)); } catch { return null; } };

  const vals = {}, types = {}, res = {};
  for (const [name, def] of entries(defs)) {
    const type = def && (def.type === 'number' || def.type === 'boolean') ? def.type : 'text';
    types[name] = type;
    vals[name] = coerce(type, def && def.initial);
  }
  const lookupName = name => (own(vals, name) ? vals[name] : own(res, name) ? res[name] : 0);

  const evaluate = n => {
    switch (n.t) {
      case 'lit': return n.v;
      case 'var': return lookupName(n.v);
      case 'tbl': return 0;
      case 'neg': return fin(-toNum(evaluate(n.a)));
      case 'not': return !truthy(evaluate(n.a));
      case 'bin': return binary(n);
      case 'call': return call(n);
    }
    return 0;
  };
  const binary = n => {
    const a = evaluate(n.a), b = evaluate(n.b);
    switch (n.o) {
      case '||': return truthy(a) || truthy(b);
      case '&&': return truthy(a) && truthy(b);
      case '==': case '!=': case '<': case '<=': case '>': case '>=': {
        let c;
        if (typeof a === 'string' && typeof b === 'string') c = cmpText(a, b);
        else { const x = toNum(a), y = toNum(b); c = x < y ? -1 : x > y ? 1 : 0; }
        switch (n.o) {
          case '==': return c === 0;
          case '!=': return c !== 0;
          case '<': return c < 0;
          case '<=': return c <= 0;
          case '>': return c > 0;
          default: return c >= 0;
        }
      }
    }
    const x = toNum(a), y = toNum(b);
    switch (n.o) {
      case '+': return fin(x + y);
      case '-': return fin(x - y);
      case '*': return fin(x * y);
      case '/': return y === 0 ? 0 : fin(x / y);
      case '%': return y === 0 ? 0 : fin(x % y);
      case '^': return fin(Math.pow(x, y));
    }
    return 0;
  };
  const call = n => {
    const args = n.args;
    const num = i => (i < args.length ? toNum(evaluate(args[i])) : 0);
    switch (n.f) {
      case 'min': return args.length ? fin(Math.min(...args.map((_, i) => num(i)))) : 0;
      case 'max': return args.length ? fin(Math.max(...args.map((_, i) => num(i)))) : 0;
      case 'round': return roundTo(num(0), args.length > 1 ? num(1) : 0);
      case 'floor': return fin(Math.floor(num(0)));
      case 'ceil': return fin(Math.ceil(num(0)));
      case 'abs': return fin(Math.abs(num(0)));
      case 'clamp': return fin(Math.min(Math.max(num(0), num(1)), num(2)));
      case 'sum': {
        let total = 0;
        for (const a of args) {
          if (a.t === 'tbl') { for (const v of Object.values(obj(tables[a.v]))) if (typeof v === 'number') total += v; }
          else total += toNum(evaluate(a));
        }
        return fin(total);
      }
      case 'lookup': {
        const fallback = args.length > 2 ? evaluate(args[2]) : 0;
        if (!args.length || args[0].t !== 'tbl' || args.length < 2) return fallback;
        const key = toText(evaluate(args[1])), table = obj(tables[args[0].v]);
        return own(table, key) ? table[key] : fallback;
      }
      case 'if': return truthy(args.length ? evaluate(args[0]) : false) ? (args.length > 1 ? evaluate(args[1]) : 0) : (args.length > 2 ? evaluate(args[2]) : 0);
    }
    return 0;
  };

  const compiled = {};
  for (const [name, src] of entries(sources)) compiled[name] = compile(src);
  const refs = (n, acc) => {
    if (!n || typeof n !== 'object') return acc;
    if (n.t === 'var') acc.add(n.v);
    if (n.a) refs(n.a, acc);
    if (n.b) refs(n.b, acc);
    if (n.args) for (const a of n.args) refs(a, acc);
    return acc;
  };
  const order = [], seen = new Set();
  const visit = name => {
    if (seen.has(name)) return;
    seen.add(name);
    for (const d of refs(compiled[name], new Set())) if (own(compiled, d)) visit(d);
    order.push(name);
  };
  for (const name of Object.keys(compiled)) visit(name);

  const recompute = () => {
    const changed = [];
    for (const name of order) {
      const next = compiled[name] ? evaluate(compiled[name]) : 0;
      if (!own(res, name) || res[name] !== next) { res[name] = next; changed.push(name); }
    }
    return changed;
  };
  recompute();

  const valueOf = name => (own(vals, name) ? vals[name] : own(res, name) ? res[name] : undefined);

  const subs = new Map();
  const inputs = new Map();
  const outputs = [];
  const cssNames = new Set(entries(defs).filter(([name, def]) => def && def.cssVar === true && types[name] !== 'text').map(([name]) => name));
  const dirty = new Set();
  let flushing = false, skip = null;

  const paintVar = name => {
    const v = vals[name], s = typeof v === 'boolean' ? (v ? '1' : '0') : numText(v), key = `--fw-v-${name}`;
    if (html.style.getPropertyValue(key) !== s) html.style.setProperty(key, s);
  };
  const writeInput = (el, v) => {
    if (el.type === 'checkbox') { const on = truthy(v); if (el.checked !== on) el.checked = on; }
    else if (el.type === 'radio') { const on = el.value === toText(v); if (el.checked !== on) el.checked = on; }
    else { const s = toText(v); if (el.value !== s) el.value = s; }
  };
  const paintOutput = out => {
    const v = valueOf(out.from);
    const s = typeof v === 'string' || typeof v === 'boolean' ? `${out.o.prefix || ''}${String(v)}${out.o.suffix || ''}` : format(toNum(v), out.o);
    if (out.node.data !== s) out.node.data = s;
  };
  const render = names => {
    for (const name of names) {
      if (cssNames.has(name)) paintVar(name);
      const list = inputs.get(name);
      if (list && own(vals, name)) for (const el of list) if (el !== skip) writeInput(el, vals[name]);
    }
    for (const out of outputs) if (names.has(out.from)) paintOutput(out);
    for (const name of names) {
      const fns = subs.get(name);
      if (fns) for (const fn of [...fns]) guard(() => fn(valueOf(name), name));
    }
  };
  const flush = () => {
    if (flushing) return;
    flushing = true;
    try {
      for (let turns = 0; dirty.size && turns < 100; turns++) {
        const names = new Set(dirty);
        dirty.clear();
        for (const name of recompute()) names.add(name);
        render(names);
      }
    } finally { flushing = false; dirty.clear(); }
  };
  const set = (name, value) => {
    if (typeof name !== 'string' || !own(types, name)) return;
    const next = coerce(types[name], value);
    if (vals[name] === next) return;
    vals[name] = next;
    dirty.add(name);
    flush();
  };
  const get = name => (typeof name === 'string' ? valueOf(name) : undefined);
  const subscribe = (name, fn) => {
    if (typeof fn !== 'function') return () => {};
    let fns = subs.get(name);
    if (!fns) subs.set(name, (fns = new Set()));
    fns.add(fn);
    return () => { fns.delete(fn); };
  };
  globalThis.__formwebVariables = Object.freeze({ get, set, subscribe });

  const cache = new Map();
  (globalThis.__formwebActions ||= {})['set-variable'] = step => {
    if (!step || typeof step !== 'object') return;
    const name = step.variable;
    if (typeof name !== 'string' || !own(types, name)) return;
    if (step.value !== undefined) { set(name, step.value); return; }
    if (typeof step.formula !== 'string') return;
    if (!cache.has(step.formula)) cache.set(step.formula, compile(step.formula));
    const tree = cache.get(step.formula);
    if (tree) set(name, evaluate(tree));
  };

  const read = el => {
    if (el.type === 'checkbox') return el.checked;
    if (el.type === 'radio') return el.checked ? el.value : undefined;
    return el.value;
  };
  const textNode = el => {
    const walker = doc.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    const first = walker.nextNode();
    if (first) return first;
    const created = doc.createTextNode('');
    el.appendChild(created);
    return created;
  };

  ready(() => {
    for (const [id, o] of entries(spec.inputs)) {
      if (!o || typeof o.variable !== 'string' || !own(types, o.variable)) continue;
      const name = o.variable, event = o.event === 'change' ? 'change' : 'input';
      for (const el of nodes(id)) guard(() => {
        let list = inputs.get(name);
        if (!list) inputs.set(name, (list = []));
        list.push(el);
        if (el.tagName === 'SELECT') writeInput(el, vals[name]);
        el.addEventListener(event, () => {
          const v = read(el);
          if (v === undefined) return;
          skip = el;
          try { set(name, v); } finally { skip = null; }
        });
      });
    }
    for (const [id, o] of entries(spec.outputs)) {
      if (!o || typeof o.from !== 'string') continue;
      for (const el of nodes(id)) guard(() => {
        const out = { from: o.from, o, node: textNode(el) };
        outputs.push(out);
        paintOutput(out);
      });
    }
    for (const name of cssNames) paintVar(name);
  });
})();
