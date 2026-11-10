# HASHOUT_LOG · src-tauri · formpublisher

Living log for the desktop shell (Tauri 2). Source files stay comment-free; what they would have said lives here.

Current build version: v0.1.0
Last updated: 2026-11-10 · v0.1.0 first shell; Cargo.toml, Cargo.lock and tauri.conf.json carry 0.1.0.

---

## Org-navi-map

```
src-tauri/
├── Cargo.toml          package formpublisher, its own [workspace]; tauri 2 (macos-private-api), shell, dialog, single-instance, serde_json; gtk on Linux, objc2 on macOS (reveal only)
├── Cargo.lock          resolved by cargo check on Linux (466 packages)
├── build.rs            the app commands with generated allow permissions (app_ready, open_window)
├── tauri.conf.json     splash window, macOSPrivateApi, externalBin, resources, bundle metadata
├── entitlements.plist  hardened runtime exceptions for the frozen Python engine
├── capabilities/       default.json: the engine origin http://127.0.0.1:8280/* as a remote URL
├── icons/              32x32, 128x128, 128x128@2x, icon.png, icon.icns, icon.ico
├── binaries/           .gitkeep; the frozen engine is placed here at build time
└── src/
    ├── main.rs         engine health check and start, main window, open_window, exit
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
