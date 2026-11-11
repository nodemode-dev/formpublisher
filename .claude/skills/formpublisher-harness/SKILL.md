---
name: formpublisher-harness
description: Drives FormPublisher, the Form family's site publisher, through its formpublisher MCP server or the ./formpublisher run command line. Use whenever the person wants a FormWeb site exported as site-export.zip imported, a FormWeb publication folder opened, the site currently open in a running FormWeb brought in, the imported sites listed, or a site's routes listed; or when formpublisher tools such as status, sites, import and routes are available or fail. Not for editing a site (that is FormWeb), not for changing FormPublisher's own source code (use formpublisher-skillset), and not for device preview, checks, packaging, signing or publishing, which are in development.
metadata:
  version: "0.1.0"
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

## Rules

- Say what was imported and how many routes it has; do not claim a check, a package or a publication, because those are in development.
- A failed import names the reason (not a zip, no `routes.json`, FormWeb not reachable); report it as it is and ask for the right path.
- Never write into FormPublisher's data folder by hand; use `import`.
- Never call FormWeb's `/api/load` or any route that changes FormWeb.
