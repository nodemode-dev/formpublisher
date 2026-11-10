---
name: formpublisher-harness
description: Drives FormPublisher, the Form family's site publisher, through its formpublisher MCP server or the ./formpublisher run command line. Use whenever the person wants a FormWeb site exported as site-export.zip imported, a FormWeb publication folder opened, the site currently open in a running FormWeb brought in, the imported sites listed, a site's routes listed, a .fweb project opened, a site mounted for preview, checked (static or deep), built into a deterministic site.zip, or signed and verified with an Ed25519 key; or when formpublisher tools such as status, sites, import and routes are available or fail. Not for editing a site (that is FormWeb), not for changing FormPublisher's own source code (use formpublisher-skillset), and not for publishing to a host, which is in development.
metadata:
  version: "0.1.1"
---

# formpublisher harness

FormPublisher opens what FormWeb makes and shows its routes in a FormDeck-style window. Its engine keeps imported sites in its data folder (`~/FormPublisher`, or `FORMPUBLISHER_HOME`). The MCP server, named `formpublisher`, exposes the engine as tools; `./formpublisher run` is the same surface on the command line (each tool is a command with the same name).

When the FormPublisher window is open, the tools talk to its engine on 127.0.0.1:8280 and every change appears in the window as it happens. When it is closed, the tools run the engine's routes inside the server process against the same data folder. `status` says which.

## What it reads

- A FormWeb site export, `site-export.zip` (from FormWeb's export).
- A FormWeb publication folder, `publications/[slug]/[version]/`.
- The site currently open in a running FormWeb, read through FormWeb's read-only `/api/export` on loopback.

FormPublisher only reads FormWeb. It never calls FormWeb's `/api/load`, which would replace the document FormWeb has open, and it never changes a site. Edits go back to FormWeb.

## The loop

1. `status`: the engine, the data folder, the version, and whether a FormWeb is reachable.
2. `sites`: the sites already imported.
3. `import`: bring a site in. Give a path to a `site-export.zip` or to a publication folder, or ask for the site open in FormWeb. Ask the person before reading from a running FormWeb.
4. `routes`: the routes of one imported site (path, page, locale, item, stylesheet), the same list the window's routes strip shows.

```sh
./formpublisher run status
./formpublisher run sites
./formpublisher run import ~/Downloads/site-export.zip
./formpublisher run import-formweb
./formpublisher run routes SITE-ID
./formpublisher run --help
```

`--json` after any command prints the raw answer.

A `.fweb` project (envelope format `com.nodemode.formweb`) imports the same way. It needs `formweb-core`; without it the import fails with 422 and the message says to run `./setup/install_compiler`. Tell the person; do not try to work around it.

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

A wrong passphrase answers 400 "The passphrase does not unlock this key." Ask the person for the passphrase; never invent or store one. Deleting a key (`DELETE /api/keys/KEY-ID`) or a build (`DELETE /api/builds/ID`) moves it to the trash, and should be done only when the person asks.

## Rules

- Say what was imported and how many routes it has. Say what a check or a build reported, with its numbers; do not claim a publication, because publishing to a host is in development.
- Do not sign with a key the person did not name. Do not report a package as signed until verify answers `valid: true`.
- A failed import names the reason (not a zip, no `routes.json`, FormWeb not reachable); report it as it is and ask for the right path.
- Never write into FormPublisher's data folder by hand; use `import`.
- Never call FormWeb's `/api/load` or any route that changes FormWeb.
