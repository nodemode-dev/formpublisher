# Security policy

## Supported versions

Security fixes go into the newest release. Please update before reporting, and check whether the problem is still there.

| Version | Supported |
| --- | --- |
| 0.1.x (latest release) | Yes |
| Anything older | No |

## Reporting a vulnerability

**Do not open a public issue for a security problem.** Use GitHub's private reporting instead: on the repository's **Security** tab, choose **Report a vulnerability**. Include what you found, the steps to reproduce it, the version and platform, and what an attacker could do with it.

You can expect an acknowledgement within a week. We will keep you informed while it is fixed and credit you in the release notes, unless you would rather not be named.

## What counts

FormPublisher runs on your own machine and opens files that are not yours yet (site exports and publication folders from FormWeb, and the site open in a running FormWeb), so the things that matter most are the ways that content, or something outside the machine, could get further than it should:

- **The engine** listens on loopback (127.0.0.1:8280, or `FORMPUBLISHER_PORT`). Anything that makes it reachable from another machine, or lets a web page on another origin drive it.
- **Imports**: opening a `site-export.zip` or a folder in a way that writes outside its site folder in the data folder (a path with `..`, an absolute path, a symlink or an oversized archive), or that runs anything the site contains.
- **The FormWeb connection**: FormPublisher only reads FormWeb. Anything that makes it write to FormWeb, call a route that changes FormWeb's document, or reach a host other than the loopback FormWeb the person chose.
- **Local files**: the data folder (`~/FormPublisher`, or `FORMPUBLISHER_HOME`) is private to your user account; anything that exposes it or reads outside it.
- **Agents and the MCP server** (`./formpublisher mcp`, Claude Code, Codex and Cursor): a tool reaching beyond the data folder, or acting without the step you would take in the window.

Bugs that need someone to already control your machine, or to run a modified build of FormPublisher, are ordinary bugs: please open an issue for those.
