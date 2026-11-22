# Changelog

## 0.8.0 · 2026-11-22

- Agents can do everything the window does. Seven new MCP tools and commands: `list_keys`, `receive_status`, `inspect_build`, `compare_builds`, `reproduce_build`, `verify_prepared` and `preview_site`. On the command line they are `keys`, `receive-status`, `inspect`, `compare`, `reproduce`, `verify-prepared` and `preview`.
- Each tool says what it may change. It either reads only, writes only in FormPublisher's own data folder, or writes to a path you name. Each tool now also describes its parameters to agents.
- The list of tools and commands is generated into `docs/mcp-tools.json`, and the documents take their counts from it: 29 tools and 27 commands.
- An installed FormPublisher can add itself to your agents. Run its engine program with `agents install` (the manual gives the path on each system) and Claude Code, Codex, Cursor and Antigravity get its tools.
- Antigravity joins Claude Code, Codex and Cursor in `agents install` and `agents status`.
- The repository's agent settings start FormPublisher's MCP server on Windows too.
- The server follows MCP revision 2026-07-28 and still answers older clients.

## 0.7.0 · 2026-11-22

- FormPublisher looks like the rest of the FormAI family. Its accent is green; if you picked your own accent, it is kept. Orange is still offered. Text on the accent and accent-coloured text on the light themes are drawn in an ink that stays readable.
- Every chooser is the family's dropdown, with full keyboard use, and menus show shortcuts as key caps.
- Lists are cards, and the current item glows. The routes column, the inspector and the bottom panel can be resized by dragging or with the keyboard, and they remember their size. The routes column folds to a narrow strip of thumbnails.
- Signing keys and the deep check's browser have their own panels in Preferences. The Package sheet only chooses a key, and Manage keys opens the panel. Advice that names a setting opens Preferences at it.
- The agent dock: View, Agent Dock (Cmd or Ctrl+J) opens a terminal panel at the bottom of the window, which can move to the right. It has a shell, and a tab for each of Claude Code, Codex, Cursor and Antigravity that is on your computer. It finds them even when the app was started from the Finder or the Start menu. The line under the tabs hands a request to Claude Code. Each agent tab can use FormPublisher's tools with a key of its own, and the key ends when the tab closes.
- The splash stays in front of other windows while it shows.
- Nothing that flashed or jumped when lists refreshed still does: the builds compare, the FormWeb project list and the bottom panel keep their content and update in place.

## 0.6.0 · 2026-11-22

- Only the FormPublisher window, its command line and its MCP server can change anything. Every request that changes something needs a key the engine makes at each start; reads work as before, and FormWeb's Send to FormPublisher keeps its own rule. A site you preview cannot reach the app.
- In the desktop app only the engine's own address may use the app's system functions, and the window is served with a content security policy.
- Signing keys are kept in your system's password store (macOS Keychain, Windows Credential Manager, the Secret Service on Linux). The store is opened only to create, sign, export, import or remove a key; listing keys never touches it. Where there is no store, the secret is a file only you can read. Keys from earlier versions move over the first time they are used.
- Removing a key removes its secret. Trash keeps only the public half, and a key restored from Trash can verify but not sign.
- Export and Import in the Package sheet, and `keys --export` and `keys --import` on the command line: a key leaves as a PEM file encrypted with a passphrase you choose, and comes back from one. Agents have no tool for either.
- Verify tells you who signed. A signature made with one of your keys says so with the key's name. A valid signature from a key you do not have is a warning, "Signed by a key you do not have", in the window, on the command line (which then exits 1 unless `--allow-unknown`) and in the MCP tool's answer (`known`).
- Preview and Problems each say in one line that previewing and the deep check load what the site itself loads from other hosts. FormPublisher sends nothing of its own.
- The engine's test suite cannot find or start an agent program and never touches your real home folder or password store.

## 0.5.0 · 2026-11-22

