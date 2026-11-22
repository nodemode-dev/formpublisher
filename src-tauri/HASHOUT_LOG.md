# HASHOUT_LOG · src-tauri · formpublisher

Living log for the desktop shell (Tauri 2). Source files stay comment-free; what they would have said lives here.

Current build version: v0.8.0
Last updated: 2026-11-22 · v0.8.0, no shell change; v0.7.0 the splash stays above other windows as FormDeck's does; v0.6.0 the shell hands the engine's window key to the page, only the engine's own origin may use Tauri, and the splash has a content policy; v0.5.0 the engine is held in a Windows job object, a leftover engine is replaced, a failed start shows the engine's last lines and its log, the engine ships as a folder resource, Rust is pinned at 1.97.0 and the Intel Mac build declares macOS 14; v0.4.1, no shell change (the window text is in the 26 languages; see frontend/HASHOUT_LOG.md); v0.4.0, no shell change (the window gains Templates and the hosting guide; see frontend/HASHOUT_LOG.md); v0.3.4 the desktop build runs a pinned Tauri command line from frontend/node_modules, and build_app.bat stops when the install fails; v0.3.0 the macOS overlay title bar: the traffic lights have their own inset, the title row drags the window, and extra windows share the style.

---

## Org-navi-map

```
src-tauri/
├── Cargo.toml          package formpublisher, its own [workspace]; tauri 2 (macos-private-api), shell, dialog, single-instance, serde_json; gtk on Linux, objc2 on macOS (reveal and traffic lights)
├── Cargo.lock          resolved by cargo check on Linux (466 packages)
├── build.rs            the app commands with generated allow permissions (app_ready, open_window, reveal_path)
├── rust-toolchain.toml the pinned Rust version (1.97.0, minimal profile)
├── tauri.conf.json     splash window, macOSPrivateApi, resources (the engine folder among them), bundle metadata
├── entitlements.plist  hardened runtime exceptions for the frozen Python engine
├── capabilities/       default.json: the engine origin http://127.0.0.1:8280/* as the only remote URL (another port is granted at run time)
├── icons/              32x32, 128x128, 128x128@2x, icon.png, icon.icns, icon.ico
├── engine/             .gitkeep; setup/freeze_backend places the frozen engine folder here at build time
└── src/
    ├── engine_start.rs the engine's last lines, the start failures and their sentences, the data folder and log path, the health answer, replacing a leftover engine
    ├── files.rs        reveal_path, limited to the data folder
    ├── main.rs         port choice, engine start in its own process group with its output followed, signals, main window, open_window, exit
    ├── reveal.rs       splash minimum, bar finish, fallback, rounded splash, hidden-until-ready main window
    ├── traffic_lights.rs  macOS: the inset of the close, minimize and zoom buttons in the overlay title bar
    └── win_job.rs      Windows: the job object that ends the engine with the shell (FormDeck's file, unchanged)
```

---

## Splash and reveal {#reveal}
- refers-to: src/reveal.rs · tauri.conf.json :: app.windows[splash]
- kind: decision
- logged: v0.0.0 · 2026-11-10

FormDeck's logic, with the family constants: the splash is 360 by 200, undecorated, transparent, shadowless, built hidden, and shown by `round_splash` (macOS rounds its content layer to 16 px first). `SPLASH_MIN` is 2600 ms from `mark_launch`, the first line of main. When the page calls `invoke('app_ready', {bg})` the shell waits out the minimum, runs `window.formpublisherSplashDone()` in the splash so the bar completes, waits `BAR_FINISH` 220 ms, shows the main window and closes the splash. `FALLBACK` 20 s reveals the window anyway. On macOS and Linux the main window is built hidden-by-alpha (shown at opacity 0, clicks through on macOS) because a hidden web view stops animation frames; elsewhere it is built visible behind the splash. `BACKGROUND` is `#0a0a0a` on both windows and `bg` from the page replaces it, so no white frame appears. `close_splash` is public so a failed start can remove the splash before the error dialog.

The Linux `set_seen` imports `gtk::prelude::{GtkWindowExt, WidgetExt}` and so Cargo.toml lists `gtk = "0.18"` under Linux; form.ext and FormDeck rely on it arriving implicitly, which is not sound in edition 2021.

---

## Engine and windows {#engine}
- refers-to: src/main.rs :: healthy, spawn_engine, start_engine, open_main, open_window
- kind: decision
- logged: v0.0.0 · 2026-11-10

