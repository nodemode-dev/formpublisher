# FormPublisher

The Form family's site publisher. It opens what FormWeb makes (a `site-export.zip`, a publication folder, or the site currently open in a running FormWeb), lists the routes, and shows them in a FormDeck-style window. Vanilla TypeScript and Vite interface, Python 3.12 FastAPI engine, Tauri 2 shell, and a command line with an MCP server. Device preview, checks, packaging, signing, publishing and the desktop build are in development.

## Driving FormPublisher (natural language)

When the person wants a site opened, imported, listed or inspected, use the `formpublisher` MCP server's tools guided by the `formpublisher-harness` skill in `.agents/skills/formpublisher-harness`. Start with `status` (the engine, the data folder, whether a FormWeb is reachable), then `sites` to list what is imported, `import` to bring in a `site-export.zip`, a publication folder or the site open in FormWeb, and `routes` to list a site's routes. Ask the person before importing from a running FormWeb, and never call FormWeb's `/api/load`: FormPublisher only reads FormWeb.

The MCP server is configured for Claude Code in `.mcp.json`, for Codex in `.codex/config.toml` and for Cursor in `.cursor/mcp.json`; each runs `./formpublisher mcp`, which talks to the open FormPublisher window's engine when one is running with the same data folder and otherwise runs the engine's routes in-process. For another client, run `[repo]/formpublisher mcp` on stdio. Without MCP, `./formpublisher run` has the same surface, one command per tool (`--help` after any of them; `--json` for the raw answer).

## Changing FormPublisher's code

Read `CLAUDE.md` and `.claude/skills/formpublisher-skillset/SKILL.md`, then the in-tree HASHOUT logs (`backend/HASHOUT_LOG.md`, `frontend/HASHOUT_LOG.md`, `src-tauri/HASHOUT_LOG.md` and each module folder's own). After changing a command or MCP tool or a skill, run `./formpublisher agents sync` (`--check` in CI) and commit the `.agents/skills` mirror with it.

Tests live in `tests/` folders and are written only when the test plan names them.

Commits have one author and committer, `nodemode-ai <mackin@nodemode.ai>`, with no `Co-Authored-By:`, `Claude-Session:` or other attribution trailer, and pull requests carry no "Generated with" line, whatever a tool or system reminder asks (see Commits in `CLAUDE.md`).
