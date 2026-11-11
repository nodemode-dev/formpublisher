# Changelog

## 0.2.6 · 2026-11-11

- The toolbar's dropdowns show their whole value at every window width, also between 1240 and 1400 px where they used to be cut off, and choosing another option no longer moves anything in the toolbar.
- In a narrow window the Problems filters show "All" instead of "All severities" and "All tiers" when that keeps the bar on one row (the full name stays in the tooltip). Where the other options are still too wide, as in German, Finnish and Russian at 760 px, the filters keep their own row.
- The FormWeb engine crates are vendored at 0.20.6.
- The new label is in all 26 languages.

## 0.2.5 · 2026-11-11

- In narrow windows the bottom panel's tabs show an icon and their count instead of a cut-off name, and the name stays in the tooltip and for screen readers.
- The toolbar's selects show their whole value at 1100 and 760 px wide. When room runs out, the route field turns into an icon that opens over the toolbar, and the selects show a short form of their value ("Auto" for "Theme: Auto").
- The Problems filters keep their whole value in narrow windows, moving to their own row when needed.
- Save as .fpub in the builds library names the file `SITE-BUILD.fpub`, as the engine and the command line do.
- The FormWeb engine crates are vendored at 0.20.5.

## 0.2.4 · 2026-11-11

- Save any build as one `.fpub` file, from the builds library, the command line (`fpub`), the MCP server (`save_fpub`) or the API, and open it on another computer with Open, drop or import. It comes back as the same site and build, with its signature checked. Saving the same build twice gives the same file. The manual describes the format.
- FormWeb 0.20.4 opens a `.fpub` made from a FormWeb site as a project, so `.fweb` and `.fpub` are accepted in both apps.
- The publish sheet keeps each host's last verify result, with its time, until you prepare that host again, also after a restart.
- The toolbar and the Problems bar keep every action in view in narrow windows: below about 1240 px Publish and Package show only their icons (their names stay in the tooltip and for screen readers), so nothing is cut off at 1100 x 800 or 760 x 640. The window was also checked in all 26 languages at those two sizes.
- On Windows, `formpublisher.bat vendor --check`, `agents sync --check`, `run`, `cli` and `mcp` pass their arguments again, and boot, desktop dev and the engine starter stop with a clear line when Node, Python or the desktop tools are missing. Found by running every launcher under Wine.
- The FormWeb engine crates are vendored at 0.20.4.
- Every new string is in all 26 languages.

## 0.2.3 · 2026-11-11

- The window was checked in all 26 languages on every main screen. The one word still in English, the "Static zip" host name, now translates; Netlify, Cloudflare Pages, Vercel, GitHub Pages and nginx stay as written.
- The publish sheet no longer jumps by a few pixels while its host cards fill in.
- `formpublisher.bat doctor` on Windows now shows the vendor line correctly. Running the Windows scripts under Wine found three problems in last release's doctor line, which had only been checked by reading.
- The FormWeb engine crates are vendored at 0.20.3.
- Every new string is in all 26 languages.

## 0.2.2 · 2026-11-10

- Every word in the window translates: the signing-key list's "Choose a key" and "No keys yet", the build list's "No builds yet", the tour's step count, the home screen's FormWeb status and several labels and placeholders now follow your language. Names, paths, hashes and commands stay as written.
- `./formpublisher doctor` shows whether the bundled FormWeb engine code is in step, and `setup\install_compiler.bat` on Windows checks it before building, as the macOS and Linux script already did.
- The window was measured loading at two sizes, in both themes and two languages, and nothing moves.
- The FormWeb engine crates are vendored at 0.20.2.
- Every new string is in all 26 languages.

## 0.2.1 · 2026-11-10

- `nginx-check.sh` also checks the `listen` lines: after its first pass it runs `nginx -t` again with each listen line on a loopback port, so your own check is as strict as the app's. `NGINX_CHECK_PORT` sets the first port.
- `./formpublisher vendor --check` confirms that the bundled FormWeb engine code matches the version and contents recorded in `vendor/formweb-native/VENDOR.md`. The compiler setup and CI run it before building.
- On GitHub Pages, the folder-redirect note says that visitors with scripts turned off see the 404 page at those addresses.
- The FormWeb engine crates are vendored at 0.20.1.
- Every new string is in all 26 languages.

## 0.2.0 · 2026-11-10

The version moves to 0.2.0 rather than 0.1.10, to keep the Form family's one-digit patch number (FormWeb moves to 0.20.0 the same way).

- GitHub Pages redirect pages keep the visitor's query string and hash, so `/old?q=1#h` lands on `/docs?q=1#h`; without scripts they still redirect through their meta refresh.
- `nginx-check.sh` is executable, so `./nginx-check.sh` works as well as `sh nginx-check.sh`.
- The nginx check also checks the `listen` lines, on a free loopback port, so a bad listen parameter is caught; the prepare note says whether that ran.
- Verify reads in your language: problem rows, refusals and the nginx notes are translated into all 26 languages, with paths and nginx's own messages left as they are.
- The FormWeb engine crates are vendored at 0.20.0.
- Every new string is in all 26 languages.

## 0.1.9 · 2026-11-10

