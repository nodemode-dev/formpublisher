# Architecture

```text
interface (vanilla TypeScript, Vite, port 5280)
  shell: title bar, tabs, routes strip, inspector, bottom panel, agent dock, status bar, Home, theme boot, 26 interface languages switched in place
    -> HTTP /api/* and the live WebSocket
engine (Python 3.12, FastAPI, 127.0.0.1:8280)
  routers: one file each under backend/app/routers, auto-included
  services: paths and the data folder, settings, site intake, the read-only FormWeb connection
    -> data folder (FORMPUBLISHER_HOME): sites, settings
    -> a running FormWeb on loopback: read-only GETs only (export, publications, releases, access, projects)
site host (ASGI app.host, 127.0.0.1:8281): the mounted revision, probe script, no /api
  services: host, checks, deep (Chrome or Edge via Playwright, served through the host), package, keys (secrets in the system password store), compile (formweb-core), trash, enginelog, window_key, terminal (PTY tabs), agent_programs (the agent programs, their tab folders and keys), agent_lookup (the family's finder)
  -> data folder: checks/, builds/, keys/ (index.json), trash/, logs/engine.log, engine.json, engine.key, agent-tabs/
command line and MCP server -> the same routes, with the key from engine.key
desktop shell (Tauri 2) -> frozen engine folder src-tauri/engine, program formpublisher-engine
```

## The interface

The shell builds every container in its final layout before the first paint, and the inline boot script sets the theme and density on the root so nothing moves when the window is revealed. Every `z-index` comes from a layer token in `frontend/src/styles/tokens.css`; icons are inline `currentColor` SVG.

The tokens use the family's names. The type scale is `--fs-9` to `--fs-18` and the frame sizes are `--cv-titlebar-h`, `--cv-tabs-h`, `--cv-options-h`, `--cv-status-h` and `--cv-rail-w` (FormPublisher's own values for the heights: 44, 32, 44 and 28 px); `--fp-strip-w`, `--fp-props-w`, `--fp-bottom-h` and `--fp-pasteboard` stay, because the family has no name for them. The accent is `#5fe07a`, with a dark ink on it (`--text-on-accent`, computed per accent), and on the light themes accent text and icons use `--accent-ink`, the accent mixed toward black until it reads at 4.5 to 1 (`themes.ts` and the inline boot script both compute it). Every chooser is `ui/dropdown.ts`, the family's dropdown, never a native select. `ui/resizers.ts` resizes the routes strip, the inspector and the bottom panel and folds the strip to a rail, and `ui/prefs-keys.ts` and `ui/prefs-checks.ts` are the Signing keys and Checks panels of Preferences.

## The engine

`app.main` includes `router` from every `routers/*.py`; a router that fails to import is listed in `/api/health` and the rest keep working. The engine listens on 127.0.0.1 only and refuses a Host or Origin it does not expect. `backend/formpublisher_engine.py` is the entry: it serves, runs `--selfcheck`, and takes the subcommands `cli` and `mcp`.

## The guards

`services/window_key.py` makes two keys at each engine start, and `WindowKeyGuard` (middleware in `app.main`) refuses any request that is not GET, HEAD or OPTIONS without one of them in the header `X-FormPublisher-Key`: 403, code `forbidden`. The window's key goes to the desktop shell on standard output and from there into the page by an initialization script; a browser tab on the development start claims it with `POST /api/window/key`, which answers only the window's own origins (and nothing at all when the desktop app started the engine). The second key is written to `engine.key` in the data folder (user-only, new at every start, removed at exit) for the command line and the MCP server, whose `Client` sends it with every change. `POST /api/receive/formweb` keeps its own rule, this computer only. A new write route needs nothing extra, and nothing is added to the short open list. The window is `frontend/src/window-key.ts` adding the key to every request to the engine's `/api/`. A third kind of key belongs to one agent tab of the dock: `window_key.issue_tab` makes it and `revoke_tab` ends it, the guard's `valid` accepts the window's key, the engine's key or a live tab's key, and the terminal router checks `personal`, which accepts the first two only, so a tab's key cannot open, change or attach terminal tabs.

