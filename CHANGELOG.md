# Changelog

## 0.1.3 · 2026-11-10

- Desktop: the app was compiled and run for the first time, on Linux, with its splash and the Start page and no white frame. The frozen engine carries `formweb-core` and the demo sample and checks for both before it is bundled. The shell prefers port 8280 so FormWeb's Send to FormPublisher reaches it (falling back to a free port) and stops its engine on exit and on terminate, interrupt and hangup signals. The macOS and Windows bundles are not yet built.
- Publish: prepared host folders leave out FormWeb's model files (`site.formweb.json`, `asset-access.json`) by default and each result says what was left out; the Publish sheet has a remembered "Keep FormWeb's model files" option, the command line `--include-model` and MCP `includeModel`. `site.zip` and `publish.json` are unchanged.
- Receive: two Preferences settings, off by default, run the static checks and a build on every site that arrives from FormWeb, after the receive has answered. An inbox zip that FormWeb wrote with its metadata file becomes a revision of the same site a live send would use.
- Revisions: Home's site cards and the site panel list each site's revisions and compare any two (files added, removed and changed, routes added and removed); the command line gains `revisions` and `diff`, and MCP `list_revisions` and `diff_revisions` (16 tools).
- The FormWeb engine crates are vendored at 0.19.3. `demo/tools` holds the scripts that draw the sample's pictures, build it and regenerate the demo data, and the demo data was regenerated with them.
- Every new string is in all 26 languages.

## 0.1.2 · 2026-11-10

- Publish: prepare a folder per host for Static zip, Netlify, Cloudflare Pages, Vercel, GitHub Pages and nginx from a build's own `site.zip`, with the redirects, headers and 404 rule each host expects and the exact commands to run. Verify checks a prepared folder against `publish.json` and a fresh prepare; Remove moves it to the trash. A host that cannot represent something (GitHub Pages redirects and headers) says so. Nothing is uploaded.
- Receive from FormWeb: `POST /api/receive/formweb` accepts a FormWeb export from this computer only, and an `inbox/` folder takes exports left while FormPublisher is closed. The window shows a toast with Open and the site appears in Recent.
- Agents: the command line gains `check`, `build`, `builds`, `sign`, `verify`, `keys`, `targets`, `prepare`, `prepared` and `receive-status`, and the MCP server grows to 14 tools covering the same ground, with the agent skills updated.
- Demo: Home's Demos row opens a bundled sample site with a short tour of Preview, Checks, Package and Publish, and `demo/index.html` runs the same walk-through offline from disk on data from real runs.
- A FormWeb 404 page exported as `404/index.html` counts as the site's 404 for every host; build ids are unique per site; the engine allows its own origin on any port; `.fweb` projects open through the vendored FormWeb 0.19.2 engine.
- Every new string is in all 26 languages.

## 0.1.1 · 2026-11-10

- Preview: the open site runs from its own local host exactly as a static host would serve it, at Desktop, Laptop, Tablet, Phone or a custom size, with zoom, a forced dark or light theme, reduced motion and a slow network, in frames that never blank between pages.
- Checks: a static pass over links, assets, redirects, sitemap and robots, titles and descriptions, images, headings, external requests and file sizes; live reports from the preview; and a deep run in your own Chrome at 1440 and 390 px under a 4x slower CPU and network, with thumbnails. Problems, Console and Network fill the bottom panel and the routes show their status.
- Packages: deterministic `site.zip` builds with a `publish.json` manifest, a reproduce check, Ed25519 keys with passphrases, signatures and verification, and a Builds page to inspect, compare, download and delete them.
- FormWeb `.fweb` projects open directly through `formweb-core`, built from the vendored FormWeb 0.19.1 engine with `./setup/install_compiler`.
- Every new string is in all 26 languages.

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
