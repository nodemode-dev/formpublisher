---
name: formpublisher-skillset
description: Use for any change to FormPublisher's own code, the Form family's site publisher. Covers the FastAPI engine in backend/app (routers, services, the site intake of FormWeb exports and publication folders, the read-only FormWeb connection, settings and the data folder), the vanilla TypeScript and Vite interface in frontend (the shell, Home, tabs, routes strip, inspector, status bar, tokens and the zero-flash rules), the command line and MCP server behind backend/formpublisher_engine.py, the Tauri 2 shell in src-tauri and its frozen engine sidecar, and the ./formpublisher scripts. Trigger on FormPublisher source files, a new route, a new tool, an engine or interface bug, ports 8280 or 5280, or HASHOUT_LOG. Not for driving FormPublisher to import and list sites (use formpublisher-harness).
metadata:
  version: "0.1.3"
---

# formpublisher-skillset

Route every change to FormPublisher's code through this file. It maps where the code lives and states the rules that hold everywhere.

## Where the code lives

| Area | Root |
| --- | --- |
| Engine entry | `backend/formpublisher_engine.py` (serve, `--selfcheck`, `cli`, `mcp`) |
| Engine routes | `backend/app/routers/[name].py`, each exporting `router`, auto-included by `backend/app/main.py` |
| Engine services | `backend/app/services/[name].py`: paths and the data folder, settings, site intake, the FormWeb connection, `compile` (formweb-core for .fweb), `host` (static host on 8281, served by `backend/app/host.py`), `checks` and `deep`, `package` and `keys`, `publish` and `inbox` (prepared folders per host, and FormWeb's Send to FormPublisher), `pipeline` (the optional check and build on arrival) and `revisions` (revision lists and diffs); `backend/app/static/probe.js` is the preview probe |
| Host targets | `backend/app/targets/[id].py`, one adapter per host (`ID`, `NAME`, `DESCRIPTION`, `LOCAL_TOOL`, `prepare`), discovered by `backend/app/targets/__init__.py`; adding a host is adding a module |
| Command line and MCP | `backend/app/cli.py` (`Client`: HTTP to a running engine, else the same services in-process) and `backend/app/mcp.py` (one tool per `Client` method); a new route gets a `Client` method, a command and a tool together |
| Interface | `frontend/src/`: the shell, Home, tabs, routes strip, inspector, status bar; styles and tokens in `frontend/src/styles/` |
| Desktop shell | `src-tauri/` (Tauri 2) and the frozen engine sidecar from `setup/freeze_backend` |
| Scripts | `./formpublisher`, `./formpublisher_oc_install`, `./build_app`, each with a `.bat` twin; `setup/agents.py`, `setup/lib.sh` |
| Agent kit | `.claude/skills` (source), `.agents/skills` (mirror), `.mcp.json`, `.codex/config.toml`, `.cursor/mcp.json` |
| Docs | `docs/MANUAL.md`, `.docs/wiki/`, `README.md`, `CHANGELOG.md`, `NOTICE.md` |

## How the pieces depend

```text
backend/app/services (paths, settings, site intake, the FormWeb reader)
  -> backend/app/routers (one router per file, auto-included)
       -> frontend over /api and the live WebSocket
       -> the command line and MCP server over the same routes
  -> backend/formpublisher_engine.py (PyInstaller entry) -> src-tauri sidecar
```

## The laws

- **The engine does the work.** Every capability is a route; the window, the command line and the MCP server are surfaces over it. A capability one surface has and another lacks is a bug: add the route, then the command and tool, then the pane.
- **FormWeb is read, never written.** Import zips and folders, and call only a running FormWeb's read-only routes (`/api/export`, `/api/publications`, `/api/releases`). Never `/api/load`.
- **The engine stays on loopback.** 127.0.0.1:8280, exact Host check, no other origin drives it.
- **Zero flash.** Every container exists in its final layout before the first paint and is filled in place. Every `z-index` is a layer token from `frontend/src/styles/tokens.css`. Icons are inline `currentColor` SVG; no icon libraries.
- **Surgical edits.** Hand-made edits, one region at a time; no codemods or scripted text replacement. No emoji, no em dashes in Markdown, no commented-out code, near-zero comments: the reasoning goes in the HASHOUT logs.
- **Read the logs first.** `backend/HASHOUT_LOG.md`, `frontend/HASHOUT_LOG.md`, `src-tauri/HASHOUT_LOG.md` and each module's own `HASHOUT_LOG.md`. Planning documents are in the sidecar, not in this tree.
- **Keep the agents in step.** After changing a command, a tool or a skill, run `./formpublisher agents sync` (it mirrors `.claude/skills` to `.agents/skills` and checks the skill files; `--check` fails on drift).
- **Versions** are `X.Y.Z`; `frontend/package.json`, `backend/app/__init__.py`, `src-tauri/tauri.conf.json` and `src-tauri/Cargo.toml` carry the same one.
- **Dependencies** each get a row in `NOTICE.md`. GPL stays out of the distributed bundle.
- **Commits** as `nodemode-ai <mackin@nodemode.ai>` only, no trailers of any kind (see `CLAUDE.md`).

## Run it

```bash
./formpublisher_oc_install     # backend venv and interface packages
./formpublisher boot           # engine on 127.0.0.1:8280 and interface on localhost:5280
./formpublisher serve          # the built interface served by the engine on 8280
./formpublisher run status     # the command line
./formpublisher mcp            # the MCP server on stdio
./formpublisher doctor         # toolchain, installs and ports
FORMPUBLISHER_HOME=/tmp/fp ./formpublisher run sites   # a scratch data folder
```
