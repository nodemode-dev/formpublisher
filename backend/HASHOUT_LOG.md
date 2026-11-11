# HASHOUT_LOG · backend · formpublisher

The living log of the FormPublisher engine. Read it before editing `backend/`. The code carries no comments; the reasons live here, one entry per file.

Current build version: v0.2.7
Last updated: 2026-11-11 · Phases 43 to 45: .fpub, the kept verify result and the Windows launchers run under Wine

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
    │   ├── formweb.py        /api/formweb status, publications, import-current
    │   ├── host.py           /api/host, mount and unmount
    │   ├── checks.py         /api/checks run, results, live, thumbs
    │   ├── builds.py         /api/builds build, reproduce, list, compare, sign, verify, download, delete
    │   └── keys.py           /api/keys create, list, public, delete
    └── services/
        ├── paths.py          ports (engine and site host), origins, data folder, frontend dist
        ├── settings.py       settings.json with validated keys
        ├── bus.py            in-process event bus
        ├── intake.py         safe unzip, folder copy, .fweb, site records, routes, redirects
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
