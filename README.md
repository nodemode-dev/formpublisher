<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/app-icon/formpublisher-256.png">
    <img src="assets/app-icon/formpublisher-light-256.png" width="128" height="128" alt="FormPublisher icon: three puzzle pieces, one lifted in violet and coral, on a rounded square">
  </picture>
</p>

<h1 align="center">FormPublisher</h1>

<p align="center">
  <b>Open what FormWeb makes; see every route of the site.</b><br>
  Import a FormWeb export, a publication folder or the site open in FormWeb,<br>
  list its routes and look at them in a FormDeck-style window. Free and open source.
</p>

<p align="center">
  <img alt="version 0.1.0" src="https://img.shields.io/badge/version-0.1.0-4f6bff?style=flat-square">
  <img alt="Python FastAPI engine" src="https://img.shields.io/badge/Python-FastAPI%20engine-3776ab?style=flat-square&logo=python&logoColor=white">
  <img alt="TypeScript" src="https://img.shields.io/badge/TypeScript-interface-3178c6?style=flat-square">
  <img alt="Tauri 2" src="https://img.shields.io/badge/Tauri-2-24C8DB?style=flat-square">
  <img alt="License: GPL-3.0" src="https://img.shields.io/badge/license-GPL--3.0-3a3a3a?style=flat-square">
  <img alt="Status: in development" src="https://img.shields.io/badge/status-in%20development-d69e2e?style=flat-square">
</p>

<p align="center">
  <a href="docs/MANUAL.md">Manual</a> ·
  <a href=".docs/wiki/Home.md">Wiki</a> ·
  <a href="AGENTS.md">Agents</a> ·
  <a href="#run-it-from-source">Run it from source</a>
</p>

<br>

<p align="center">
  <a href="#features">Features</a> · <a href="#everything-in-the-box">In the box</a> · <a href="#built-for-agents">Agents</a> · <a href="#under-the-hood">Under the hood</a> · <a href="#run-it-from-source">Run from source</a>
</p>

<br>

<table>
  <tr>
    <td width="25%" valign="top"><h3>Reads FormWeb</h3>Opens a <code>site-export.zip</code>, a publication folder, or the site currently open in a running FormWeb, and never changes it.</td>
    <td width="25%" valign="top"><h3>Every route</h3>Lists the site's routes from its <code>routes.json</code>: path, page, locale, item and stylesheet.</td>
    <td width="25%" valign="top"><h3>FormDeck's window</h3>Home, tabs, a routes strip, an inspector and a status bar, in the Form family's look, with 26 interface languages.</td>
    <td width="25%" valign="top"><h3>Agent-ready</h3>The window, a command line and an MCP server share one engine, so Claude Code, Codex and Cursor import and list sites the way a person does.</td>
  </tr>
</table>

<br>

## Features

<table>
  <tr>
    <td width="50%" valign="top">
      <h3>Import a FormWeb export</h3>
      Drop a <code>site-export.zip</code> from FormWeb on Home, or pick it from the file dialog. FormPublisher unpacks it into its own data folder.
    </td>
    <td width="50%" valign="top">
      <h3>Open a publication folder</h3>
      Point it at a FormWeb publication folder (<code>publications/[slug]/[version]/</code>) and it imports the site exactly as FormWeb wrote it.
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <h3>The site open in FormWeb</h3>
      With FormWeb running on the same computer, import the site it has open through FormWeb's read-only <code>/api/export</code>. FormPublisher only reads; it never replaces or edits what FormWeb has open.
    </td>
    <td width="50%" valign="top">
      <h3>Routes at a glance</h3>
      Every route of the site in a strip beside the stage, with its page, locale, item and stylesheet in the inspector, and the count in the status bar.
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <h3>A window you know</h3>
      Home with Start and Recent, one tab per open site, a title bar, a status bar, a dark theme and a light one, built on the same layout as FormDeck.
    </td>
    <td width="50%" valign="top">
      <h3>26 interface languages</h3>
      The interface comes in 26 languages, from English and Spanish to Japanese and Korean, chosen in Preferences.
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <h3>Preview</h3>
      The mounted site is served by a static host on its own origin (port 8281), as a real host would. Pick a device size, force the dark or light theme, emulate reduced motion, throttle the network to Fast or Slow, and open the current route in your browser.
    </td>
    <td width="50%" valign="top">
      <h3>Checks</h3>
      Static checks run offline on the files: links, assets, redirects, sitemap, robots, metadata, images, headings, external requests and size budgets. Live checks report the console, failed requests and layout shift from the preview. A deep check drives the Chrome you already have, at two widths on a slow network and CPU.
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <h3>Package and sign</h3>
      Build a deterministic <code>site.zip</code> with a <code>publish.json</code> that lists every file by SHA-256, reproduce it byte for byte, and sign it with an Ed25519 key. Verify a signature, inspect a build and compare two.
    </td>
    <td width="50%" valign="top">
      <h3>Open .fweb projects</h3>
      Import a <code>.fweb</code> project directly. <code>formweb-core</code>, built from the vendored FormWeb crates by <code>./setup/install_compiler</code>, exports it to a site the same way FormWeb does.
    </td>
  </tr>
</table>

> [!NOTE]
> Publishing to a host and the desktop build are in development. This version imports, previews, checks, packages and signs; it does not upload anywhere.

## Everything in the box

<table>
  <tr>
    <td width="33%" valign="top"><h4>In the window</h4>Home · Start and Recent · site tabs · routes strip · inspector · status bar · Preferences</td>
    <td width="33%" valign="top"><h4>Command line and MCP tools</h4>status · list sites · import (zip, folder or the site open in FormWeb) · routes</td>
    <td width="33%" valign="top"><h4>Three ways in</h4>site-export.zip · publication folder · the running FormWeb's current site</td>
  </tr>
