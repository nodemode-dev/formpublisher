---
name: formpublisher-harness
description: Drives FormPublisher, the Form family's site publisher, through its formpublisher MCP server or the ./formpublisher run command line. Use whenever the person wants a FormWeb site exported as site-export.zip imported, a FormWeb publication folder opened, the site currently open in a running FormWeb brought in, the imported sites listed, a site's routes listed, its revisions listed or compared, a .fweb project opened, a site mounted for preview, checked (static or deep), built into a deterministic site.zip, or signed and verified with an Ed25519 key, or prepared for a host (Netlify, Cloudflare Pages, Vercel, GitHub Pages, nginx or a plain zip); or when formpublisher tools such as list_sites, import_site, run_checks, build_package or prepare_publish are available or fail. Not for editing a site (that is FormWeb), not for changing FormPublisher's own source code (use formpublisher-skillset), and not for uploading to a host, which FormPublisher never does.
metadata:
  version: "0.2.0"
---

# formpublisher harness

FormPublisher opens what FormWeb makes and shows its routes in a FormDeck-style window. Its engine keeps imported sites in its data folder (`~/FormPublisher`, or `FORMPUBLISHER_HOME`). The MCP server, named `formpublisher`, exposes the engine as tools; `./formpublisher run` is the same surface on the command line (each tool has a command, listed in the table below).

When the FormPublisher window is open, the tools talk to its engine on 127.0.0.1:8280 and every change appears in the window as it happens. When it is closed, the tools run the engine's routes inside the server process against the same data folder. `status` says which.

## What it reads

- A FormWeb site export, `site-export.zip` (from FormWeb's export).
- A FormWeb publication folder, `publications/[slug]/[version]/`.
- The site currently open in a running FormWeb, read through FormWeb's read-only `/api/export` on loopback.

FormPublisher only reads FormWeb. It never calls FormWeb's `/api/load`, which would replace the document FormWeb has open, and it never changes a site. Edits go back to FormWeb.

## The tools

These are the exact MCP tool names, with the command that does the same thing. Ids are the ones the previous tool returned: a site id from `list_sites`, a build id from `list_builds`, a target id from `list_targets`.

| MCP tool | Command | Does | Reads only |
| --- | --- | --- | --- |
| `formpublisher_status` | `status` | engine, data folder, site count, FormWeb reachability | yes |
| `list_sites` | `sites` | imported sites | yes |
| `import_site` (path) | `import PATH` | import a site export zip or publication folder as a new revision | no |
| `import_formweb_current` | `import-formweb` | import the site open in a running FormWeb | no |
| `site_routes` (id) | `routes ID` | routes of the latest revision | yes |
| `list_revisions` (id) | `revisions ID` | revisions newest first, with files, bytes, routes and what changed from the one before | yes |
| `diff_revisions` (id, from_revision, to_revision) | `diff ID [--from R] [--to R]` | files added, removed and changed (path, size, SHA-256) and routes added and removed between two revisions; default the latest against the one before | yes |
| `run_checks` (id, deep, widths, revision) | `check ID [--deep] [--widths 390,1440]` | run the static tier, and the Chrome tier with deep | no |
| `get_checks` (id, revision) | `check ID --last` | stored results, nothing runs | yes |
| `build_package` (id, revision) | `build ID [--revision R]` | deterministic site.zip and publish.json | no |
| `list_builds` | `builds` | builds, newest first | yes |
| `sign_build` (build, key, passphrase) | `sign BUILD [--key K]` | detached Ed25519 signature | no |
| `verify_build` (build) | `verify BUILD` | check the signature against the zip | yes |
| `list_targets` | `targets` | the six hosts | yes |
| `prepare_publish` (build, targets, includeModel) | `prepare BUILD --target T [--target T] [--include-model]` | a folder per target with the commands to run | no |
| `get_prepared` (build) | `prepared BUILD` | what is already prepared | yes |
| `list_trash` | `trash` | trash entries newest first, with kind, label, origin, time and size | yes |
| `restore_from_trash` (entry, passphrase) | `trash restore ENTRY` | move an entry back to its recorded or inferred origin (entries from before 0.1.4 have an inferred one); 409 with the reason when the place is taken, and 409 `origin-unknown` when there is none. A trashed key with a missing or damaged record is rebuilt from its `.pem`: an encrypted one answers 409 `passphrase-required`, then `passphrase-wrong`, so ask the person and pass `passphrase`; the CLI reads it with `--passphrase-stdin`. Never log or store it | no |

Not tools: `trash delete ENTRY` deletes one trash entry for good and `trash empty --yes` deletes them all. There is no tool for either, and deleting stays a person's action: do it only when the person asks for that entry. `trash restore ENTRY --to PATH` (the HTTP body `{origin}`, or the Trash page's "Where does it go" dialog) restores to a named place for an entry whose origin is unknown; it stays a person's or the command line's action, and the MCP tool only restores recorded or inferred origins, so when it answers `origin-unknown` tell the person rather than inventing a path. Every error answer is `{detail, code}`, the CLI prints `error [code]: detail` (exit 1, or 3 when the engine is unreachable) and MCP tool errors start with the same label; branch on the code. The named place must fit its kind (site: lowercase letters, digits, hyphens; key: 16 hex; build: `[site]/[12-hex id]`; prepared: `[site]/[build id]/[target]`) or the engine answers 409 `place-invalid`. The full list is in the manual under Error codes. `keys` lists the signing keys and `keys --create NAME [--passphrase P]` makes one, and `receive-status` shows the endpoint, inbox folder and last receipts for FormWeb's Send to FormPublisher. `agents sync` is `./formpublisher agents sync`.