- The desktop app's engine starts and ends with its window on every system. On Windows the shell holds the engine in a job object, so ending the app by any means ends the engine; everywhere the engine also watches the app that started it and leaves within about two seconds of it going. An engine left running by an earlier copy is ended and replaced, never reused.
- When the engine cannot start, the app says why: missing from the install, could not be started, stopped with its exit code, no answer in 90 seconds, or another version answering. The message carries the engine's last lines and the path of its log.
- The engine keeps a log, `logs/engine.log` in the data folder (1 MB, three older files kept), and an unexpected error names that file.
- The engine is frozen as a folder inside the app instead of one file that unpacked itself at every launch, and on Windows it has no console window. On macOS every program file in that folder is signed with the app.
- Deep checks work in the installed app, with the Chrome or Edge you already have. Nothing is downloaded. A deep check that fails now shows an error in Problems with the reason, instead of ending as if it had passed.
- Help, Documentation opens the manual that ships inside the app, in the window, with the network off too. The Open the manual step of an error opens it at that error's row.
- The same build every time: the engine's Python packages, PyInstaller among them, install from a lock file with hashes; the Rust compiler is pinned at 1.97.0; Node 22.12 is the one minimum named everywhere.
- The Intel Mac build says it needs macOS 14 (Apple silicon stays at 13).
- `formpublisher_oc_install.bat` stops with a message when the FormWeb core cannot be built.
- CI also type-checks the desktop shell on Windows and macOS, checks that every language has every string, and checks the lock files.

## 0.4.1 · 2026-11-22

- The window text that 0.4.0 added in English only is now in all 26 languages: Templates (its title, the intro, Get the templates and Check again, the kept-list line with its date and counts, Start a site from this, the line a template without a description shows, the result and the two buttons after a start, the note on how to open the project in FormWeb), Start from a Template in File and on Home, Host It Yourself in Help, What to do with this folder on each prepared host and the line beside it, and the 18 messages the templates flow can raise (the index could not be read, a size or SHA-256 that does not match, a folder that does not exist, and the rest). Each translation follows the wording of its language's earlier files, es-MX and fr-CA with theirs. Product names, file names and commands stay as written. Nobody who speaks these languages has read the 25 new translations; they were written and checked for placeholders and length, and the FormWeb menu names inside a sentence (File, Import .fweb or .fpub file) are those of FormWeb's own translations.
- The Host it yourself guide, `docs/HOSTING.md`, stays in English, in the window as in the file. The sheet's title, its Close button and a one-line note beside Close that says so ("The guide is in English.") are translated; in English the note is not shown.
- The kept-list line writes its date in the window's language (it followed the system's before) and writes it again when the language changes, and the sheet says "1 whole site", "1 more is a part ..." and "1 file" in the singular, where it said "1 whole sites", "1 more are parts ..." and "1 files".
- A language switch holds the Templates sheet still up and down: the intro, the status line and the result line keep the room of the longest text in any of the 26 languages, and the note under What to do with this folder in Publish wraps over two lines where it used to be cut off with an ellipsis (it was cut in English too). Still open, by the same decision as the toolbar in 0.3.3: in the Templates sheet the status text starts where Get the templates ends, and Publish it follows the width of Edit in FormWeb, so both move sideways by a few pixels at a switch. The sheet is modal and covers the window's controls, so the switch was tried by script, not by hand.
- A template's name, licence and credit come from the repository and are shown as written; its description too when the repository gives one.

## 0.4.0 · 2026-11-22

- Templates to start a site from. Templates (File, Home) lists FormWeb's whole-site templates from the public formai-templates repository, read only when you press Get the templates and kept with its date (Check again reads it anew). Start a site from this downloads that one file, keeps it only when its size and SHA-256 match the index, opens it with the FormWeb core and writes a FormWeb project into a folder you choose; then Edit in FormWeb or Publish it. Sections, components and the library starter are parts for FormWeb's own library and are not offered as a whole site. `templates` and `start` on the command line, `list_templates` and `start_from_template` over MCP.
- Host it yourself: `docs/HOSTING.md`, also in the window (Help, and What to do with this folder on each prepared host), takes each of the six prepared folders to your own host: what you need, the steps, your domain's DNS records, HTTPS and updating later. You pay your host and your domain; nothing to FormPublisher.
- A test suite: `backend/tests` (pytest, 38 tests) covers opening each kind of site, the checks, packaging and signatures, the six host folders, the receive endpoint, the MCP tools and the templates, and CI runs it on pull requests and on `main`.
- The vendored FormWeb core says what it is: the 0.27.0 release (the same source it already was), so packages built from `.fweb` projects record FormWeb 0.27.0.
- The README says what FormPublisher is and what it does not do (no hosting, no editor of its own, no shop or forms backend).

## 0.3.4 · 2026-11-21

