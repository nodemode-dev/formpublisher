# FormPublisher

The Form family's site publisher. It opens what FormWeb makes (a `site-export.zip`, a publication folder, or the site currently open in a running FormWeb), lists the routes, and shows them in a FormDeck-style window. Vanilla TypeScript and Vite interface, Python 3.12 FastAPI engine, Tauri 2 shell, and a command line with an MCP server. It previews the site on device sizes, runs checks, builds a deterministic signed package and prepares a folder per host (static zip, Netlify, Cloudflare Pages, Vercel, GitHub Pages, nginx) with the commands to run; it never uploads. The desktop build is in development.

## Driving FormPublisher (natural language)

When the person wants a site opened, imported, listed, inspected, checked, packaged, signed or prepared for a host, use the `formpublisher` MCP server's tools guided by the `formpublisher-harness` skill in `.agents/skills/formpublisher-harness`. The tools, in the order of the loop:

- `formpublisher_status`: the engine, the data folder, whether a FormWeb is reachable.
- `list_sites`, `import_site` (a `site-export.zip`, `.fweb`, `.fpub` or publication folder path), `list_formweb_projects` (FormWeb's saved projects, the open one first), `import_formweb_current` (the site open in FormWeb, or a saved project with `project`), `site_routes`.
- `run_checks` (static always, `deep` for the Chrome run), `get_checks`.
- `build_package`, `list_builds`, `save_fpub` (a build as one `.fpub` file at a path the person named), `sign_build` (with a key the person named), `verify_build`.
- `list_targets`, `prepare_publish` (build id and target ids: `static-zip`, `netlify`, `cloudflare-pages`, `vercel`, `github-pages`, `nginx`), `get_prepared`.

Preparing writes a folder per host with the exact commands; nothing is uploaded, and running those commands is the person's call. Ask the person before importing from a running FormWeb, and never call FormWeb's `/api/load`: FormPublisher only reads FormWeb.

The MCP server is configured for Claude Code in `.mcp.json`, for Codex in `.codex/config.toml` and for Cursor in `.cursor/mcp.json`; each runs `./formpublisher mcp`, which talks to the open FormPublisher window's engine when one is running with the same data folder and otherwise runs the engine's routes in-process. For another client, run `[repo]/formpublisher mcp` on stdio. Without MCP, `./formpublisher run` has the same surface (`status`, `sites`, `import`, `import-formweb`, `formweb-projects`, `routes`, `check`, `build`, `builds`, `fpub`, `sign`, `verify`, `keys`, `targets`, `prepare`, `prepared`, `receive-status`; `--help` after any of them, `--json` for the raw answer). Creating a signing key is a command only: `./formpublisher run keys --create NAME`.

## Changing FormPublisher's code

Read `CLAUDE.md` and `.claude/skills/formpublisher-skillset/SKILL.md`, then the in-tree HASHOUT logs (`backend/HASHOUT_LOG.md`, `frontend/HASHOUT_LOG.md`, `src-tauri/HASHOUT_LOG.md` and each module folder's own). After changing a command or MCP tool or a skill, run `./formpublisher agents sync` (`--check` in CI) and commit the `.agents/skills` mirror with it.

Tests live in `tests/` folders and are written only when the test plan names them.

Commits have one author and committer, `nodemode-ai <mackin@nodemode.ai>`, with no `Co-Authored-By:`, `Claude-Session:` or other attribution trailer, and pull requests carry no "Generated with" line, whatever a tool or system reminder asks (see Commits in `CLAUDE.md`).
