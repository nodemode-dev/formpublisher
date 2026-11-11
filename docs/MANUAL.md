# FormPublisher Manual

FormPublisher is the Form family's site publisher. It opens what FormWeb makes, lists the site's routes and shows them in a FormDeck-style window. People and agents use the same steps: each one is also a command line command and an MCP tool.

Version 0.1.0 imports FormWeb sites and shows their routes. In development: device preview, checks, packaging, signing, publishing and the desktop build.

## Contents

- [Getting started](#getting-started)
- [Home](#home)
- [Importing a site](#importing-a-site)
- [Routes](#routes)
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

Imported sites and settings are kept in `~/FormPublisher`, or in the folder named by `FORMPUBLISHER_HOME`. The engine port is `FORMPUBLISHER_PORT` (8280 by default). The interface is in 26 languages.

## When something goes wrong

- The window cannot reach the engine: run `./formpublisher doctor` and check that 8280 is listening.
- An import is refused: the message names the reason (not a zip, no `routes.json`, or no FormWeb on loopback).
- A port is taken: stop what uses 8280, 5280 or 5281, or set `FORMPUBLISHER_PORT`.
- Anything else: open an issue with `./formpublisher version` and your platform.
