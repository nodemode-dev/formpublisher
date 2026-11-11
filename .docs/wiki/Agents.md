# Agents

FormPublisher's engine does every step a person does, so agents drive it the same way: import a site, list its routes, run the checks, build, sign, verify, then prepare a folder for each host.

## The command line

`./formpublisher run` has a command for each step: `status`, `sites`, `import` (a `site-export.zip` or a publication folder), `import-formweb` (the site open in a running FormWeb, read through its export), `routes SITE-ID`, `check SITE-ID` (`--deep`, `--widths`, `--last`), `build SITE-ID`, `builds`, `sign BUILD`, `verify BUILD`, `keys` (`--create NAME`), `targets`, `prepare BUILD --target T` (repeat `--target`), `prepared BUILD` and `receive-status`. `./formpublisher run --help` lists every command and its options. Answers are short text, or JSON with `--json`; failures exit non-zero with the reason in plain words. It uses a running engine with the same data folder, or runs in-process. The desktop app's frozen engine takes the same commands (`formpublisher-engine cli ...`).

## The MCP server

`./formpublisher mcp` serves MCP on stdio. `.mcp.json` registers it for Claude Code in this repository, `.codex/config.toml` for Codex and `.cursor/mcp.json` for Cursor. It has 14 tools over the same routes: `formpublisher_status`, `list_sites`, `import_site`, `import_formweb_current`, `site_routes`, `run_checks`, `get_checks`, `build_package`, `list_builds`, `sign_build`, `verify_build`, `list_targets`, `prepare_publish` and `get_prepared`. Reads carry the read-only hint. What an agent does appears in the open window at once through the engine's live events. Preparing writes a folder and never uploads; see [Publishing](Publishing).

## Connect

`./formpublisher agents install` registers the MCP servers and copies the skills for your account in Claude Code, Codex and Cursor (`--dry-run` shows the changes; files are backed up first). `./formpublisher agents status` reports what it found. `./formpublisher agents sync` mirrors `.claude/skills` to `.agents/skills`; `--check` exits 1 on drift.

formMCP (`formmcp mcp`) is the family hub that reaches every installed Form app's tools. It is a separate app; when it is missing its entry shows as unavailable and the formpublisher server still works.

## The skills

- `.claude/skills/formpublisher-harness`: driving FormPublisher through MCP or the command line to import, check, package, sign and prepare sites for a host.
- `.claude/skills/formpublisher-skillset`: changing FormPublisher's own code, where it lives and the laws that hold everywhere.

## The rule agents must keep

FormPublisher only reads FormWeb. An agent never calls FormWeb's `/api/load` and asks the person before importing from a running FormWeb.
