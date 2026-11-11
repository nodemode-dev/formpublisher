# Getting Started

## Requirements

Node 22.12 or newer and Python 3.12. The desktop app also needs Rust and the Tauri 2 toolchain. `./formpublisher doctor` checks the toolchain, the installs and the ports.

## Install and run

```bash
./formpublisher_oc_install        # the engine venv (backend/venv) and the interface packages
./formpublisher                   # the engine on 127.0.0.1:8280 and the interface on http://localhost:5280
```

`./build_app` makes the desktop app start to finish (log in `build_app.log`); the desktop build is in development. Windows: `formpublisher_oc_install.bat`, `formpublisher.bat`, `build_app.bat`. `./formpublisher agents install` connects Claude Code, Codex and Cursor.

`./formpublisher backend` and `./formpublisher frontend` start one half each. One process serving the built interface: `./formpublisher build`, then `./formpublisher serve` (http://127.0.0.1:8280).

## The first import

1. In FormWeb, export the site to get a `site-export.zip`.
2. In FormPublisher, drop the zip on Home, or run `./formpublisher run import site-export.zip`.
3. The site opens in a tab. Its routes are listed in the routes strip, with the count in the status bar.
4. `./formpublisher run routes SITE-ID` prints the same list; `./formpublisher run sites` shows each site's id.

## Where things are kept

Imported sites and settings live in FormPublisher's data folder: `~/FormPublisher`, or the folder named by `FORMPUBLISHER_HOME`.

## Ports

| Port | What |
| --- | --- |
| 8280 | the engine, on 127.0.0.1 (`FORMPUBLISHER_PORT`) |
| 5280 | the Vite interface, localhost only |
| 5281 | the Vite preview of a production build |
