# HASHOUT_LOG · backend · formpublisher

The living log of the FormPublisher engine. Read it before editing `backend/`. The code carries no comments; the reasons live here, one entry per file.

Current build version: v0.5.0
Last updated: 2026-11-22 · v0.5.0, Phase 72: the desktop engine is a folder with a log, leaves with its shell, ships deep checks, serves the manual to Help, reports a failed deep run, and installs from hashed locks; v0.4.1, no engine change (the messages of the templates flow are in the 26 languages in the window; see frontend/HASHOUT_LOG.md, Phase 69); v0.4.0, Phase 71: a pytest suite, the vendored core says 0.27.0, templates to start from; v0.3.4, Phase 70: the vendored FormWeb core stays 0.21.2, checked against FormWeb 0.27.0; v0.3.3, Phases 68 and 69: demos update in place, one old FormWeb site is adopted by name, Import lists FormWeb's saved projects, a build with no checks records null, external.request is one warning per URL, the vendored core is 0.21.2; v0.3.2: no engine change (NOTICE.md and demo/MEDIA.md record the offline demo's four copies of the mark as GPL-3.0-only, like every FormPublisher icon, at the owner's decision); Phase 67: the forms.local-address check, one site per FormWeb project on Import, the demo credits and the community files

---

## Org-navi-map

```
backend/
├── formpublisher_engine.py   entry: serve, --selfcheck, --version, cli, mcp
├── requirements.txt          pinned runtime dependencies
├── boot_backend              bash dev launcher (venv, uvicorn --reload)
├── boot_backend.bat          Windows twin
├── HASHOUT_LOG.md            this file
└── app/
    ├── __init__.py           __version__
    ├── main.py               FastAPI app, LocalAccess guard, router auto-include, SPA fallback
    ├── cli.py                Client (HTTP or in-process) and the command line
    ├── mcp.py                MCP server on stdio over the same Client
    ├── host.py               the site host ASGI app on its own port, serve_revision for deep runs
    ├── static/probe.js       the live probe injected into previewed pages only
    ├── routers/
    │   ├── health.py         GET /api/health
    │   ├── settings.py       GET, PUT /api/settings
    │   ├── sites.py          /api/sites, import, routes, delete
    │   ├── live.py           WS /api/live
    │   ├── formweb.py        /api/formweb status, publications, projects, import-current
    │   ├── host.py           /api/host, mount and unmount
    │   ├── checks.py         /api/checks run, results, live, thumbs
    │   ├── builds.py         /api/builds build, reproduce, list, compare, sign, verify, download, delete
    │   ├── demo.py           /api/demo sample and open/<id>, each demo imported once
    │   └── keys.py           /api/keys create, list, public, delete
    └── services/
        ├── paths.py          ports (engine and site host), origins, data folder, frontend dist
        ├── settings.py       settings.json with validated keys
        ├── bus.py            in-process event bus
        ├── intake.py         safe unzip, folder copy, .fweb, site records, routes, redirects
        ├── demo_refresh.py   adds a changed bundled demo as a revision of its site
        ├── formweb.py        read-only FormWeb client
        ├── compile.py        formweb-core JSON-lines session and asset bundling for .fweb
        ├── host.py           static host rules, mount state, throttle, probe injection
        ├── checks.py         the static tier and stored results
        ├── deep.py           the deep tier through the installed Chrome
        ├── package.py        deterministic site.zip, publish.json, build library
        └── keys.py           Ed25519 keys and signatures
```

## Table of contents

