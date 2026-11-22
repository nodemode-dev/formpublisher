# FormPublisher

Release version: 0.10.1.

The Form family's site publisher. FormPublisher opens what FormWeb makes (a `site-export.zip`, a FormWeb publication folder, or the site currently open in a running FormWeb), lists its routes, and shows them in a FormDeck-style window with Home, tabs, a routes strip, an inspector and a status bar. It reads FormWeb and never changes it. It also starts a new site from a template, as a FormWeb project to edit in FormWeb, and reads a `.fweb` project or a `.fpub` package.

Every step is also a command line command and an MCP tool, so Claude Code and other agents drive it the same way people do. The window has an agent dock, with a shell and a tab for Claude Code, Codex, Cursor and Antigravity, that starts them with those tools connected.

It also previews the site on device sizes from its own static host, runs static, live and deep checks, builds deterministic, Ed25519-signed packages, and prepares a folder with the exact commands for six hosts (it never uploads). After you deployed the folder yourself, the live-site check reads your public site and says what to fix. It keeps removed items in a Trash you can restore from, lets you rebind keyboard shortcuts, receives sites sent from FormWeb and ships a demo on a sample site, in the app and offline in `demo/index.html`. In development: the desktop build.

## Pages

- [Getting Started](Getting-Started) · install, run, the first import
- [Templates](Templates) · start a site from a FormWeb starter, the fixed release, the hash checks
- [Importing Sites](Importing-Sites) · the ways in, including .fweb projects and .fpub packages, and what each reads
- [Preview](Preview) · the site host, device sizes, theme, motion and network
- [Checks](Checks) · static, live and deep problems
- [Packages and Signatures](Packages-and-Signatures) · site.zip, publish.json, keys and signing
- [Publishing](Publishing) · the six hosts, the Publish sheet, receiving from FormWeb
- [Hosting](Hosting) · the hosting guide, forms, analytics, the live-site check
- [Agents](Agents) · the command line, the MCP server, the agent dock, the skills
- [Architecture](Architecture) · the engine, the interface, the shell
- [Releasing](Releasing) · the version sites, the checks, the release commit, the build in FormCompiler

The whole manual is `docs/MANUAL.md`, and the hosting guide is `docs/HOSTING.md`.