</table>

## Built for agents

The window, the command line and the MCP server call one engine, so an agent and a person see the same sites, and an import an agent makes appears in the open window at once.

```sh
./formpublisher run status                     # the engine, the data folder, whether FormWeb is reachable
./formpublisher run sites                      # the sites already imported
./formpublisher run import site-export.zip     # import a FormWeb export (or a publication folder)
./formpublisher run import-formweb             # import the site open in a running FormWeb, read-only
./formpublisher run routes SITE-ID             # the routes of one site
./formpublisher mcp                            # MCP server on stdio
```

`.mcp.json`, `.codex/config.toml` and `.cursor/mcp.json` are already wired in this repo, with the `formpublisher-harness` skill for driving the app and `formpublisher-skillset` for changing it. See [`AGENTS.md`](AGENTS.md).

### Agents

```sh
./formpublisher agents install       # the same MCP server and skills for your account: Claude Code, Codex and Cursor
./formpublisher agents status        # what is installed, which servers, how many skills, whether formMCP is found
./formpublisher agents sync          # mirror .claude/skills to .agents/skills
./formpublisher agents sync --check  # exits 1 on any drift, for CI
```

Two MCP servers are registered: `formpublisher` and `formmcp`, the Form family hub that reaches every installed Form app's own tools. formMCP is a separate app: when it is not installed, `formmcp` shows as failed or unavailable in your agent and everything else works.

## Under the hood

- **One engine:** a FastAPI engine on 127.0.0.1:8280 owns the imported sites and the data folder; the interface, the command line and the MCP server are thin layers over its routes.
- **Read-only toward FormWeb:** FormPublisher imports exports and folders and may read a running FormWeb's `/api/export`; it never calls FormWeb's `/api/load` and never writes to FormWeb.
- **Loopback only:** the engine answers on 127.0.0.1 and refuses any other Host or Origin.
- **Zero flash:** every container exists in its final layout before the first paint, and the window is revealed once it is ready.
- **Inline icons, no libraries:** icons are inline `currentColor` SVG; colours, sizes and every `z-index` come from tokens.

## Run it from source

**Requires:** Node 22.12 or newer, Python 3.12, git. Rust stable and the Tauri prerequisites only for the desktop window.

```sh
git clone git@github.com:nodemode-dev/formpublisher.git
cd formpublisher
./formpublisher_oc_install        # engine venv and interface packages
./setup/install_compiler          # builds formweb-core for .fweb projects (needs Rust; the install runs it when cargo is present)
./formpublisher                   # interface at http://localhost:5280, engine on 127.0.0.1:8280
```

`./formpublisher_oc_install` is the install, `./formpublisher` is the boot, and `./build_app` makes the desktop app start to finish and logs to `build_app.log`. On Windows use `formpublisher_oc_install.bat`, `formpublisher.bat` and `build_app.bat`.

Ports and folders:

| Port | What |
| --- | --- |
| 5280 | interface (Vite, localhost only) |
| 5281 | Vite preview of a production build |
| 8280 | engine (`FORMPUBLISHER_PORT`) |
| 8281 | site host, serves the mounted site (`FORMPUBLISHER_HOST_PORT`) |

| Data folder | Holds |
| --- | --- |
| `sites/` | imported sites and their revisions |
| `checks/` | stored check results and deep-run thumbnails |
| `builds/` | packages: `site.zip`, `publish.json`, `site.zip.sig` |
| `keys/` | signing keys |
| `trash/` | deleted items |

`./formpublisher serve` serves a production build from the engine alone, `./formpublisher desktop dev` opens the desktop window, and `./formpublisher doctor` checks the toolchain. `FORMPUBLISHER_HOME` moves the data folder (`~/FormPublisher` by default).

> [!IMPORTANT]
> **Status:** in development. Importing from the site open in FormWeb needs FormWeb running on the same computer. The desktop build and publishing are not finished. The deep check needs Chrome and the optional `requirements-deep.txt`; `.fweb` projects need `formweb-core`.

**Contributing:** changes to FormPublisher come here as pull requests into `main`; changes to how a site is made or exported belong in FormWeb. See [`CONTRIBUTING.md`](CONTRIBUTING.md), [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) and [`AGENTS.md`](AGENTS.md). Report security issues privately as [`SECURITY.md`](SECURITY.md) describes.

## Repository

| Path | What it is |
| --- | --- |
| `frontend/` | the interface (vanilla TypeScript and Vite) |
| `backend/` | the FastAPI engine, the command line and the MCP server |
| `src-tauri/` | the Tauri 2 shell |
| `setup/` | install, build and agent scripts |
| `docs/` | the manual |
| `.docs/wiki/` | the wiki pages |
| `assets/` | the app icon used by this README |

Docs: [`docs/MANUAL.md`](docs/MANUAL.md), [`.docs/wiki`](.docs/wiki) · Agents: [`CLAUDE.md`](CLAUDE.md), [`AGENTS.md`](AGENTS.md) · Changes: [`CHANGELOG.md`](CHANGELOG.md)

---

## Maintainers

| Maintainer | Role |
|---|---|
| [@nodemode-ai](https://github.com/nodemode-ai) | Owner |
| [@gbarnai](https://github.com/gbarnai) | Co-owner |

## License

FormPublisher is licensed under the GNU General Public License v3.0 ([`LICENSE`](LICENSE), SPDX `GPL-3.0-only`). Copyright 2026 NodeAgentc, Inc. Third-party notices: [`NOTICE.md`](NOTICE.md).
