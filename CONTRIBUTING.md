# Contributing to FormPublisher

Thank you for helping. FormPublisher aims to be a free site publisher that opens what
FormWeb makes (a `site-export.zip`, a publication folder, or the site open in a
running FormWeb), previews and checks it, and prepares a package for the host you
choose, and it gets there through real use and real contributions.

## Where to start

- **Use it and report what goes wrong.** Import a FormWeb export, list its routes,
  and open an issue with the steps, the version (`./formpublisher version`) and your
  platform when something breaks.
- **Look at the open issues.** Comment on one before starting larger work, so nobody
  builds the same thing twice.
- **Know which repository your change belongs in.** Changes to FormPublisher (the
  window, the engine, the command line, the MCP server, the desktop shell) come here.
  Changes to how a site is made or edited, or to what FormWeb exports, belong in
  FormWeb's repository, because FormPublisher never edits a site and only reads what
  FormWeb exports. Changes to another Form app belong in that app's repository.
- **Translations** are welcome: FormPublisher ships in English and 25 more languages,
  with the tables in `frontend/src/i18n/locales`.

## Setting up

Clone the repository and run `./formpublisher_oc_install`, then `./formpublisher` (or
`formpublisher_oc_install.bat` and `formpublisher.bat` on Windows). The first creates
the engine's Python environment and installs the interface's packages; the second
starts the engine on 127.0.0.1:8280 and the interface on http://localhost:5280. To open
`.fweb` projects, run `./setup/install_compiler`, which builds `formweb-core` from the
vendored FormWeb crates and needs Rust. `./formpublisher help` lists every command and
`./formpublisher doctor` checks the toolchain. `./formpublisher agents install` sets up
Claude Code, Codex and Cursor; for working on FormPublisher itself, they load the
`formpublisher-skillset` skill. The README's "Run it from source" has the details and
the requirements: Node 22.12 or newer and Python 3.12.

The code lives in:

| Folder | What is there |
| --- | --- |
| `frontend/src` | the interface (vanilla TypeScript, Vite) |
| `backend/app` | the engine (Python, FastAPI): one router per file in `routers/`, the work in `services/`, one host adapter per file in `targets/` |
| `backend/formpublisher_engine.py` | the engine entry: serve, `--selfcheck`, `cli`, `mcp` |
| `src-tauri` | the desktop shell (Rust, Tauri 2, pinned in `rust-toolchain.toml`) and `engine/`, the frozen engine folder that `setup/freeze_backend` writes |
| `vendor/formweb-native` | FormWeb's engine crates, vendored unedited, which build `formweb-core` |
| `setup` | install, build, vendor check and agent scripts |
| `demo` | the sample site, the three FormWeb demo sites and the offline demo |
| `docs` | the manual and its screenshots |
| `.docs/wiki` | the wiki's source |
| `.claude/skills`, `.agents` | the formpublisher skills, mirrored for agents that do not read `.claude` |

## Before you open a pull request

Run the same checks CI runs (the `frontend` and `engine` jobs):

```sh
(cd frontend && npm ci --no-fund && npm audit --audit-level=low && npm run build && npm run typecheck:dock)
python setup/lock_requirements.py --check
pip install --require-hashes -r backend/requirements.lock
python setup/i18n_check.py
python setup/dock_check.py
python backend/formpublisher_engine.py --selfcheck
python -m compileall -q backend/app setup
./formpublisher agents sync --check
./formpublisher vendor --check
(cd vendor/formweb-native && cargo build --release --locked)
vendor/formweb-native/target/release/formweb-core --selfcheck
```

The build type checks the interface and builds it; the self check imports every
router. `npm run typecheck:dock` compiles `frontend/src/dock` with the seven strict
flags its contract names, and `python setup/dock_check.py` fails, naming the file,
when a file of that folder differs from `MANIFEST.json`, is missing or is extra.
`./formpublisher agents sync --check` also fails when `agent_lookup.py` does not match
the hash recorded for its version. The lock check fails when a lock lacks a pin of a requirements file: after
changing one, run `python setup/lock_requirements.py` (it needs uv 0.11.32) and commit
the locks. The language check fails when a key of `frontend/src/i18n/keys` is missing
from any locale folder, a placeholder is lost or a string holds an em dash. CI also
checks the shell scripts with `bash -n`, and type checks the desktop shell on Windows
and macOS (`cargo check --locked`, with the Rust version `src-tauri/rust-toolchain.toml`
pins). After changing the command
line, the MCP tools or a skill, run `./formpublisher agents sync` so the `.agents`
mirror follows.

The engine's tests run with `python -m pytest -q backend/tests` (install
`backend/requirements-test.txt` first; the `.fweb` tests need `formweb-core` built).
Every test runs against stand-ins that the fixture in `backend/tests/conftest.py`
sets: its own home folder, a `PATH` of the system folders only (so no agent program
can be found), its own agent configuration folders and keyring's fail backend, so a
test never touches your real files, your agents' setup or your password store.

