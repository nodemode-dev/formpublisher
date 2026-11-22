# Security policy

## Supported versions

Security fixes go into the newest release. Please update before reporting, and
check whether the problem is still there.

| Version | Supported |
| --- | --- |
| 0.10.x (the current line) | Yes |
| Anything older | No |

## Reporting a vulnerability

**Do not open a public issue for a security problem.** Use GitHub's private
reporting instead: on the repository's **Security** tab, choose **Report a
vulnerability**. Include what you found, the steps to reproduce it, the version and
platform, and what an attacker could do with it.

You can expect an acknowledgement within a week. We will keep you informed while it
is fixed and credit you in the release notes, unless you would rather not be named.

## The window key

Every request to the engine that is not a GET, HEAD or OPTIONS must carry a key in
the header `X-FormPublisher-Key`. The engine makes its keys when it starts, keeps
them in memory and accepts three kinds:

- **The window's key.** In the desktop app the engine prints it for the shell, and
  the shell hands it to the window, only on the engine's own origin and only in the
  top frame. On the development start a browser tab claims it from
  `POST /api/window/key`, which answers only the window's own origins and answers
  nothing in the desktop app.
- **The local key**, for the command line and the MCP server. It is in `engine.key`
  in the data folder, a file only the person can read (mode 0600), new at every
  engine start and removed when the engine ends.
- **A tab key**, one for each agent tab of the agent dock, good while that tab's
  program runs (see **The agent dock** below).

Anything else gets 403 with the code `forbidden`. Two routes take no key:
`/api/window/key` itself and `/api/receive/formweb`, which accepts only this
computer.

## What counts

FormPublisher runs on your own machine and opens files that are not yours yet (site
exports, `.fweb` projects, `.fpub` packages and publication folders from FormWeb, and
the site open in a running FormWeb), so the things that matter most are the ways that
content, or something outside the machine, could get further than it should:

- **The engine** listens on loopback (127.0.0.1): port 8280 in development
  (`FORMPUBLISHER_PORT` changes it), and port 8280 or another free loopback port in
  the desktop app. Anything that makes it reachable from another machine, or lets a
  web page on another origin drive it. Anything that lets a request without a key
  change something, or hands a key to a page that is not the window (see **The
  window key** below).
- **The site host**, the second loopback listener that serves the mounted site for
  Preview and the deep checks (port 8281, or another free loopback port): anything
  that makes it reachable from another machine, serves files outside the mounted
  site, or lets a site it serves reach the engine. A script in a previewed site gets
  no key and cannot change anything.
- **The desktop shell**: only the engine's own origin may use the shell's commands.
  The capability names `http://127.0.0.1:8280/*`, and when the shell picks another
  port it grants that one origin at run time; no other loopback port, the site
  host included, is granted anything. The engine serves the window with a
  Content-Security-Policy header: scripts only from the engine itself (the page's
  own inline script by its SHA-256), frames only from the site host, connections
  only to the engine and the shell, and no page may frame the window. The splash
  has its own policy in `tauri.conf.json`. Anything that gives another origin the
  shell's commands or loosens either policy.
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
- **The live-site check**: the one part that reaches the person's own public site.
  It runs only when asked, reads only the address the person gives (a public domain
  name over https, never an IP address or a local name) and `www.` in front of it,
  follows no redirect, and sends no form, no cookie and no upload. Anything that
  makes it read another address, run without being asked, or send something.
- **Templates**: the list and each template come from the public formai-templates
  repository at the release this version names, fetched only when asked. A template
  or a preview is kept only when it matches the SHA-256 in the list, and the list
  may only name paths under `apps/formweb/`. Anything that keeps a file that does
  not match, or writes outside the data folder and the folder the person chose.
- **Local files**: the data folder (`~/FormPublisher`, or `FORMPUBLISHER_HOME`), with
  `engine.key` and `agent-tabs/` in it, and the Trash that restores from it: anything
  that exposes it, or reads or writes outside it other than where the person points.
- **The agent dock** (terminal tabs for a shell, Claude Code, Codex, Cursor and
  Antigravity, opened from the window): each agent tab works in its own folder,
  `agent-tabs/[id]/` in the data folder (readable only by the person, mode 0700), and
  gets its own key for FormPublisher's tools, a file `tab.key` there (mode 0600) that
  the program's MCP entry reads with `--tab-key-file`. The key is never on a command
  line or in the environment, the engine accepts it for the tools while the tab's
  program runs, it is refused on the dock's own routes (a tab cannot open, change or
  attach terminal tabs), and it ends when the program ends or the tab closes, when
  the folder is removed too. A plain shell tab has no key and no entry. A tab's
  output streams only to a socket opened with a one-use ticket, bought with the
  window's key for that tab, good for 60 seconds and accepted only from the window's
  own origin. A tab's environment drops the engine's own `FORMPUBLISHER_` variables.
  The dock's folder (`frontend/src/dock/`) and the finder that looks for the programs
  (`backend/app/services/agent_lookup.py`) are shared with other Form apps and checked
  against recorded hashes. Anything that puts a tab key on a command line, in a log
  or in a file others can read, lets one tab's key open or read another tab, lets a
  key outlast its tab, opens a stream without a ticket, or gives a plain shell a key.
- **Agents and the MCP server** (`./formpublisher mcp`, Claude Code, Codex and
  Cursor): a tool reaching beyond the data folder, or acting without the step you would
  take in the window.

Bugs that need someone to already control your machine, or to run a modified build of
FormPublisher, are ordinary bugs: please open an issue for those.