1. [formpublisher_engine.py](#formpublisher_enginepy)
2. [requirements.txt](#requirementstxt)
3. [boot_backend and boot_backend.bat](#boot_backend-and-boot_backendbat)
4. [app/__init__.py](#app__init__py)
5. [app/main.py](#appmainpy)
6. [app/cli.py](#appclipy)
7. [app/mcp.py](#appmcppy)
8. [app/routers/health.py](#approutershealthpy)
9. [app/routers/settings.py](#approuterssettingspy)
10. [app/routers/sites.py](#approuterssitespy)
11. [app/routers/live.py](#approuterslivepy)
12. [app/routers/formweb.py](#approutersformwebpy)
13. [app/services/paths.py](#appservicespathspy)
14. [app/services/settings.py](#appservicessettingspy)
15. [app/services/bus.py](#appservicesbuspy)
16. [app/services/intake.py](#appservicesintakepy)
17. [app/services/formweb.py](#appservicesformwebpy)

---

## formpublisher_engine.py

- refers-to: app/main.py, app/cli.py, app/mcp.py
- Serves uvicorn on `127.0.0.1` and `FORMPUBLISHER_PORT` (default 8280). `FORMPUBLISHER_HOST` exists for tests only; the guard still accepts only loopback Host values on the engine port.
- `--selfcheck` imports every module under `app/routers` and `app/services`, `app.cli`, builds the MCP server and imports `app.main`, then prints `OK` and one JSON line. It reports whether a built frontend is present but never fails on its absence, because CI runs it before any frontend build. It fails on a missing dependency or any router import error.
- `cli` and `mcp` are passthroughs to `app.cli.main` and `app.mcp.main`, so the frozen sidecar has one entry for all three faces.
- `watch_parent` exits the engine when the launching process dies (posix only), so a closed desktop shell never leaves an orphan on 8280. `FORMPUBLISHER_WATCH_PARENT=0` turns it off.
- A dist folder named `frontend_dist` beside the frozen binary is picked up through `FORMPUBLISHER_DIST`.

## requirements.txt

- fastapi 0.141.1, uvicorn 0.53.0 and python-multipart 0.0.32 match form.ext.
- mcp 2.3.0 is the official SDK. It depends on `httpx2`, not `httpx`, so plain `httpx` cannot be pinned beside it; the FormWeb client uses `httpx2` 2.16.0, the version pip resolves for mcp 2.3.0.
- No cryptography yet: signing arrives with the package phase, where the Intel macOS pin question from form.ext will be revisited. No macOS-specific requirements file is needed today.

## boot_backend and boot_backend.bat

- Create `backend/venv` with Python 3.12 when missing, install `requirements.txt`, then run uvicorn on `app.main:app`. `FORMPUBLISHER_RELOAD=0` turns off `--reload`; with it on only `app/` is watched, so a new router loads without a restart.

## app/__init__.py

- `__version__` is `0.1.0`; the other version sites are listed in the root log in the planning sidecar.

## app/main.py

- refers-to: app/services/paths.py, app/routers/
- `LocalAccess` is a pure ASGI middleware, modelled on FormWeb's guard, and runs for HTTP and WebSocket scopes. The Host must be exactly `localhost`, `127.0.0.1` or `[::1]` with the engine port, which defeats DNS rebinding (421). An Origin, when present, must be in the allow-list (403); with no Origin, `Sec-Fetch-Site: cross-site` is refused (403), because a browser omits Origin on some cross-site simple requests. Non-browser clients (curl, the CLI, the Tauri shell without a custom Origin) send neither and pass. A Content-Length above 600 MiB is refused up front (413).
- Consequence for the dev server: Vite's `/api` proxy must set `changeOrigin: true` (or rewrite Host) so the engine sees `127.0.0.1:8280`, not `localhost:5280`.
- On WebSocket refusal the middleware closes with code 1008 before accept; the browser sees a failed handshake.
- CORS is the explicit allow-list only (no regex). Origins come from `FORMPUBLISHER_ORIGINS` (comma separated) when set.
- Responses get `X-Content-Type-Options: nosniff` and `Referrer-Policy: no-referrer`.
- Router auto-include imports each `routers/*.py` exporting `router`, core order health, settings, sites, live, then alphabetical. An import failure is recorded in `app.state.router_errors` and shown by `/api/health`, so one bad module never stops the engine; the self check turns it into a failure.
- `IntakeError`, `FormwebError` and plain `ValueError` become `{detail}` JSON with their status (400 for ValueError).
- The SPA fallback resolves the dist folder on every request, so a frontend built after the engine started is served without a restart. Without a dist, non-API paths answer 503 JSON; `/api/*` misses stay 404 JSON. Files under `assets/` are cached immutable, everything else `no-cache`. Paths that resolve outside the dist root fall back to `index.html`.

## app/cli.py

- refers-to: app/services/intake.py, app/services/formweb.py
- `Client` probes `http://127.0.0.1:<port>/api/health` for 1.5 s and only accepts an answer whose `app` is `formpublisher`; otherwise it runs the same service functions in-process. `--engine URL` or `FORMPUBLISHER_URL` forces HTTP and fails with exit code 3 if nothing answers; `--in-process` never calls out. HTTP mode ignores proxy environment variables.
- Paths are made absolute on the client side before being sent, because the engine's working directory differs.
- In-process runs share the data folder with the engine, but the bus has no loop there, so a window already open sees the change only on its next list. That is accepted: the CLI prints which mode it used.
- Exit codes: 0 ok, 1 refused or invalid, 3 engine unreachable or failing.

## app/mcp.py

- Uses the official SDK (`MCPServer`, stdio). Tools: `formpublisher_status`, `list_sites`, `import_site` (path), `import_formweb_current`, `site_routes` (id). Each has an explicit description and read-only or non-destructive annotations; the JSON schema comes from the type hints.
- Every tool calls the same `Client` as the CLI, in a worker thread so the blocking urllib or file work never stalls the stdio loop. Failures are raised as `ToolError` so the agent gets the real message and `isError`, not a generic one.
- No tool deletes or writes settings: removing a site stays a person's action in the window.

## app/routers/health.py

- Answers `{ok, app: "formpublisher", version, api: "1", home, frozen}` plus `routers`, `routerErrors`, `liveClients` and `frontend` (bool). Clients identify the engine by `app`, which is how the CLI avoids talking to another Form app on a reused port.

## app/routers/settings.py

- GET returns the merged settings plus `home`. PUT merges a partial object; `home` is read-only and dropped. A `null` value resets a key to its default.

## app/routers/sites.py

- `POST /api/sites/import` takes either `multipart/form-data` (the first file part is the zip; optional `name`) or JSON `{path, name?}` where path is an absolute zip or folder. Anything else is 415. Intake work runs in a thread pool so imports never block the event loop.
- Uploads are streamed to a temp file with the 512 MiB cap enforced again, then removed in a `finally`.
- `GET /api/sites/{id}/routes?revision=` reads the latest revision unless one is named. `DELETE` moves to `trash/`, never deletes.

## app/routers/live.py

- Sends `{type: "hello", app, version}` on connect, then every bus event as `{type, ..., at}`: `site.imported`, `site.removed`, `settings.changed`. Text `ping` answers `{type: "pong"}`. The loop is attached to the bus on connect as well as at startup, so events emitted from worker threads reach the socket.

## app/routers/formweb.py

- `GET /api/formweb/status` never raises: unreachable FormWeb is `{reachable: false, error}` with HTTP 200 so the UI can show a state, not a failure. `publications` and `import-current` answer 502 when FormWeb is down.
- Only GET routes of FormWeb are ever called. `POST /api/load` and every mutating route are off limits by design (AD6).

## app/services/paths.py

- Data folder: `FORMPUBLISHER_HOME`, else `~/FormPublisher`, with `sites/`, `builds/`, `keys/`, `prepared/`, `trash/` and `settings.json`. Created lazily and at startup.
- Default origins: 5280 (dev UI), 5281 (preview), 8280 (engine) on `localhost` and `127.0.0.1`, plus `tauri://localhost` and `http://tauri.localhost`.
- Frontend dist order: `FORMPUBLISHER_DIST`, `frontend_dist` beside the frozen binary, `../frontend/dist`; the folder counts only if it holds `index.html`.

## app/services/settings.py

- Only `theme`, `language`, `density` and `formwebUrl` are stored; unknown keys are rejected with 400 so typos surface. `formwebUrl` must be an http(s) loopback URL, which stops a page that reaches the settings route from steering the engine at an arbitrary host (SSRF). Its default is `FORMPUBLISHER_FORMWEB_URL`, else `http://127.0.0.1:8240`. Writes are atomic (temp file then rename) and emit `settings.changed`.

## app/services/bus.py

- Thread-safe fan-out to per-client bounded queues; a full queue drops the event instead of blocking the emitter. `emit` posts to the server loop with `call_soon_threadsafe` when called from another thread, and is a silent no-op before a loop is attached (CLI in-process).

## app/services/intake.py

- refers-to: AD2, AD6
- Site id is the slug of the name (from `site.formweb.json` `name`, `site.name`, `title`, else the zip or folder name) plus six hex of SHA-1 over name and a source key (`zip:<path>`, `folder:<path>`, `upload:<filename>`, `formweb:<url>`). The same source imported again keeps its id and gains a revision; two different sources with the same name stay separate.
- Revision is a UTC timestamp `YYYYMMDDTHHMMSSZ`, with `-2`, `-3` on a same-second collision. Layout is `sites/<id>/<revision>/` with `sites/<id>/site.json`.
- `site.json`: `id, name, source{kind: zip|folder|formweb, path|url, upload?}, revisions[] (strings, oldest first), revision (latest), routes (count), bytes, files, skipped (symlinks left out of a folder copy), redirects{present,count,byStatus,external,invalid,loops}, sitemap, robots, createdAt, importedAt`. The numbers describe the latest revision.
- Safe unzip: each name is normalised (backslashes to slashes) and refused when absolute, drive-lettered, NUL-bearing or containing `..`; symlink entries, encrypted entries and case-insensitive duplicates are refused; at most 20,000 files (40,000 entries), 1 GiB declared and 1 GiB actually written (the declared size can lie), 512 MiB compressed. `__MACOSX/` is skipped. Everything extracts into a hidden `.staging-*` folder first and is moved into place with one rename, so a refused archive leaves nothing behind. The resolved target is checked against the staging root as a second line of defence.
- A zip or folder wrapped in a single top-level directory is unwrapped when the top level has no `routes.json`, `index.html` or `site.formweb.json`.
- Folder import copies, never links, skips `.git` and symlinks, and applies the same count and size caps. A source with neither `routes.json` nor any `index.html` is refused as not a site.
- Routes: `routes.json` (an array, or an object with `routes`) is normalised to `{path,page,locale,item,stylesheet}`; when absent or unreadable the tree is walked for `index.html` (hidden folders skipped), giving `/` and `/dir/`. The result says which source it used.
- Redirects follow FormWeb's own reader: a list, `{redirects: [...]}`, or a from-to map; `from|source`, `to|target`, status in 301, 302, 307, 308. Rows that do not fit count as invalid. `loops` counts start points that enter a cycle (a two-way loop reports 2).
- Ids are validated against `^[a-z0-9][a-z0-9-]{0,100}$` before touching disk, so an id can never carry a path. Imports and removal share a lock. Removal moves the whole site folder into `trash/<id>-<timestamp>`.

## app/services/formweb.py

- Uses `httpx2` with `trust_env=False` (no proxy variables for a loopback call) and no redirect following. Probe timeout 2 s; reads 120 s.
- The export is streamed to a temp file with the 512 MiB cap, imported as `source.kind = formweb` with the URL, and deleted afterwards.
- FormWeb's optional `FORMWEB_AUTH_TOKEN` is not sent: FormPublisher has no token setting yet. A token-protected FormWeb will answer 401, which surfaces as a 502 here. Revisit with the FormWeb settings pane.

## Phases 4 to 6 · v0.1.1 (2026-11-10)

The executor spec is `TURN_B_SPEC.md` in the 0.1.1 planning sidecar.

### app/host.py, app/services/host.py, app/routers/host.py

- The site host is its own ASGI app on `FORMPUBLISHER_HOST_PORT` (8281), started by the engine's lifespan as a second `uvicorn.Server` task. `capture_signals` is overridden as a no-op, because a second server in the same loop would replace the engine's SIGINT handler. A port already in use logs an error and the engine keeps running.
- Host guard: exact `127.0.0.1:<port>` or `localhost:<port>` (421), GET and HEAD only (405), websockets closed with 1008. The engine's origin allow-list does not contain the host origin, so a page on the host cannot call `/api/*`.
- Rules: one percent-decode; NUL, backslash and `..` give 400; symlinks resolving outside the revision give 404; lookup `a/b`, `a/b/index.html`, `a/b.html`; `redirects.json` parsed locally (intake only returns a summary), exact matches before splats, 3xx keep the query, 200 rewrites; `404.html` with status 404; single ranges only (multiple or malformed ranges serve the whole file); `no-store`, `nosniff` and `strict-origin-when-cross-origin` on every response.
- `probe` defaults to false; the preview sends `probe: true`. Injection goes right after `<head ...>`, else after `<html ...>`, else after the doctype, else after a BOM, else at byte 0, never before the doctype (quirks mode). Ranges on injected HTML use the injected bytes. `/__fp/` is reserved; `/__fp/probe.js` is read from `app/static/probe.js` two levels above `services/host.py`, so the frozen engine needs `app/static` as data (`setup/freeze_backend` adds it).
- Throttle waits the latency before the first byte, then paces 16 KiB chunks to the bandwidth; the probe and the 421 and 405 replies are never throttled.
- `serve_revision(root)` pre-binds `127.0.0.1:0` so the Host guard knows the port before startup, and serves one folder with no probe and no throttle.

### app/static/probe.js

- One IIFE under 12 KiB that never throws into the page; every wrapper (console, fetch, XHR, matchMedia, `Storage.getItem`) calls through. Forced `matchMedia` answers are real MediaQueryLists built from always-true or always-false queries, so listeners work. Only JS `matchMedia` is forced: CSS `@media (prefers-color-scheme)` rules follow the browser, which the manual notes.
- In `error` messages the envelope keeps `source: 'fp-probe'` and the script URL travels as `file`.

### app/services/checks.py, app/routers/checks.py

- Standard library only; HTML through `html.parser`; the sitemap read with a regex rather than an XML parser, to avoid entity expansion on untrusted files. Paths resolve as the host resolves them. Ids are `static:<code>:<route>:<line or key>`, stable between runs.
- A site with no `sitemap.xml` gets one `sitemap.missing` warning on `/`. `img.size` skips `img[data-fw-poster]`, whose box comes from its component host. Own hosts for `external.request` are the canonical link hosts, the sitemap hosts and loopback.
- Results live in `checks/<site>/<revision>/results.json` as one block per tier (`static`, `deep`); live problems stay in memory, at most 1,000 per revision, tier forced to `live`. One run per site at a time (409 otherwise). The summary's `tiers` is a count per tier and `ran` lists the tiers with results.
- `checks.chromePath` is a settings key (an absolute path up to 1,024 characters).

### app/services/deep.py

- Playwright is imported inside the run, so `--selfcheck` passes without it. Chrome comes from `checks.chromePath`, then `channel="chrome"`, then the known install paths; never `playwright install`. Missing pieces give one `deep.unavailable` info problem.
- It serves the revision with its own threaded `http.server` on `127.0.0.1:0`, reusing `checks.SiteIndex` rules, because `serve_revision` landed after it; switching is a later cleanup.
- CDP CPU and network throttling are applied per page session after `Network.enable`. Scroll is 8 steps down, then one jump to the top. Thumbnails come from a separate unthrottled context with `device_scale_factor` 320/1440, so Chrome renders 320 by 200 directly with no image library. `ERR_ABORTED` failures and the generic "Failed to load resource" console line are ignored as duplicates of `deep.request`.

### app/services/package.py, app/routers/builds.py

- `site.zip` is streamed through `ZipFile.open(info, "w")` with `force_zip64=False`; intake caps trees at 1 GiB, which stays under the zip64 threshold. Names starting with `.fp`, symlinks and non-files are left out.
- `build.json` is the only file with a time in it. A rebuild of identical bytes returns the existing build with `created: false` and writes nothing, so a build's `publish.json` reflects the checks stored when it was first built.
- Source kinds map to `formweb-export` (zip uploads and FormWeb pulls), `folder` and `fweb`; `formwebVersion` comes from `site.formweb.json`, else the engine version an `.fweb` import recorded.
- The check summary counts the stored static and deep problems only; live problems are left out so the manifest stays deterministic.
- Build ids are looked up across sites by scanning `builds/*/<id>`.

### app/services/keys.py, app/routers/keys.py

- Ed25519 through `cryptography`; PKCS8 PEM written `0600`; `BestAvailableEncryption` when a passphrase is given. Any failure to load the key with the given passphrase maps to "The passphrase does not unlock this key."; a locked key with no passphrase answers "This key needs a passphrase."; a passphrase sent for an unencrypted key is ignored.
- Verify checks the fingerprint against the stored public key first, then the signature over the current zip bytes.

### app/services/compile.py, intake changes

- `formweb-core` is found at `FORMPUBLISHER_FORMWEB_CORE`, then `backend/bin/formweb-core`, then the frozen resource folder. Each request has a 120 s timer that kills the child, which unblocks `readline`; the child is closed, terminated and killed on every path.
- `compile.py` raises its own `CompileError`, converted by intake, because intake imports it and the reverse import would be circular. Only the envelope's `site` is loaded; the checkpoint is ignored. `baseUrl` is the site's own or `https://example.com`, as the core would pick.
- The FormWeb `bundle_assets` rules are ported: `/api/assets/<sha>.<ext>` becomes `assets/<file>` with the right `../` depth, `asset-access.json` is rebuilt last, `CREDITS.txt` is written when assets carry licences (without the Lucide text, which is not vendored). An image the project references but the file does not carry fails the import.
- `.fweb` detection reads the first 4 KB for the `format` field; the extension is the main signal. Upload source keys are `fweb-upload:<label>`, so an upload never shares an id with a zip of the same name.

## Phases 7 to 9 · v0.1.2 (2026-11-10)

The executor spec is `TURN_C_SPEC.md` in the 0.1.2 planning sidecar.

### app/targets/*.py, app/services/publish.py, app/routers/publish.py

- Adapters are discovered from `targets/*.py`; modules starting with `_` are helpers. `_common.py` holds `PreparedInput`, `PreparedResult` and the shared redirect, header and 404 helpers. Adapters write only `commands`, `notes` and `warnings`; the service fills `files` by walking the folder, so a folder is byte-identical across prepares and carries no timestamps.
- Prepared metadata lives beside the folders as `prepared/<site>/<build>/.<target>.json`; dot names are skipped when listing. Delete moves the folder to `trash/prepared-<site>-<build>-<target>-<stamp>`.
- A FormWeb page at `/404` exports as `404/index.html`; `has_404` accepts it and `copy_site` also writes it as the root `404.html` every host looks for. Its relative asset paths resolve correctly at `/404.html`; on hosts that serve that file for a deep unknown path, relative paths are the site's own concern.
- Verify compares every `site/` file with `publish.json` and every file with a fresh prepare in a temporary folder, reporting `missing`, `hash differs from publish.json`, `extra file` or `differs from a fresh prepare`.
- nginx: `root /usr/share/nginx/html`, `try_files $uri $uri/ $uri.html =404`, a relative `include` in `nginx-test.conf` that resolves against the `-c` file's folder. Not run here (no nginx); read only.

### app/services/inbox.py, app/routers/receive.py, main.py lifespan

- Router `on_startup` hooks do not run under a custom lifespan, so `main.py` starts and stops the inbox watcher inside `lifespan`. It polls every 5 s and imports a file only after it has stayed unchanged for 2 s; results move to `inbox/imported/` or `inbox/failed/` with a `.txt` reason. The last five receipts are kept in memory.
- `POST /api/receive/formweb` takes the raw zip body; `LocalAccess` refuses foreign origins and the handler refuses non-loopback clients. The site id is hashed from the site name and source key, so FormWeb must send a stable `X-FormWeb-Site-Name` for re-sends to land as revisions of one site.

### app/services/package.py, app/services/paths.py

- Build ids are the first 12 hex digits of SHA-256 over `<site id>:<zip sha256>`, so the same export imported as two sites gets two builds (the old id, the zip hash alone, let `/api/publish/{build}` answer for the wrong site). `publish.json` still records the zip's own hash.
- `origins()` adds the engine's own origin on whatever port it runs when `FORMPUBLISHER_ORIGINS` is unset, because the engine serves the built window itself.

### app/routers/demo.py, app/cli.py, app/mcp.py

- `POST /api/demo/sample` imports `resource_dir()/demo/sample-site.zip` once under a lock, matched by `source.kind` `demo` and a fixed key, and returns `{site, created}`; the frozen engine carries the zip.
- CLI and MCP call the same services in-process when no engine answers. `sign` without `--key` uses the only key and refuses when there are none or several. Over HTTP a deep check polls `GET /api/checks/{site}/{revision}` until `running` clears, capped at 15 minutes. Key creation is CLI-only (`keys --create`); MCP has 14 tools with `readOnlyHint` on the eight that only read.

Checked: `formpublisher_engine.py --selfcheck` lists every router with no errors; one build prepared for all six targets twice gave identical folders; receive, inbox, verify, delete, the MCP stdio walk and every CLI command were run as the spec's exits ask.

## Phases 10 to 12 · v0.1.3 (2026-11-10)

The executor spec is `TURN_D_SPEC.md` in the 0.1.3 planning sidecar. The vendored FormWeb crates are 0.19.3 (`vendor/formweb-native/VENDOR.md`).

### formpublisher_engine.py, setup/freeze_backend

- `--selfcheck` now also reports whether the built window, the demo sample and `formweb-core` were found, so a frozen engine missing any of them fails before it is copied into `src-tauri/binaries`. `freeze_backend` bundles `formweb-core` and `demo/sample-site.zip`, and collects the `mcp` package's data without its `cli` module, which pulls in a terminal stack the engine never uses. The frozen engine is about 87 MB on Linux.

### app/services/publish.py, app/targets/_common.py, app/routers/publish.py

- Prepared `site/` folders leave out `site.formweb.json` and `asset-access.json` (FormWeb's model files) unless `includeModel` is true. The choice is stored in the prepared metadata, so verify skips the files that were left out on purpose and names them instead of reporting them missing; every result carries `leftOut`. `site.zip` and `publish.json` still list every file, because they describe the build, not a host folder. Owner question 18, taken with its default.

### app/services/pipeline.py, app/services/settings.py

- Two settings, `receive.autoCheck` and `receive.autoBuild`, both off by default. `after_receive` returns at once when both are off; otherwise it starts one daemon thread that runs the static checks and then a build under a module lock, emitting the same `checks.done` event as the manual action (with `auto: true`) and then `receive.pipeline` with what ran or the error. The receive answers before the thread does any work (24 ms measured with both on). A failure is logged and reported in the event; it never undoes the import.

### app/services/inbox.py

- FormWeb writes `<zip>.json` beside an inbox zip with `siteName`, `project` and `version` (strings, trimmed, 200 characters at most). With it, the zip is imported under the same site id a live send would use, so it becomes a revision of that site rather than a new site; without it, the old file-name behaviour stands. The metadata file moves to `imported/` or `failed/` with its zip. `announce`, which both the receive route and the watcher go through, starts `pipeline.after_receive`.

### app/services/revisions.py, app/routers/sites.py, app/cli.py, app/mcp.py

- `GET /api/sites/{id}/revisions` lists revisions newest first with file count, bytes, route count and the files added, removed and changed from the revision before. `GET /api/sites/{id}/diff?from=&to=` compares two revisions by path, size and SHA-256 and lists added and removed routes; without `to` it takes the latest, without `from` the revision before `to`. Revision times come from the revision id's stamp. CLI `revisions` and `diff` and MCP `list_revisions` and `diff_revisions` (both read-only, 16 tools in all) call the same functions in-process or over HTTP. `prepare` gains `--include-model` and `includeModel`.

Checked: two receives of one project gave one site with two revisions; with the settings off no checks or builds ran, with them on the check and build followed the 24 ms answer; diffs read the same through the route, the CLI in-process, HTTP and MCP; an inbox zip with metadata became the fourth revision of the same site; all six targets prepared with `includeModel` false, true and omitted verified clean, with two fewer files per site folder by default; the frozen engine selfchecked, served the window and imported the demo.

## Phases 13 to 15 · v0.1.4 (2026-11-10)

The executor spec is `TURN_E_SPEC.md` in the 0.1.4 planning sidecar. The vendored FormWeb crates are 0.19.4.

### app/services/trash.py, app/routers/trash.py, the remove functions in intake.py, keys.py, publish.py and package.py

- `trash.move(path, kind, label, origin, payload=None)` is the only way into `trash/`; callers keep their entry names and return shapes and no longer move folders themselves. It writes `<entry>.trash.json` (kind, label, origin relative to the data folder, moved, size). A key is a file, so its entry is a folder holding the `.pem` and `entry.json` (the key's row, passed as payload); a prepared folder's hidden `.<target>.json` is removed by the move, so it is kept in the metadata as `payload` and written back on restore, which verify needs.
- `GET /api/trash` lists entries newest first, skipping metadata files and dot names. Entries from before 0.1.4 have no metadata: kind comes from the `build-`, `key-` or `prepared-` prefix (else site) and origin is null, so they list but answer 409 on restore.
- An entry name is only accepted if it is in the folder listing, never joined from input. Restore resolves the origin inside the data folder and requires it to sit under the kind's own folder (`sites`, `builds`, `keys`, `prepared`), so a damaged metadata file cannot send an entry elsewhere; a taken place, an existing key id or a damaged key record answer 409 with the reason. Restore emits the event the matching create emits (`site.imported`, `builds.created`, `keys.created`, `publish.prepared`, each with `restored: true`) so Home and the builds library refresh, and every move, restore, delete and empty emits `trash.changed`.
- CLI `trash`, `trash restore`, `trash delete`, `trash empty --yes` (refused without `--yes`), in-process or over HTTP like every command. MCP adds `list_trash` (read-only) and `restore_from_trash`; deleting stays out of MCP, so a person decides what is gone for good. 18 tools.

### app/services/paths.py, app/main.py lifespan

- `engine.json` in the data folder is the discovery file for FormWeb: `{app, port, pid, version, started}`, written through `engine.json.<pid>.tmp` and `os.replace`. The lifespan writes it after the site host and the inbox watcher are up, so a reader never finds an engine that is not ready, and removes it first on shutdown, only if it still names this pid, so a second engine that took over the folder keeps its file. `GET /api/health` already answers `app: formpublisher`, which FormWeb checks before sending.

### app/services/deep.py

- The deep run serves the revision through `host.serve_revision`, so deep checks see the site host's lookup, redirect and 404 rules instead of a second server's. Playwright's sync API runs on a threadpool worker, so `LocalServer` schedules `serve_revision` and its stop on the engine loop with `asyncio.run_coroutine_threadsafe` (the lifespan hands the loop over with `deep.attach`); without an attached loop (the in-process CLI) it runs a private loop on a daemon thread. The old `ThreadingHTTPServer` handler and MIME table are gone.

### app/services/compile.py, intake.is_fweb

- FormWeb's version 2 `.fweb` is a zip with `project.json` first and `assets/<id>` stored; FormWeb writes it only when version 1 would pass 64 MiB. It is checked up front with FormWeb's own rules (project.json first and at most 64 MiB, format and version 2, a site object, at most 500 assets listed once, every member exactly `assets/<listed id>`, digest, mime, and FormWeb's per-type sizes: 8 MiB images, 64 MiB mp4 and webm, 4 MiB woff2, 2 MiB svg, enforced while streaming), capped at 512 MiB, then each asset is copied from the zip into the build folder in 1 MiB chunks and hashed again on the way, so a large project never sits in memory. `looks_like_fweb` accepts a zip only when its first member is a version 2 `project.json`, so `is_fweb` now asks it for any file and ordinary site zips are unaffected. Version 1 keeps its 128 MiB file cap and no per-type sizes.

Checked: on lab engines a removed site, build, key and prepared folder were listed and restored and worked again; 409, 404, delete and empty answered as above; the CLI matched in-process and over HTTP and the MCP stdio walk listed and restored. Two engines each named their own port and pid in `engine.json` and SIGTERM removed only its own. A static and deep run on the demo gave the same problems, summary and thumbnails before and after the host switch. A version 1 project and its version 2 twin built with identical file lists and hashes, and bad archives were refused with their reasons. With this engine on port 8402, FormWeb 0.19.4 found it through `engine.json` and delivered live.

## Phases 16 to 18 · v0.1.5 (2026-11-10)

The executor spec is `TURN_F_SPEC.md` in the 0.1.5 planning sidecar. The vendored FormWeb crates are 0.19.5.

### app/services/trash.py, app/routers/trash.py, app/cli.py, app/mcp.py

- Entries without a `.trash.json` (moved by 0.1.3 and earlier) get an inferred origin, and listing marks those rows `originInferred`. Kind: a folder holding `site.json` is a site, otherwise the `build-`, `key-` or `prepared-` prefix, else site. The stamp (`-%Y%m%dT%H%M%SZ`, optionally `-N`) is stripped from the end. A site's origin is `sites/<id>` from its `site.json`; a key's is `keys/<id>.pem` from its `entry.json`; a build's is `builds/<site>/<id>` from `build-<site>-<12 hex>`; a prepared folder's is `prepared/<site>/<build>/<target>`, matching the registered target ids longest first as a suffix (they contain hyphens) and anchoring on the 12-hex build id. Anything else has no origin.
- An old prepared entry lost its hidden `.<target>.json` when 0.1.3 moved it, so restore prepares the same target again from its build with `publish.prepare` (prepared folders are deterministic) and deletes the entry, answering 409 naming the build when it is missing or belongs to another site. It runs outside the trash lock because `publish.remove` takes the publish lock and then the trash lock, and the opposite order would invert them.
- `POST /api/trash/{entry}/restore` takes an optional `{origin}`, used only when none is recorded or inferred. It must be relative, resolve inside the kind's own folder (a key directly in `keys/`, a prepared origin as `prepared/<site>/<12 hex>/<target>`, which re-prepares) and be free. Without a usable origin the answer is 409 `{code: "origin-unknown"}`; a bad or taken origin is 409; a non-object body or non-text origin is 400. The `code` field exists only on this route, because the shared `IntakeError` handler answers `{detail}`. CLI `trash restore ENTRY [--to PATH]`. MCP `restore_from_trash` takes no origin, so agents can restore only to recorded or inferred places.

### app/services/deep.py

- `Collector.add` hashed the failing URL including the revision host's random port into the problem id, so the same problem got a new id on every run (with the 0.1.3 server too). The hash now covers the URL with the host replaced by `host`; messages and `url` fields keep the real address.

Checked: on a lab data folder, a site, build, key and two prepared folders (one with a `-2` counter) trashed the 0.1.3 way listed with inferred origins and restored (the site's revisions, a 27-file download, a valid signature, verify on both targets; re-prepared folders hashed identically to the originals); a prepared entry whose build was in the trash answered 409 naming it and restored after the build; unparseable entries answered `origin-unknown` and refused `../`, absolute, wrong-kind and taken origins before restoring to a valid one; CLI `--to` in-process and over HTTP. A FormWeb site with a missing image, an external image, overflow at 390, a code section that logs an error and throws, and two late images without dimensions gave the same 18 problems (8 errors, 10 warnings) on FormPublisher 0.1.3 and this branch at 1440 and 390, with the same codes, routes, severities and messages; the only differences were the request ids (the bug above; two more runs after the fix gave identical ids) and the thumbnail of the page whose external image loads with varying timing. Evidence was kept under `/tmp/p3-deep/` during the turn.

## Phases 19 to 21 · v0.1.6 (2026-11-10)

The executor spec is `TURN_G_SPEC.md` in the 0.1.6 planning sidecar. The vendored FormWeb crates are 0.19.6.

- `services/codes.py` (new): `STATUS_CODES` and `default_code(status)`, the code an error answer carries when none is named: invalid 400 (also 405, 421 and validation 422s), unauthorized 401, forbidden 403, not-found 404, conflict 409, too-large 413, unsupported 415, unprocessable 422, internal 500, upstream 502, unavailable 503, timeout 504. Clients key on codes, never on detail text, so detail can be reworded without breaking them.
- `IntakeError`, `FormwebError` and `CompileError` take an optional `code` that defaults through `default_code`; `OriginUnknown` keeps its class attribute so `origin-unknown` is unchanged. The `_error` helpers in `keys`, `package`, `publish` and `trash` take a third `code` argument. Specific codes sit where a client can act: not-a-site, path-missing, site-missing, revision-missing, build-missing, key-missing, trash-missing, prepared-missing, target-unknown, build-damaged, core-missing, passphrase-required, passphrase-wrong, check-running, formweb-unreachable, formweb-refused, origin-unknown, place-invalid, place-taken, entry-damaged; the CLI adds engine-unreachable.
- `main.py`: the IntakeError, FormwebError, CompileError and ValueError handlers answer `{detail, code}`; new handlers turn Starlette's HTTPException into the status default, FastAPI validation errors into 422 `invalid` with a readable `field: message` detail, and any unhandled exception into 500 `internal` with the traceback in the log. `LocalAccess` refusals (421, 403, 413), the unknown `/api` path and the missing-frontend 503 carry codes too. `routers/trash.py` answers `{code, detail, message}` for every restore refusal (`message` kept for 0.1.5 clients); `routers/formweb.py` and `routers/receive.py` add `code` to their own answers.
- `cli.py`: `OpError` carries `error_code` and `label()`; failures print `error [code]: detail` to stderr, passing an engine answer's code through (exit 1), or `engine-unreachable` (exit 3). `mcp.py`: tool errors use the same label.
- `services/trash.py`: an origin given on restore must also have its kind's shape (`_shape_ok`: site id; `<16 hex>.pem`; `<site>/<12 hex>`; `<site>/<12 hex>/<target>`), else 409 `place-invalid` with the same sentence the window shows; before, any name inside the kind's folder was accepted, and a site could come back as `sites/Bad Name!` and list without an id. `_settle_site_id` writes the folder name as `id` into a restored site's `site.json` when it has no valid one.
- `services/host.py` `serve_missing`: falls back to `404/index.html` after `404.html`, because FormWeb exports its 404 page only as `404/index.html` and the site host answered every missing path of a FormWeb site with a plain "Not found".

Checked: about 60 refusals across sites, keys, builds, checks, publish, host, trash, receive and the middleware over HTTP on 8781, each with its status and code; the CLI against the engine, in process and with the engine down; `--selfcheck`; core-missing forced in process (the repo ships the core, so it cannot be reached over HTTP). A FormWeb site with 301, 302 and splat redirects, clean URLs, a directory index, a custom 404 and one deep problem per page gave the same summaries (8 errors, 12 warnings), the same 20 problems and byte-identical thumbnails on 0.1.3 and this branch at 1440 and 390; only two `deep.request` ids differ, from the 0.1.4 host normalization. 58 GET and HEAD requests to both site hosts matched in status, Location, type and size. The splat and the root `404.html` had to be added to the export by hand: FormWeb rejects `*` in a redirect and writes no root `404.html`. With the fallback, a FormWeb export without `404.html` answers `/missing` and `/bare/` with its 404 page. Restoring an unparseable site entry in process: no origin gives `origin-unknown`, `sites/Bad Name!` and `sites/a/b` give `place-invalid`, `sites/restored-one` restores and lists by that id. The director's cross-app run ended with a FormWeb live send whose refusal check answered `{detail: "site not found", code: "site-missing"}` and whose mounted page served the pasted image, posts and token CSS.

## Phases 22 to 24 · v0.1.7 (2026-11-10)

The executor spec is `TURN_H_SPEC.md` in the 0.1.7 planning sidecar. The vendored FormWeb crates are 0.19.7.

- `services/trash.py`: `_key_record` says whether a trashed key still has a usable `entry.json`; when it does not, `restore` skips `_free_destination` and `_rescue_key` rebuilds the key from the entry's single `.pem`. Loading without a password tells unencrypted (loads), encrypted (`TypeError`) and unreadable (`ValueError`, `entry-damaged`) apart; an encrypted key needs `passphrase` (409 `passphrase-required`, then `passphrase-wrong` with `keys.WRONG_PASSPHRASE`); a non-Ed25519 key is `entry-damaged`. The id is `sha256(raw public)[:16]`, the fingerprint comes from `keys.fingerprint_of`, the row is named `Recovered key <id>` with `created` from the file time, and under `keys._lock` an id already in the index or on disk answers `place-taken`; otherwise the file moves to `keys/<id>.pem` (0600), the row is appended and the result carries `rescued: true`. The imports sit inside the function to keep `trash` and `keys` from importing each other at load time. Other kinds, and keys with a good record, take the 0.1.6 path.
- `routers/trash.py` reads `passphrase` from the restore body (non-text is 400 `invalid`). `cli.py` adds `trash restore ENTRY --passphrase-stdin` (one line from stdin; no flag takes the value) and only sends keys that are set. `mcp.py` `restore_from_trash(entry, passphrase=None)`. The passphrase is never logged, stored or echoed.
- `targets/_common.py`: `PreparedInput.fallback_404`, and `copy_site` writes an older export's `404/index.html` as `404.html` with `../` in `href`, `src`, `poster` and `action` made root-absolute, so the page loads its styles at nested missing paths; each host target's notes say so and static-zip stays byte-for-byte. FormWeb 0.19.7's splats needed no change: netlify and cloudflare-pages write `/blog/* /docs/:splat 301`, vercel `:path*`, nginx a regex `return 301 /docs/$1`, github-pages skips splats with a warning.
- `services/host.py` `serve_missing`: `404.html` first as before; for a `404/index.html` fallback the same `../` rewrite is applied (with the probe injected for deep runs) before it is delivered with status 404. Served raw, the fallback asked for `/a/b/assets/...` at `/a/b/c`; found by P3 while checking FormWeb's root page. A `../` inside the page's JSON configuration stays; it is data the browser does not load.

Checked: a lab engine on 8781 with an unencrypted and an encrypted key whose records were deleted or corrupted, restored through the API, the CLI and MCP; each signs a build that verifies; the passphrases appear nowhere in the engine log; a garbage `.pem` gives `entry-damaged`, a duplicate `place-taken`; `--selfcheck` OK. A FormWeb 0.19.7 site built through FormWeb's API with `/old` 301, `/promo` 302, `/blog/*` and a 404 page prepared clean on all six targets, as did an older export through the fallback; the host answered every redirect and the 404. The director's run: an element with a 20 MiB video behind a clip went from one FormWeb to another and live to this engine on 8606, whose host served the image and video, `/old` and `/blog/x/y` 301s, and the custom 404 at `/a/b/c` with its stylesheet and runtime answering 200; netlify, cloudflare-pages, vercel and nginx each wrote the splat and a `404.html`; an unknown site answered `site-missing`. P2's report that the demo sample lists without an id did not reproduce on a clean lab engine.

## Phases 25 to 27 · v0.1.8 (2026-11-10)

The executor spec is `TURN_I_SPEC.md` in the 0.1.8 planning sidecar. The vendored FormWeb crates are 0.19.8.

- `targets/nginx.py`: `check(folder)` runs `nginx -t` when `nginx` is on PATH and the folder has `nginx-test.conf`. It copies the wrapper and `formpublisher.conf` into a fresh `mkdtemp` scratch folder that is also the prefix, with `-e` for the error log, a 20 s timeout and no stdin, and swaps each `listen` in the copy for a unix socket inside the scratch folder: `nginx -t` opens its listen sockets, so `[::]:80` failed here without IPv6 and port 80 fails for a normal user. It answers `{ran, ok, version, output}` (output trimmed to nginx's own lines, at most 2 KiB, scratch paths shown as the prepared folder); without nginx `ran` is false and `ok` is None. `message_of` picks the first `[emerg]`, `[alert]` or `[crit]` line; `annotate` turns the check into a prepare note or warning. The wrapper's `pid` is now `nginx.pid`, relative to the prefix, because `/tmp/formpublisher-nginx/nginx.pid` failed unless that folder existed; an nginx folder prepared by 0.1.7 therefore differs from a fresh prepare until it is prepared again. The listen lines themselves are not syntax-checked, and a hand-written resolver or proxy host would still be resolved.
- `services/publish.py`: `prepare` calls a target's optional `annotate(result, folder)` after the folder is in place; `verify` calls a target's optional `check(folder)` after the comparison, adds `nginx` to the answer and, on failure, the problem row `{formpublisher.conf, "nginx -t: <message>", source "nginx -t"}`. `verify` also takes a target's optional `rewritten(inp)`: files a target changes on purpose skip the `publish.json` hash check but are still compared with a fresh prepare, so tampering is caught.
- `targets/github_pages.py`: splat rules are no longer skipped. `_base_path` takes the path of the model's `settings.baseUrl` (read from `site.formweb.json` in the build even when it is left out of the site), else of the 404 page's canonical link (trailing `/404` removed), else the root. `_splat_rules` keeps `/path/*` rules with a local or http(s) target, local targets prefixed with the base path, longest prefix first. `_script_tag` writes one comment-free inline script (JSON literals with `<`, `>` and `&` escaped) that trims trailing slashes, requires the base path, matches `prefix + "/"`, strips every leading `/` and `\` from the remainder, fills `:splat` by split and join, keeps the query and hash and calls `location.replace` unless the target is the current path; `/blog` and `/blog/` do not match, as in FormWeb releases. `_place_script` puts it right after `<head>` (after a leading meta charset). Exact redirect stubs and the minimal 404 page's home link now use the base path too (the director's fix after P4 saw `/old` leave a project site for `/docs`). `rewritten` names `404.html` when a splat rule exists. `redirects/README.txt` lists exact stubs and splats separately.

Checked: `--selfcheck` OK. With nginx 1.24 here, a FormWeb export with 301, 302 and 308 redirects, a splat, headers, gzip, clean URLs and a 404 page passed `nginx -t` on prepare and verify, also as uid 65534; a misspelt directive failed verify with nginx's `[emerg]` line; with nginx off PATH verify answered `ran: false`. Three FormWeb sites (base path `/repo` with and without a 404 page, and the root) prepared for GitHub Pages and verified clean; on a stand-in that answers every missing path with `404.html`, headless Chrome went from `/repo/blog/a/b?q=1#h` to `/repo/docs/a/b?q=1#h`, kept `/repo/blog//evil.com` on the site, followed `/blog/archive/*` before `/blog/*`, and left `/repo/blog`, `/repo/blogx/y` and unknown paths on the 404 page. The director's run: FormWeb 0.19.8 copied a card over MCP with a 20 MiB video behind a clip, pasted it into a second FormWeb and sent it live to this engine on 8606; all six targets verified clean, nginx with `ran: true, ok: true, version 1.24.0`, the GitHub Pages `404.html` carried the script before its stylesheet with base `/repo`, `/repo/old` landed on `/repo/docs`, and an unknown site answered `site-missing`.

## Phases 28 to 30 · v0.1.9 (2026-11-10)

The executor spec is `TURN_J_SPEC.md` in the 0.1.9 planning sidecar. The vendored FormWeb crates are 0.19.9.

- `targets/nginx.py`: `CHECK_SCRIPT` is written as `nginx-check.sh` (fixed bytes, POSIX sh, no comments). It exits 127 when nginx is missing, finds its own folder from `$0`, makes a `mktemp -d` scratch folder under `${TMPDIR:-/tmp}` (a template, so it works on macOS), copies the wrapper into `scratch/conf/`, writes a copy of `formpublisher.conf` there with awk swapping each `listen` for `unix:scratch/lN.sock`, runs `nginx -t -p -e -c` on the copy from inside the scratch folder, prints nginx's output with the scratch path replaced by the prepared folder's, removes the scratch folder through an EXIT trap (HUP, INT and TERM exit 1 first) and returns nginx's status. `put()` cannot set the executable bit, so the command is `sh nginx-check.sh`; the scratch-folder command is gone, `LOCAL_TOOL` names the script and one note explains it. The engine's own `check()` stays Python, so Windows and the window keep working without sh.
- `targets/nginx.py` redirects: every `return` ends with `$is_args$args` unless the target already holds `?`, because nginx dropped the query string on every redirect while the other targets and the site host keep it (found by P3 on a live nginx). Local targets never contain `?` (SAFE_PATH), so only an external target with its own query keeps it as written. nginx folders prepared by 0.1.8 differ from a fresh prepare until prepared again.
- `targets/github_pages.py`: `DESCRIPTION` says its 404 page also follows folder redirects. No other change: P3 found that an export without `site.formweb.json` and `asset-access.json` imports, and GitHub Pages then takes `/repo` from the 404 page's canonical link with the note naming that source; and that external targets (`/ext` to `https://example.org/x`, `/out/*` to `https://example.org/:splat`, added by hand since FormWeb refuses them) come out right everywhere: a stub with meta refresh, a script rule used as written, `_redirects` lines for Netlify and Cloudflare Pages, `:path*` in `vercel.json`, nginx `return`s that pass `nginx -t`, and the site host's 301s, which encode `%0d%0a` in Location so no header is injected. In Chrome under `/repo`, `/out//evil.com` went to `https://example.org/evil.com`, never to `//evil.com`.

Checked: `nginx-check.sh` passed as root and as uid 65534 (`setpriv`), failed with nginx's `[emerg]` line on a broken copy and left nothing in TMPDIR; 24 prepared folders (four exports, six targets) verified clean; on a live nginx serving the prepared config, `/old?q=1` answered 301 to `/docs?q=1` and `/blog/x/y?q=1&r=2` 301 to `/docs/x/y?q=1&r=2`; the selfcheck passes.

## Phases 31 and 33 · v0.2.0 (2026-11-10)

The executor spec is `TURN_K_SPEC.md` in the 0.2.0 planning sidecar (planned as 0.1.10; released as 0.2.0 to keep the family's one-digit patch number, which FormWeb's version test enforces). The vendored FormWeb crates are 0.20.0, which changed only the workspace version.

- `targets/github_pages.py`: `STUB` gains `{script}` right after its meta charset, filled by `_stub_script(to)` from `STUB_SCRIPT`: the target as a JSON literal with `<`, `>` and `&` escaped, split at its own `#`, then `location.replace` with the target, the visitor's `location.search` unless the target has its own `?`, and the target's hash or else the visitor's. The meta refresh and canonical link stay as the fallback; the page bytes depend only on the target, so verify stays clean.
- `targets/_common.py`: `put(out, rel, data, mode=None)` chmods when a mode is given. `targets/nginx.py`: `CHECK_SCRIPT` starts with `#!/bin/sh` and is written 0755; the mode survives because `publish.prepare` `os.replace`s the whole staged folder. The command still reads `sh nginx-check.sh`, which works when a copy loses the mode.
- `targets/nginx.py` `check()`: `_run_nginx` holds one `nginx -t` run. After the unix-socket pass passes, `_free_ports(n)` binds n loopback sockets to port 0, reads their ports and closes them, and `_loopback_listens` (with `LISTEN_RX`) points each listen line at `127.0.0.1:port`, keeping its other parameters, for a second run. A failure there fails the check with nginx's message; no free port, a bind race ("Address already in use") or a timeout skips it. The answer gains `listen {ran, ok, output}`. `annotate` writes "The config passed nginx -t with nginx X, and so did its listen lines on a loopback port." or that they were not checked; the director reworded P3's first text, which began "nginx -t passed with nginx X", because the window's translator matched it to part14's verify line `nginx -t passed with nginx {0}.` and would have left the rest in English.

Checked: on a GitHub Pages stand-in under `/repo`, `/repo/old?q=1#h` landed on `/repo/docs?q=1#h` and on `/repo/docs` with scripts off; an external target with its own query, added by hand, went to `https://example.org/x?a=1#h`. `nginx-check.sh` was `-rwxr-xr-x` and `./nginx-check.sh` passed as root and as uid 65534; verify ran both passes; a hand-broken `listen 80 bogusparam;` failed only the listen pass with nginx's `invalid parameter` message; two prepares were byte-identical with the same modes; the selfcheck passes.

## Phases 34 to 36 · v0.2.1 (2026-11-10)

Three changes, none of which touch the engine's routes.

- `targets/nginx.py`: `CHECK_SCRIPT` runs `nginx -t` a second time after the unix-socket pass, on a second scratch copy whose listen lines keep their parameters but point at `127.0.0.1` and one consecutive port per line, matched exactly as the engine's own listen pass. The first port is `NGINX_CHECK_PORT` when it is a number from 1024 to 60999, otherwise 20000 plus the process id modulo 41000. On "Address already in use" it tries the next base, at most five times, then says the listen lines were not checked and exits 0 on the first pass; any other listen-pass failure prints nginx's message and exits 1. It prints "nginx-check.sh: both passes passed (unix sockets, then the listen lines on loopback ports).", the not-checked line, or a line saying the listen lines were not checked because the config has none. Finding: nginx 1.24 here does not fail `nginx -t` on a busy loopback port, so the retry only matters on builds that report it. The Check the config note now says the script runs `nginx -t` on a scratch copy with unix sockets, then again with each listen line on a loopback port. nginx folders prepared by 0.2.0 differ from a fresh prepare until prepared again.
- `setup/vendor_check.py`, run by `./formpublisher vendor --check` (and `formpublisher.bat`), `./setup/install_compiler` and the CI step "Vendored crates in step" before "Build formweb-core": it passes only when the Version row of `vendor/formweb-native/VENDOR.md` equals the vendored workspace version, the four crates resolve to it and `Cargo.lock` lists them at it. In a git checkout it compares each crate's tree row with the tree of the staged (index) state, computed from `git ls-files --stage` without writing to `.git`, and refuses unstaged changes and untracked files under `vendor/formweb-native` outside `target/`; outside git it skips those with one line. It prints "vendor: in step at VERSION" or each mismatch with what to do; `install_compiler` refuses with "the vendored crates are out of step (see above); nothing was built". The vendoring flow in `VENDOR.md` now stages the folder with `git add vendor/formweb-native` before building.
- `targets/github_pages.py`: the prepare notes and `redirects/README.txt` add "With scripts off, a visitor at a splat address sees the 404 page, because only the script follows these redirects." Both new notes are translated in all 26 languages (`keys/part17.json`); verify rows were checked in the window in German and Japanese (FormPublisher has no right-to-left language).

Docs: `docs/MANUAL.md`, the README command list, the wiki pages Publishing, Importing-Sites and Agents, and the harness and skillset skills in both trees carry the new behaviour.

## The vendor check on Windows and in doctor · v0.2.2 (2026-11-10)

One change, none of which touches the engine's routes (commit b833812).

- `setup/install_compiler.bat` runs `setup\vendor_check.py --check` before cargo, with Python found as `formpublisher.bat` finds it (the backend venv, else `python`), and refuses with the same sentence as `setup/install_compiler`: "the vendored crates are out of step (see above); nothing was built".
- `./formpublisher doctor` and `formpublisher.bat doctor` gain a vendor row: "vendor: in step at VERSION", or the first problem with a pointer to `./formpublisher vendor --check` for the rest.

Checked: `./formpublisher doctor` printed "vendor: in step at 0.20.1" on the tree and the Version row problem with the pointer in a /tmp clone with a changed row; `bash -n formpublisher` passes; the `.bat` changes were checked by reading, since Windows is not available here.

Docs: `docs/MANUAL.md` (doctor and the install_compiler passage), the wiki pages Getting-Started and Importing-Sites, and the harness and skillset skills in both trees.

## The Windows doctor vendor row works when run · v0.2.3 (2026-11-11)

One file changed, `formpublisher.bat` (commit 0a31cb9). Running `formpublisher.bat doctor` and `setup\install_compiler.bat` under Wine 9.0 (with a stand-in `python.exe` handing off to the Linux Python) showed three defects in the v0.2.2 vendor row, which had been checked by reading only.

- The `for /f` command began with a quote, so `cmd /c` stripped the outer quotes and the check never ran; it is now wrapped in an extra pair.
- The first-line capture kept the last line under Wine; it is now a `:vfirst` subroutine.
- Echoing a problem line with parentheses and a comma ran its tail as a command; the line is now held in a quoted `VTAIL` variable.
- `setup\install_compiler.bat` needed no change.

Checked: under Wine 9.0 in a /tmp clone, doctor printed "vendor: in step at 0.20.2", and with a changed Version row it printed the problem line and the pointer with no stray errors; `install_compiler.bat` refused before the cargo check when out of step and reached the cargo-missing line when in step. Real Windows has still not been run.

Docs: `docs/MANUAL.md` (the install_compiler passage) and the wiki page Getting-Started.

## Phase 43: save a build as .fpub and open one · v0.2.4 (2026-11-11)

One build in one file, so a build can move between two FormPublishers with its signature intact (commit e14279a). The format is `formpublisher-package` version 1 and is written out in `docs/MANUAL.md`.

- `services/fpub.py` (new): `write_file(build_id, target)` reads `build.json`, `publish.json` and `site.zip`, refuses with 409 `build-damaged` when the zip no longer matches `publish.json` or a present signature no longer holds, and writes a zip of exactly `fpub.json`, `publish.json`, `site.zip` and, when signed, `site.zip.sig`, in that order. Every entry is stored with the time 1980-01-01, create system 3, mode 0644, deflate, no extra field and no comment, and `fpub.json` is `json.dumps` with indent 2 and a trailing newline, so one build always gives the same bytes. It writes to `NAME.tmp` and `os.replace`s, and a file over 512 MiB is 413 `too-large`. The signature record in `fpub.json` (`keyId`, `fingerprint`, `publicKey`) is taken from the key in `site.zip.sig` after checking the signature over the zip, so a record that does not verify is never written.
- `services/fpub.py` `import_file`: unpacks into a `.fpub-` scratch folder inside `builds/`, so the final move is a rename on one filesystem. `_unpack` refuses a file over 512 MiB, a bad zip, unsafe names (through `intake._clean_member`), entries other than the three or four in that order, encrypted entries, and entries over their limit (1 MiB, 32 MiB, 512 MiB, 64 KiB), counting bytes while it copies so a lying header cannot get past. `_read_meta` checks the format, the integer version 1 (a boolean is not a version), the site id with `intake.ID_RE`, the build id with `package.ID_RE`, the text fields and the package record. Then the size and SHA-256 of `site.zip` against `fpub.json` (400 `fpub-tampered`), `publish.json` against `site.zip` and the site id (`fpub-tampered`), and the signature (`fpub-signature`): the entry must exist exactly when `fpub.json` says signed, the algorithm is ed25519, the fingerprint is recomputed from the public key, the signature verifies over the zip bytes, and the key id, fingerprint and public key equal what `fpub.json` records. The verdict is `{valid, key, keyId, known}`; `known` says whether the key is in this computer's `keys/`, and a valid signature from a key you do not hold is still accepted and reported as such.
- `services/fpub.py` restore: `intake._finish` imports `site.zip` as a revision of the same site id (it gained optional `site_id` and `revision_name`, so a revision keeps the name `fpub.json` records when it looks like `YYYYMMDDTHHMMSSZ`), then under `package._lock` the build folder is moved to `builds/[site]/[id]`. `_free_id` keeps the id when it is free and otherwise picks a new 12-hex id, so a second open of the same file does not overwrite the first; `build.json` records `imported {from, remapped, at, signature}` and the answer carries `build {id, originalId, remapped, signed, signature}`. If anything fails after the site import, the new revision folder is removed and `site.json` is put back (or the site folder removed when the site was new), so a refusal leaves the data folder as it was. The source record keeps `kind` from the original (`zip`, `folder`, `fweb`), plus `fpub {build, revision}`.
- `services/intake.py`: `import_path` and the upload path call `fpub.is_fpub` before anything else, by a `.fpub` name or by a zip whose first entry is `fpub.json`, so the existing `POST /api/sites/import`, `cli import` and `import_site` open a `.fpub` with no new route.
- `routers/builds.py`: `GET /api/builds/{id}/fpub` writes the file to a temp path and answers it as a download named `SITE-BUILD.fpub`, removing the temp file afterwards. `cli.py`: `fpub BUILD [--out FILE] [--force]`; the default name is `SITE-BUILD.fpub` in the current folder, the name must end in `.fpub`, a folder, a missing parent folder or an existing file without `--force` is refused, and over HTTP the bytes stream to `NAME.part` and are renamed, in-process the service writes directly. `mcp.py`: `save_fpub(build, path)` never replaces a file (it passes `force` false); `import_site` says it takes a `.fpub`. 22 commands and 19 tools.

Checked: one signed FormWeb export saved through HTTP, the CLI and MCP gave identical bytes every time; opened in a second engine it kept the sha256 of `site.zip`, `publish.json` and the signature, verified valid and reproduced, and prepared and verified on all six targets; fifteen tampered or foreign files (checksum, size, signature, fingerprint, format, version, entries, an escaping path, not a zip, an oversized entry) were refused with the data folder unchanged; the selfcheck passes. The director's exit run: an engine on 8791 saved a signed .fpub of a FormWeb site, twice byte-identical, and the CLI gave the same bytes; a second engine on 8792 opened it as the same site and build id with a valid signature, prepared and verified all six hosts clean; a .fpub with one byte of `site.zip` flipped was refused ("site.zip does not match the checksum recorded in fpub.json") and another format was refused; FormWeb 0.20.4 opened the same file as a project with the same pages, nodes and image.

Docs: `docs/MANUAL.md` (a section, The .fpub format, with the entries and the `fpub.json` fields, and the CLI, MCP and error code tables), the README, the wiki pages Importing-Sites, Packages-and-Signatures and Agents, `AGENTS.md`, and the harness and skillset skills in both trees. The counts are now 22 commands and 19 tools.

## Phase 44: the last verify result is kept · v0.2.4 (2026-11-11)

The publish sheet forgot every verify verdict when it was closed and reloaded, so a person could not tell whether a prepared host had been checked (commit df07b7f).

- `services/publish.py`: `verify` writes its result to `prepared/[site]/[build]/.TARGET.verify.json` (`target`, `verifiedAt`, `ok`, `checked`, `problems`, `nginx`) after the check, through `package._write_text`. The file sits beside the prepared record (`.TARGET.json`) and outside the host folder, so it is never compared against a fresh prepare, never packaged and never copied to a host. `_stored_verify` reads it back and returns nothing for a file that is missing, not an object or lacks `verifiedAt` and a boolean `ok`. `prepared` adds it to each host's row as `verified {verifiedAt, ok, checked, problems, nginx}`, and the verify answer carries `verifiedAt`.
- `prepare` deletes the host's file when it puts the new folder in place, and `remove` deletes it with the folder, so a result never outlives the folder it describes; the other hosts keep theirs. A result that failed stays as a failure until the next prepare, and nothing re-verifies by itself.
- `get_prepared` (MCP) and `prepared BUILD` (CLI) carry `verified` because they return the same listing; no new route, command or tool.

Checked: with two hosts failing and four passing, `GET /api/publish/BUILD` returned each result with its time; preparing one host cleared only that host's result; target folders stayed byte-identical across verifies and prepares; the selfcheck passes. The director's exit run: the kept results survived an engine restart and were cleared by the next prepare.

Docs: `docs/MANUAL.md` (the Publish section), the wiki page Publishing, and the harness skill in both trees (`get_prepared` returns `verified`).

## Phase 45: the Windows launchers run under Wine · v0.2.4 (2026-11-11)

Two files changed, `formpublisher.bat` and `backend/boot_backend.bat` (commit b1baae1). Every `.bat` launcher was run under Wine 9.0 with stand-in tools in a CRLF clone under /tmp, and five defects came out. `build_app.bat` and `formpublisher_oc_install.bat` needed no change.

- `formpublisher.bat` `run`, `cli`, `mcp`, `agents` and `vendor` used `shift &` on one line. cmd expands `%1` before `shift` runs, so the subcommand was passed on too, and `formpublisher.bat vendor --check` and `agents sync --check` printed their usage and exited 2. They now pass `%2` to `%9`, up to 8 arguments.
- `boot` went on after a failed install; it now stops with exit code 1.
- `desktop dev` ran into a missing `tauri.cmd`; it now prints "the desktop tools are missing: run formpublisher.bat install" and exits 1.
- `backend/boot_backend.bat` went on without `py` and its venv; it now prints "Python 3.12 is needed", or that installing the engine requirements failed, and exits 1.
- `doctor` printed the shell's error when node was missing; it now prints "missing".

Checked: each launcher path above was run under Wine 9.0, before and after the fix. Real Windows has still not been run.

Docs: `docs/MANUAL.md` (the Getting started passage on the Windows launchers).

## Phase 56: a second engine binds its own preview host · v0.2.8 (2026-11-11)

Three files changed: `app/host.py`, `app/services/paths.py` and `app/routers/health.py` (commit 3c3c4fd). Running the desktop shell on Linux beside another engine showed that when 8281 (or `FORMPUBLISHER_HOST_PORT`) was already taken, uvicorn failed to bind, `_run` only logged "site host stopped", and this engine kept building `host_url()` from the same number, so its preview and live checks reached the other engine's site.

- `host.start()` binds the socket itself, as `serve_revision()` does, with `SO_REUSEADDR`. If the wanted port raises `OSError` it binds port 0, logs one warning naming both ports, and calls `paths.set_host_port()` with the bound port, so `host_port()`, `host_url()`, `host_origin()` and `HostApp`'s Host check all use it. The socket goes to `serve(sockets=[sock])` and is closed in `stop()`.
- `engine.json` (written after the host starts) and `/api/health` carry `hostPort`; no existing field changed.
- A free wanted port behaves as before: same port, no warning.

Checked: two engines on 9012 and 9014 while 8281 was held by a third took different host ports, reported them in `/api/health` and `engine.json`, and each preview and its assets came from its own port, with no `live.request` errors on the second; `FORMPUBLISHER_HOST_PORT=9099` was taken exactly with no warning; `compileall`; engine `--selfcheck`.

## Phase 61: every demo has its own route · v0.3.0 (2026-11-15)

- `app/routers/demo.py`: `POST /api/demo/open/<id>` opens `demo/sites/<id>.zip` from the resource folder. `DEMO_ID` (`[a-z0-9][a-z0-9-]{0,40}`) is checked before the id becomes a file name, so the route cannot be made to read another path. `_open(key, archive, stem, missing)` is the one import path for every demo: a demo is imported once, under the source key `demo:<id>`, and opening it again answers the same site with `created: false`. `POST /api/demo/sample` keeps its address and its key for Northwind Notes, so a data folder from 0.2.8 finds its sample again.
- `setup/freeze_backend`: the frozen engine carries `demo/sites` when the folder exists.

## Phase 62: the engine's part of the full review · v0.3.0 (2026-11-15)

- `app/services/intake.py`: a zip that holds a file and a folder of one name answered 500; the `mkdir` for an entry's parent now runs inside the guarded block and the message carries the system's own words (`strerror`), so it answers 400 with "cannot read ... from the zip".
- `app/cli.py`: printing into a closed pipe (`./formpublisher run sites | head -1`) ended in a traceback. `BrokenPipeError` is caught and stdout is pointed at the null device, so Python's exit flush stays quiet.
- `app/services/package.py`: `SOURCE_KINDS` maps `demo` to `formweb-export`; `publish.json` of a demo site's build had no known source kind.
- `formpublisher_engine.py`: `--selfcheck` used to report `core: true` when the `formweb-core` file was present. `core_runs()` now runs `formweb-core --selfcheck` (60 s limit), so a frozen engine whose inner program cannot start, for example because a signature broke it, fails its self-check at build time and not at a user's first `.fweb`.
- `build_app`: with `APPLE_SIGNING_IDENTITY` set, a failed `codesign --verify --deep --strict` stops the build (an ad hoc build still only warns). On macOS the engine inside the finished app runs its self-check, under the app's signature and with a temporary data folder, before the disk image is packed. `build_app` does not notarize; a build signed with a Developer ID and not notarized starts, and macOS asks once at first open (the manual's troubleshooting has the step).
- `formpublisher.bat`: arguments after the command were passed as `%2` to `%9`, so the ninth and later were dropped. `:rest` shifts through all of them into `%REST%`.

Checked: 22 odd or hostile archives and 68 bad requests against every route (no 500); `compileall`; engine `--selfcheck`. The macOS steps of `build_app` were read, not run: no Mac here.

## Phase 63: three FormWeb demo sites are bundled · v0.3.0 (2026-11-15)

- `demo/sites/lowlight.zip`, `looking-back.zip`, `harbour-ferries.zip`: FormWeb's plain exports of its three demo sites, repacked the same way every time (sorted names, dates 1980-01-01, deflate 9, mode 0600) so a rebuild of the zip does not change the file. They open through Phase 61's route.
- `NOTICE.md`, `demo/MEDIA.md`: every picture in every demo site with its source and status, and the fonts with their copyright lines. `demo/licenses/OFL-*.txt`: the SIL Open Font License text of each of the seven font families the demo sites embed, because the licence asks for its text to travel with the font files.
- `setup/freeze_backend`: the frozen engine carries `demo/licenses` beside `demo/sites`.

## Phase 64: the probe measures the page, not the preview · v0.3.0 (2026-11-15)

`app/static/probe.js`, the script the site host adds to previewed pages. The window's part is in `frontend/HASHOUT_LOG.md`, Phase 64.

- Layout shift after a resize: the preview resizes the frame on a Device switch, and Chrome reports the reflow as a layout shift without `hadRecentInput`, within 0 to 7 ms of the resize event and sometimes just before it. `viewResized()` watches `innerWidth` and `innerHeight` and opens a quiet window of 500 ms; a shift that starts inside it is dropped and moves the window's end to 500 ms after that shift, up to 2500 ms after the resize in all. 500 ms is the window Chrome itself uses to excuse shifts after a visitor's input (`hadRecentInput`); the Device switch is such an input, but it happens in the window around the frame, so Chrome cannot know. The extension covers a reflow that arrives in several entries (media queries, pictures choosing another size), and the cap is there so a page that never stops moving is still reported.
- Layout shift before first paint: a frame in the same process reports the move from unstyled to styled when its stylesheet arrives, which no visitor sees. Shifts are held in `clsHeld` until a `paint` observer gives the first-paint time; those that started before it are dropped.
- Each document makes an id at start (`doc`) and sends it with every message, so the window can tell the document a frame is leaving from the one it is loading.
- Overflow: `checkOverflow()` returns when the document or the window has no width, and runs 300 ms after load and after a resize (`queueOverflow()`), not in the same tick, so it measures the settled layout.
- The other live checks (`console`, `error`, `request`, `nav`) were read for the same two mistakes: none depends on the frame's size or on timing against a resize.

## Phase 65: the vendored FormWeb core is 0.21.0 · v0.3.0 (2026-11-15)

`vendor/formweb-native` is FormWeb's `native/` workspace at its 0.21.0 release, copied unedited (`VENDOR.md` has the tree ids); `./formpublisher vendor --check` answers `in step at 0.21.0` and `formweb-core --selfcheck` answers version 0.21.0. It brings FormWeb's export and engine fixes to `.fweb` projects opened here. Project files written by FormWeb 0.20.8 still open and compile to the same files as the 0.21.0 ones.

## Phase 66: the hand-off with FormWeb 0.21.0, both directions · v0.3.0 (2026-11-15)

Both apps were run together and every path between them tried: Send to FormPublisher with FormPublisher running and stopped (inbox), Import from FormWeb, `.fweb` projects, `.fpub` packages opened in FormWeb, and a FormWeb publication folder. What reaches FormPublisher by send, inbox or import is byte for byte FormWeb's plain export. Two faults were on this side.

- `app/services/compile.py`: `bundle()` rewrites `/api/assets/<name>` links to relative `assets/<name>` by the file's depth. FormWeb also writes a root `404.html`, a second copy of the page at `/404`, that hosts serve at any missing address, however deep; relative links break there. FormWeb 0.21.0's own bundling roots that one file's links at the prefix its runtime script already carries (`ROOT_404_PREFIX`), and `bundle()` now has the same rule. Before, a `.fweb` opened here differed from FormWeb's export in exactly that file, and its not-found page lost pictures and fonts below the top folder.
- `app/services/host.py`: `base_path(root)` reads the folder a site is addressed under from the Sitemap line of its own `robots.txt` (`https://example.org/shop/sitemap.xml` gives `/shop/`; the root gives ""). `within(base, path)` takes it off a path. `robots.txt` is used, not the model's `baseUrl`, because it records what the export really wrote: a FormWeb publication folder is written for `/published/<slug>/<version>/` whatever the model says. The site host looks a request up as it is first and then with the base path taken off, so the root `404.html` of such a site, whose links start with the base path, loads its files in the preview as it will on its host. `Serving` carries `base`; `app/host.py` passes it for deep runs too.
- `app/services/checks.py`: `SiteIndex.lookup()` does the same two-step lookup and `local()` maps a sitemap address to a route. Before, the Lowlight demo with the base address `https://example.org/shop/` got 11 `asset.missing` and 8 `link.broken` errors on `/404.html` and 5 `sitemap.missing` and 5 `sitemap.extra` warnings, all false; a site at the root is looked up exactly as before, and a link to a page that does not exist is still reported.

Not changed, by decision: FormPublisher has no check for forms. A posting form in a site sent from FormWeb carries FormWeb's local address (`http://127.0.0.1:8240/api/forms/...`), which FormWeb's own audit warns about (`forms.local-address`); a `.fweb` compiled here gets `/api/forms/...` because `compile_fweb()` passes an empty `formsEndpoint`. Neither works on a static host and neither is reported here. Send to FormPublisher and Import from FormWeb give two sites for one FormWeb project, because the first is keyed by the project and the second by FormWeb's address. There is no version gate in the live hand-off: FormWeb looks for `app: formpublisher` in `/api/health`, and the engine does not read `X-FormWeb-Version`.

Checked: the three demo `.fweb` files and a starter project compile to the same files as FormWeb's exports (the starter differs only in the form address above); three project files written by FormWeb 0.20.8 open and give the same files; a `.fpub` saved here, signed and unsigned, opens in FormWeb as a project and FormWeb's export after it is byte for byte the export before; the base-path site has 0 findings and a styled not-found page at a missing address; Northwind Notes still has its 1 error and 2 warnings; `compileall`; engine `--selfcheck`.

## Phase 67: a check for forms that post to a local address, and one site per FormWeb project · v0.3.1 (2026-11-15)

Phase 66 left two things "not changed, by decision": no check for forms, and two sites for one FormWeb project (Send keyed by project, Import keyed by FormWeb's address). Both are changed here; the rest of Phase 66 stands. The window's part is in `frontend/HASHOUT_LOG.md`, Phase 66.

- `app/services/checks.py`, `forms.local-address` (warning). `Page` now collects every `form` tag with its line and attributes (`forms`), and `Runner.check_forms()` runs from the page check for every HTML file, routed or not, like the image checks. A form with no `action`, an action starting with `#`, an action that resolves to the same page, or an action to a service on the web is not reported. A form is reported when its action leaves the page for this computer or the local network, or goes into `/api/forms/` on the site itself. The reason: a form FormWeb exports without a scripted reply posts to FormWeb's own address (`http://127.0.0.1:8240/api/forms/...`), and a `.fweb` compiled here posts to `/api/forms/<site>/<form>` (`compile_fweb()` passes an empty `formsEndpoint`); neither answers on a host, so the form silently does nothing, while the rest of the page works, which is why the severity is warning. A form with a scripted reply carries no action and no finding, as does one pointed at a form service on the web by `node.update`.
- `local_host(host)` decides "local": `localhost`, any `.localhost` or `.local` name, and a name with no dot and no colon (a single-label host such as `printer`) are local; an IP literal is local when it is loopback, private, link-local or unspecified, and an IPv4-mapped IPv6 address is judged by the IPv4 address inside it. A name that merely looks like an address (`10.0.0.1.nip.io`) is not an IP literal and is not local, because its address cannot be known offline and a false warning costs more than a missed one. `urlsplit` gets `http:` in front of a `//host/...` action so the host is read.
- The action is resolved by `target_path()`, the function links use. An absolute address comes back as "ext" or as "own" (the site's own hosts include loopback, so `http://127.0.0.1:8240/...` is "own"), and both kinds are judged by `local_host()` on the host alone. A relative action comes back as "int" and goes through `SiteIndex.local()`, so `../api/forms/x` and a base-path site (Phase 66) resolve as a link would; only a path under `/api/forms/` is reported, so a form posting to `/search/` is not.
- Id and message: the id is the usual static one (`static:forms.local-address:<route>:<line>`, with `:2` for a second finding on the same line), so two forms on one page are two findings. The message names the page and the address; the fix names FormWeb's own remedy (Motion > Script, trigger Submit, or a form service on the web). The code is the same string FormWeb's audit uses for the same problem, so one finding reads the same in both apps.
- `app/services/formweb.py`, `project_id()`: `GET /api/access` on the running FormWeb, read only and with the probe timeout, returns `projectId`, the value FormWeb puts in `X-FormWeb-Project` and in the inbox's `.zip.json` when it sends. Any failure (not reachable, not 200, not JSON, no usable field, an older FormWeb without the route, a FormWeb that asks for a sign-in) gives None, and `import_current()` then keys the site by FormWeb's address as 0.3.0 did, so Import never fails for want of this answer. The value is trimmed and cut to 200 characters, and `import_current()` passes it as `receive:<projectId>`, the key `inbox.receive_zip()` and the inbox watcher already use.
- `app/services/intake.py`, `project_site()`: a site id is the name's slug plus six hex of SHA-1 over the name and the key (`make_id`), so a project that was renamed in FormWeb would get a new id from the same key. For a `formweb:receive:<project>` key, `project_site()` first takes the id of the site whose recorded source is the same key, so a renamed project still goes to its site and gains a revision. It does not do this for `formweb:receive:formweb` (the key of a send that carried no project: every such site shares it, and merging them would join unrelated sites) or when the id from the new name already exists. Sites that were imported the old way keep their address key (`formweb:http://127.0.0.1:8240`) and are not merged or moved: the old key says only which FormWeb answered, not which project was open, so there is no safe way to say which project such a site belongs to. The next Import of that project makes its own site; the old one is removed from Home when it is no longer needed.
- The CLI, the MCP tool and the HTTP route for Import are unchanged; what changed is the key under them. The reply is still the site record; the window reads `revisions` from it.

Not changed: FormPublisher still reads FormWeb only (`GET /api/export`, `/api/publications`, `/api/releases`, `/api/access`), never `/api/load`, and the vendored FormWeb core stays at 0.21.0: FormWeb 0.21.1 changes the version number and not the core code, and `./formpublisher vendor --check` says in step at 0.21.0.

Checked: against FormWeb on 8240 with the same data folder: Send four times then Import (six sites before and after; the fifth revision equals the fourth); Import then Send (one site, two revisions); a project that arrived through the inbox, then Import in German (one site, revision added); a site copied from the 0.3.0 data folder opens, previews, checks and builds. The check was run on sites made by hand with actions to an outside host, `localhost`, `/api/forms/...`, `192.168.x.x`, `//printer.local`, `[::1]`, `0.0.0.0`, `169.254.x.x`, a single-label host and `../api/forms/x` (all reported), and to `mailto:`, `?q`, `/search/`, `https://example.org/api/forms` and `10.0.0.1.nip.io` (none reported). The three FormWeb demos have 0 findings and Northwind Notes still has its 1 error and 2 warnings.

Also in 0.3.1 (no code): `NOTICE.md` and `demo/MEDIA.md` record every demo picture at its source (own work as Apache-2.0, the NASA pictures with the credit their source page states, the Hubble Ultra Deep Field as CC BY 4.0 with the credit "NASA, ESA, and S. Beckwith (STScI) and the HUDF Team"; it was "public domain" before, which its publisher does not say). `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md` and `SECURITY.md` follow the shape formvis and formdeck use. The Lowlight and Looking Back zips in `demo/sites/` are rebuilt from the corrected FormWeb sites, so the credits shown inside the demos (Lowlight's footer, Looking Back's picture credits) match the records; they are repacked by Phase 63's rule.

## Phase 68: the open items of 0.3.1 are fixed: demos update, old sites are adopted, Import lists projects, no-check builds say so, `external.request` is grouped · v0.3.3 (2026-11-15)

The 0.3.1 build notes listed six things as not fixed that belong to the engine; each is fixed here. The window's part (the project list, the tooltip, the language-switch work) is in `frontend/HASHOUT_LOG.md`, Phase 67.

- `app/services/demo_refresh.py` (new), `app/routers/demo.py`, `intake.import_zip_file(site_id=)`: `_open()` used to return an existing demo site as it was, so a demo opened by 0.3.0 never got the corrected credits that 0.3.1 put in the Lowlight and Looking Back zips. `refresh()` now runs when the demo's site exists. It builds a table of (path, SHA-256) for every file of the bundled zip (unzipped into a hidden `.demo-` folder under `sites/`, which `list_sites()` skips, and cached by the zip's path, mtime and size) and for every revision in the site's history, and adds the zip as a new revision of the same site (same id, `source` kept) only when no revision in the history equals it. Comparing with the whole history, not only the newest revision, means a second open adds nothing, and a bundle that equals any earlier revision is never added twice. It does nothing when the site has builds or prepared folders (`_touched()` looks for any non-hidden child in `builds/<id>` and `prepared/<id>`): the decision is that "changed" means the person built or prepared it, and a build is tied to one revision, so a demo someone worked from is not moved under them. Any read failure (`IntakeError`, `OSError`) leaves the site as it is. The reply gains `updated` (true when a revision was added); the window does not use it. `_finish()` already took `site_id`, so the new argument only passes it through.
- `app/services/intake.py`, `_address_site()` and `project_site()`: a site imported by 0.3.0 or earlier is keyed by FormWeb's address (`formweb:http://...`), which says which FormWeb answered and not which project was open, so 0.3.1 could not tell which project it belonged to and made a second site on the next Import. The name is the only extra evidence. When a project arrives for the first time (no site has its id and none has its key) and exactly one old address-keyed site has the same name (trimmed, case folded), `project_site()` returns that site's id, so the revision is added to it: its id, revisions, checks and builds stay and its `source` becomes `receive:<project>` like any project site. With two or more candidates (the same name from two FormWeb addresses, or two copies) nothing is adopted and a new site is made, because a wrong merge joins unrelated histories and cannot be undone by the person. Only sites whose source is kind `formweb` with an `http` or `https` address count, so a zip, a folder or a demo of the same name is never taken. The key `formweb:receive:formweb` (a send with no project) still never matches.
- `app/services/formweb.py`, `app/routers/formweb.py`, `app/cli.py`, `app/mcp.py`: Import from FormWeb read only the open site, so FormWeb's saved projects could not be imported. `projects()` reads `GET /api/projects` (read only) and `project_id()` for the open one, and answers the open project first: the saved row with its name and time when it is saved, else `{saved: false}` with the id (an unsaved site) or no id at all. A 404 from `/api/projects` (an older FormWeb) is an empty list, so the picker is never offered and Import behaves as before; any other failure is the usual refusal. `_clean_id()` keeps an id only if it is a string of at most 200 characters with no slash, no backslash and no leading dot, because the id goes into a URL path and into a site key. `import_project(project)`: no project, or the open project's id, goes through `import_current()` (the export, so unsaved changes come along); another id downloads `GET /api/projects/<id>/file` (the `.fweb` envelope, with the shared `_download()` that now takes the route, suffix and what it is downloading, and answers a 404 as `project-missing`) and compiles it here with `import_fweb_file()`, keyed `formweb:receive:<id>`, the key Send and the inbox use, so the site is the same one as that project's Send. FormWeb is never asked to open anything and `/api/load` is not called. The CLI has `formweb-projects` and `import-formweb --project ID`; the MCP server has `list_formweb_projects` (read only) and `project` on `import_formweb_current`; the HTTP route is `GET /api/formweb/projects` and `import-current` takes `{project}`. That makes 23 commands and 20 tools.
- `app/services/checks.py`, `external.request`: a page that links a remote file used to report once per reference, and FormWeb's product-site starter, which links remote media from many places, got 129 warnings. `external()` now only collects the references per full URL (not per host: two files on one host are two findings, each with its own fix) and `report_external()` runs once after every file is read and adds one warning per URL, on the first page by route and line, with `count` and `pages` on the problem. A URL used once keeps the old message; a URL used more than once says how many references and on which pages. The id is the usual static one (`static:external.request:<route>:<line>` of the first reference, `:2` when two addresses share that line, as `srcset` can); the URLs come in the order the files are scanned, so a rerun gives the same ids. The starter went from 129 to 84 warnings with the counts summing to 129 and every id unique.
- `app/services/package.py`, `_check_summary()`: a build made before any check ran wrote `checks: {errors: 0, warnings: 0, infos: 0, tiers: []}`, which reads as a clean result. It now returns `None` when no tier ran, and `publish.json` has `"checks": null`. Readers treat an empty `tiers` the same way (`frontend/src/api-builds.ts`, `demo/demo.js`), because builds written by 0.3.2 or earlier have the old shape and are not rewritten. The package manifest's other fields and the zip are unchanged, so a reproduce still gives the same hash.
- Docs: `docs/MANUAL.md`, the wiki pages Checks, Importing Sites and Packages and Signatures, `AGENTS.md`, `CLAUDE.md` and both copies of the two skills say the same; `CLAUDE.md` and the skillset skill list `GET /api/projects` and `GET /api/projects/{id}/file` among the read-only routes FormWeb is asked for. Release chores added the demo update, the tool and command counts and the toolbar paragraph in `docs/MANUAL.md` and `README.md`, and corrected the manual, which had described a toolbar that does not move at a language switch (see `frontend/HASHOUT_LOG.md`, Phase 67, for why it does).

Checked (the engine on 8280 and a FormWeb on its own port with its own data folder, the data under `/home/claude/work/run/formpublisher/turn5/`): Lowlight made the way 0.3.0's `_open` did went from 1 to 2 revisions on open (12 files changed, the corrected credit only in the new revision), a second open changed nothing, Looking Back (with a build) and Harbour Ferries (same zip) were not changed; Beta Works (one old site) was adopted, with id, 2 revisions and its build kept and its source now `receive:<id>`, and Alpha Studio (two old sites) got a new site with the old two untouched; the picker rows, `formweb-projects`, `import-formweb --project` and an unknown id (`project-missing`); a build with no checks has `"checks": null`, one with static checks has counts and tiers, and a `.fpub` of a null-checks build saves and opens; the starter 129 to 84.

## Phase 69: the vendored FormWeb core is 0.21.2 · v0.3.3 (2026-11-15)

`vendor/formweb-native` is FormWeb's `native/` workspace at its 0.21.2 release, copied unedited like Phase 65's 0.21.0 (`VENDOR.md` has the new tree ids; `Cargo.toml` and `Cargo.lock` carry the new version; `vendor/formweb-native/HASHOUT_LOG.md` carries FormWeb's own entry for the release). It brings what FormWeb added in 0.21.1 and 0.21.2 to `.fweb` projects opened here: a poster per component instance, a chosen look for a selected tab or filter chip, counters that keep their width, font faces carried with a pasted element, and a site search that starts from `?q=`. `NOTICE.md` names 0.21.2 in the row for the vendored crates. No dependency is added or removed: the crates keep the same licence (Apache-2.0) and the same dependencies. The three FormWeb demo sites in `demo/sites/` were exported again by FormWeb 0.21.2 so that the demos carry the same site runtime as FormWeb's own export: in each zip the one file that differs from 0.3.2 is `assets/runtime.js` (compared file by file by SHA-256: 54 files in Lowlight, 33 in Looking Back, 42 in Harbour Ferries, nothing added or removed). These zips are generated data, not hand-written source, and the credits, pictures and fonts inside them are unchanged, so `NOTICE.md` and `demo/MEDIA.md` stay as they are. Because a demo's bundled zip changed, a demo opened before the upgrade gets one new revision when it is next opened (Phase 68), unless it has a build or a prepared folder.

## Phase 70: the vendored FormWeb core stays 0.21.2; FormWeb 0.27.0 files open with it · v0.3.4 (2026-11-21)

FormWeb is at 0.27.0 and `vendor/formweb-native` is its `native/` at 0.21.2. The engine crates are the same source. A `git archive` of FormWeb's v0.27.0 `native/` compared with `vendor/formweb-native` (without `crates/formweb-render` and `target/`) differs in the workspace version in `Cargo.toml` and the four crate versions in `Cargo.lock`, nothing else, and the four tree ids in `VENDOR.md` are the ones v0.27.0 has. FormWeb's `CHANGELOG.md` for 0.21.3 to 0.27.0 names no change to the `.fweb` format (`com.nodemode.formweb`, versions 1 and 2, `schemaVersion` 1), to the export or to the crates: 0.21.3 is Windows set-up scripts, 0.22.0 to 0.27.0 are agents, the terminal panel, the desktop shell's start, a theme and the style sheet's names. FormWeb's `backend/app/assets.py` and `fpub.py`, which write the project files, and its export routes did not change between its 0.21.2 and 0.27.0 either.

What `compile.py` uses of the core is `hello`, `load {site}` and `export {locale, baseUrl, formsEndpoint, all}` over the JSON-lines protocol, on version 1 (JSON) and version 2 (zip) `.fweb` files; export zips and publication folders are read as plain files and do not touch the core.

Checked, in a scratch folder under /tmp (removed): `formweb-core` built from FormWeb's v0.27.0 `native/` and from this tree (`cargo build --release --locked`, 40 s and 50 s). `compile_fweb` opened FormWeb 0.27.0's three shipped demo projects (`frontend/public/demos/*/site.fweb`, version 1), a version 2 archive made from each, and a starter site made by the 0.27.0 core, with each core: 8 of 8 opened with no warning beyond the starter's example.com one, every output file byte for byte the same with both cores and between version 1 and 2, and for the three demos the same 54, 33 and 42 files, byte for byte, as `demo/sites/*.zip`, which FormWeb 0.21.2 exported. The command line imported, checked and built them with each core (same file list in `publish.json`). An export zip and a publication folder written with the 0.27.0 core imported as `zip` and `folder`. The one difference: `hello` reports the crate's own version, so a package built from a `.fweb` project records `source.formwebVersion` 0.21.2 (`package.py` `_source_block`) where the 0.27.0 core records 0.27.0, also for a project saved by FormWeb 0.27.0. Refreshing the copy is the step `VENDOR.md` describes and would change only that label (`Cargo.toml`, four lines of `Cargo.lock`, the table, the `NOTICE.md` row); it was not done because nothing is lost or refused.

## Phase 71: tests, the core says 0.27.0, templates to start from, a hosting guide · v0.4.0 (2026-11-22)

`backend/tests` is the engine's first suite (plain `pytest`, pinned in `requirements-test.txt`, which does not ship; 38 tests, about 11 s). `conftest.py` gives every test its own `FORMPUBLISHER_HOME`, an in-process `Client`, a `core` fixture that finds `formweb-core` (skips without it, fails with `FORMPUBLISHER_REQUIRE_CORE=1`, as CI's `tests` job sets), `.fweb` version 1 and 2 files made from the core's `new` starter (the repository ships no `.fweb`), and `asgi_call`, which drives `app.main:app` with a hand-made scope because the requirements carry `httpx2`, not the `httpx` Starlette's TestClient needs, and so the receive endpoint's loopback check sees a chosen client address. The templates tests serve a stand-in repository on a loopback port (`FORMPUBLISHER_TEMPLATES_URL`) and assert which paths it was asked for.

`vendor/formweb-native`: the documented `VENDOR.md` step with FormWeb's tag `v0.27.0` (`Cargo.toml` and `Cargo.lock` copied, the table's Version, Branch and native tree, the `NOTICE.md` row). The crate trees did not change. `hello` now answers 0.27.0, so `publish.json` records `formwebVersion` 0.27.0; FormWeb's three demo projects compile to the same bytes as `demo/sites/*.zip` (54, 33 and 42 files).

`services/templates.py`, `routers/templates.py`: the list is the `formweb` app of formai-templates' `index.json`, read only by `fetch()` (the window's Get the templates and Check again, the CLI's `templates --fetch`), never at start, and kept in `templates/index.json` with `fetchedAt`. Every item path and preview must be a relative POSIX path under `apps/formweb/` with no `.` or `..` part, no backslash, no drive and no leading slash; one bad path refuses the whole list and keeps nothing (a list with a planted path is not trusted in part). Only `kind: demo` items ending `.fweb` are offered (`start: true`): they are whole FormWeb projects. The 50 other FormWeb items are 21 components and 27 sections (`library/components`, `library/sections` in FormWeb), the `formai-studio` design preset and the `product-site` starter, which FormWeb's Python backend (`library_routes.library_apply_starter`) assembles from section ids, five of which the index does not carry; the vendored core cannot make a project of any of them, so they are counted (`notStartable`) and not offered. `start()` downloads one file, stops reading past the index's `bytes`, compares length and SHA-256 and keeps the file (in `templates/files/[sha256].fweb`) only on a match; opens it with `compile_fweb` as an import would; then writes the verified bytes to `[slug].fweb` in the chosen folder with an exclusive create. The file is FormWeb's own project file, which FormWeb opens with File, Import .fweb or .fpub file; FormPublisher never calls FormWeb's `/api/load`. Previews are fetched on demand through `GET /api/templates/preview?id=` (2 MiB cap, webp, png or jpg) only after the list was kept. `httpx2` here honours the system proxy (`trust_env` default), unlike the loopback FormWeb client.

`cli.py` `templates [--fetch]` and `start TEMPLATE --to FOLDER [--name N]`; `mcp.py` `list_templates` (reads the kept list only, fetches nothing) and `start_from_template` (openWorldHint, an absolute folder required). There is no MCP tool to fetch the list: the person asks for it.

## Phase 72: the desktop engine is a folder with a log, leaves with its shell, ships deep checks, and installs from hashed locks · v0.5.0 (2026-11-22)

`formpublisher_engine.py`: the three standard streams are replaced with the null device when they are `None`, before anything else is imported. A Windows program built without a console has none, and the first `print` or log line would raise. `serve` builds the uvicorn server first and attaches the log after, because uvicorn's own logging setup replaces the handlers of its loggers. `watch_parent` now asks `enginelog.watch_shell` first (the pid in `FORMPUBLISHER_SHELL_PID`, on every system); the old `getppid` poll stays for a POSIX start without that variable (`./formpublisher serve` under a terminal). On leaving, `engine.json` is removed before `os._exit(0)`, since the lifespan's own removal does not run on that path.

`services/enginelog.py` (new): `attach` adds one rotating file handler, `logs/engine.log` in the data folder (1 MB, 3 older files, opened on the first line), to the root logger, `uvicorn` and `uvicorn.access`; `uvicorn.error` reaches it through `uvicorn`, and adding it there too wrote every line twice. `attached` gives the path for messages. `alive` is `OpenProcess(SYNCHRONIZE)` and a zero wait on Windows (access denied counts as alive) and signal 0 elsewhere; `watch_shell` polls it every 2 s.

`main.py` `internal_error`: the answer was "see its log" with no log anywhere. It now names the file (`detail`, and `log` for the window), or says "the terminal that started it" when no file is attached (the in-process CLI and the tests).

`routers/checks.py` `_background`: `except Exception: pass` and then `checks.done` with the old summary made a failed deep run look finished. The failure is logged with its traceback, and the event is `checks.failed` (run, site, revision, tier `deep`, reason: the first line of the message cut to 200 characters, or the class name). `deep.execute` already turns a missing browser into `deep.unavailable`, which still ends in `checks.done`; only an unexpected failure takes the new path.

`routers/docs.py` (new): `GET /api/docs/manual` serves `docs/MANUAL.md` from the resource folder and `GET /api/docs/images/{name}` its screenshots (the name must match `^[a-z0-9][a-z0-9-]*\.webp$` and resolve directly inside `docs/images`). Help opens these in the window, so it works with the network off and while the repository is private. `docs/HOSTING.md` is still bundled into the window at build time; the manual is three times its size and has pictures, so it is fetched when asked for.

`services/deep.py`: `launch` tries the `chrome` channel and then `msedge` before the known paths, so a Windows machine with only Edge runs deep checks. In a frozen engine `deep.unavailable` carries `BROWSER_FIX` (install Chrome or Edge, or set the path in Preferences) instead of the advice to run the install script, which an installed app does not have.

Deep checks ship (the handoff's item 1.4, decided for the person using the app): `setup/freeze_backend` collects all of `playwright`, including the Node.js driver it carries (119 files under `_internal/playwright/driver` in the Linux freeze, with its `LICENSE` and notices), and `NOTICE.md` lists Playwright, the Node.js runtime inside the driver and greenlet as shipped. No browser is downloaded or shipped.

`setup/freeze_backend`: `--onedir` on every system, `--noconsole` on Windows (`FORMPUBLISHER_ENGINE_WINDOWED=0` keeps the console for a debugging build). The folder goes to `src-tauri/engine/` (its `.gitkeep` is kept) and Tauri ships it as the resource `engine`. A one-file freeze made PyInstaller's bootloader the process the shell started, with Python as its child, and unpacked everything to a temporary folder at each launch. On macOS `flatten_engine` replaces `Python.framework` with its library and every symbolic link with a copy, because Tauri copies resources file by file, and `sign_engine` signs each Mach-O file with the hardened runtime, a timestamp and the entitlements when `APPLE_SIGNING_IDENTITY` is set; both functions are FormVis's (`setup/freeze_backend` there, Apache-2.0, the same owner) with this script's `die` and `say`. The self-check runs on the folder that will ship, after flattening and signing, and the list of frozen files is written to `backend/build/engine-files.txt` so NOTICE can be held against it.

Locks: `requirements-build.txt` pins PyInstaller 6.22.3 (it was a variable inside the freeze script, installed without a hash). `setup/lock_requirements.py` writes `requirements.lock` (runtime, deep, build) and `requirements-test.lock` (those and pytest) with `uv pip compile --universal --generate-hashes` for Python 3.12, uv pinned at 0.11.32, so one lock serves Linux, macOS and Windows with markers (`pefile`, `pywin32-ctypes`, `macholib`, `uvloop`). `requirements-extra-hashes.json` adds one hash to `cryptography==50.0.2`: the wheel formcompiler supplies for Intel Macs through `PIP_FIND_LINKS` (its public `deps-macos-x64.json` lists it), which `--require-hashes` would otherwise refuse. `--check` confirms each lock holds every pin of its requirement files and has hashes; it does not need uv or the network. The install scripts, the freeze and CI install with `pip install --require-hashes -r backend/requirements.lock`; the `--upgrade pip` line is gone from the install scripts, since an unpinned pip was the last floating piece. `backend/boot_backend` still installs from `requirements.txt` for a quick development start.

`setup/i18n_check.py` (new, CI's engine job): every key of `frontend/src/i18n/keys/*.json` has a non-empty translation in each of the 25 locale folders, with the same placeholders (a plural form `{0:one=...}` counts as `{0}`), no em dash, no stray key and no locale folder missing from `index.ts`'s list.

Checked here (Linux, Python 3.12.3): a venv made from `requirements-test.lock` with `--require-hashes`; `python -m pytest -q backend/tests`, 38 passed; `setup/freeze_backend` end to end, 2056 files, 255 MB, the frozen folder's `--selfcheck` OK with the core, the demo and the window found; the frozen engine started with `FORMPUBLISHER_SHELL_PID` naming a stand-in process, wrote `logs/engine.log` and `engine.json`, answered health as frozen, and after the stand-in was ended it logged why and was gone in 1.7 s with `engine.json` removed. Not run: any freeze on macOS or Windows (`flatten_engine`, `sign_engine` and `--noconsole` have not executed anywhere for this app), a deep check from the frozen engine, the Intel Mac install against formcompiler's wheel.
