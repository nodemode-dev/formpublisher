# Security policy

## Supported versions

Security fixes go into the newest release. Please update before reporting, and
check whether the problem is still there.

| Version | Supported |
| --- | --- |
| 0.3.x (latest release) | Yes |
| Anything older | No |

## Reporting a vulnerability

**Do not open a public issue for a security problem.** Use GitHub's private
reporting instead: on the repository's **Security** tab, choose **Report a
vulnerability**. Include what you found, the steps to reproduce it, the version and
platform, and what an attacker could do with it.

You can expect an acknowledgement within a week. We will keep you informed while it
is fixed and credit you in the release notes, unless you would rather not be named.

## What counts

FormPublisher runs on your own machine and opens files that are not yours yet (site
exports, `.fweb` projects, `.fpub` packages and publication folders from FormWeb, and
the site open in a running FormWeb), so the things that matter most are the ways that
content, or something outside the machine, could get further than it should:

- **The engine** listens on loopback (127.0.0.1): port 8280 in development
  (`FORMPUBLISHER_PORT` changes it), and port 8280 or another free loopback port in
  the desktop app. Anything that makes it reachable from another machine, or lets a
  web page on another origin drive it.
- **The site host**, the second loopback listener that serves the mounted site for
  Preview and the deep checks (port 8281, or another free loopback port): anything
  that makes it reachable from another machine, serves files outside the mounted
  site, or lets a site it serves reach the engine.
- **Receiving from FormWeb** (`/api/receive/formweb` and the `inbox/` folder): a site
  accepted from any client but this computer, or an inbox file that is imported in a
  way that writes outside its site folder.
- **Imports**: opening a `site-export.zip`, a `.fweb` project, a `.fpub` package or a
  folder in a way that writes outside its site folder in the data folder (a path with
  `..`, an absolute path, a symlink or an oversized archive), that runs anything the
  site contains, or that accepts a `.fpub` whose checksum or signature does not match.
- **The FormWeb connection**: FormPublisher only reads FormWeb. Anything that makes it
  write to FormWeb, call a route that changes FormWeb's document, or reach a host
  other than the loopback FormWeb the person chose.
- **The deep check**, which loads an imported site in the Chrome you already have:
  a site getting out of that page.
- **Signing keys**: the Ed25519 keys in the `keys/` folder, which may be locked with a
  passphrase. Anything that leaks a private key or passphrase, or makes a signature
  verify for files it was not made for.
- **Publish**: it prepares a folder per host with the commands to run and never
  uploads. Anything that makes it send a site or a key anywhere, or run those commands,
  without the person.
- **Local files**: the data folder (`~/FormPublisher`, or `FORMPUBLISHER_HOME`) and
  the Trash that restores from it: anything that exposes it, or reads or writes outside
  it other than where the person points.
- **Agents and the MCP server** (`./formpublisher mcp`, Claude Code, Codex and
  Cursor): a tool reaching beyond the data folder, or acting without the step you would
  take in the window.

Bugs that need someone to already control your machine, or to run a modified build of
FormPublisher, are ordinary bugs: please open an issue for those.
