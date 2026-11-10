# Changelog

## 0.0.0 · 2026-11-09

The foundations; no release yet. The first release, 0.1.0, follows in a later commit.

- **Repository:** launchers `formpublisher`, `formpublisher_oc_install` and `build_app`, each with a `.bat` twin; `setup/lib.sh`, `setup/agents.py` and `setup/freeze_backend`; the license (GPL-3.0-only, Copyright 2026 NodeAgentc, Inc.), `.gitignore`, `.gitattributes` and `.editorconfig`.
- **Community:** `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `NOTICE.md`, `.github/CODEOWNERS` and a CI workflow with a `frontend` job (audit, type check, build) and an `engine` job (self check, compile, agent skills in step, shell syntax).
- **Agents:** `CLAUDE.md`, `AGENTS.md`, `.claude/settings.json` with attribution off, the `formpublisher-harness` and `formpublisher-skillset` skills mirrored to `.agents/skills`, and MCP wiring for Claude Code, Codex and Cursor.
- **Docs:** the README, a short manual in `docs/MANUAL.md` and the wiki in `.docs/wiki`.
- **Identity:** the FormPublisher icon set for the app, the README and the window.
- Ports and paths: engine 127.0.0.1:8280, interface 5280, preview 5281, data folder `~/FormPublisher` (`FORMPUBLISHER_HOME`).
- Not covered: device preview, checks, packaging, signing, publishing and the desktop build are in development.
