# FormPublisher

Release version: 0.7.0.

The Form family's site publisher. FormPublisher opens what FormWeb makes (a `site-export.zip`, a FormWeb publication folder, or the site currently open in a running FormWeb), lists its routes, and shows them in a FormDeck-style window with Home, tabs, a routes strip, an inspector and a status bar. It reads FormWeb and never changes it.

Every step is also a command line command and an MCP tool, so Claude Code and other agents drive it the same way people do. The window has an agent dock, with a shell and a tab for Claude Code, Codex, Cursor and Antigravity, that starts them with those tools connected.

It also previews the site on device sizes from its own static host, runs static, live and deep checks, builds deterministic, Ed25519-signed packages, and prepares a folder with the exact commands for six hosts (it never uploads). It keeps removed items in a Trash you can restore from, lets you rebind keyboard shortcuts, receives sites sent from FormWeb and ships a demo on a sample site, in the app and offline in `demo/index.html`. In development: the desktop build.

## Pages

- [Getting Started](Getting-Started) · install, run, the first import
- [Importing Sites](Importing-Sites) · the ways in, including .fweb projects and .fpub packages, and what each reads
- [Preview](Preview) · the site host, device sizes, theme, motion and network
- [Checks](Checks) · static, live and deep problems
- [Packages and Signatures](Packages-and-Signatures) · site.zip, publish.json, keys and signing
- [Publishing](Publishing) · the six hosts, the Publish sheet, receiving from FormWeb
- [Agents](Agents) · the command line, the MCP server, the agent dock, the skills
- [Architecture](Architecture) · the engine, the interface, the shell
- [Releasing](Releasing) · versions and the release commit

The whole manual is `docs/MANUAL.md`.
