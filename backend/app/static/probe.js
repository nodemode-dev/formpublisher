(function () {
  'use strict';
  try {
    var W = window;
    if (W.__fpProbe) return;
    W.__fpProbe = 1;
    var own = document.currentScript;
    var params = new URLSearchParams('');
    try {
      params = new URL(own && own.src ? own.src : '', location.href).searchParams;
    } catch (e) {}
    var gen = Number(params.get('gen')) || 0;
    var theme = params.get('theme');
    var motion = params.get('motion');
    var forcedTheme = theme === 'dark' || theme === 'light' ? theme : '';
    var forcedMotion = motion === 'reduce' ? 'reduce' : '';

    var failed = {};
    var doc = Date.now().toString(36) + Math.random().toString(36).slice(2);

    function send(type, data) {
      try {
        if (W.parent === W) return;
        if (type === 'request' && data.ok === false) {
          if (failed[data.url]) return;
          failed[data.url] = 1;
        }
        var m = { source: 'fp-probe', gen: gen, doc: doc, type: type };
        for (var k in data) {
          if (k !== 'source' && k !== 'gen' && k !== 'doc' && k !== 'type') m[k] = data[k];
        }
        W.parent.postMessage(m, '*');
      } catch (e) {}
    }

    function path() {
      return location.pathname + location.search + location.hash;
    }

    function text(v) {
      try {
        if (typeof v === 'string') return v;
        if (v instanceof Error) return v.stack || v.message || String(v);
        if (v && typeof v === 'object') return JSON.stringify(v);
        return String(v);
      } catch (e) {
        return Object.prototype.toString.call(v);
      }
    }

    function ownUrl(u) {
      return typeof u === 'string' && u.indexOf('/__fp/') !== -1;
    }

    if (forcedTheme || forcedMotion) {
      try {
        var realMatch = W.matchMedia;
        var yes = '(min-width: 0px)';
        var no = '(max-width: -1px)';
        W.matchMedia = function matchMedia(q) {
          var source = String(q);
          var rewritten = source;
          if (forcedTheme) {
            rewritten = rewritten.replace(/\(\s*prefers-color-scheme\s*:\s*(dark|light)\s*\)/gi, function (all, v) {
              return v.toLowerCase() === forcedTheme ? yes : no;
            });
          }
          if (forcedMotion) {
            rewritten = rewritten.replace(/\(\s*prefers-reduced-motion\s*:\s*(reduce|no-preference)\s*\)/gi, function (all, v) {
              return v.toLowerCase() === forcedMotion ? yes : no;
            });
          }
          var list = realMatch.call(W, rewritten);
          if (rewritten !== source) {
            try {
              Object.defineProperty(list, 'media', { value: source, configurable: true });
            } catch (e) {}
          }
          return list;
        };
      } catch (e) {}
    }

    if (forcedTheme) {
      try {
        var realGet = Storage.prototype.getItem;
        Storage.prototype.getItem = function getItem(key) {
          if (typeof key === 'string' && key.indexOf('fw-theme-') === 0) return forcedTheme;
          return realGet.apply(this, arguments);
        };
      } catch (e) {}
    }

    ['error', 'warn'].forEach(function (level) {
      try {
        var real = console[level];
        console[level] = function () {
          try {
            var parts = [];
            for (var i = 0; i < arguments.length; i++) parts.push(text(arguments[i]));
            send('console', { level: level, text: parts.join(' ').slice(0, 2000) });
          } catch (e) {}
          return real.apply(this, arguments);
        };
      } catch (e) {}
    });

    var ELEMENTS = { IMG: 1, SCRIPT: 1, LINK: 1, VIDEO: 1, AUDIO: 1, SOURCE: 1 };

    W.addEventListener(
      'error',
      function (event) {
        try {
          var t = event.target;
          if (t && t !== W && t.nodeType === 1) {
            if (ELEMENTS[t.tagName]) {
              var url = t.currentSrc || t.src || t.href || '';
              if (!ownUrl(url)) {
                send('request', { url: url, kind: t.tagName.toLowerCase(), status: 0, ok: false, ms: 0, bytes: 0 });
              }
            }
            return;
          }
          send('error', {
            message: String(event.message || (event.error && event.error.message) || 'Error'),
            file: event.filename || '',
            line: event.lineno || 0,
            col: event.colno || 0
          });
        } catch (e) {}
      },
      true
    );

    W.addEventListener('unhandledrejection', function (event) {
      try {
        var r = event.reason;
        send('error', {
          message: 'Unhandled rejection: ' + (r && r.message ? r.message : text(r)),
          file: '',
          line: 0,
          col: 0
        });
      } catch (e) {}
    });

    try {
      var realFetch = W.fetch;
      if (typeof realFetch === 'function') {
        W.fetch = function fetch(input, init) {
          var started = performance.now();
          var url = '';
          try {
            url = typeof input === 'string' ? input : input && input.url ? input.url : String(input);
          } catch (e) {}
          var result = realFetch.apply(this, arguments);
          try {
            result.then(
              function (res) {
                try {
                  if (ownUrl(url)) return;
                  var len = Number(res.headers.get('content-length')) || 0;
                  send('request', { url: res.url || url, kind: 'fetch', status: res.status, ok: res.status < 400, ms: Math.round(performance.now() - started), bytes: len });
                } catch (e) {}
              },
              function () {
                if (!ownUrl(url)) send('request', { url: url, kind: 'fetch', status: 0, ok: false, ms: Math.round(performance.now() - started), bytes: 0 });
              }
            );
          } catch (e) {}
          return result;
        };
      }
    } catch (e) {}

    try {
      var proto = XMLHttpRequest.prototype;
      var realOpen = proto.open;
      var realSend = proto.send;
      proto.open = function open(method, url) {
        try {
          this.__fpUrl = String(url);
        } catch (e) {}
        return realOpen.apply(this, arguments);
      };
      proto.send = function send_() {
        try {
          var xhr = this;
          var started = performance.now();
          xhr.addEventListener('loadend', function () {
            try {
              var url = xhr.responseURL || xhr.__fpUrl || '';
              if (ownUrl(url)) return;
              var len = Number(xhr.getResponseHeader('content-length')) || 0;
              send('request', { url: url, kind: 'xhr', status: xhr.status, ok: xhr.status > 0 && xhr.status < 400, ms: Math.round(performance.now() - started), bytes: len });
            } catch (e) {}
          });
        } catch (e) {}
        return realSend.apply(this, arguments);
      };
    } catch (e) {}

    try {
      new PerformanceObserver(function (list) {
        try {
          list.getEntries().forEach(function (entry) {
            var kind = entry.initiatorType;
            if (kind === 'fetch' || kind === 'xmlhttprequest' || ownUrl(entry.name)) return;
            var status = entry.responseStatus || 0;
            send('request', {
              url: entry.name,
              kind: kind || 'other',
              status: status,
              ok: status === 0 || status < 400,
              ms: Math.round(entry.duration),
              bytes: entry.transferSize || entry.encodedBodySize || 0
            });
          });
        } catch (e) {}
      }).observe({ type: 'resource', buffered: true });
    } catch (e) {}

    var clsValue = 0;
    var clsSent = -1;
    var clsTimer = 0;
    var clsLast = 0;
    var clsQuiet = 0;
    var clsQuietMax = 0;
    var clsPaint = -1;
    var clsHeld = [];
    var viewW = W.innerWidth;
    var viewH = W.innerHeight;

    function viewResized() {
      var w = W.innerWidth;
      var h = W.innerHeight;
      if (w === viewW && h === viewH) return;
      viewW = w;
      viewH = h;
      clsQuiet = performance.now() + 500;
      clsQuietMax = clsQuiet + 2500;
    }

    function flushCls() {
      clsTimer = 0;
      try {
        var rounded = Math.round(clsValue * 10000) / 10000;
        if (rounded !== clsSent) {
          clsSent = rounded;
          clsLast = Date.now();
          send('cls', { value: rounded });
        }
      } catch (e) {}
    }

    function armCls() {
      if (!clsTimer) {
        var wait = Math.max(0, 500 - (Date.now() - clsLast));
        clsTimer = setTimeout(flushCls, wait);
      }
    }

    function countShift(entry) {
      if (entry.startTime < clsPaint) return;
      if (entry.startTime < clsQuiet) {
        clsQuiet = Math.min(clsQuietMax, Math.max(clsQuiet, entry.startTime + 500));
        return;
      }
      clsValue += entry.value;
    }

    try {
      new PerformanceObserver(function (list) {
        try {
          viewResized();
          list.getEntries().forEach(function (entry) {
            if (entry.hadRecentInput) return;
            if (clsPaint < 0) {
              if (clsHeld.length < 200) clsHeld.push(entry);
              return;
            }
            countShift(entry);
          });
          armCls();
        } catch (e) {}
      }).observe({ type: 'layout-shift', buffered: true });
      new PerformanceObserver(function (list) {
        try {
          if (clsPaint >= 0) return;
          list.getEntries().forEach(function (entry) {
            if (clsPaint < 0 || entry.startTime < clsPaint) clsPaint = entry.startTime;
          });
          viewResized();
          var held = clsHeld;
          clsHeld = [];
          held.forEach(countShift);
          armCls();
        } catch (e) {}
      }).observe({ type: 'paint', buffered: true });
      document.addEventListener('visibilitychange', function () {
        if (document.visibilityState === 'hidden') flushCls();
      });
    } catch (e) {}

    var lastOverflow = '';
    var overflowTimer = 0;

    function checkOverflow() {
      overflowTimer = 0;
      try {
        var el = document.documentElement;
        if (!el) return;
        var sw = el.scrollWidth;
        var cw = el.clientWidth;
        if (cw <= 0 || W.innerWidth <= 0) return;
        if (sw > cw) {
          var key = sw + ':' + cw;
          if (key !== lastOverflow) {
            lastOverflow = key;
            send('overflow', { scrollWidth: sw, clientWidth: cw });
          }
        } else {
          lastOverflow = '';
        }
      } catch (e) {}
    }

    function queueOverflow() {
      if (overflowTimer) clearTimeout(overflowTimer);
      overflowTimer = setTimeout(checkOverflow, 300);
    }

    function hello() {
      send('hello', { path: path(), title: document.title || '' });
    }

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', hello);
    } else {
      hello();
    }
    if (document.readyState === 'complete') {
      queueOverflow();
    } else {
      W.addEventListener('load', queueOverflow);
    }
    W.addEventListener('resize', function () {
      viewResized();
      queueOverflow();
    });
    W.addEventListener('pageshow', function () {
      send('nav', { path: path() });
    });
    W.addEventListener('popstate', function () {
      send('nav', { path: path() });
    });
    W.addEventListener('hashchange', function () {
      send('nav', { path: path() });
    });
  } catch (e) {}
})();
