(function () {
  'use strict';
  var D = window.FP_DEMO;
  var SITE_DIR = 'sample-site/';
  var $ = function (id) { return document.getElementById(id); };
  var body = document.body;

  function h(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  }

  function icon(path) {
    var s = h('span', 'icon is-sm');
    s.innerHTML = '<svg viewBox="0 0 24 24">' + path + '</svg>';
    return s;
  }

  var ICON_ALERT = '<path d="M12 4l9 15.5H3z"/><path d="M12 10v4.5M12 17.2v.01"/>';
  var ICON_INFO = '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5M12 8v.01"/>';
  var ICON_COPY = '<rect x="8.5" y="8.5" width="11" height="11" rx="2"/><path d="M15.5 8.5v-2a2 2 0 0 0-2-2h-7a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h2"/>';

  function bytes(n) {
    if (n < 1024) return n + ' B';
    if (n < 1048576) return (n / 1024).toFixed(1) + ' KB';
    return (n / 1048576).toFixed(1) + ' MB';
  }

  function plural(n, one, many) { return n + ' ' + (n === 1 ? one : many); }

  var build = D.publish;
  var manifest = build.publish;
  var checks = D.checks;
  var prepared = D.prepared.results;

  /* ---------- theme ---------- */
  function setTheme(light) {
    body.classList.toggle('theme-light', light);
    body.classList.toggle('theme-dark', !light);
  }
  setTheme(!!(window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches));
  $('theme').addEventListener('click', function () { setTheme(!body.classList.contains('theme-light')); });

  /* ---------- preview ---------- */
  var frame = $('frame');
  var box = $('frame-box');
  var stage = $('stage');
  var size = { w: 1440, h: 900 };
  var current = 'index.html';

  function fit() {
    var cw = stage.clientWidth - 32;
    var ch = stage.clientHeight - 32;
    if (cw <= 0 || ch <= 0) return;
    var k = Math.min(1, cw / size.w, ch / size.h);
    frame.style.width = size.w + 'px';
    frame.style.height = size.h + 'px';
    frame.style.transform = 'scale(' + k + ')';
    box.style.width = Math.round(size.w * k) + 'px';
    box.style.height = Math.round(size.h * k) + 'px';
  }
  if (window.ResizeObserver) new ResizeObserver(fit).observe(stage);
  window.addEventListener('resize', fit);

  var devices = $('devices');
  devices.addEventListener('click', function (e) {
    var b = e.target.closest('button');
    if (!b) return;
    Array.prototype.forEach.call(devices.children, function (x) { x.setAttribute('aria-pressed', String(x === b)); });
    size = { w: Number(b.dataset.w), h: Number(b.dataset.h) };
    $('dims').textContent = size.w + ' x ' + size.h;
    fit();
  });

  /* ---------- routes ---------- */
  var routeStatus = {};
  checks.problems.forEach(function (p) {
    var key = String(p.route || p.file || '').replace(/^\//, '');
    var rank = p.severity === 'error' ? 2 : 1;
    if (!routeStatus[key] || routeStatus[key] < rank) routeStatus[key] = rank;
  });

  var routeButtons = {};
  var list = $('routes');
  manifest.routes.forEach(function (r) {
    var b = h('button', 'route');
    b.type = 'button';
    b.setAttribute('role', 'option');
    b.dataset.path = r.path;
    b.appendChild(h('span', 'route-path', r.path));
    b.appendChild(h('span', 'route-meta', r.page));
    var rank = routeStatus[r.path] || 0;
    b.appendChild(h('span', 'dot ' + (rank === 2 ? 'is-error' : rank === 1 ? 'is-warn' : 'is-ok')));
    b.addEventListener('click', function () { go(r.path); });
    list.appendChild(b);
    routeButtons[r.path] = b;
  });
  $('route-count').textContent = String(manifest.routes.length);
  $('st-routes').textContent = plural(manifest.routes.length, 'route', 'routes');

  function go(path) {
    current = path;
    Object.keys(routeButtons).forEach(function (k) { routeButtons[k].setAttribute('aria-selected', String(k === path)); });
    $('route').textContent = '/' + path;
    var target = SITE_DIR + path;
    if (frame.getAttribute('src') !== target) frame.setAttribute('src', target);
  }
  go(current);

  /* ---------- checks ---------- */
  var s = checks.summary;
  $('pill-errors').lastChild.textContent = plural(s.errors, 'error', 'errors');
  $('pill-warnings').lastChild.textContent = plural(s.warnings, 'warning', 'warnings');
  $('pill-ran').lastChild.textContent = 'Static checks, ' + plural(manifest.routes.length, 'route', 'routes');

  var problems = $('problems');
  checks.problems.slice().sort(function (a, b) {
    return (a.severity === 'error' ? 0 : 1) - (b.severity === 'error' ? 0 : 1) || String(a.file).localeCompare(String(b.file));
  }).forEach(function (p) {
    var b = h('button', 'problem is-' + p.severity);
    b.type = 'button';
    b.appendChild(icon(p.severity === 'error' ? ICON_ALERT : ICON_INFO));
    var text = h('span');
    text.appendChild(h('div', 'problem-msg', p.message));
    text.appendChild(h('div', 'problem-fix', p.fix));
    b.appendChild(text);
    b.appendChild(h('span', 'problem-file', p.file + (p.line ? ':' + p.line : '')));
    b.addEventListener('click', function () { var key = String(p.route || p.file).replace(/^\//, ''); if (routeButtons[key]) go(key); });
    problems.appendChild(b);
  });
  if (!checks.problems.length) problems.appendChild(h('div', 'note-line', 'No problems found.'));

  /* ---------- inspector ---------- */
  $('p-name').textContent = manifest.site.name;
  $('p-source').textContent = 'Bundled sample site';
  $('p-routes').textContent = String(manifest.routes.length);
  $('p-size').textContent = bytes(build.size);
  var reds = $('p-redirects');
  manifest.redirects.forEach(function (r) {
    var row = h('div', 'prop');
    row.appendChild(h('span', 'prop-label', String(r.status)));
    row.appendChild(h('span', 'prop-value mono', r.from + ' to ' + r.to));
    reds.appendChild(row);
  });
  var heads = $('p-headers');
  manifest.headers.forEach(function (g) {
    Object.keys(g.values).forEach(function (k) {
      var row = h('div', 'prop');
      row.appendChild(h('span', 'prop-label', g.for));
      row.appendChild(h('span', 'prop-value mono', k + ': ' + g.values[k]));
      heads.appendChild(row);
    });
  });

  /* ---------- dialogs ---------- */
  var openScrim = null;
  var opener = null;

  function openDialog(scrim, from) {
    openScrim = scrim;
    opener = from || null;
    scrim.hidden = false;
    scrim.querySelector('.dialog').focus({ preventScroll: true });
  }

  function closeDialog() {
    if (!openScrim) return;
    openScrim.hidden = true;
    openScrim = null;
    if (opener) opener.focus({ preventScroll: true });
  }

  Array.prototype.forEach.call(document.querySelectorAll('.scrim'), function (scrim) {
    scrim.addEventListener('mousedown', function (e) { if (e.target === scrim) closeDialog(); });
    Array.prototype.forEach.call(scrim.querySelectorAll('[data-close]'), function (b) { b.addEventListener('click', closeDialog); });
  });
  document.addEventListener('keydown', function (e) {
    if (!openScrim) return;
    if (e.key === 'Escape') { e.preventDefault(); closeDialog(); return; }
    if (e.key !== 'Tab') return;
    var items = Array.prototype.filter.call(openScrim.querySelectorAll('button, [tabindex="0"]'), function (x) { return !x.disabled && x.offsetParent !== null; });
    if (!items.length) return;
    var first = items[0];
    var last = items[items.length - 1];
    if (e.shiftKey && (document.activeElement === first || document.activeElement === openScrim.querySelector('.dialog'))) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  });

  /* ---------- package ---------- */
  function kv(pairs) {
    var dl = h('dl', 'kv');
    pairs.forEach(function (p) {
      dl.appendChild(h('dt', '', p[0]));
      var dd = h('dd', p[2] ? 'mono' : '', p[1]);
      dl.appendChild(dd);
    });
    return dl;
  }

  function fileList(rows) {
    var wrap = h('div', 'files');
    rows.forEach(function (f) {
      var r = h('div', 'file');
      r.appendChild(h('span', '', f.path));
      r.appendChild(h('span', '', bytes(f.size)));
      r.appendChild(h('span', '', f.sha256.slice(0, 12)));
      wrap.appendChild(r);
    });
    return wrap;
  }

  function section(title, node) {
    var sec = h('section');
    sec.appendChild(h('div', 'sec-title', title));
    sec.appendChild(node);
    return sec;
  }

  var pb = $('package-body');
  var card = h('div', 'card');
  card.appendChild(kv([
    ['Package', manifest.package.file],
    ['Build', build.id, true],
    ['SHA-256', manifest.package.sha256, true],
    ['Size', bytes(manifest.package.size) + ', ' + plural(manifest.files.length, 'file', 'files')],
    ['Checks', manifest.checks && manifest.checks.tiers && manifest.checks.tiers.length ? plural(manifest.checks.errors, 'error', 'errors') + ', ' + plural(manifest.checks.warnings, 'warning', 'warnings') + ' (' + manifest.checks.tiers.join(', ') + ')' : 'Not run'],
    ['Signed', build.signed ? 'Yes' : 'Not signed yet'],
    ['Built with', manifest.builtWith],
  ]));
  pb.appendChild(section('Build', card));
  pb.appendChild(section('Files (' + manifest.files.length + ')', fileList(manifest.files)));
  $('open-package').addEventListener('click', function (e) { openDialog($('package-scrim'), e.currentTarget); });
  $('package-next').addEventListener('click', function () { closeDialog(); openDialog($('publish-scrim'), $('open-publish')); });
  $('open-publish').addEventListener('click', function (e) { openDialog($('publish-scrim'), e.currentTarget); });

  /* ---------- publish ---------- */
  var order = Object.keys(prepared).sort();
  var picked = order.indexOf('netlify') >= 0 ? 'netlify' : order[0];
  var targets = $('targets');
  var result = $('result');

  function shortFolder(p) {
    var i = p.indexOf('/prepared/');
    return i >= 0 ? 'prepared/' + p.slice(i + '/prepared/'.length) : p;
  }

  function copy(text, btn) {
    var done = function () { var old = btn.textContent; btn.textContent = 'Copied'; window.setTimeout(function () { btn.textContent = old; }, 1200); };
    if (navigator.clipboard && window.isSecureContext) { navigator.clipboard.writeText(text).then(done, done); return; }
    var t = document.createElement('textarea');
    t.value = text;
    t.style.cssText = 'position:fixed;left:-9999px;top:0';
    document.body.appendChild(t);
    t.select();
    try { document.execCommand('copy'); } catch (err) { /* nothing to do offline */ }
    t.remove();
    done();
  }

  function paintResult() {
    var r = prepared[picked];
    result.textContent = '';
    var head = h('div', 'card');
    head.appendChild(kv([['Host', r.name], ['Folder', shortFolder(r.folder), true], ['Files', plural(r.files.length, 'file', 'files')]]));
    head.querySelector('dl').children[3].classList.add('folder');
    result.appendChild(section('Prepared folder', head));
    var cmds = h('div');
    r.commands.forEach(function (c) {
      var row = h('div', 'cmd');
      var t = h('div', 'cmd-text');
      t.appendChild(h('span', 'cmd-label', c.label));
      t.appendChild(document.createTextNode(c.run));
      var b = h('button', 'btn btn-sm', 'Copy');
      b.type = 'button';
      b.appendChild(document.createTextNode(''));
      b.addEventListener('click', function () { copy(c.run, b); });
      row.appendChild(t);
      row.appendChild(b);
      cmds.appendChild(row);
    });
    result.appendChild(section('Commands to run', cmds));
    if (r.notes.length || r.warnings.length) {
      var nw = h('div');
      r.warnings.forEach(function (w) { nw.appendChild(h('div', 'warn-line', w)); nw.lastChild.style.marginBottom = '6px'; });
      r.notes.forEach(function (n) { nw.appendChild(h('div', 'note-line', n)); });
      result.appendChild(section('Notes and warnings', nw));
    }
    result.appendChild(section('Files in the folder (' + r.files.length + ')', fileList(r.files)));
  }

  function paintTargets() {
    Array.prototype.forEach.call(targets.children, function (b) { b.setAttribute('aria-pressed', String(b.dataset.id === picked)); });
  }

  order.forEach(function (id) {
    var r = prepared[id];
    var b = h('button', 'target');
    b.type = 'button';
    b.dataset.id = id;
    b.appendChild(h('b', '', r.name));
    b.appendChild(h('span', '', plural(r.files.length, 'file', 'files') + ', ' + plural(r.commands.length, 'command', 'commands')));
    b.addEventListener('click', function () { picked = id; paintTargets(); paintResult(); });
    targets.appendChild(b);
  });
  paintTargets();
  paintResult();

  fit();
  var reveal = function () { fit(); body.classList.add('ready'); };
  var settle = function () { window.requestAnimationFrame(function () { window.requestAnimationFrame(reveal); }); };
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(settle, settle); else settle();
})();
