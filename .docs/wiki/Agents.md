# Agents

FormPublisher's engine does every step a person does, so agents drive it the same way: import a site, list its routes, run the checks, build, sign, verify, then prepare a folder for each host.

## The command line

`./formpublisher run` has a command for each step: `status`, `sites`, `import` (a `site-export.zip`, a `.fweb`, a `.fpub` or a publication folder), `import-formweb` (the site open in a running FormWeb, read through its export; `--project ID` takes one of its saved projects), `formweb-projects` (the running FormWeb's saved projects, the open one first), `routes SITE-ID`, `revisions SITE-ID`, `diff SITE-ID` (`--from R`, `--to R`; default the latest against the one before), `check SITE-ID` (`--deep`, `--widths`, `--last`), `build SITE-ID`, `builds`, `fpub BUILD` (`--out FILE`, `--force`: save a build as a `.fpub`), `sign BUILD`, `verify BUILD` (`--allow-unknown`: exit 0 for a valid signature by a key you do not have; without it that exits 1), `keys` (`--create NAME`; `--export ID --to FILE [--force]` and `--import FILE [--name NAME]` write and read an encrypted `.pem` file, asking for a passphrase of at least 8 characters, or reading `FORMPUBLISHER_KEY_PASSPHRASE`), `targets`, `prepare BUILD --target T` (repeat `--target`; `--include-model` keeps FormWeb's model files, which are left out by default), `prepared BUILD`, `trash` (`trash restore ENTRY` with `--to PATH` to name the place of an entry whose origin is unknown, `trash delete ENTRY` and `trash empty --yes`) and `receive-status`. `./formpublisher run --help` lists every command and its options. Answers are short text, or JSON with `--json`; failures exit non-zero with the reason in plain words. It uses a running engine with the same data folder, or runs in-process. The desktop app's frozen engine takes the same commands (`formpublisher-engine cli ...`).

## The MCP server

`./formpublisher mcp` serves MCP on stdio. `.mcp.json` registers it for Claude Code in this repository, `.codex/config.toml` for Codex and `.cursor/mcp.json` for Cursor. It has 22 tools over the same routes: `list_templates` (read only, the template list the person fetched) and `start_from_template` (a FormWeb project from one, in a folder the person named), and `formpublisher_status`, `list_sites`, `import_site` (an export, a `.fweb`, a `.fpub` or a folder), `list_formweb_projects` (read only), `import_formweb_current` (with `project`, a saved FormWeb project), `site_routes`, `list_revisions` and `diff_revisions` (read only: a site's revisions, and the files and routes added, removed and changed between two), `run_checks`, `get_checks`, `build_package`, `list_builds`, `save_fpub` (a build as one `.fpub` file at an absolute path; it never replaces a file), `sign_build`, `verify_build` (read only: `valid`, `known` when the signer's key is one of the person's own, `trusted` when both, `signer`, `message` and, when not valid, `reason`; `valid` with `known` false is a warning to pass on, not a verified package), `list_targets`, `prepare_publish` (with `includeModel`, and `leftOut` in each result), `get_prepared`, `list_trash` (read only) and `restore_from_trash`, which restores only a recorded or inferred origin and takes `passphrase` for a locked key rebuilt from its `.pem` (the CLI reads it with `trash restore ENTRY --passphrase-stdin`). No tool deletes, restores to a named place, or exports or imports a signing key: removing an entry from the trash for good, `trash restore --to`, `keys --export` and `keys --import` are a person's actions. The server sends the key from `engine.key` with each change, so it works with an engine that is running and needs no key in-process. Reads carry the read-only hint. What an agent does appears in the open window at once through the engine's live events. Preparing writes a folder and never uploads; see [Publishing](Publishing).

## Connect

`./formpublisher agents install` registers the MCP servers and copies the skills for your account in Claude Code, Codex and Cursor (`--dry-run` shows the changes; files are backed up first). `./formpublisher agents status` reports what it found. `./formpublisher agents sync` mirrors `.claude/skills` to `.agents/skills`; `--check` exits 1 on drift. `./formpublisher vendor --check` exits 1 when the vendored FormWeb crates are out of step.

formMCP (`formmcp mcp`) is the family hub that reaches every installed Form app's tools. It is a separate app; when it is missing its entry shows as unavailable and the formpublisher server still works.

## The skills

- `.claude/skills/formpublisher-harness`: driving FormPublisher through MCP or the command line to import, check, package, sign and prepare sites for a host.
- `.claude/skills/formpublisher-skillset`: changing FormPublisher's own code, where it lives and the laws that hold everywhere.

## The rule agents must keep

FormPublisher only reads FormWeb. An agent never calls FormWeb's `/api/load` and asks the person before importing from a running FormWeb.
