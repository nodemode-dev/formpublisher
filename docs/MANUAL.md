# FormPublisher Manual

FormPublisher is the Form family's site publisher. It opens what FormWeb makes, lists the site's routes and shows them in a FormDeck-style window. People and agents use the same steps: each one is also a command line command and an MCP tool.

It imports FormWeb sites, previews them on device sizes, checks them, and builds signed packages. In development: publishing to a host and the desktop build.

## Contents

- [Getting started](#getting-started)
- [Home](#home)
- [Importing a site](#importing-a-site)
- [Routes](#routes)
- [.fweb projects](#fweb-projects)
- [Preview](#preview)
- [Checks](#checks)
- [Packages and signatures](#packages-and-signatures)
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

## Home

Home is the start page. It offers a drop zone for a FormWeb export, the list of recent sites, and your open sites. Opening a site puts it in a tab.

## Importing a site

There are three ways in, and all of them only read:

- **A site export.** Drop FormWeb's `site-export.zip` on Home, or choose it.
- **A publication folder.** Choose a FormWeb publication folder, `publications/[slug]/[version]/`.
- **The site open in FormWeb.** With FormWeb running on the same computer, import its current site. FormPublisher asks FormWeb's `GET /api/export` over loopback. It never calls `/api/load` and never changes what FormWeb has open.

## Routes

A site's routes come from its `routes.json`. Each has a path, a page, a locale, an item and a stylesheet. The routes strip lists them, the inspector shows the selected route, and the status bar shows how many there are.

## .fweb projects

A `.fweb` file is a FormWeb project: a JSON envelope with the format `com.nodemode.formweb`. Import it like a zip or a folder, from Home or the file dialog. FormPublisher hands it to `formweb-core`, the compiler built from the FormWeb crates vendored in `vendor/formweb-native/`. The compiler loads the project and exports every locale with the site's default locale as the base, and FormPublisher writes the files and the referenced assets (`/api/assets/[sha].[ext]` references become real files, as FormWeb's own bundling does). The import is recorded with source kind `fweb`; importing the same project again adds a revision.

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

A deep check drives the Chrome you already have installed through Playwright. It serves the revision from its own temporary host with no probe, and for each route at 1440 by 900 and 390 by 844 (or the widths you pass) it opens a fresh context, applies a 4x CPU slowdown and a slow network (150 ms, 200 KB/s), records layout shifts, loads the page, scrolls to the bottom in 8 steps and back, and reads the results. Problems:

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

A build contains every file in the revision except FormPublisher's own records. `site.zip` is deterministic: entries sorted by UTF-8 path, forward slashes, timestamps fixed at 1980-01-01, mode 0644, deflate level 9, no directory entries, no extra fields and no comment. The same revision gives the same bytes on every machine. The build id is the first 12 hex digits of the zip's SHA-256. Building an identical revision again returns the existing build.

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
  "builtWith": "FormPublisher 0.1.1",
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

Builds in Home lists builds newest first with site, id, date, size and signed. Inspect shows the file table from `publish.json`. Compare takes two builds and lists the files added, removed and changed by path, with the count that are the same. Delete moves a build to the trash. Download saves the zip.

## The command line

`./formpublisher run` has one command per step:

```sh
./formpublisher run status
./formpublisher run sites
./formpublisher run import site-export.zip
./formpublisher run import-formweb
./formpublisher run routes SITE-ID
./formpublisher run --help
```

Answers are short text, or JSON with `--json`. A failure exits non-zero with the reason. The command uses a running engine with the same data folder, or runs in-process.

## The MCP server

`./formpublisher mcp` serves MCP on stdio with the same tools. `.mcp.json` registers it for Claude Code in this repository, `.codex/config.toml` for Codex and `.cursor/mcp.json` for Cursor. `./formpublisher agents install` sets Claude Code, Codex and Cursor up for your account.

## Settings and the data folder

Everything is kept in `~/FormPublisher`, or in the folder named by `FORMPUBLISHER_HOME`: `sites/` (imports), `checks/` (results and thumbnails), `builds/` (packages), `keys/` (signing keys), `trash/` and `settings.json`. The engine port is `FORMPUBLISHER_PORT` (8280 by default) and the site host port is `FORMPUBLISHER_HOST_PORT` (8281). The interface is in 26 languages.

## When something goes wrong

- The window cannot reach the engine: run `./formpublisher doctor` and check that 8280 is listening.
- An import is refused: the message names the reason (not a zip, no `routes.json`, or no FormWeb on loopback).
- A port is taken: stop what uses 8280, 8281, 5280 or 5281, or set `FORMPUBLISHER_PORT` or `FORMPUBLISHER_HOST_PORT`.
- The preview shows a short text page: nothing is mounted (503). Open a site again.
- A `.fweb` import answers 422: run `./setup/install_compiler`.
- The deep check reports `deep.unavailable`: run `./formpublisher_oc_install` and make sure Chrome is installed, or set `checks.chromePath`.
- Anything else: open an issue with `./formpublisher version` and your platform.
