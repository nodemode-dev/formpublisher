# FormPublisher Manual

FormPublisher is the Form family's site publisher. It opens what FormWeb makes, lists the site's routes and shows them in a FormDeck-style window. People and agents use the same steps: each one is also a command line command and an MCP tool.

It imports FormWeb sites, previews them on device sizes, checks them, builds signed packages, and prepares a folder with the exact commands for each of six hosts. It never uploads anything. It runs in a browser tab or as a desktop app.

## Contents

- [Getting started](#getting-started)
- [The desktop app](#the-desktop-app)
- [Home](#home)
- [Trash](#trash)
- [Keyboard shortcuts](#keyboard-shortcuts)
- [Importing a site](#importing-a-site)
- [Routes](#routes)
- [.fweb projects](#fweb-projects)
- [Preview](#preview)
- [Checks](#checks)
- [Packages and signatures](#packages-and-signatures)
- [Publish](#publish)
- [Receive from FormWeb](#receive-from-formweb)
- [Revisions and diffs](#revisions-and-diffs)
- [The demo](#the-demo)
- [Agents](#agents)
- [The command line](#the-command-line)
- [The MCP server](#the-mcp-server)
- [Settings and the data folder](#settings-and-the-data-folder)
- [When something goes wrong](#when-something-goes-wrong)

## Getting started

From the repository:

```sh
./formpublisher_oc_install        # the engine's Python venv and the interface packages, once
./formpublisher                   # engine on 127.0.0.1:8280 and interface on http://localhost:5280
```

Open http://localhost:5280. `./formpublisher build` then `./formpublisher serve` runs the built interface from the engine alone on http://127.0.0.1:8280. `./formpublisher doctor` checks the toolchain, the installs and the ports. Windows has `formpublisher.bat` and `formpublisher_oc_install.bat`.

## The desktop app

`./build_app` (`build_app.bat` on Windows) builds the desktop app from this folder, start to finish, and logs to `build_app.log`. It freezes the engine with PyInstaller into one `formpublisher-engine` program (the built interface, the demo site and the `formweb-core` compiler go inside it), then builds the Tauri 2 shell around it. `formpublisher-engine --selfcheck` proves a frozen engine starts, and it takes the same commands as the command line (`formpublisher-engine cli ...`).

When the app starts it shows a small splash with a gradient bar, starts the engine, and reveals the main window only once the interface has drawn its first frame, so there is no white flash. A second launch focuses the running window instead of opening another. Closing the last window ends the app and the engine it started; a terminate or interrupt signal does the same, engine and anything the engine started included.

The port rule: the app uses `FORMPUBLISHER_PORT` when that is set, else 8280 when it is free, else any free port the system hands out. If something already answers the health route on the chosen port, the app uses that engine and does not start another. Once the site host and the inbox watcher are up, the engine writes `engine.json` in the data folder with `app`, `port`, `pid`, `version` and `started`, so FormWeb finds the running app on whatever port it took. A stopping engine removes the file only when it still names its own pid, so a second engine on another port and data folder never loses its file. When FormPublisher is closed, FormWeb leaves the site in the inbox, where the engine imports it on its next scan (see [Receive from FormWeb](#receive-from-formweb)). Running from source, `./formpublisher desktop dev` opens the window over the source tree instead of the frozen engine.

In the desktop app, Open Folder uses the system folder panel. Cancelling the panel imports nothing, and if the panel fails the app falls back to the typed path dialog, which is also what the browser always shows. Reveal Site Folder opens the site's folder in the system file manager through the app's `reveal_path` command, which only accepts a path inside the data folder (`FORMPUBLISHER_HOME`, or `~/FormPublisher`); anything outside it, or a path that does not exist, is refused.

## Home

Home is the start page. It offers a drop zone for a FormWeb export, the list of recent sites, and your open sites. Opening a site puts it in a tab.

## Importing a site

There are three ways in, and all of them only read:

- **A site export.** Drop FormWeb's `site-export.zip` on Home, or choose it.
- **A publication folder.** Choose a FormWeb publication folder, `publications/[slug]/[version]/`.
- **The site open in FormWeb.** With FormWeb running on the same computer, import its current site. FormPublisher asks FormWeb's `GET /api/export` over loopback. It never calls `/api/load` and never changes what FormWeb has open.

## Routes

A site's routes come from its `routes.json`. Each has a path, a page, a locale, an item and a stylesheet. The routes strip lists them, the inspector shows the selected route, and the status bar shows how many there are.

## Trash

Removing a site, a build, a signing key or a prepared folder moves it to `trash/` in the data folder; nothing is deleted at once. Each entry gets a `.trash.json` record beside it with its kind, label, origin, time and size. Home's Trash page lists the entries newest first with a kind icon, the label, the kind, the time and the size. Restore moves an entry back to where it came from. Delete for good and Empty Trash remove entries for good, and both ask first. The page refreshes by itself when something is removed or restored, and restoring a site refreshes Recent.

A restore only goes ahead when the place is free: if something already sits at the origin (or a key with the same id exists) it answers 409 with the reason, and the window shows it as a notice. Entries moved to the trash before 0.1.4 have no record; they are listed with a kind taken from their name but cannot be restored.

The routes are `GET /api/trash`, `POST /api/trash/{entry}/restore`, `DELETE /api/trash/{entry}` and `DELETE /api/trash` (empty). An entry name is only accepted when it appears in the folder listing. See [The command line](#the-command-line) and [The MCP server](#the-mcp-server) for the agent side: an agent can list the trash and restore from it, but deleting for good stays with a person.

## Keyboard shortcuts

Keyboard Shortcuts (`Mod+/`, in the Help menu) lists every command with its keys. Each row has Change and Reset. Change records the next combination you press; no command runs while it records. Escape cancels, and Backspace clears the binding. Reset restores that command's default, and Reset all restores every default.

Some combinations are refused with a reason: ones without a modifier, ones the browser or the system keeps, and the text-editing commands (copy, paste and the like). When another command already holds the combination, the dialog names it and offers Replace or Cancel. Overrides are stored in the browser's local storage under `formpublisher_shortcuts`, and the menus, the command palette, the dialog and the desktop app's native menus pick them up at once.

## .fweb projects

A `.fweb` file is a FormWeb project: a JSON envelope with the format `com.nodemode.formweb`. Import it like a zip or a folder, from Home or the file dialog. FormPublisher hands it to `formweb-core`, the compiler built from the FormWeb crates vendored in `vendor/formweb-native/`. The compiler loads the project and exports every locale with the site's default locale as the base, and FormPublisher writes the files and the referenced assets (`/api/assets/[sha].[ext]` references become real files, as FormWeb's own bundling does). The import is recorded with source kind `fweb`; importing the same project again adds a revision.

Version 2 projects import too. When a project is too big for the JSON envelope, FormWeb 0.19.4 writes a zip `.fweb` instead: `project.json` first, then each asset stored as `assets/[id]`. FormPublisher applies FormWeb's own checks to it: `project.json` comes first and is at most 64 MiB, the format and version are right, at most 500 assets are listed once each, every member is exactly `assets/[listed id]`, and each asset matches its digest, size limit and mime type. The file is capped at 512 MiB and assets stream from the zip in 1 MiB chunks. A bad file is refused with the reason. A version 2 zip is recognised by its contents, so it imports as a project even without the `.fweb` extension, and ordinary site zips are unaffected. A version 1 project and its version 2 twin build to the same files and hashes.

`formweb-core` is not part of the Python install. Build it once with `./setup/install_compiler` (`setup\install_compiler.bat` on Windows), which runs `cargo build --release --locked` and copies the binary to `backend/bin/formweb-core`. `./formpublisher_oc_install` runs it when Rust is installed and says how to get Rust when it is not. `FORMPUBLISHER_FORMWEB_CORE` points to a binary elsewhere. Without the binary an import answers: "Opening .fweb projects needs formweb-core. Run ./setup/install_compiler."

## Preview

Opening a site mounts a revision on the site host, a second listener at 127.0.0.1:8281 (`FORMPUBLISHER_HOST_PORT`) that serves the files the way a production static host does. It is a separate origin from the interface, so the site gets its own storage and cannot call the engine's `/api` routes. One site is mounted at a time; mounting another replaces it.

How the host resolves a request:

- `/a/b` is the file `a/b`, then `a/b/index.html`, then `a/b.html`; `/a/b/` is `a/b/index.html`; `/` is `index.html`. Query strings are ignored.
- Paths with `..`, a backslash or a NUL byte are refused (400); symlinks that leave the revision are not followed.
- `redirects.json` applies when no file matches: 301, 302, 307 and 308 answer with `Location`, 200 rewrites to the target, and a trailing `*` in `from` becomes `:splat` in `to`.
- A missing path answers with the root `404.html` (status 404), or plain text.
- Single-range requests answer 206, or 416 when unsatisfiable. Every response carries `Cache-Control: no-store`, `X-Content-Type-Options: nosniff` and `Referrer-Policy: strict-origin-when-cross-origin`.
- Only `GET` and `HEAD` are accepted, and only for `127.0.0.1:[port]` or `localhost:[port]` as Host.

The options toolbar above the stage controls the preview:

| Control | Choices |
| --- | --- |
| Route | an editable field; Enter navigates, and it follows the page's own navigation |
| Device | Desktop 1440 by 900, Laptop 1280 by 800, Tablet 834 by 1112, Phone 390 by 844, Custom |
| Rotate | swaps width and height |
| Zoom | Fit, 50, 75, 100 percent |
| Theme | Auto, Dark, Light |
| Motion | Auto, Reduce |
| Network | None, Fast (40 ms, 1,500 KB/s), Slow (150 ms, 200 KB/s) |
| Reload, Open in browser | reload the frame; open the current route in the system browser |

Theme, motion and network remount the site with the new options and reload the frame. Size and zoom never reload it. Navigating loads a hidden second frame and swaps it in once it has loaded, so the page never blanks. The choices are remembered per window.

Theme and motion are emulated by a probe script that the host injects into HTML responses right after `<head>` (only while previewing, never in a package). It makes `prefers-color-scheme` and `prefers-reduced-motion` answer as chosen, and makes `fw-theme-*` storage keys return the forced theme. The same probe reports the console, errors, requests, layout shift and horizontal overflow to the window for the live checks.

The routes strip shows a thumbnail box and a status dot per route: none when not checked, green for no problems, amber for warnings, red for errors. Thumbnails come from a deep check.

## Checks

Checks produce problems. Each problem has an id (stable for the same finding), a tier (`static`, `live` or `deep`), a severity (`error`, `warning`, `info`), a code, the route, a message and a fix, and optionally the file, line, selector and URL. The Problems tab lists them with filters by severity and tier, and clicking a row selects its route. Counts show in the tab and the status bar. Run checks starts the static tier; Deep check starts the deep tier.

### Static tier

Runs offline on the revision's files, in the Python standard library. HTML is parsed, paths resolve the way the host resolves them, and results are sorted by route, code and line.

| Code | Severity | Rule |
| --- | --- | --- |
| `link.broken` | error | an internal `href` resolves to no file, route or redirect |
| `link.anchor` | warning | a `#id` fragment has no element with that id on the target page |
| `asset.missing` | error | `src`, `srcset`, `poster`, `link href`, CSS `url()` or `@import` resolves to no file |
| `redirect.loop` | error | following `redirects.json` returns to a visited path |
| `redirect.chain` | warning | a redirect target is itself redirected |
| `redirect.target` | error | a redirect target resolves to nothing |
| `sitemap.missing` | warning | a route is not in `sitemap.xml` (unless the page is `noindex`) |
| `sitemap.extra` | warning | a sitemap URL path resolves to no route |
| `robots.sitemap` | warning | `robots.txt` has no `Sitemap:` line, or it does not end in `/sitemap.xml` |
| `robots.blocks` | warning | `robots.txt` disallows `/` for `*` |
| `meta.title` | error when missing, warning over 60 characters | the `title` element |
| `meta.description` | warning when missing or over 160 characters | `meta name="description"` |
| `meta.lang` | warning | `html` has no `lang` |
| `img.size` | warning | an `img` has no `width` and `height` and no inline `aspect-ratio` |
| `img.alt` | warning | an `img` has no `alt` (an empty `alt` is fine) |
| `heading.h1` | warning | a page has no `h1`, or more than one |
| `heading.order` | info | a heading level is skipped going down |
| `external.request` | warning | an `http(s)` URL in a resource position (`src`, `srcset`, `poster`, stylesheet `href`, CSS `url()`, `@import`, and string literals passed to `fetch(`, `import(` or `new URL(` in `.js` files) that is not on the site's own host |
| `budget.file` | warning over 1 MiB, error over 5 MiB | HTML, CSS and JS files; media (images, video, audio, fonts) warn over 20 MiB |
| `budget.page` | warning | a route's HTML plus the CSS and JS it references directly totals over 500 KiB |

### Live tier

While you preview, the probe reports what the page does and the window turns it into problems at once: `console.error` and page errors are errors, `console.warn` is a warning, a failed request (network error or status 400 and up) is an error, layout shift above 0 is a warning and 0.1 or more an error, and horizontal overflow is an error. The window accepts probe messages only from the visible frame, from the host origin and for the current mount. Live problems are sent to the engine at most once a second so the Problems list holds all tiers. The Console and Network tabs show the raw messages.

### Deep tier

A deep check drives the Chrome you already have installed through Playwright. It serves the revision through the same site host as the preview (with no probe), so a deep check sees the same host rules, and for each route at 1440 by 900 and 390 by 844 (or the widths you pass) it opens a fresh context, applies a 4x CPU slowdown and a slow network (150 ms, 200 KB/s), records layout shifts, loads the page, scrolls to the bottom in 8 steps and back, and reads the results. Problems:

| Code | Severity | Meaning |
| --- | --- | --- |
| `deep.console` | error | a console error |
| `deep.pageerror` | error | an uncaught error |
| `deep.request` | error | a failed request or a response of status 400 and up |
| `deep.external` | warning | a request to another host |
| `deep.cls` | warning above 0, error at 0.1 and up | layout shift, with the value in the message |
| `deep.overflow` | error | the page is wider than the viewport |
| `deep.unavailable` | info | Playwright or Chrome is missing |

Each message names the route and width. A thumbnail of each route (1440 by 900, scaled to 320 px wide) is saved under `checks/[site]/[revision]/thumbs/`.

The deep tier needs `backend/requirements-deep.txt` (`./formpublisher_oc_install` installs it) and Chrome. FormPublisher never downloads a browser. It uses Chrome from the `checks.chromePath` setting, or finds one in the usual places (Google Chrome on macOS, `google-chrome`, `google-chrome-stable` or `chromium` on Linux, `Program Files` on Windows). Results are stored per revision in `checks/[site]/[revision]/results.json`.

## Packages and signatures

Package opens with Package (Mod+Shift+B). It shows the check summary, then builds the revision.

### Build

A build contains every file in the revision except FormPublisher's own records. `site.zip` is deterministic: entries sorted by UTF-8 path, forward slashes, timestamps fixed at 1980-01-01, mode 0644, deflate level 9, no directory entries, no extra fields and no comment. The same revision gives the same bytes on every machine. The build id is the first 12 hex digits of the SHA-256 of the site id, a colon and the zip's SHA-256, so the same bytes imported as two sites get two builds; `publish.json` still records the zip's own SHA-256. Building an identical revision again returns the existing build.

Each build lives in `builds/[site]/[id]/`:

| File | What |
| --- | --- |
| `site.zip` | the package |
| `publish.json` | what the package is, kept beside the zip and never inside it |
| `site.zip.sig` | the signature, once signed |
| `build.json` | the library record: id, site, revision, created, size, files, signed; the only file that holds a time |

`publish.json` has sorted keys, two-space indent and a trailing newline:

```json
{
  "builtWith": "FormPublisher 0.1.3",
  "checks": { "errors": 0, "infos": 0, "tiers": ["static"], "warnings": 0 },
  "files": [ { "path": "index.html", "sha256": "...", "size": 1024 } ],
  "format": "formpublisher-site",
  "headers": [
    { "for": "/*", "values": { "Referrer-Policy": "strict-origin-when-cross-origin", "X-Content-Type-Options": "nosniff" } },
    { "for": "/assets/*", "values": { "Cache-Control": "public, max-age=3600" } }
  ],
  "package": { "file": "site.zip", "sha256": "...", "size": 20480 },
  "redirects": [],
  "routes": [],
  "site": { "id": "...", "name": "...", "revision": "...", "source": { "formwebVersion": "0.19.1", "kind": "formweb-export" } },
  "version": 1
}
```

`source.kind` is `formweb-export`, `publication`, `fweb` or `folder`.

Reproduce rebuilds the revision in a temporary folder and compares the SHA-256 with the stored one: it answers `same`, the new hash and the expected hash.

### Keys

Signing uses Ed25519. New key creates a pair: the private key is PKCS8 PEM in `keys/[id].pem`, mode 0600, encrypted when you give a passphrase; the public key is raw 32 bytes in base64 in `keys/index.json` with the name, fingerprint, created time and whether it is encrypted. The fingerprint is `SHA256:` followed by the base64 (no padding) of the SHA-256 of the raw public key, and the key id is the first 16 hex digits of that digest. Deleting a key moves its files to the trash. Back up the private key; FormPublisher cannot recover a lost one.

### Sign and verify

Sign signs the exact bytes of `site.zip` and writes `site.zip.sig`, sorted JSON with a trailing newline:

```json
{
  "algorithm": "ed25519",
  "key": "SHA256:...",
  "publicKey": "base64 of the 32-byte public key",
  "signature": "base64 of the signature"
}
```

A wrong passphrase is refused with "The passphrase does not unlock this key." Verify checks that the signature is valid over the current zip bytes with the public key in the file and that the fingerprint matches that key. It answers `valid`, the key, and a reason when invalid. Changing any byte of `site.zip` makes it invalid.

### The Builds page

Builds in Home lists builds newest first with site, id, date, size and signed. Inspect shows the file table from `publish.json`. Compare takes two builds and lists the files added, removed and changed by path, with the count that are the same. Delete moves a build to the [trash](#trash). Download saves the zip.

## Publish

Publish opens from the toolbar's Publish button, from the Publish button in the Package sheet, or from the command palette (`publish.open`). It prepares a package for a host. It writes a folder and shows the exact commands to run, and it never uploads anything: running the commands is up to you.

The sheet has three parts:

- **Build.** A picker lists the builds of the open site, the latest selected. With no build yet, Build now makes one first.
- **Hosts.** One card per host with a check box: Static zip, Netlify, Cloudflare Pages, Vercel, GitHub Pages and nginx. Select all and Select none tick them together. Prepare writes a folder for each ticked host.
- **Keep FormWeb's model files.** A check box under the hosts, off by default. See below.
- **Prepared folders.** One panel per prepared host with the folder path (Reveal opens it in the system file manager, Copy path copies it), the commands (each has a copy button), notes and warnings, Verify, and Remove.

What each host gets. Every folder is written from the build's own `site.zip`, never from the live site folder, and the same build always gives the same bytes.

| Host | Writes | Commands |
| --- | --- | --- |
| Static zip | `site.zip` (the build's own bytes), `publish.json`, `SHA256SUMS`, `README.txt` | `unzip site.zip -d site`, `python3 -m http.server -d site 8080` |
| Netlify | `site/` with `_redirects` (301 or 302 per redirect, then `/* /404.html 404` when the site has a 404 page) and `_headers` | `npx netlify-cli deploy --dir site` (draft), the same with `--prod`, and `npx netlify-cli dev --dir site` |
| Cloudflare Pages | `site/` with `_redirects` and `_headers` in Cloudflare's syntax; no 404 rule, because Pages serves `404.html` itself | `npx wrangler pages deploy site --project-name SLUG`, `npx wrangler pages dev site` |
| Vercel | `site/` with `vercel.json` (`cleanUrls`, `trailingSlash`, `redirects`, `headers`) | `npx vercel deploy site`, with `--prod`, and `npx vercel dev site` |
| GitHub Pages | `site/` with `.nojekyll`, a `404.html`, a small meta-refresh `index.html` per redirect, and `.github/workflows/pages.yml` | the `git` commands for a `gh-pages` branch, or the Actions workflow |
| nginx | `site/` with `formpublisher.conf` (a `server` block with `try_files`, `error_page 404`, one `location =` per redirect, `add_header ... always`, gzip) and `nginx-test.conf` | `nginx -t -c ...`, and a `docker run` line with `nginx:stable` |

A FormWeb 404 page exported as `404/index.html` counts as the site's 404, and is also written as `404.html` for the hosts that look for that name. A host that cannot represent something says so under Warnings and never drops it silently: GitHub Pages has no server redirects and ignores custom headers, so each redirect becomes a meta-refresh page and each ignored header is named.

Left-out model files. A FormWeb site carries its editing model, `site.formweb.json`, and `asset-access.json`. A host does not need them, and they can reveal more of the site than its visitors see, so the `site/` folder of each host is written without them. The Publish sheet's Keep FormWeb's model files box, `--include-model` on the command line and `includeModel: true` in the MCP tool put them back for one prepare. Each prepared panel says "Left out: ..." and the result lists them under `leftOut`; Verify knows which files were left out and does not report them missing. The package is unchanged: `site.zip` is the build's own bytes and still holds both files, and the Static zip host writes that zip as it is, so the option affects the `site/` folders of the other five hosts only.

Verify re-reads the folder and checks every file against the hashes in `publish.json`, and the host's own files against a fresh prepare. Remove moves the folder to `trash/`. Preparing again replaces the folder. Prepared folders live at `prepared/[site]/[build]/[host]/` in the data folder, and the sheet remembers what is prepared for each build when you close and reopen it.

## Receive from FormWeb

FormWeb's Send to FormPublisher hands a site over without a file dialog. There are two ways in, and both end in the same import (a re-send of the same project adds a revision to the same site).

- **The endpoint.** `POST /api/receive/formweb` takes the bytes of a FormWeb `site-export.zip` as `application/zip` (up to 512 MiB), with the header `X-FormWeb-Version` and optionally `X-FormWeb-Site-Name` and `X-FormWeb-Project`. It answers `{site, revision, opened}`, where `opened` is true when a window is listening. Only this computer may send: a request from another address is refused with 403, and so is one with a foreign `Origin`. A running window shows a toast, "Received [name] from FormWeb", with Open; on Home the new site appears in Recent with no reload.
- **The inbox.** When FormPublisher is closed, FormWeb writes the file into `inbox/` in the data folder instead. Every `*.zip` or `*.fweb` there that has not changed for 2 seconds is imported when the engine starts and every 5 seconds while it runs. A file that imports moves to `inbox/imported/` with a timestamp in front of its name; one that does not moves to `inbox/failed/` with a `.txt` file giving the reason.

Inbox metadata. FormWeb writes a small `NAME.zip.json` beside the zip it leaves in the inbox, with `siteName`, `project` and `version` (the same three things the endpoint takes as headers). The import reads it, so a site that arrives through the inbox gets its name and its project, and a later arrival of the same project adds a revision to the same site instead of making a new one. The file moves with the zip to `imported/` or `failed/`. Without it the site arrives with no name and no project.

Auto-check and auto-build. Two switches in Preferences, FormWeb section, both off by default: Check a site when it arrives, and Build a site when it arrives (settings `receive.autoCheck` and `receive.autoBuild`). When on, each site that arrives from FormWeb, by the endpoint or the inbox, gets the static checks run and then the package built, in that order, on a background thread so the receive answer never waits. They emit the same events as the manual actions (`checks.done`, then the build's own) and a `receive.pipeline` event with the outcome, so a window that is open updates by itself and the problems are ready when you open the site. A failure is reported in that event and never breaks the import.

`GET /api/receive/status` (and `./formpublisher run receive-status`) reports the endpoint, the inbox path, whether the watcher is running, how many files are waiting, and the last five receipts.

## Revisions and diffs

A site that arrives more than once, by the same project, gains a revision each time. Home's site card shows "N revisions" when there are several; pressing it opens the Revisions dialog, and the site's own panel has a Revisions tab. The list shows each revision's time, its file count and, from the second on, how many files were added, removed and changed from the one before. Pick any two with From and To to see the files that were added, removed and changed (path, size before and after, short hash) and the routes added and removed. With one revision the dialog says there is nothing to compare yet.

The same lists come from `GET /api/sites/{id}/revisions` and `GET /api/sites/{id}/diff?from=&to=` (without `from` and `to` the latest revision is compared with the one before it), from `./formpublisher run revisions SITE-ID` and `./formpublisher run diff SITE-ID [--from R] [--to R]`, and from the MCP tools `list_revisions` and `diff_revisions`. All of them only read.

## The demo

Home has a Demos row with a FormPublisher demo card. It imports the bundled sample site, "Northwind Notes", once (opening it again finds the same site) and opens it. A quick tour strip then walks the toolbar through Preview, Checks, Package and Publish. It can be skipped, it is remembered, and it moves nothing on screen. The sample is a three-page product site exported from FormWeb, with only CC0 pictures drawn for it (`demo/MEDIA.md` lists each file's source).

`demo/index.html` is an offline version that runs straight from disk, with no network and no build step. It shows the FormPublisher window in both themes driving the sample site in a frame through the device widths, the checks list from a real run, the package manifest from a real build and the six prepared folders with their files and commands. The three data files in `demo/data/` come from real runs of the engine, never written by hand; `demo/data/data.js` bundles them so the page opens from `file://`.

## Agents

An agent does every step a person does. The command line and the MCP server are thin layers over the same engine routes as the window, so what an agent does appears in the open window at once. They use a running engine that has the same data folder, or run the routes in-process when none runs.

The loop is: import a site, list its routes (and, for a site that arrived again, its revisions and what changed), run the checks, build, sign, verify, list the targets, prepare, read what is prepared. Asking the person comes first for anything that reads from a running FormWeb, for creating or choosing a signing key and for any passphrase. Preparing writes only inside the data folder.

`./formpublisher agents sync` mirrors `.claude/skills` to `.agents/skills` and checks the skill files; `--check` exits 1 on drift. `./formpublisher agents install` registers the MCP servers and copies the skills for your account in Claude Code, Codex and Cursor. The repository's kits (`.claude/skills/formpublisher-harness`, `.claude/skills/formpublisher-skillset`, `AGENTS.md`, `CLAUDE.md`) name the tools and commands below.

## The command line

`./formpublisher run` has one command per step. Every command takes `--json` for the raw answer, `--engine URL` to name an engine and `--in-process` to skip any running engine.

| Command | Does |
| --- | --- |
| `status` | the engine, the data folder, the site count and whether FormWeb answers |
| `sites` | lists the imported sites |
| `import PATH [--name N]` | imports a FormWeb export zip or a publication folder |
| `import-formweb` | imports the site open in a running FormWeb, read-only |
| `routes ID` | lists the routes of a site |
| `check ID [--revision R] [--deep] [--widths 390,1440] [--last]` | runs the checks and prints the problems; `--last` prints the stored result |
| `build ID [--revision R]` | builds the deterministic `site.zip` and `publish.json` |
| `builds` | lists builds, newest first |
| `sign BUILD [--key K] [--passphrase P]` | signs a build with an Ed25519 key |
| `verify BUILD` | verifies a signature; exits 1 when it is not valid |
| `keys [--create NAME] [--passphrase P]` | lists signing keys, or creates one |
| `targets` | lists the six host targets |
| `revisions ID` | lists a site's revisions, newest first, with what changed from the one before |
| `diff ID [--from R] [--to R]` | the files and routes added, removed and changed between two revisions |
| `prepare BUILD --target T [--target T] [--include-model]` | prepares a folder per target, with the commands to run; FormWeb's model files are left out unless `--include-model` |
| `prepared BUILD` | lists what is prepared for a build |
| `trash` | lists the trash, newest first, with each entry's kind, label, time and size |
| `trash restore ENTRY` | moves an entry back to where it came from; fails with the reason when the place is taken |
| `trash delete ENTRY` | deletes one entry for good |
| `trash empty --yes` | deletes every entry for good; refuses to run without `--yes` |
| `receive-status` | the receive endpoint, the inbox folder and the last receipts |

```sh
./formpublisher run import demo/sample-site.zip
./formpublisher run check SITE-ID
./formpublisher run build SITE-ID
./formpublisher run prepare BUILD-ID --target netlify --target nginx
./formpublisher run --help
```

Answers are short text, or JSON with `--json`. A failure exits non-zero with the reason. The command uses a running engine with the same data folder, or runs in-process.

## The MCP server

`./formpublisher mcp` serves MCP on stdio with 18 tools over the same routes. `.mcp.json` registers it for Claude Code in this repository, `.codex/config.toml` for Codex and `.cursor/mcp.json` for Cursor. `./formpublisher agents install` sets Claude Code, Codex and Cursor up for your account.

| Tool | Does |
| --- | --- |
| `formpublisher_status` | the engine, the data folder, the site count, FormWeb reachability (read only) |
| `list_sites` | the imported sites (read only) |
| `import_site` | imports a FormWeb export or publication folder from an absolute path |
| `import_formweb_current` | imports the site open in a running FormWeb |
| `site_routes` | the routes of a site (read only) |
| `list_revisions` | the revisions of a site, newest first, with what changed from the one before (read only) |
| `diff_revisions` | the files and routes added, removed and changed between two revisions (read only) |
| `run_checks` | runs the static tier, or the deep tier too, and stores the result |
| `get_checks` | the stored check results (read only) |
| `build_package` | builds `site.zip` and `publish.json` |
| `list_builds` | the builds, newest first (read only) |
| `sign_build` | signs a build with a named key |
| `verify_build` | verifies a build's signature (read only) |
| `list_targets` | the six hosts a build can be prepared for (read only) |
| `prepare_publish` | prepares a folder per host for a build, with commands, notes and warnings; `includeModel: true` keeps FormWeb's model files, and `leftOut` lists what was left out |
| `get_prepared` | what is prepared for a build (read only) |
| `list_trash` | the trash entries, newest first (read only) |
| `restore_from_trash` | moves an entry back to where it came from |

There is no tool that deletes. Deleting an entry for good or emptying the trash is for a person, in the window or with `trash delete` and `trash empty --yes`.

## Settings and the data folder

Everything is kept in `~/FormPublisher`, or in the folder named by `FORMPUBLISHER_HOME`: `sites/` (imports), `checks/` (results and thumbnails), `builds/` (packages), `prepared/` (the folders Publish writes), `inbox/` (files FormWeb leaves for FormPublisher, each with its `.json` metadata), `keys/` (signing keys), `trash/` (removed items and their `.trash.json` records), `engine.json` (the running engine's app, port, pid, version and start time) and `settings.json`. The engine port is `FORMPUBLISHER_PORT` (8280 by default) and the site host port is `FORMPUBLISHER_HOST_PORT` (8281). The interface is in 26 languages.

## When something goes wrong

- The window cannot reach the engine: run `./formpublisher doctor` and check that 8280 is listening.
- An import is refused: the message names the reason (not a zip, no `routes.json`, or no FormWeb on loopback).
- A port is taken: stop what uses 8280, 8281, 5280 or 5281, or set `FORMPUBLISHER_PORT` or `FORMPUBLISHER_HOST_PORT`. The desktop app picks another free port by itself when 8280 is taken, and FormWeb then falls back to the inbox.
- A prepared folder has no `site.formweb.json`: that is the default. Prepare again with Keep FormWeb's model files (`--include-model`) to include it.
- The preview shows a short text page: nothing is mounted (503). Open a site again.
- A `.fweb` import answers 422: run `./setup/install_compiler`.
- The deep check reports `deep.unavailable`: run `./formpublisher_oc_install` and make sure Chrome is installed, or set `checks.chromePath`.
- Anything else: open an issue with `./formpublisher version` and your platform.