- The desktop build runs the same Tauri command line every time. `@tauri-apps/cli` is pinned to 2.12.5 in `frontend/package.json` and its lock file, the release of the `tauri` crate in `src-tauri/Cargo.lock`, and `build_app` and `build_app.bat` run that copy from `frontend/node_modules` instead of fetching whatever `@tauri-apps/cli@2` is newest with `npx`. A checkout whose `frontend/node_modules` was installed before this installs it first. `@tauri-apps/api` stays at 2.12.1, on the same minor line as the crate.
- `build_app.bat` stops with a plain message and exit code 1 when the install of the engine or of the window fails, instead of going on to a build that cannot succeed.
- The FormWeb engine crates stay vendored at 0.21.2. FormWeb 0.27.0's engine crates are the same source, only the version number differs, so `.fweb` projects saved by FormWeb 0.27.0, in both file versions, open here with nothing lost and to the same files as FormWeb's own 0.27.0 engine makes. Export zips and publication folders are read as files and do not touch the crates. One label differs: a package built from a `.fweb` project records FormWeb 0.21.2 as its engine, the version of the vendored copy.

## 0.3.3 · 2026-11-15

- The demos update in place. Opening a demo whose bundled site changed since you first opened it adds the new version as a revision of the same site, so the corrected credits in Lowlight and Looking Back reach a data folder written by 0.3.0 without removing anything. A demo you have built or prepared a host folder for is left as it is, and opening a demo that has not changed adds nothing.
- An old FormWeb site is adopted. A site imported by 0.3.0 or earlier is keyed by FormWeb's address; the first time its project arrives (Import, Send or the inbox), the project's revision is added to that site, which keeps its revisions, checks and builds. This happens only when exactly one old site has the project's name; with two or more, or none, a new site is made and nothing is moved.
- Import from FormWeb offers FormWeb's saved projects. When FormWeb has saved projects, a short list shows them, the open site first, and each lands on the same site as that project's Send. FormPublisher only reads FormWeb (`GET /api/projects` and `GET /api/projects/[id]/file`), never opens anything in it and never calls `/api/load`. The command line (`formweb-projects`, `import-formweb --project ID`) and the MCP server (`list_formweb_projects`, and `project` on `import_formweb_current`) do the same.
- The tooltip of a row in Problems shows the translated message and fix, as the panel does, in all 26 languages.
- A build made before any check ran says so: `publish.json` records `"checks": null` instead of a clean "0 errors, 0 warnings", and the offline demo's package manifest shows "Not run". Builds written by 0.3.2 or earlier, with an empty list of tiers, are read the same way.
- `external.request` gives one warning per remote address instead of one per reference, on the first page that uses it, with the number of references and the pages that use it. FormWeb's product-site starter went from 129 warnings to 84 and no reference is lost.
- Changing the language no longer moves Preferences (each row keeps the height of its longest hint, and Done keeps its width), the hint strip of the quick tour (its counter, title and buttons keep their widths) or the width of the menubar, so the title row stays still. Still open, by decision: the toolbar above the preview shifts sideways once at the moment you pick a new language, because every control takes the width of the labels in the language shown. Keeping it still needs every control sized for the widest of the 26 languages, which narrows the English route field from 294 to 177 px and widens Zoom, Publish and Package; the same approach was tried in 0.2.8 and not kept, and a version of it is saved in case the owner chooses it. The menu buttons in the title bar still move slightly at a switch (reserving each slot would make the English menubar about 1.8 times wider), and the bottom Checks panel and the count in the routes strip shift a little.
- The three FormWeb demo sites are exported with FormWeb 0.21.2's site runtime, and the vendored FormWeb core is the 0.21.2 release: orbit-style components keep a poster for each instance, a chosen tab or filter chip can have its own look, counters keep their width while counting, and a site search starts from `?q=`. A site that uses none of these exports as before.
- The documentation pictures that showed the old menubar (Checks, Preview and the notice action, in dark and light) are retaken.
- The new and changed labels are in all 26 languages.

## 0.3.2 · 2026-11-15

- Every FormPublisher icon is GPL-3.0-only, including the four copies of the mark in the offline demo, which `NOTICE.md` and `demo/MEDIA.md` listed as Apache-2.0.

## 0.3.1 · 2026-11-15

