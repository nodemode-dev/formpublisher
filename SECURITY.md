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
  web page on another origin drive it. Every request that is not a GET, HEAD or
  OPTIONS needs the window key in the header `X-FormPublisher-Key`, and one without
  it is refused with 403 and the code `forbidden`. The engine makes the key when it
  starts: the desktop shell hands it to its window, and a browser tab on the
  development start claims it from `POST /api/window/key`, which answers only the
  window's own origins. The command line and the MCP server use a second key from
  `engine.key` in the data folder, which only the person can read, is new at every
  engine start and is removed when the engine ends. Anything that lets a request
  without a key change something, or hands a key to a page that is not the window.
- **The site host**, the second loopback listener that serves the mounted site for
  Preview and the deep checks (port 8281, or another free loopback port): anything
  that makes it reachable from another machine, serves files outside the mounted
  site, or lets a site it serves reach the engine. A script in a previewed site gets
  no key and cannot change anything.
- **The desktop shell**: only the engine's own origin may use the shell's commands.
  The capability names `http://127.0.0.1:8280/*`, and when the shell picks another
  port it grants that one origin at run time; no other loopback port, the site
  host included, is granted anything. The engine serves the window with a
  Content-Security-Policy header, and the splash has its own policy in
  `tauri.conf.json`. Anything that gives another origin the shell's commands or
  loosens either policy.
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
- **The deep check**, which loads an imported site in the Chrome or Edge you already
  have, in the desktop app too (Playwright and its Node.js driver are frozen into the
  engine, and no browser is downloaded): a site getting out of that page.
- **Signing keys**: Ed25519 keys, which may be locked with a passphrase. The private
  half is kept in the system password store (the Keychain on macOS, the Credential
  Manager on Windows, the Secret Service on Linux), reached only to create, sign,
  export, import and remove a key; listing a key never touches it. Where the
  computer has no store, the secret is a file only the person can read. Removing a
  key deletes its secret, and the Trash keeps only the public half. An exported key
  is always encrypted with a passphrase and written readable only by the person, and
  the MCP server has no tool to export or import one. Verify says whether a signature
  was made by one of the person's own keys (`known`), and reports one made by a key
  they do not have as a warning, not as verified. Anything that leaks a private key
  or passphrase, writes an export that is not encrypted, or makes a signature verify
  for files it was not made for.
- **Publish**: it prepares a folder per host with the commands to run and never
  uploads. Anything that makes it send a site or a key anywhere, or run those commands,
  without the person.
- **Local files**: the data folder (`~/FormPublisher`, or `FORMPUBLISHER_HOME`), with
  `engine.key` in it, and the Trash that restores from it: anything that exposes it,
  or reads or writes outside it other than where the person points.
- **Agents and the MCP server** (`./formpublisher mcp`, Claude Code, Codex and
  Cursor): a tool reaching beyond the data folder, or acting without the step you would
  take in the window.

Bugs that need someone to already control your machine, or to run a modified build of
FormPublisher, are ordinary bugs: please open an issue for those.
