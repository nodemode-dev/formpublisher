# HASHOUT_LOG · backend · formpublisher

The living log of the FormPublisher engine. Read it before editing `backend/`. The code carries no comments; the reasons live here, one entry per file.

Current build version: v0.1.0
Last updated: 2026-11-10 · Phase 2 engine skeleton and site intake

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
    ├── routers/
    │   ├── health.py         GET /api/health
    │   ├── settings.py       GET, PUT /api/settings
    │   ├── sites.py          /api/sites, import, routes, delete
    │   ├── live.py           WS /api/live
    │   └── formweb.py        /api/formweb status, publications, import-current
    └── services/
        ├── paths.py          ports, origins, data folder, frontend dist
        ├── settings.py       settings.json with validated keys
        ├── bus.py            in-process event bus
        ├── intake.py         safe unzip, folder copy, site records, routes, redirects
        └── formweb.py        read-only FormWeb client
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