- Keep each pull request to one change.
- Write commit subjects in Conventional Commits: `feat(engine): ...`,
  `fix(window): ...`, `docs(...)`. Leave the version and `CHANGELOG.md` alone; a
  maintainer does both when releasing.
- Interface text goes through the translation tables: add each new string to every
  language.
- Edits are surgical and made by hand: no codemods or scripted rewrites of source.
- `frontend/src/dock/` (the agent dock, module 2.2.1) and
  `backend/app/services/agent_lookup.py` (the finder for the agent programs) are
  copied from FormVis and never edited here. A change to either is made in FormVis,
  released there as a whole new version, and copied here whole (the dock with its
  `MANIFEST.json`; the finder with its new hash added to `LOOKUP_HASHES` in
  `setup/agents.py`). FormPublisher's own part of the
  dock is `frontend/src/dock-adapter.ts`, `frontend/src/styles/dock-tokens.css` and the
  engine's `services/terminal.py` and `services/agent_programs.py`. A check of the dock
  uses stand-in programs and never starts a real agent program.
- Every chooser is the family's dropdown (`frontend/src/ui/dropdown.ts`), never a
  native `select`. Keys and settings are made and changed only in Preferences; a sheet
  that needs one offers a chip that opens Preferences at that panel. Accent-coloured
  text and icons use `--accent-ink`, which stays readable on the light themes.
- The window never flashes or shifts: every container exists in its final layout before
  the first paint, colours, sizes and every `z-index` come from
  `frontend/src/styles/tokens.css`, and icons are inline `currentColor` SVG.
- No emoji anywhere, no em dash in Markdown, no commented-out code.
- Every dependency that ships gets a row in `NOTICE.md` with its licence before it is
  used.
- FormPublisher only reads FormWeb. Nothing here calls FormWeb's `/api/load` or writes
  to FormWeb, and the engine stays on loopback.
- Never commit anything from your data folder (`FORMPUBLISHER_HOME`) or a site you do
  not have the right to share.

## Maintainers

FormPublisher is maintained by:

- the [nodemode-dev](https://github.com/nodemode-dev) organisation on GitHub
- [@nodemode-ai](https://github.com/nodemode-ai)
- [@gbarnai](https://github.com/gbarnai)

Reach them through issues and pull requests. They own every file
([.github/CODEOWNERS](.github/CODEOWNERS)).

## How changes land

Only a maintainer pushes to `main`. Everyone else forks the repository and opens a pull request into `main`. A pull request merges when both checks, `frontend` and `engine`, pass on an up-to-date branch and a maintainer has approved it after its last push. Pull requests are merged with a merge commit, so signed commits keep their signatures.

## Releases

A release is a version, and only a maintainer makes one: the version moves in every
place together, and the `CHANGELOG.md` entry is written in the release commit, the
last one on its pull request. No push from a contributor starts a release. See the
wiki's [Releasing](.docs/wiki/Releasing.md) page.

## Licensing

FormPublisher is licensed under the GNU General Public License v3.0 ([LICENSE](LICENSE),
SPDX `GPL-3.0-only`). By contributing, you agree that your contribution is licensed under
the same terms. Only add code you have the right to contribute, and name any third-party
code and its licence in the pull request.

## Patents and other people's IP

Some features are deliberately not built, or were taken out, because they come too close to someone else's patent, trademark, copyright or design. The maintainers hold that line with counsel; contributors do not decide it, and nobody here redesigns a feature on their own reading of a patent. This is engineering diligence, not legal advice.

### Features this project will not implement

The repository records none yet. The rules below apply to every contribution, and a feature the maintainers decline for patent, trademark or copyright reasons is listed here, with their written decision, before it counts as declined.

### Rules for every contribution

- Patents: do not add a feature, or a dependency that provides one, that reproduces a method you know to be patented. If you are unsure, open an issue that describes what the feature does, not which patent it resembles. Patent numbers stay out of code, commits, comments, logs and changelogs.
- Trademarks: other vendors' product and feature names appear only to name a file format or compatibility ("opens <format> files", "for use with"). No command, menu, panel, tool, preset, template, theme or agent tool takes another product's feature name, and no text says "like X" or "the way X does it". Describe what the feature does.
- Copyright: never copy another product's help, tooltip, dialog or documentation text (link to it instead); never trace or import vendor icons; never bundle vendor templates, themes, presets, brushes, swatches, LUTs, materials, sample files, sound libraries, stock media or fonts; colour-book names only when reading a person's file. Compatibility layers carry names and signatures only. Test fixtures come from this repository's own scripts.
- Licences: every new dependency, binary, model, font, profile or data file gets a row in `NOTICE.md` before it is used. No third-party GPL code goes into the distributed bundle (FormPublisher's own code is GPL-3.0-only), AGPL nowhere, LGPL dynamically linked and replaceable, MPL files unedited. CC BY credited, CC BY-SA only unmodified, CC NC and ND never. Models with gated or non-commercial terms are optional downloads, never bundled.

## Conduct

Everyone taking part follows the [code of conduct](CODE_OF_CONDUCT.md). Security
problems go through [SECURITY.md](SECURITY.md), never a public issue.