The engine answers `index.html` with a Content-Security-Policy header (its own scripts and the hash of the inline theme boot, the site host as the only frame and outside image source, the live socket, nothing else). In `src-tauri`, only the engine's own origin may use the shell's commands: the capability names `http://127.0.0.1:8280/*`, another port is granted at run time for that one origin, and the splash has its own policy in `tauri.conf.json`. `services/keys.py` keeps each signing key's private half in the system password store (keyring 25.7.0) and answers every listing from `keys/index.json`.

## FormWeb

FormPublisher reads FormWeb and never writes to it. It imports a `site-export.zip` or a publication folder, and may call a running FormWeb's read-only `GET /api/export`, `/api/publications`, `/api/releases`, `/api/access`, `/api/projects` and `/api/projects/[id]/file`. It never calls `/api/load`.

## Desktop

The Tauri 2 shell in `src-tauri/` runs the engine frozen as a folder, built by `setup/freeze_backend` (PyInstaller `--onedir`) into `src-tauri/engine/` and shipped as the resource folder `engine`: `formpublisher-engine` inside it, with Playwright and its Node.js driver frozen in. The shell reads `engine.json`, ends and replaces an engine that file names and that still answers `/api/health`, then starts its own with `FORMPUBLISHER_SHELL_PID` and `FORMPUBLISHER_DESKTOP=1` and waits up to 10 seconds for the window key the engine hands over; the engine watches the shell's process and leaves within about 2 seconds of its disappearing (on Windows the shell also holds it in a job object). When the engine does not start, a native dialog says why. The engine's log is `logs/engine.log` in the data folder. Help > Documentation shows the manual the engine bundles. The desktop build is in development.

## The agent dock

The dock is two shared pieces and FormPublisher's own glue between them. Both pieces are copied from FormVis and never edited here.

- `frontend/src/dock/` is the dock module, 2.2.1, 15 files copied byte for byte. Its `MANIFEST.json` lists each file's SHA-256, and `setup/dock_check.py` (a CI step) fails naming any file that differs, is missing or is extra. `frontend/tsconfig.dock.json` compiles the folder with the seven strict flags its contract names (`npm run typecheck:dock`, also in CI). The module's English words go through the window's `t()`, never edited.
- `backend/app/services/agent_lookup.py` is the family's finder, version 1.0.1, copied unchanged from FormVis. `setup/agents.py` records its SHA-256 per version (`LOOKUP_HASHES`) and `./formpublisher agents sync --check` fails naming the file when its bytes differ.
- `frontend/src/dock-adapter.ts` is the glue on the window's side: FormPublisher's words, the kinds the engine says it can open (Claude Code is always offered beside a shell, so the ask line and its install note show), the ticket and the stream, the agent status from `/api/agent-programs`, and the placement (the module's own: bottom, or right from 960 px, remembered). `styles/dock-tokens.css` maps the module's tokens to FormPublisher's; the dock's accent is the accent ink. `ui/chrome.ts` mounts it and adds the title bar button, View, Agent Dock and the palette entry.
- `backend/app/services/terminal.py` runs the tabs: a PTY each (ptyprocess on macOS and Linux, pywinpty on Windows) with 256 KB of scrollback replayed on attach, restart, resize and close; a slow reader loses output and never blocks the program; every tab is closed at engine shutdown. A stream opens only with a one-use ticket (60 seconds) bought with the window's key. `routers/terminal.py` has the routes and `routers/agent_programs.py` answers `GET /api/agent-programs`.
- `backend/app/services/agent_programs.py` passes what is FormPublisher's own into the finder (the four `FORMPUBLISHER_*_BIN` variables), keeps a 30 second status cache, and opens the agent tabs: a folder `agent-tabs/[id]/` (0700) with `tab.key` (0600) and the program's entry for the MCP server `formpublisher_tab`, which runs `mcp --tab-key-file` (`cli.Client` takes a key at construction). Claude Code reads `mcp.json` there, Cursor `.cursor/mcp.json`, Antigravity `.agents/mcp_config.json`, and Codex gets `-c` values. The key is revoked when the program ends or the tab closes, and the folder is removed at close. A plain shell gets none of this.

Only stand-in programs have been used to check any of it.

## Living logs

`frontend/HASHOUT_LOG.md`, `backend/HASHOUT_LOG.md`, `src-tauri/HASHOUT_LOG.md` and one `HASHOUT_LOG.md` per module folder hold what comments would have said. Read them before editing.