## The loop

1. `formpublisher_status`: the engine, the data folder, the version, and whether a FormWeb is reachable.
2. `list_sites`: the sites already imported.
3. `import_site` or `import_formweb_current`: bring a site in. Give a path to a `site-export.zip` or to a publication folder, or ask for the site open in FormWeb. Ask the person before reading from a running FormWeb.
4. `site_routes`: the routes of one imported site (path, page, locale, item, stylesheet), the same list the window's routes strip shows.
5. `run_checks`, then `build_package`, `sign_build`, `verify_build`, `list_targets` and `prepare_publish`, as described under Publishing.

```sh
./formpublisher run status
./formpublisher run sites
./formpublisher run import ~/Downloads/site-export.zip
./formpublisher run import-formweb
./formpublisher run routes SITE-ID
./formpublisher run --help
```

`--json` after any command prints the raw answer.

## Publishing

FormPublisher prepares; it never uploads. Publishing is a chain, and each link needs the id the one before returned.

1. `run_checks` with the site id. Report the counts and each problem with its code and fix. Add `deep` only when the person wants the browser run; `deep.unavailable` means Chrome or Playwright is missing, so say so.
2. `build_package` with the site id. The same site gives the same build id, so a repeated call returns the existing build with `created` false.
3. `sign_build` with the build id and a key the person named (a key id from `keys`). With one key in the data folder and no `key` argument it uses that one and says which; with none it fails and the person creates one with `./formpublisher run keys --create NAME`. Then `verify_build` and report `valid` as returned.
4. `list_targets` for the six ids: `static-zip`, `netlify`, `cloudflare-pages`, `vercel`, `github-pages`, `nginx`.
5. `prepare_publish` with the build id and the target ids the person wants. Each result has the prepared `folder`, its `files`, the `commands` (label, run, cwd) to run, `notes` and `warnings`. Show the commands exactly as returned and the warnings in full (for example GitHub Pages has no server redirects); do not run a deploy command yourself unless the person asks. Preparing again replaces the folder. Where nginx is installed, preparing the nginx target also runs `nginx -t` and adds a note or a warning, and a verify of a prepared folder answers `nginx` with `ran`, `ok`, `version` and `output` (a failure is a problem row; `ran: false` without nginx); `nginx` also carries `listen` with `ran`, `ok` and `output` for the second pass that points every listen line at a free loopback port, so a bad listen parameter fails; the nginx folder also carries `nginx-check.sh`, which the person can run with `sh nginx-check.sh` or `./nginx-check.sh` without root (it checks unix sockets, then each listen line on a loopback port, and `NGINX_CHECK_PORT` sets the first). GitHub Pages follows splat redirects through a script at the top of `404.html` under the site's base path, and with scripts off a splat address shows the 404 page, so report its note about the assumed path. The host folders leave out FormWeb's model files (`site.formweb.json`, `asset-access.json`), which no host needs, and each result lists them under `leftOut`; pass `includeModel` true only when the person wants them kept.
6. `get_prepared` reads back what exists for a build without preparing anything.

