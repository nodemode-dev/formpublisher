# Architecture

```text
interface (vanilla TypeScript, Vite, port 5280)
  shell: title bar, tabs, routes strip, inspector, status bar, Home, theme boot, 26 interface languages switched in place
    -> HTTP /api/* and the live WebSocket
engine (Python 3.12, FastAPI, 127.0.0.1:8280)
  routers: one file each under backend/app/routers, auto-included
  services: paths and the data folder, settings, site intake, the read-only FormWeb connection
    -> data folder (FORMPUBLISHER_HOME): sites, settings
    -> a running FormWeb on loopback: GET /api/export only
site host (ASGI app.host, 127.0.0.1:8281): the mounted revision, probe script, no /api
  services: host, checks, deep (Chrome via Playwright, served through the host), package, keys, compile (formweb-core), trash
  -> data folder: checks/, builds/, keys/, trash/, engine.json
command line and MCP server -> the same routes
desktop shell (Tauri 2) -> frozen engine sidecar formpublisher-engine
```

## The interface

The shell builds every container in its final layout before the first paint, and the inline boot script sets the theme and density on the root so nothing moves when the window is revealed. Every `z-index` comes from a layer token in `frontend/src/styles/tokens.css`; icons are inline `currentColor` SVG.

## The engine

`app.main` includes `router` from every `routers/*.py`; a router that fails to import is listed in `/api/health` and the rest keep working. The engine listens on 127.0.0.1 only and refuses a Host or Origin it does not expect. `backend/formpublisher_engine.py` is the entry: it serves, runs `--selfcheck`, and takes the subcommands `cli` and `mcp`.

## FormWeb

FormPublisher reads FormWeb and never writes to it. It imports a `site-export.zip` or a publication folder, and may call a running FormWeb's read-only `GET /api/export`. It never calls `/api/load`.

## Desktop

The Tauri 2 shell in `src-tauri/` runs the engine as a frozen sidecar built by `setup/freeze_backend` (PyInstaller, one file, `formpublisher-engine`). The desktop build is in development.

## Living logs

`frontend/HASHOUT_LOG.md`, `backend/HASHOUT_LOG.md`, `src-tauri/HASHOUT_LOG.md` and one `HASHOUT_LOG.md` per module folder hold what comments would have said. Read them before editing.