- A new check, `forms.local-address` (a warning): a form whose action goes to this computer or the local network (`localhost`, a `.local` name, a private or loopback address) or into FormWeb's own `/api/forms/` route will not send once the site is published, because nothing answers there. The message names the page and the address and says how to fix it in FormWeb: give the form a scripted reply, or point its action at a form service on the web. Forms with no action, and forms that post to a service on the web, are not reported.
- Import from FormWeb lands on the same site as Send to FormPublisher. One FormWeb project is now one site here, in any order: Send then Import, Import then Send, or a site that arrived through the inbox and is then imported. A second arrival adds a revision, and the notice says "Added a revision to" the site's name instead of "Imported". Sites you imported with 0.3.0 or earlier keep working as they are and are not merged; the next Import of the same project makes its own site, and you can remove the old one from Home.
- The credits shown inside the Lowlight and Looking Back demo sites match the records: the Hubble Ultra Deep Field carries its CC BY 4.0 credit, and Looking Back's picture credits read as their sources state them.
- `NOTICE.md` and `demo/MEDIA.md` record every demo picture at its source. The Hubble Ultra Deep Field is now listed under CC BY 4.0 with the credit "NASA, ESA, and S. Beckwith (STScI) and the HUDF Team" (it was listed as public domain); the NASA pictures carry the credit line their source pages state; the sample's own pictures are recorded as the owner's work under Apache-2.0.
- `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md` and `SECURITY.md` are in the shape the other Form apps use, and the README links them.
- The FormWeb engine crates stay vendored at 0.21.0.
- The new and changed labels are in all 26 languages.

## 0.3.0 · 2026-11-15

- Home has a new layout: a side panel with Start, Recent sites, Builds and Trash (the last two with a count) and the three ways to import, and a Demos row on Start. A site that arrives while Home is open no longer pushes the cards around: a note says that it arrived and Show brings it in. Deleting a build or emptying the trash asks in a row inside Home instead of a dialog over it.
- Four demo sites open from Home, from Help > Demos and from the command palette: Lowlight, Looking Back and Harbour Ferries, the three demo sites FormWeb ships, and Northwind Notes, the sample with problems for the checks to find. `NOTICE.md` and `demo/MEDIA.md` list every picture and font in them with its source and licence.
- The menubar has a Window menu (Minimize, Maximize, Full Screen), Home is the first item of File, and every menu works from the keyboard: F10 or Alt, the arrow keys, Home and End, Escape, and typing the start of an item's name. On macOS, View > Menus in Window keeps the menus in the window from the next start.
- Preferences is one scrolling page with a rail of its sections beside it. Each section folds, and the rail collapses to icons.
- macOS: the title row drags the window, and the close, minimize and zoom buttons sit in that row with room of their own.
- The live checks no longer report a layout shift or a sideways overflow that the preview itself caused. Switching Device on a finished site used to mark every route with `live.cls`. A page's own shifts and overflow are still found.
- With FormWeb 0.21.0: a `.fweb` project opened here gives the same not-found page as FormWeb's own export, so its pictures and fonts load at any missing address. A site whose address has a folder in it (`https://example.org/shop/`, a GitHub project page, a FormWeb publication folder) no longer gets false missing-file, broken-link and sitemap findings, and its not-found page is styled in the preview. The inspector names FormWeb as the source of a site sent from FormWeb.
- Fifteen fixes from a review of the whole app. Among them: a zip with a file and a folder of one name is refused with a clear message instead of an error 500; importing the open site again, or Reload Routes, no longer empties the routes strip; Builds and Trash hold still on a language switch and their tables scroll in a narrow window; dialogs and Preferences fit a narrow window; `formpublisher.bat` passes every argument; the command line survives a closed pipe; the desktop build checks the engine inside the finished macOS app.
- The splash shows the app icon.
- The manual says how to open a macOS build that is signed but not notarized.
- The FormWeb engine crates are vendored at 0.21.0.
- The new and changed labels are in all 26 languages.

## 0.2.8 · 2026-11-11

- The toolbar's dropdowns start at their final width in every language, so the first pick after starting in German, for example, no longer moves the toolbar.
- In the narrowest toolbar the device dropdown is only as wide as its preset names, and Custom shows a short word where its full name is long (German "Andere"). The tooltip names the full device.
- A second FormPublisher engine, such as the desktop app next to a command-line engine, now serves its previews on a free port of its own instead of reaching the first engine's site. `/api/health` and `engine.json` report the port as `hostPort`.
- The desktop app was built and run on Linux: the in-window menus, the toolbar and the Problems filter match the browser.
- The FormWeb engine crates are vendored at 0.20.8.
- The new label is in all 26 languages.

## 0.2.7 · 2026-11-11

- Where the Problems filters cannot share one row even with "All", they give way to a single funnel button. A dot shows when a filter is active, the tooltip names both choices, and its menu sets severity and tier by mouse or keyboard. The bar is one row in every language and size.
- Choosing a language in Preferences changes the open window at once instead of reloading it. The open site, the selected route, the panel, the preview, open dialogs and typed text stay as they are.
- In the Linux desktop shell (WebKitGTK) the toolbar stays on one row with whole values in German at every width; it used to push Package off the row at 1440 and 760 px.
- The FormWeb engine crates are vendored at 0.20.7.
- The new and changed labels are in all 26 languages.

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
