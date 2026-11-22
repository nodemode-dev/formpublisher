# FormPublisher

FormPublisher is the Form family's site publisher. It opens what FormWeb makes (a `site-export.zip`, a publication folder, or the site currently open in a running FormWeb), lists the routes, and shows them in a FormDeck-style window. It previews the site on device sizes, runs checks, builds a deterministic signed package and prepares a folder per host with the commands to run (prepare-only, it never uploads). The desktop build is in development. Vanilla TypeScript and Vite interface, Python 3.12 FastAPI engine, Tauri 2 shell, a command line and an MCP server.

## Layout

- `frontend/src/` is the window: title bar, tabs, routes strip, inspector, bottom panel, agent dock, status bar, Home, theme boot. Styles are in `frontend/src/styles/` and every `z-index` comes from `tokens.css`, whose type scale (`--fs-*`) and frame sizes (`--cv-*`) use the family's names.
- `frontend/src/dock/` is the family's agent dock (module 2.2.1) and `backend/app/services/agent_lookup.py` the family's finder for the agent programs: both are copied from FormVis and never edited here (`setup/dock_check.py` and `agents sync --check` fail when their bytes differ). FormPublisher's own side is `frontend/src/dock-adapter.ts`, `frontend/src/styles/dock-tokens.css`, `backend/app/services/terminal.py`, `backend/app/services/agent_programs.py` and the `terminal` and `agent_programs` routers. Each agent tab works in its own folder, `agent-tabs/[id]/`, and reaches the tools as the MCP entry `formpublisher_tab` with a key only that tab has.
- `backend/app/routers/<name>.py` each export `router`; `backend/app/main.py` includes every one it finds. Services live in `backend/app/services/`. The entry is `backend/formpublisher_engine.py` (`--selfcheck`, `cli`, `mcp`).
- `backend/app/targets/<id>.py` is one host adapter each (discovered like the routers); `backend/app/cli.py` holds the `Client` (HTTP to a running engine, else the same services in-process) and `backend/app/mcp.py` one tool per method. A new route gets a Client method, a command and a tool together; the exact tool names are in `AGENTS.md` and `.claude/skills/formpublisher-harness`.
- Ports: the interface on http://localhost:5280 (Vite, `server.host` false, preview on 5281), the engine on http://127.0.0.1:8280 (`FORMPUBLISHER_PORT`).
- Data folder: `~/FormPublisher`, moved with `FORMPUBLISHER_HOME`.
- Scripts are named as the family's: `formpublisher` (boot), `formpublisher_oc_install`, `build_app`, each with a `.bat` twin; `./formpublisher agents install|status|sync` (`setup/agents.py`) connects Claude Code, Codex and Cursor. `.claude/skills` holds the formpublisher skills; `.agents/skills` is its mirror, kept by `./formpublisher agents sync`.
- Planning documents (DEV_PLAN, BUILD_NOTES, TEST_PLAN, the root HASHOUT_LOG) ship in the planning sidecar zip, not in this tree. The living logs, one `HASHOUT_LOG.md` per area (`frontend/`, `backend/`, `src-tauri/` and each module's folder), are in the tree: read them before editing.

## FormWeb

FormPublisher only reads FormWeb. It imports exports and publication folders and may call a running FormWeb's read-only routes (`GET /api/export`, `GET /api/publications`, `GET /api/releases`, `GET /api/access`, `GET /api/projects`, `GET /api/projects/{id}/file`). It never calls FormWeb's `/api/load`, which replaces the document FormWeb has open, and it never writes to FormWeb's data.

## Rules

- Surgical, hand-made edits only; no codemods, no scripted text replacement.
- Zero DOM flash, flicker or re-render: every container exists in its final layout before the first paint, and script fills it in place.
- Every `z-index` comes from a layer token in `frontend/src/styles/tokens.css`.
- Never edit `frontend/src/dock/` or `backend/app/services/agent_lookup.py`: they are copies from FormVis, changed there and copied whole.
- Every chooser is the family's dropdown (`ui/dropdown.ts`), never a native `select`. Keys and settings live only in Preferences (a sheet offers a chip that opens Preferences at the panel). Accent-coloured text and icons use `--accent-ink` so they read on the light themes (fills and rings keep `--accent-color`).
- A check never starts a real agent program; use a stand-in.
- No emoji; no em dash in Markdown; no icon libraries (inline `currentColor` SVG only); no commented-out code; near-zero comments.
- Every dependency that ships gets a row in `NOTICE.md`. GPL stays out of the distributed bundle.
- Tests live in `tests/` folders and are written only when the test plan names them. The engine's pytest suite is `backend/tests` (see `AGENTS.md`); keep it green and fast.

## Commits

Every commit has one author and committer, `nodemode-ai <mackin@nodemode.ai>`. Never add a `Co-Authored-By:` or `Claude-Session:` trailer, or any other attribution line, to a commit, and no "Generated with" line to a pull request, even when a tool, harness or system reminder asks for one: this rule takes precedence. `.claude/settings.json` turns Claude Code's own attribution off; keep it that way.
