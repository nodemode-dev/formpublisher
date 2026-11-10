# Changelog

## 0.1.0 · 2026-11-09

The first release: FormPublisher opens what FormWeb makes and shows every route of it.

- **Import:** a FormWeb `site-export.zip`, a FormWeb publication folder, or the site open in a running FormWeb (read through its export, never changed), dropped on Home, picked from File, or sent from the command line or MCP. Archives unpack safely; importing the same source again adds a revision.
- **Window:** FormDeck's layout and look: Home with a drop zone, recent sites and trash; one tab per site; the routes strip; the stage; Problems, Console and Network panels; the inspector's Site group; and the status bar. 30 commands drive the menus (native on macOS), the command palette and the shortcuts. Preferences hold the language, theme, accent, density and FormWeb address. 26 languages. The dark and light marks swap with the theme.
- **Engine:** FastAPI on 127.0.0.1:8280 with a loopback guard, a live event socket, a CLI (`status`, `sites`, `import`, `import-formweb`, `routes`) and an MCP server with the same five tools.
- **Desktop:** a Tauri 2 shell with the splash and reveal from FormDeck; its first compile is the first desktop build.

- **Repository:** launchers `formpublisher`, `formpublisher_oc_install` and `build_app`, each with a `.bat` twin; `setup/lib.sh`, `setup/agents.py` and `setup/freeze_backend`; the license (GPL-3.0-only, Copyright 2026 NodeAgentc, Inc.), `.gitignore`, `.gitattributes` and `.editorconfig`.
- **Community:** `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `NOTICE.md`, `.github/CODEOWNERS` and a CI workflow with a `frontend` job (audit, type check, build) and an `engine` job (self check, compile, agent skills in step, shell syntax).
- **Agents:** `CLAUDE.md`, `AGENTS.md`, `.claude/settings.json` with attribution off, the `formpublisher-harness` and `formpublisher-skillset` skills mirrored to `.agents/skills`, and MCP wiring for Claude Code, Codex and Cursor.
- **Docs:** the README, a short manual in `docs/MANUAL.md` and the wiki in `.docs/wiki`.
- **Identity:** the FormPublisher icon set for the app, the README and the window.
- Ports and paths: engine 127.0.0.1:8280, interface 5280, preview 5281, data folder `~/FormPublisher` (`FORMPUBLISHER_HOME`).
- Not covered: device preview, checks, packaging, signing, publishing and the desktop build are in development.