```sh
./formpublisher run check SITE-ID
./formpublisher run build SITE-ID
./formpublisher run keys --create "release key"
./formpublisher run sign BUILD-ID --key KEY-ID
./formpublisher run verify BUILD-ID
./formpublisher run targets
./formpublisher run prepare BUILD-ID --target netlify --target nginx
./formpublisher run prepared BUILD-ID
./formpublisher run receive-status
```

A site sent from FormWeb's Send to FormPublisher arrives on its own: it is imported by the running window's engine, or dropped in the data folder's `inbox/` while FormPublisher is closed. Either way, a site sent again becomes a new revision of the same site, so `list_revisions` and `diff_revisions` show what changed between sends. It then shows in `list_sites` like any import. Two Preferences settings, off by default, run the static checks and a build on every arrival; when they are on, call `get_checks` and `list_builds` instead of running them again.

Removing a site, build, key or prepared folder moves it to the trash, so `list_trash` shows it and `restore_from_trash` brings it back when the person asks, entries from before 0.1.4 included. Use the entry name `list_trash` returned. In the window one Restore from the trash dialog asks for a place, a passphrase or both, and a build-missing or site-missing notice offers Restore when one trash entry matches.

A `.fweb` project (envelope format `com.nodemode.formweb`, or FormWeb's version 2 zip of up to 512 MiB) imports the same way. It needs `formweb-core`; without it the import fails with 422 and the message says to run `./setup/install_compiler`. Tell the person; do not try to work around it.

## Preview, checks, builds and keys

These are engine routes on 127.0.0.1:8280 (the window must be open, or the engine running with `./formpublisher serve`). Send JSON; every route answers JSON. Put a site id from `sites` in `site`; `revision` is optional and defaults to the latest.

Mount a revision on the site host (port 8281, a separate origin that serves it like a static host). One mount is active; a new one replaces it.

```sh
curl -s -X POST 127.0.0.1:8280/api/host/mount -H 'Content-Type: application/json' \
  -d '{"site": "SITE-ID", "probe": true, "theme": "dark", "motion": "reduce", "throttle": "fast"}'
# {"url": "http://127.0.0.1:8281/", "generation": 3, "origin": "http://127.0.0.1:8281"}
curl -s 127.0.0.1:8280/api/host                       # the current mount
curl -s -X DELETE 127.0.0.1:8280/api/host/mount       # unmount
```

`theme` is auto, dark or light; `motion` is auto or reduce; `throttle` is none, fast or slow. `probe` injects the preview probe script and is for previewing only.

Run checks and read the problems. The static tier is offline and returns at once; the deep tier needs the person's installed Chrome and the optional Playwright requirements, runs in the background, and reports `checks.progress` and `checks.done` on the live socket.

```sh
curl -s -X POST 127.0.0.1:8280/api/checks/run -H 'Content-Type: application/json' \
  -d '{"site": "SITE-ID", "tiers": ["static", "deep"], "widths": [1440, 390], "motion": "auto"}'
# {"run": "..."}
curl -s 127.0.0.1:8280/api/checks/SITE-ID/REVISION
# {"problems": [{"id": "static:link.broken:about/:3", "tier": "static", "severity": "error",
#   "code": "link.broken", "route": "/about/", "message": "...", "fix": "...", "file": "about/index.html", "line": 3}],
#  "summary": {"errors": 1, "warnings": 0, "infos": 0, "tiers": ["static"], "ran": true},
#  "thumbs": {"/": "/api/checks/SITE-ID/REVISION/thumbs/ab12.png"}}
```

Report the counts and the problems as returned, with each code and fix. A `deep.unavailable` problem means Chrome or Playwright is missing; say so and do not install a browser. The codes are listed in `docs/MANUAL.md`.

Build, reproduce, compare and download:

```sh
curl -s -X POST 127.0.0.1:8280/api/builds -H 'Content-Type: application/json' -d '{"site": "SITE-ID"}'
# {"id": "3f9a1c0b7d42", "site": "SITE-ID", "revision": "...", "size": 20480, "files": 12, "signed": false}
curl -s -X POST 127.0.0.1:8280/api/builds/3f9a1c0b7d42/reproduce
# {"same": true, "sha256": "...", "expected": "..."}
curl -s 127.0.0.1:8280/api/builds                     # newest first
curl -s 127.0.0.1:8280/api/builds/3f9a1c0b7d42        # build.json plus publish.json
curl -s 127.0.0.1:8280/api/builds/3f9a1c0b7d42/compare/OTHER-ID
# {"added": [], "removed": [], "changed": [{"path": "index.html", "a": {"sha256": "...", "size": 1}, "b": {"sha256": "...", "size": 2}}], "same": 11}
curl -s -o site.zip 127.0.0.1:8280/api/builds/3f9a1c0b7d42/download
```

Keys and signatures. A key is Ed25519; the private half never leaves `keys/` and is never returned.

```sh
curl -s -X POST 127.0.0.1:8280/api/keys -H 'Content-Type: application/json' -d '{"name": "release key", "passphrase": "optional"}'
# {"id": "...", "name": "release key", "fingerprint": "SHA256:...", "created": "...", "encrypted": true}
curl -s 127.0.0.1:8280/api/keys                       # list, no private material
curl -s 127.0.0.1:8280/api/keys/KEY-ID/public         # {"id", "fingerprint", "publicKey"}
curl -s -X POST 127.0.0.1:8280/api/builds/3f9a1c0b7d42/sign -H 'Content-Type: application/json' -d '{"key": "KEY-ID", "passphrase": "optional"}'
curl -s -X POST 127.0.0.1:8280/api/builds/3f9a1c0b7d42/verify
# {"valid": true, "key": "SHA256:..."}   or   {"valid": false, "key": "SHA256:...", "reason": "..."}
```

A wrong passphrase answers 400 "The passphrase does not unlock this key." Ask the person for the passphrase; never invent or store one. Deleting a key (`DELETE /api/keys/KEY-ID`) or a build (`DELETE /api/builds/ID`) moves it to the trash (`GET /api/trash` lists it, `POST /api/trash/ENTRY/restore` restores it), and should be done only when the person asks. `DELETE /api/trash/ENTRY` and `DELETE /api/trash` remove for good; never call them unprompted. A locked key restored from the trash takes `{"passphrase": "..."}` in the restore body when its record has to be rebuilt.

## Rules

- Say what was imported and how many routes it has. Say what a check or a build reported, with its numbers; do not claim a publication: a prepared folder is not a deployed site until the person runs its commands.
- Do not sign with a key the person did not name, and do not create a key unless asked. Do not report a package as signed until verify answers `valid: true`.
- A failed import names the reason (not a zip, no `routes.json`, FormWeb not reachable); report it as it is and ask for the right path.
- Never write into FormPublisher's data folder by hand; use `import`.
- Never call FormWeb's `/api/load` or any route that changes FormWeb.