The engine address is fixed at http://127.0.0.1:8280. `healthy` makes a plain TCP request for `GET /api/health` and accepts a 200, so no HTTP client crate is needed. If it answers, the main window opens on it and no process is owned. If not, the shell starts either `formpublisher-engine` beside the executable (where Tauri puts externalBin, `Contents/MacOS` on macOS) or, in a source checkout, `formpublisher serve` from `FORMPUBLISHER_ROOT` (default the folder above src-tauri in debug builds), with `FORMPUBLISHER_PORT=8280`. It polls every 250 ms for up to 60 s, then shows an error dialog and exits. On exit an owned child gets SIGTERM, up to 1.5 s to leave, then a kill. The work runs on a thread; the window is built on the main thread through `run_on_main_thread`.

Main window: 90% of the primary screen, at least 1024 by 680, centred, an overlay title bar on macOS (see [Overlay title bar and traffic lights](#traffic-lights)) and the system title bar elsewhere, drag-drop handler off so the page receives dropped files. `open_window(path, title)` opens a further window on the engine origin only (the path is appended to the fixed origin), label `extra-<millis>`, concealed the same way and revealed by that page's `app_ready`. A second launch focuses the main window.

---

## Build-time engine injection {#sidecar}
- refers-to: tauri.conf.json :: bundle.externalBin
- kind: decision
- logged: v0.0.0 · 2026-11-10

Following form.ext and FormDeck, the sidecar is declared as `externalBin: ["binaries/formpublisher-engine"]` and the file `binaries/formpublisher-engine-<target triple>` is produced by the backend's freeze step and `build_app` before `tauri build`; the shell tree carries only `.gitkeep`. Tauri's build script requires that file to exist, so `cargo check` and `tauri build` both need it present.

---

## Capability {#capability}
- refers-to: capabilities/default.json
- kind: decision
- logged: v0.0.0 · 2026-11-10

The remote origin is `http://127.0.0.1:8280/*`, covering windows `splash`, `main` and `extra-*`. Permissions: core defaults, title, close, minimise, maximise toggle, shell open, the four dialog commands, and the generated `allow-app-ready` and `allow-open-window`.

---

## Bundle metadata {#bundle}
- refers-to: tauri.conf.json :: bundle
- kind: note
- logged: v0.0.0 · 2026-11-10

Publisher "NodeAgentc, Inc.", copyright "Copyright 2026 NodeAgentc, Inc.", license GPL-3.0-only, macOS minimum 13.0 with hardened runtime and entitlements. `resources` ships ../LICENSE and ../NOTICE.md at the resource root; `licenseFile` is ../LICENSE. NOTICE.md must exist at the repo root before the first bundle.

---

## Verification limits {#verify}
- refers-to: Cargo.toml
- kind: note
- logged: v0.0.0 · 2026-11-10

`cargo check` on the Linux build box resolved the crate graph and wrote Cargo.lock, then stopped in the GTK system crates (gdk-3.0 not found); WebKitGTK development files are not installed there and none were added. The crate's own code was therefore not compiled; it was parsed with rustfmt. The first desktop build on the owner's machine is the compile check.

---

## Port, process group and signals {#port}
- refers-to: src/main.rs :: DEFAULT_PORT, PORT, ENGINE_GROUP, on_signal, watch_signals, choose_port, spawn_engine, kill_backend, main · capabilities/default.json · tauri.conf.json :: bundle.resources
- kind: decision
- logged: v0.1.3 · 2026-11-10

`DEFAULT_PORT` is 8280 because FormWeb's Send to FormPublisher looks there first. `choose_port` takes `FORMPUBLISHER_PORT` when it is set and positive, else 8280 when it binds, else any free port the system hands out; the result goes into `PORT` and is passed to the engine as `FORMPUBLISHER_PORT`. The capability's remote URL is therefore `http://127.0.0.1:*/*`. When the shell lands on another port, FormWeb's live send misses and its inbox fallback takes over.

`spawn_engine` starts the engine as its own process group (`process_group(0)` on Unix, `CREATE_NO_WINDOW` on Windows), and `ENGINE_GROUP` holds its pid, which is the group id; it stays 0 until the engine starts. `kill_backend` signals the negative id, so the whole group stops: the PyInstaller one-file bootloader and the Python engine under it. The engine's own parent watch only sees the bootloader, which is why the group matters.

A terminate, interrupt or hangup signal skips Tauri's `RunEvent::Exit`, so `watch_signals` installs `on_signal` for 1, 2 and 15 through libc's `signal`; the handler sends 15 to the engine group when there is one and calls `_exit(0)`. The run loop exits the app when the last webview window is destroyed, and `RunEvent::Exit` stops the engine the shell started.

`tauri.conf.json` bundles `demo/sample-site.zip` as a resource, so the frozen engine finds the demo. `src-tauri/permissions/autogenerated/` is written by the Tauri build and ignored by git.

Checked on Linux after installing WebKitGTK from apt: `cargo build --release` with no warnings; under xvfb the shell with the frozen engine showed the splash, then the Start page with no white frame; `kill -TERM` on the shell left no engine process and freed the port within 3 s. Not run: `tauri build` bundles, macOS and Windows.

---

## Files and folder panel {#files}
- refers-to: src/files.rs :: data_folder, reveal_path · src/main.rs :: invoke_handler · build.rs :: APP_COMMANDS · capabilities/default.json
- kind: decision
- logged: v0.1.4 · 2026-11-10

`reveal_path` shows a path in the system file manager only when its canonical form lies under the canonical data folder. The shell derives the data folder exactly as the engine does (`FORMPUBLISHER_HOME` with a leading `~/` expanded, else `~/FormPublisher`), because the engine inherits the same environment, so the two agree without asking the engine. Canonicalizing follows links first, so a link inside the data folder that points outside is refused; a missing path answers "That path does not exist"; Windows' `\\?\` prefix is stripped before use. macOS runs `open -R`, Windows `explorer /select,`, Linux `xdg-open` on the folder (the parent of a file), because xdg-open cannot select. It is an async command listed in `build.rs`, which generates `allow-reveal-path`, granted in the capability. Open Folder's system panel is the dialog plugin's own `open` with `directory: true`; `dialog:allow-open` was already granted.

Checked on Linux: `cargo build --release` with no warnings; under xvfb `reveal_path` accepted the data folder's `sites` folder (xdg-open, stubbed to log, received it) and refused `/etc` and a missing path. Not run: the macOS and Windows branches, the panel itself (no portal under xvfb), a real file manager window.

---

## Linux shell check {#linux-shell-028}
- refers-to: src/main.rs :: choose_port, spawn_engine, sidecar_path · tauri.conf.json :: bundle.externalBin · setup/freeze_backend
- kind: note
- logged: v0.2.8 · 2026-11-11

Built on Linux with WebKitGTK 2.52.6 (already installed): `setup/freeze_backend` (44 s, it installs PyInstaller into the venv itself) wrote `binaries/formpublisher-engine-x86_64-unknown-linux-gnu`, ignored by git; `CARGO_TARGET_DIR=/tmp/... cargo build --release` took 8 minutes cold with no warnings, and Tauri copied the engine beside the executable, so `sidecar_path` used it. Under Xvfb with `FORMPUBLISHER_PORT=9012` and `FORMPUBLISHER_HOME` under /tmp the window opened at 90% of the screen, an imported `.fpub` opened, the in-window menus (native menus are macOS only) followed a live language switch in English, German and Russian, and the window title stayed "FormPublisher" (the brand is not translated; the page shows the site name). The toolbar, bottom tab strip, Problems bar and compact filter matched Chrome on the same engine at 1024 x 680 and 1440 x 900; WebKitGTK selects are about 6 px wider, so the Problems filters fall back to "All" a little earlier, as `fitBar()` measures. Without a window manager the 1024 x 680 minimum is only a size hint (`xprop` shows it). With `WEBKIT_DISABLE_DMABUF_RENDERER=1` WebKitGTK draws no `backdrop-filter`, so glass menus show what is behind them; without that variable the blur is drawn, so visual checks of glass surfaces should leave it unset. SIGTERM stopped the engine and freed the port within 4 s. The run also exposed the shared preview host port, fixed in the engine (see `backend/HASHOUT_LOG.md`, Phase 56). Not run: `tauri build` bundles, macOS native menus, Windows. No shell source changed.

---

## Overlay title bar and traffic lights {#traffic-lights}
- refers-to: src/traffic_lights.rs :: place, inset · src/main.rs :: open_main, open_window, on_page_load, on_window_event · src/reveal.rs :: conceal, reveal · capabilities/default.json · Cargo.toml :: objc2-app-kit
- kind: decision
- logged: v0.3.0 · 2026-11-15

On macOS the main window has `TitleBarStyle::Overlay` with a hidden title, so the page's title row is the window's title bar. Until 0.3.0 the page did nothing for it: no part of the row dragged the window, and the close, minimize and zoom buttons sat at the system's default place over the brand. The page's half is in `frontend/HASHOUT_LOG.md`, Phase 62 (a 38 px row, 78 px of left padding, `data-tauri-drag-region` on the row's empty parts).

`traffic_lights::place` gives the three buttons their own inset: the title bar container becomes `ROW` 38 pt tall, the buttons are centred in it and start `LEFT` 14 pt from the edge, keeping the system's own spacing (`step` is measured from the close and minimize buttons, so it follows the macOS version). AppKit lays the title bar out again, back to its defaults, whenever the window is resized, gains or loses focus, changes theme or scale factor, and after a page load, so `place` runs on those window events, after `conceal`, after the reveal and when a page finishes loading. It runs twice each time, at once and 120 ms later, because some of those layouts happen after the event is delivered. The splash is skipped. On Linux and Windows `place` is an empty function.

Windows opened by `open_window` now get the same overlay style; they had the system title bar while the page drew its row for the overlay. The capability gains `core:window:allow-start-dragging`, which `data-tauri-drag-region` needs when the page comes from a remote origin (the engine). `objc2-app-kit` gains the `NSButton` and `NSControl` features for `standardWindowButton` and the buttons' frames.

Checked: `cargo check` for Linux and for the macOS target, both exit 0 (the frozen engine replaced by a placeholder file). The page's geometry was measured in Chrome with a faked macOS shell. Not run: any of this on a Mac; whether the 120 ms second pass is enough on a slow machine is not known.

---

## The desktop build runs a pinned Tauri command line {#cli-pin}
- refers-to: ../build_app · ../build_app.bat · ../frontend/package.json :: devDependencies · Cargo.lock :: tauri
- kind: decision
- logged: v0.3.4 · 2026-11-21

Until 0.3.3 `build_app` and `build_app.bat` ran `npx --yes @tauri-apps/cli@2`, which fetches whatever 2.x is newest on the day of the build, so two builds of one commit could differ and a new release of the tool could break the build. `@tauri-apps/cli` is now a devDependency of `frontend` at 2.12.5, the version of the `tauri` crate in `Cargo.lock` (2.12.6 is the newest on that line; the lock keeps the crate at 2.12.5, so the command line and the crate stay on one release). `@tauri-apps/api` stays at 2.12.1: Tauri stops a build when the crate and the api package differ in minor version, and both are 2.12. No `@tauri-apps/plugin-*` package is a dependency (the dialog call is `invoke` from the api package, see `frontend/HASHOUT_LOG.md`), so `tauri info` lists the three as not installed, which is expected. The lock file was refreshed with `npm install` and only gained the command line and its eleven platform packages (218 lines added, none removed).

`build_app` runs `node frontend/node_modules/.bin/tauri` from the repository root, the way `./formpublisher desktop dev` already does; `build_app.bat` runs `frontend\node_modules\.bin\tauri.cmd`, as `formpublisher.bat desktop dev` does. Both install again when that file is missing (a `frontend/node_modules` from before the pin has no copy of the tool). `build_app.bat` also stops now, with exit code 1 and a message, when the install of the engine and the window fails; before, it went on to a build that could not succeed.

Checked: `npm ci`, `npm audit --audit-level=low` (0 vulnerabilities) and `npm run build` in `frontend`; from the repository root `node frontend/node_modules/.bin/tauri --version` (2.12.5), `build --help` and `info` (it finds `src-tauri`; tauri 2.12.5, api 2.12.1, no version-mismatch warning); `bash -n build_app`. Not run: a desktop build (no WebKitGTK here), any line of `build_app.bat` (no Windows or Wine here; its install check is the idiom `formpublisher.bat boot` already has, `call ... & if errorlevel 1`, which Phase 45 ran under Wine), macOS.

---

## The engine starts, stops and reports with its shell {#engine-start}
- refers-to: src/main.rs :: engine_program, follow, spawn_engine, kill_backend, engine_failed, engine_exit, start_engine · src/engine_start.rs · src/win_job.rs · Cargo.toml · tauri.conf.json :: bundle.resources
- kind: decision
- logged: v0.5.0 · 2026-11-22

Until 0.4.1 the shell adopted any 200 from `/api/health` on its port, started the one-file sidecar with its output thrown away, had no hold on it on Windows, and said only "did not start". Now:

- `win_job.rs` is FormDeck's file, byte for byte (Apache-2.0, the same owner): one job object with `KILL_ON_JOB_CLOSE`, `hold_pid` after the spawn, `end` in `kill_backend`. When the shell dies by any means Windows closes the job handle and ends the engine. `windows-sys` 0.61.2 was already in the lock through Tauri; it is now a direct dependency with the four features the file uses.
- `engine_start.rs` holds what does not need a window: `Tail` (the engine's last 12 lines, 300 characters each, never a line holding `window-key`, which 0.6.0 will send), `Failure` and its sentences, `message`, `data_folder` (`FORMPUBLISHER_HOME` with `~` expanded as the engine's `expanduser` does, else `~/FormPublisher`), `engine_log`, `health` (reads the whole answer and takes `app` and `version` from the JSON, where the old check read 16 bytes for ` 200`) and `replace_leftover`. FormDeck's unit tests of the same shapes were not brought over: no test is written until the owner has tested.
- `replace_leftover` reads `engine.json` in the data folder (the engine has written it since 0.2.x: app, pid, port, version). When the pid is not this process and the port answers as `formpublisher`, that engine is ended (`kill -TERM`, then `-KILL` after 2.5 s; `taskkill /PID n /T /F` on Windows, with no console window) and the shell waits up to 5 s for the port to stop answering. It is never adopted, whatever its version: single-instance already guarantees no other window owns it, an engine of another version would serve an old window, and from 0.6.0 an adopted engine could not hand over its window key. A stale `engine.json` whose port does not answer is left alone, so a recycled pid is never ended.
- `start_engine` then chooses the port (so 8280 is free again after a replacement), spawns, and waits up to 90 s (`HEALTH_WAIT`; a first launch on a slow disk scans a 255 MB folder) for a health answer whose version is the shell's own `CARGO_PKG_VERSION`. An engine that exits first gives `Stopped(code)`, another version gives `WrongVersion`, silence gives `TimedOut`.
- `spawn_engine` pipes stdout and stderr and `follow` drains each on its own thread into the `Tail` (a pipe nobody reads would stop the engine once it fills). The engine gets `FORMPUBLISHER_SHELL_PID` and `FORMPUBLISHER_DESKTOP=1`; it watches that pid itself (backend log, Phase 72), which covers macOS and Linux, where there is no job object, and backs the job up on Windows.
- `engine_failed` closes the splash, waits 150 ms for the reader threads to take the last lines, and shows a native error dialog: the sentence, "The engine's last lines:", and the log's path when the file exists. `open_main` failing reports `Failure::Window` from its own thread, because a blocking dialog on the main thread would stop the event loop it needs.
- `engine_program` looks in the bundle's resource folder first (`resource_dir()/engine`), then `../Resources/engine`, `engine` beside the binary (where `tauri dev` copies resources) and last beside the binary (an older one-file sidecar). `tauri.conf.json` maps `engine` to the resource `engine` and has no `externalBin`; `src-tauri/engine/.gitkeep` is tracked so `cargo check` finds the folder before any freeze, and `src-tauri/binaries/` is gone.

Checked here: `cargo check --locked --target x86_64-pc-windows-msvc` passes with no warning (Rust 1.97.0). Not run: `cargo check` for the Linux host (no GTK or WebKitGTK development packages in this workspace, and they cannot be installed) or for `aarch64-apple-darwin` (objc2's build script needs Apple's compiler); CI's new `windows-shell` and `macos-shell` jobs run both natively. Nothing was run on Windows or macOS: the job object, `taskkill`, the dialog and the replaced engine are steps in TEST_PLAN.md.

## The Rust toolchain is pinned {#rust-pin}
- refers-to: rust-toolchain.toml · setup/lib.sh :: fp_rust_pin, fp_rust_env · build_app
- kind: decision
- logged: v0.5.0 · 2026-11-22

`rust-toolchain.toml` names 1.97.0 with the minimal profile. `setup/lib.sh` exported `RUSTUP_TOOLCHAIN=stable`, and that variable wins over any toolchain file, so the pin had to go there too: `fp_rust_pin` reads the channel from this file (`FORMPUBLISHER_RUST_TOOLCHAIN` still overrides it) and `fp_rust_env` exports it when that toolchain is installed; `build_app` installs it when it is missing. The vendored `vendor/formweb-native` carries no toolchain file of its own, because that folder is a byte copy of FormWeb's and `vendor --check` refuses a file FormWeb does not have; the scripts and CI build it with the same pinned version through `RUSTUP_TOOLCHAIN`.

## The minimum macOS differs by processor {#macos-minimum}
- refers-to: tauri.conf.json :: bundle.macOS.minimumSystemVersion · build_app :: tauri_args
- kind: decision
- logged: v0.5.0 · 2026-11-22

`tauri.conf.json` says 13.0, which is what the Apple silicon build needs. The Intel build installs a `cryptography` wheel built for macOS 14 (PyPI has none for Intel at this version; the family's release build supplies one), so `build_app` adds `--config '{"bundle":{"macOS":{"minimumSystemVersion":"14.0"}}}'` when the target is `x86_64-*`. One file cannot hold two values, and saying 14 for both would turn away Apple silicon Macs on 13 that run it. formcompiler's registry entry (`catalog.minimum_os.macos`) says "macOS 13" and needs the same split; that is a change in formcompiler.

## The window key reaches the page from the shell, and only the engine's origin may use Tauri {#window-key}
- refers-to: src/main.rs :: WindowKey, key_script, grant_engine_origin, follow, start_engine, open_main, open_window · src/engine_start.rs :: window_key, key_script, WINDOW_PERMISSIONS, KEY_WAIT, Failure::NoKey · capabilities/default.json · tauri.conf.json :: app.security.csp
- kind: decision
- logged: v0.6.0 · 2026-11-22

The engine prints one line, `formpublisher-window-key: ` and 43 URL-safe characters, on its standard output when the shell started it (`FORMPUBLISHER_DESKTOP=1`). `follow` takes that line out of the stream before the tail sees it (the tail would refuse it anyway) and keeps the value in `WindowKey`. After health answers, `start_engine` waits up to 10 s for the key (`Failure::NoKey` otherwise). `key_script` is an initialization script on the main window and on every extra window: it sets `window.__FORMPUBLISHER_WINDOW_KEY` only when the page's origin is the engine's own and the frame is the top one, so the previewed site in its iframe on the host port never sees it. The page reads the value once and deletes it (frontend log, Phase 71). The shape is FormDeck's (`src-tauri/src/main.rs` there); the key is found with a plain prefix test rather than the `regex` crate, which this shell does not carry.

The capability file granted Tauri's commands to `http://127.0.0.1:*/*`: every loopback port, the preview host's among them. It now names `http://127.0.0.1:8280/*` only. When 8280 was taken and the shell picked another port, `grant_engine_origin` adds one run-time capability, `engine-origin`, for exactly that origin with the same 14 permissions (`WINDOW_PERMISSIONS`, which must stay in step with the file) on `main` and `extra-*`; if that fails the start fails with a dialog rather than opening a window whose buttons do nothing. `app.security.csp` was null; it is now a policy for the one page Tauri itself serves, the splash (own scripts and styles, inline styles, the IPC endpoints, nothing else). The window proper is served by the engine and gets its policy from the engine's response header (backend log, Phase 73).

Checked here: `cargo check --locked --target x86_64-pc-windows-msvc`, clean. Not run: the run-time capability on a second port, the splash under its policy, an iframe on the preview port calling `window.__TAURI_INTERNALS__` (all steps in TEST_PLAN.md, 2A and 2B).

## The splash matches FormDeck's {#splash-parity}
- refers-to: tauri.conf.json :: app.windows[splash] · src/reveal.rs · ../frontend/public/splash.html
- kind: decision
- logged: v0.7.0 · 2026-11-22

Compared with FormDeck 0.46.3 (96b8e0e), the family's fullest splash: `splash.html` is byte for byte the same once the app's name is normalised, and `reveal.rs` differs only by `traffic_lights::place` and the shared `close_splash` this shell's failure dialog uses. The one declaration FormDeck has and this file did not is `alwaysOnTop` on the splash, so the 360 by 200 window is not lost behind another app during the at least 2.6 s it shows; it is added. Only the splash is declared; the main window is built in `open_main` after the engine answers, with the background colour set before it is shown, and a failed engine closes the splash and shows the native dialog. FormVis and FormDeck leave `app.security.csp` unset; this shell keeps the 0.6.0 policy for the splash, and Tauri's codegen gives the splash's inline script and style their nonce and the script its hash at build time (tauri-codegen 2.7.4 `map_core_assets`, tauri 2.12.5 `replace_csp_nonce`), so the page runs under it. Not run: the splash on any desktop (TEST_PLAN.md 1A.1, 2B.3).