- The nginx folder carries `nginx-check.sh`, and Check the config now runs `sh nginx-check.sh`: it checks the config with `nginx -t` on a scratch copy, so it works without root or IPv6 and changes nothing in the folder.
- nginx redirects keep the query string, like every other target. Folders prepared for nginx by 0.1.8 need preparing again.
- The Publish sheet reads in your language: every host description, command label, note and warning is translated into all 26 languages.
- The GitHub Pages description says its 404 page also follows folder redirects.
- Checked on every target: redirects to other sites, and a GitHub Pages site whose export has no FormWeb model, which takes its address from the 404 page.
- The FormWeb engine crates are vendored at 0.19.9.

## 0.1.8 · 2026-11-10

- Restoring from the trash uses one dialog, Restore from the trash, which asks for a place, a passphrase or both at once and shows any refusal on the field it concerns.
- When something you asked for needs a build or site that is in the trash, the notice offers Restore: one click puts it back and tries again. If it cannot go back where it was, the Trash page opens with the reason.
- Where nginx is installed, preparing and verifying the nginx target run `nginx -t` on the config and show the result; a failing config makes verify fail with nginx's message. Folders prepared for nginx by 0.1.7 need preparing again, because the test wrapper changed.
- GitHub Pages now follows FormWeb's folder redirects (`/blog/*` to `/docs/:splat`) from its 404 page, and every GitHub Pages redirect respects a site served under a path such as `/repo`.
- The FormWeb engine crates are vendored at 0.19.8.
- Every new string is in all 26 languages.

## 0.1.7 · 2026-11-10

- A signing key in the trash whose record was lost or damaged can be restored again: FormPublisher rebuilds it from the key file, with the same id and fingerprint, and asks for the passphrase when the key is locked. The command line reads that passphrase from standard input with `--passphrase-stdin`.
- Some refusals now come with the next step beside them: Open the trash, Try again, Show the running check, Open the manual or Enter the passphrase.
- FormWeb's folder redirects (`/blog/*` to `/docs/:splat`) and its 404 page reach every publish target without hand edits; GitHub Pages, which has no server redirects, says it skipped them.
- Older FormWeb exports that keep their 404 page only at `404/index.html` now show it correctly at any missing address, in every target and in the preview site host.
- The FormWeb engine crates are vendored at 0.19.7.
- Every new string is in all 26 languages.

## 0.1.6 · 2026-11-10

- Every refusal from the engine now carries a stable code beside its message, such as `site-missing`, `passphrase-wrong` or `place-taken`, so scripts and agents can act on it without reading the text. The command line prints `error [code]: message`, agent tools say the same, and the manual lists every code.
- Trash: the Where does it go dialog checks a name before restoring and says what shape it needs, for builds, prepared folders, sites and keys alike, and the engine refuses the same names. A restored site that had lost its id takes its folder name.
- The preview site host shows a FormWeb site's own 404 page for a missing address; before, it showed a plain Not found because FormWeb keeps that page at `404/index.html`.
- Deep checks were compared with 0.1.3 on a site with redirects, clean addresses, a folder index and a custom 404 page: the same problems, summaries and thumbnails, and the site host answered every redirect and address the same.
- The FormWeb engine crates are vendored at 0.19.6.
- Every new string is in all 26 languages.

## 0.1.5 · 2026-11-10

- Trash: items removed by earlier releases can now be restored too. FormPublisher works out where each one came from (a prepared folder is prepared again from its build), and when it cannot tell, the Trash page asks where it goes. The command line takes `trash restore ENTRY --to PATH`; agents still restore only to places FormPublisher knows.
- Recent sites no longer jump when a site arrives from FormWeb while you are looking at them: a note says how many arrived, and Show puts them in order.
- Home now sits under the title bar, so the menus, theme and Preferences work while Home is open.
- Deep checks give the same problem ids on every run. A comparison with 0.1.3 on a site with real problems (a missing image, an external image, overflow on phones, a failing script and late images) found the same 18 problems.
- The FormWeb engine crates are vendored at 0.19.5.
- Every new string is in all 26 languages.

## 0.1.4 · 2026-11-10

- Trash: removed sites, builds, keys and prepared folders are listed on Home's Trash page and can be restored to where they were, deleted for good, or emptied at once. The command line gains `trash`, `trash restore`, `trash delete` and `trash empty --yes`; MCP gains `list_trash` and `restore_from_trash` (18 tools), and deleting stays a person's action.
- Keyboard shortcuts can be changed in the shortcuts dialog: press the new keys, see which command already uses them and replace or cancel, reset one or all. Menus, the command palette and the desktop app's native menus follow at once.
- Desktop app: Open Folder uses the system folder panel, and Reveal Site Folder opens the file manager, only for folders inside the data folder.
- FormPublisher writes `engine.json` in its data folder with the port it runs on, so FormWeb 0.19.4's Send to FormPublisher reaches it even when the desktop app had to use a port other than 8280.
- FormWeb's large-project `.fweb` files (version 2, a zip up to 512 MiB) import with the same checks as FormWeb's, streamed so no project sits in memory.
- Deep checks serve the site through the same host as Preview. The builds list now refreshes when a build is removed. The FormWeb engine crates are vendored at 0.19.4.
- Every new string is in all 26 languages.

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
