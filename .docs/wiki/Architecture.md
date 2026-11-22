# Architecture

```text
interface (vanilla TypeScript, Vite, port 5280)
  shell: title bar, tabs, routes strip, inspector, status bar, Home, theme boot, 26 interface languages switched in place
    -> HTTP /api/* and the live WebSocket
engine (Python 3.12, FastAPI, 127.0.0.1:8280)
  routers: one file each under backend/app/routers, auto-included
  services: paths and the data folder, settings, site intake, the read-only FormWeb connection
    -> data folder (FORMPUBLISHER_HOME): sites, settings
    -> a running FormWeb on loopback: read-only GETs only (export, publications, releases, access, projects)
site host (ASGI app.host, 127.0.0.1:8281): the mounted revision, probe script, no /api
  services: host, checks, deep (Chrome or Edge via Playwright, served through the host), package, keys, compile (formweb-core), trash, enginelog
  -> data folder: checks/, builds/, keys/, trash/, logs/engine.log, engine.json
command line and MCP server -> the same routes
desktop shell (Tauri 2) -> frozen engine folder src-tauri/engine, program formpublisher-engine
```

## The interface

The shell builds every container in its final layout before the first paint, and the inline boot script sets the theme and density on the root so nothing moves when the window is revealed. Every `z-index` comes from a layer token in `frontend/src/styles/tokens.css`; icons are inline `currentColor` SVG.

## The engine

`app.main` includes `router` from every `routers/*.py`; a router that fails to import is listed in `/api/health` and the rest keep working. The engine listens on 127.0.0.1 only and refuses a Host or Origin it does not expect. `backend/formpublisher_engine.py` is the entry: it serves, runs `--selfcheck`, and takes the subcommands `cli` and `mcp`.

## FormWeb

FormPublisher reads FormWeb and never writes to it. It imports a `site-export.zip` or a publication folder, and may call a running FormWeb's read-only `GET /api/export`, `/api/publications`, `/api/releases`, `/api/access`, `/api/projects` and `/api/projects/[id]/file`. It never calls `/api/load`.

## Desktop

The Tauri 2 shell in `src-tauri/` runs the engine frozen as a folder, built by `setup/freeze_backend` (PyInstaller `--onedir`) into `src-tauri/engine/` and shipped as the resource folder `engine`: `formpublisher-engine` inside it, with Playwright and its Node.js driver frozen in. The shell reads `engine.json`, ends and replaces an engine that file names and that still answers `/api/health`, then starts its own with `FORMPUBLISHER_SHELL_PID` and `FORMPUBLISHER_DESKTOP=1`; the engine watches the shell's process and leaves within about 2 seconds of its disappearing (on Windows the shell also holds it in a job object). When the engine does not start, a native dialog says why. The engine's log is `logs/engine.log` in the data folder. Help > Documentation shows the manual the engine bundles. The desktop build is in development.

## Living logs

`frontend/HASHOUT_LOG.md`, `backend/HASHOUT_LOG.md`, `src-tauri/HASHOUT_LOG.md` and one `HASHOUT_LOG.md` per module folder hold what comments would have said. Read them before editing.
