# HASHOUT_LOG · backend · formpublisher

The living log of the FormPublisher engine. Read it before editing `backend/`. The code carries no comments; the reasons live here, one entry per file.

Current build version: v0.1.4
Last updated: 2026-11-10 · Phases 13 to 15: trash service, engine.json, deep run through the site host, version 2 .fweb projects

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
