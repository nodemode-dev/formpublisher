# FormPublisher notices

FormPublisher is licensed under the GNU General Public License v3.0 (`LICENSE`, SPDX `GPL-3.0-only`). Copyright 2026 NodeAgentc, Inc. It includes or depends on the following work. Versions are the exact pins in `frontend/package-lock.json`, `backend/requirements.txt` (with the installed backend venv for the packages they bring) and `src-tauri/Cargo.lock`.

## Shipped in the app

| Component | Use | License |
| --- | --- | --- |
| FormPublisher icon art: the app icon and in-app mark (`frontend/public`, `frontend/src/assets/brand`, `src-tauri/icons`, `assets/app-icon`), the owner's own art | the window, Home, the splash, the desktop bundle and the README | GPL-3.0-only (this repository) |
| Inter by Rasmus Andersson, from `@fontsource/inter` 5.3.0 | interface font | SIL Open Font License 1.1 |
| JetBrains Mono by JetBrains, from `@fontsource/jetbrains-mono` 5.3.0 | code font | SIL Open Font License 1.1 |
| `@tauri-apps/api` 2.12.1 | the interface's calls into the desktop shell | Apache-2.0 OR MIT |
| Tauri 2: tauri, tauri-build, tauri-plugin-shell, tauri-plugin-dialog, tauri-plugin-single-instance | the desktop shell | Apache-2.0 OR MIT |
| serde_json | the shell reading the engine's port and JSON | Apache-2.0 OR MIT |
| objc2, objc2-app-kit (macOS only) | the splash window's corner mask and clear background | MIT |
| gtk (Linux only) | the desktop window on Linux | MIT |
| FastAPI 0.141.1, Starlette | the engine service | MIT, BSD-3-Clause |
| Uvicorn 0.53.0 with its `standard` extras (websockets, watchfiles, httptools, uvloop, h11, click, python-dotenv, PyYAML) | HTTP and WebSocket serving, the disk watcher | BSD-3-Clause (uvicorn, websockets, click, python-dotenv); MIT (watchfiles, httptools, h11, PyYAML, uvloop) |
| python-multipart 0.0.32 | upload bodies (site exports) | Apache-2.0 |
| mcp 2.3.0 (the official MCP Python SDK) | the MCP server on stdio | MIT |
| httpx2 2.16.0 | the engine's read-only calls to a running FormWeb | BSD-3-Clause |
| cryptography 50.0.2 | Ed25519 keys, signatures and passphrase encryption of private keys | Apache-2.0 OR BSD-3-Clause |
| FormWeb engine crates 0.19.1 (formweb-model, formweb-engine, formweb-export, formweb-core), vendored unedited in `vendor/formweb-native` with FormWeb's `LICENSE`, Copyright 2026 NodeAgentc, Inc. | `formweb-core`, built by `setup/install_compiler`, opens `.fweb` projects | Apache-2.0, compatible with GPL-3.0-only |
| serde, serde_json, sha2 and their dependencies, pinned in `vendor/formweb-native/Cargo.lock` | `formweb-core` | Apache-2.0 OR MIT |
| pydantic, pydantic-core, annotated-types, typing-extensions, anyio, idna | request models and async I/O, brought in by the packages above | MIT, BSD-3-Clause (typing-extensions PSF-2.0) |
| CPython 3.12, embedded by PyInstaller in the one-file engine sidecar | runs the engine | PSF-2.0 |

The Python rows are the packages in `backend/requirements.txt` and what they install; check `*.dist-info/METADATA` in `backend/venv` for exact licenses and versions of the transitive ones. What PyInstaller freezes is what the engine imports; the build tools below are not frozen.

## Desktop shell: crates under other licences

Tauri links its own dependencies unedited (no `[patch]`, no vendored copy), some under MPL-2.0 or LGPL-2.1-or-later terms as their crates state. The Linux bundles use the system's WebKitGTK, GTK and GLib (LGPL-2.1-or-later) as shared libraries.

## Build and development only (not shipped)

| Component | Use | License |
| --- | --- | --- |
| Vite 8.3.5 | builds the interface | MIT |
| TypeScript 7.0.2 | type checks the interface | Apache-2.0 |
| `@tauri-apps/cli` 2 | builds the desktop app (`npx @tauri-apps/cli@2`) | Apache-2.0 OR MIT |
| PyInstaller 6.22.3 | freezes the engine sidecar (`setup/freeze_backend`) | GPL-2.0-or-later with the bootloader exception, which permits distributing the frozen program under its own licence |
| Playwright for Python 1.65.0 (`backend/requirements-deep.txt`), installed by `./formpublisher_oc_install`, never with a browser download | deep checks drive the person's installed Chrome | Apache-2.0 |
| Rust toolchain (cargo, rustc) | builds `formweb-core` from the vendored crates | Apache-2.0 OR MIT |

## Media

The icon art is FormPublisher's own. There are no photographs or third-party media in the repository.

Trademarks: Form app names belong to nodemode. Other product names mentioned in the docs belong to their owners.
