# Contributing to FormPublisher

Thank you for helping. FormPublisher is the Form family's site publisher: it opens what FormWeb makes (a `site-export.zip`, a publication folder, or the site open in a running FormWeb), lists its routes and shows them in a FormDeck-style window. Device preview, checks, packaging, signing and publishing are in development.

## Which repository your change belongs in

| You want to | Where it goes |
| --- | --- |
| Fix or improve FormPublisher: the window, the engine, the command line, the MCP server, the desktop shell | Here, as described below. |
| Change how a site is made or edited, or what FormWeb exports | In FormWeb's repository. FormPublisher never edits a site and only reads what FormWeb exports. |
| Change another Form app | In that app's repository. |

## Where to start

- **Use it and report what goes wrong.** Import a FormWeb export, list its routes, and open an issue with the steps, the version (`./formpublisher version`) and your platform when something breaks.
- **Look at the open issues.** Comment on one before starting larger work, so nobody builds the same thing twice.

## Setting up

Clone the repository and run `./formpublisher_oc_install`, then `./formpublisher` (or `formpublisher_oc_install.bat` and `formpublisher.bat` on Windows). The first installs the engine's virtual environment and the interface's packages; the second starts the engine on 127.0.0.1:8280 and the interface on http://localhost:5280. `./formpublisher help` lists every command and `./formpublisher doctor` checks the toolchain. `./formpublisher agents install` sets up Claude Code, Codex and Cursor; for working on FormPublisher itself, they load the `formpublisher-skillset` skill.

Requires Node 22.12 or newer and Python 3.12.

The code lives in:

| Folder | What is there |
| --- | --- |
| `frontend/src` | the interface (vanilla TypeScript, Vite) |
| `backend/app` | the engine (Python, FastAPI): one router per file in `routers/`, the work in `services/` |
| `backend/formpublisher_engine.py` | the engine entry: serve, `--selfcheck`, `cli`, `mcp` |
| `src-tauri` | the desktop shell (Rust, Tauri 2) and its frozen engine sidecar |
| `setup` | install, build and agent scripts (`setup/agents.py`) |
| `.claude/skills`, `.agents` | the formpublisher skills, mirrored for agents that do not read `.claude` |

## Before you open a pull request

Run the same checks CI runs (the `frontend` and `engine` jobs, both required on `main`):

```sh
(cd frontend && npm ci && npm audit --audit-level=low && npm run build)
pip install -r backend/requirements.txt && python backend/formpublisher_engine.py --selfcheck
python -m compileall -q backend/app setup
./formpublisher agents sync --check
```

The build type checks the interface and builds it; the self check imports every router. After changing the command line, the MCP tools or a skill, run `./formpublisher agents sync` so the `.agents` mirror follows.

- Keep each pull request to one change.
- Write commit subjects in Conventional Commits: `feat(engine): ...`, `fix(frontend): ...`, `docs(...)`. Leave the version and `CHANGELOG.md` alone; a maintainer does both when releasing.
- Edits are surgical and made by hand: no codemods or scripted rewrites of source.
- The window never flashes or shifts: every container exists in its final layout before the first paint, colours, sizes and every `z-index` come from `frontend/src/styles/tokens.css`, and icons are inline `currentColor` SVG.
- No emoji anywhere, no em dash in Markdown, no commented-out code.
- Every dependency that ships gets a row in `NOTICE.md` with its licence before it is used.
- FormPublisher only reads FormWeb. Nothing here calls FormWeb's `/api/load` or writes to FormWeb, and the engine stays on loopback.
- Never commit anything from your data folder (`FORMPUBLISHER_HOME`) or a site you do not have the right to share.

## Maintainers

FormPublisher is maintained by:

- the [nodemode-dev](https://github.com/nodemode-dev) organisation on GitHub
- [@nodemode-ai](https://github.com/nodemode-ai)
- [@gbarnai](https://github.com/gbarnai)

Reach them through issues and pull requests. They own every file (`.github/CODEOWNERS`).

## How changes land

Only a maintainer pushes to `main`, and only through a pull request. Everyone else forks the repository and opens a pull request into `main`. A pull request merges when the `frontend` and `engine` checks pass on an up-to-date branch and a maintainer has approved it after its last push. Pull requests are merged with a merge commit, so signed commits keep their signatures.

## Releases

A release is a version, and only a maintainer makes one: the version moves in every place together and the `CHANGELOG.md` entry is written in the release commit, the last one on its pull request. See [`.docs/wiki/Releasing.md`](.docs/wiki/Releasing.md). No push from a contributor starts a release.

## Licensing

FormPublisher is licensed under the GNU General Public License v3.0 ([LICENSE](LICENSE), SPDX `GPL-3.0-only`). By contributing to it, you agree that your contribution is licensed under the same terms. Only add code you have the right to contribute, and name any third-party code and its licence in the pull request.

## Other people's names and work

Examples describe what they do in their own words. They never copy another product's help text, icons, presets, sample files or stock media. Test fixtures and screenshots come from this repository's own examples.

## Conduct

Everyone taking part follows the [code of conduct](CODE_OF_CONDUCT.md). Security problems go through [SECURITY.md](SECURITY.md), never a public issue.
