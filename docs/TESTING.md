# Testing FormPublisher

FormPublisher's tests run the app and check what a user or a calling program would notice. This page says how to run them, where they live and what a test must do to be accepted.

## Running the tests

```sh
./formpublisher test                       # every layer
./formpublisher test engine                # one layer: unit or engine
./formpublisher test engine -k intake      # the rest of the line goes to the runner
```

On Windows use `formpublisher.bat test`. Run `./formpublisher install` first. The engine tests need pytest in the backend venv:

```sh
backend/venv/bin/python -m pip install -r backend/requirements-test.txt
```

The tests that open a `.fweb` project need `formweb-core` (`./setup/install_compiler`); without it those tests are skipped with a line that says so. An unknown layer name ends with exit code 2 and a sentence that names the layers.

## The layers

| Layer | Tool | Where | What it runs against |
| --- | --- | --- | --- |
| unit | vitest, happy-dom | `frontend/tests/unit/` | exported interface functions and stores, no browser |
| engine | pytest | `backend/tests/` | the real FastAPI app in process, the command line and the MCP server, with a temporary home folder for each test |

The tests are grouped by area, one folder for each: `backend/tests/<area>/` for the engine and `frontend/tests/unit/<area>/` for the interface. A vitest file is named `*.test.ts`; a pytest file is named `test_*.py`. The tests at the top of `backend/tests/` are the suite the engine had before 0.11.0.

The Rust tests under `vendor/formweb-native` are not part of this runner. Those crates are vendored unedited from FormWeb, their tests are FormWeb's and run there; here `./formpublisher vendor --check` checks that the copy is in step. The desktop shell in `src-tauri` has no tests of its own.

## What the shared base gives a test

`backend/tests/conftest.py` gives every test its own home folder, a `PATH` of the system folders only (so no agent program is found), its own agent configuration folders and keyring's fail backend, so a test never reaches your real files, your agents or your password store. It provides `client` (the engine's HTTP client), `core` (the path of `formweb-core`, or a skip with a reason when it is not built), the helpers `starter_site`, `write_fweb` and `broken_site`, and pytest's `tmp_path`. `DEMO` is the repository's `demo/` folder with the bundled sites.

```python
def test_a_site_with_a_broken_link_is_reported_as_a_problem(client, tmp_path):
    site = broken_site(tmp_path)
    ...
```

`frontend/vitest.config.ts` runs every `tests/unit/**/*.test.ts` in happy-dom and restores mocks after each test.

## The five rules

1. The test runs the app through a public surface: an HTTP route, a command of the command line, an MCP tool, an exported interface function, or the visible interface.
2. It checks a result a user or a calling program would notice: a problem reported or not reported, a number, a saved or exported file, a refusal, something on screen.
3. Its expected value comes from outside the code under test: mathematics, the rules of a file format checked by an independent reader, the manual and the documents in `docs/`, an invariant (save then open, export then import, sign then verify), two independent paths that must agree, or a fixture that states its own content.
4. It can fail. Change the expected value once, see the test fail, and change it back.
5. Its name says the behaviour in plain words.

Not accepted:

- reading source files to check text, spelling, comments or formatting;
- checks that a file, function, class or route merely exists;
- a check of the status code alone, with nothing checked in the answer;
- snapshot files made by running the code and saving what came out;
- replacing the thing under test with a stand-in and testing the stand-in;
- a skip or an expected failure without a written reason.

## When a test shows the app is wrong

Do not bend the test. Keep it and mark it as a strict expected failure with a reason that starts with `DEFECT:` and says what the app does, what it should do and where that is stated. `git grep -n "DEFECT:" backend/tests frontend/tests` lists the known ones. When the app is fixed, the strict mark makes the test fail until the mark is removed, so a fix cannot go unnoticed.

## Changing behaviour

Tests are added when the owner asks. A change in behaviour updates its tests in the same pull request. New test data is made by hand or by FormPublisher itself; a picture or a font from outside gets its row in `NOTICE.md` and `demo/MEDIA.md` as any other does. A test never starts a real agent program, never reaches the network and never touches the system password store.

## CI

Every push to `main` and every pull request runs the job `tests` on Linux. It installs the engine and the test tools from `backend/requirements-test.lock`, builds `formweb-core` from the vendored crates and requires it, then installs the interface packages with `npm ci` on Node 22. The layers run one step each, `Engine tests` and `Interface tests`, so the step that fails names the layer. The tests do not run on macOS or Windows in CI.
