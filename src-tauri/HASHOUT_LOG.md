# HASHOUT_LOG · src-tauri · formpublisher

Living log for the desktop shell (Tauri 2). Source files stay comment-free; what they would have said lives here.

Current build version: v0.2.8
Last updated: 2026-11-11 · v0.2.3 no shell changes; Cargo.toml, Cargo.lock and tauri.conf.json carry 0.2.3.

---

## Org-navi-map

```
src-tauri/
├── Cargo.toml          package formpublisher, its own [workspace]; tauri 2 (macos-private-api), shell, dialog, single-instance, serde_json; gtk on Linux, objc2 on macOS (reveal only)
├── Cargo.lock          resolved by cargo check on Linux (466 packages)
├── build.rs            the app commands with generated allow permissions (app_ready, open_window, reveal_path)
├── tauri.conf.json     splash window, macOSPrivateApi, externalBin, resources, bundle metadata
├── entitlements.plist  hardened runtime exceptions for the frozen Python engine
├── capabilities/       default.json: the engine origin http://127.0.0.1:*/* as a remote URL (8280 or the port the shell picked)
├── icons/              32x32, 128x128, 128x128@2x, icon.png, icon.icns, icon.ico
├── binaries/           .gitkeep; the frozen engine is placed here at build time
└── src/
    ├── files.rs        reveal_path, limited to the data folder
    ├── main.rs         port choice, engine health check and start in its own process group, signals, main window, open_window, exit
    └── reveal.rs       splash minimum, bar finish, fallback, rounded splash, hidden-until-ready main window
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

Main window: 90% of the primary screen, at least 1024 by 680, centred, system title bar (the form.ext traffic-light port is not taken), drag-drop handler off so the page receives dropped files. `open_window(path, title)` opens a further window on the engine origin only (the path is appended to the fixed origin), label `extra-<millis>`, concealed the same way and revealed by that page's `app_ready`. A second launch focuses the main window.

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
