# Agents

FormPublisher's engine does every step a person does, so agents drive it the same way: import a site, list the sites, list a site's routes.

## The command line

`./formpublisher run` covers the path: `status`, `sites` (what is imported), `import` (a `site-export.zip`, a publication folder, or the site open in FormWeb) and `routes` (the routes of one site). `./formpublisher run --help` lists every command and its options. Answers are short text, or JSON with `--json`; failures exit non-zero with the reason in plain words. It uses a running engine with the same data folder, or runs in-process. The desktop app's frozen engine takes the same commands (`formpublisher-engine cli ...`).

## The MCP server

`./formpublisher mcp` serves MCP on stdio. `.mcp.json` registers it for Claude Code in this repository, `.codex/config.toml` for Codex and `.cursor/mcp.json` for Cursor. Its tools are the command line's commands under the same names. What an agent does appears in the open window at once through the engine's live events.

## Connect

`./formpublisher agents install` registers the MCP servers and copies the skills for your account in Claude Code, Codex and Cursor (`--dry-run` shows the changes; files are backed up first). `./formpublisher agents status` reports what it found. `./formpublisher agents sync` mirrors `.claude/skills` to `.agents/skills`; `--check` exits 1 on drift.

formMCP (`formmcp mcp`) is the family hub that reaches every installed Form app's tools. It is a separate app; when it is missing its entry shows as unavailable and the formpublisher server still works.

## The skills

- `.claude/skills/formpublisher-harness`: driving FormPublisher through MCP or the command line to import and list sites.
- `.claude/skills/formpublisher-skillset`: changing FormPublisher's own code, where it lives and the laws that hold everywhere.

## The rule agents must keep

FormPublisher only reads FormWeb. An agent never calls FormWeb's `/api/load` and asks the person before importing from a running FormWeb.
