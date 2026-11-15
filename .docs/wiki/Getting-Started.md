# Getting Started

## Requirements

Node 22.12 or newer and Python 3.12. The desktop app also needs Rust and the Tauri 2 toolchain. `./formpublisher doctor` checks the toolchain, the installs and the ports, and prints a vendor row (in step at a version, or the first problem). `formpublisher.bat doctor` on Windows prints the same row; it has been run under Wine, not on real Windows.

## Install and run

```bash
./formpublisher_oc_install        # the engine venv (backend/venv) and the interface packages
./formpublisher                   # the engine on 127.0.0.1:8280 and the interface on http://localhost:5280
```

`./build_app` makes the desktop app start to finish (log in `build_app.log`). Windows: `formpublisher_oc_install.bat`, `formpublisher.bat`, `build_app.bat`. `./formpublisher agents install` connects Claude Code, Codex and Cursor.

`./formpublisher backend` and `./formpublisher frontend` start one half each. One process serving the built interface: `./formpublisher build`, then `./formpublisher serve` (http://127.0.0.1:8280).

## The desktop app

`./build_app` freezes the engine with PyInstaller into `formpublisher-engine` (the built interface, the four demo sites and the `formweb-core` compiler go inside; `formpublisher-engine --selfcheck` proves it starts) and builds the Tauri 2 shell around it. The app shows a small splash, starts the engine, and reveals the window when the interface has drawn, with no white flash. A second launch focuses the running window. Closing the last window, or a terminate or interrupt signal, stops the engine and anything it started.

The port rule: `FORMPUBLISHER_PORT` when set, else 8280 when free, else any free port. An engine already answering on that port is reused. The engine writes `engine.json` (`app`, `port`, `pid`, `version`, `started`) in the data folder once it is up, so FormWeb's Send to FormPublisher finds the app on any port; when the app is closed FormWeb leaves the site in the inbox and the engine imports it from there. In the desktop app, Open Folder uses the system folder panel and Reveal Site Folder opens only paths inside the data folder. See the manual's "The desktop app".

## The first import

1. In FormWeb, export the site to get a `site-export.zip`.
2. In FormPublisher, drop the zip on Home, or run `./formpublisher run import site-export.zip`.
3. The site opens in a tab. Its routes are listed in the routes strip, with the count in the status bar.
4. `./formpublisher run routes SITE-ID` prints the same list; `./formpublisher run sites` shows each site's id.

## Where things are kept

Imported sites and settings live in FormPublisher's data folder: `~/FormPublisher`, or the folder named by `FORMPUBLISHER_HOME`. Removed sites, builds, keys and prepared folders go to `trash/` there; Home's Trash page restores them (entries from before 0.1.4 too, and one whose place is unknown asks where it goes) or deletes them for good. Home sits under the title bar, so the menubar and Preferences work over it, and Recent sites stay still when a site arrives: a row says how many arrived and Show re-sorts. Keyboard Shortcuts (`Mod+/`) lets you rebind any command with Change and Reset.

## Ports

| Port | What |
| --- | --- |
| 8280 | the engine, on 127.0.0.1 (`FORMPUBLISHER_PORT`) |
| 8281 | the site host for the preview, on 127.0.0.1 (`FORMPUBLISHER_HOST_PORT`) |
| 5280 | the Vite interface, localhost only |
| 5281 | the Vite preview of a production build |
