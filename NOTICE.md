# FormPublisher notices

FormPublisher is licensed under the GNU General Public License v3.0 (`LICENSE`, SPDX `GPL-3.0-only`). Copyright 2026 NodeAgentc, Inc. It includes or depends on the following work. Versions are the exact pins in `frontend/package-lock.json`, `backend/requirements.lock` (the hashed lock of `backend/requirements.txt`, `requirements-deep.txt` and `requirements-build.txt`, with the installed backend venv for the packages they bring) and `src-tauri/Cargo.lock`.

## Shipped in the app

| Component | Use | License |
| --- | --- | --- |
| FormPublisher icon art: the app icon and in-app mark (`frontend/public`, `frontend/src/assets/brand`, `src-tauri/icons`, `assets/app-icon`), the owner's own art | the window, Home, the splash, the desktop bundle and the README | GPL-3.0-only (this repository) |
| Inter by Rasmus Andersson, from `@fontsource/inter` 5.3.0 | interface font | SIL Open Font License 1.1 |
| JetBrains Mono by JetBrains, from `@fontsource/jetbrains-mono` 5.3.0 | code font | SIL Open Font License 1.1 |
| Fonts inside the bundled demo sites, as woff2 files in each site's `assets/`: Inter 4 variable, Copyright (c) 2016 The Inter Project Authors (Lowlight, Northwind Notes); Space Grotesk, Copyright 2020 The Space Grotesk Project Authors (Lowlight); IBM Plex Mono, Copyright 2017 IBM Corp. (Lowlight, Looking Back, Harbour Ferries); Playfair Display, Copyright 2017 The Playfair Display Project Authors (Looking Back); Source Serif 4, Copyright 2014 The Source Serif 4 Project Authors (Looking Back); Oswald, Copyright 2016 The Oswald Project Authors (Harbour Ferries); Work Sans, Copyright 2019 The Work Sans Project Authors (Harbour Ferries). Each family's licence text ships in `demo/licenses/OFL-<Family>.txt`. Files and sources: `demo/MEDIA.md` | the text of the demo sites (`demo/sites/*.zip`, `demo/sample-site.zip`) | SIL Open Font License 1.1 |
| `@tauri-apps/api` 2.12.1 | the interface's calls into the desktop shell | Apache-2.0 OR MIT |
| Tauri 2: tauri, tauri-build, tauri-plugin-shell, tauri-plugin-dialog, tauri-plugin-single-instance | the desktop shell | Apache-2.0 OR MIT |
| serde_json | the shell reading the engine's port and JSON | Apache-2.0 OR MIT |
| objc2, objc2-app-kit (macOS only) | the splash window's corner mask and clear background | MIT |
| gtk (Linux only) | the desktop window on Linux | MIT |
| windows-sys 0.61.2 (Windows only) | the job object that makes the engine end with the shell | MIT OR Apache-2.0 |
| FastAPI 0.141.1, Starlette | the engine service | MIT, BSD-3-Clause |
| Uvicorn 0.53.0 with its `standard` extras (websockets, watchfiles, httptools, uvloop, h11, click, python-dotenv, PyYAML) | HTTP and WebSocket serving, the disk watcher | BSD-3-Clause (uvicorn, websockets, click, python-dotenv); MIT (watchfiles, httptools, h11, PyYAML, uvloop) |
| python-multipart 0.0.32 | upload bodies (site exports) | Apache-2.0 |
| mcp 2.3.0 (the official MCP Python SDK) | the MCP server on stdio | MIT |
| httpx2 2.16.0 | the engine's read-only calls to a running FormWeb | BSD-3-Clause |
| cryptography 50.0.2 | Ed25519 keys, signatures and passphrase encryption of private keys | Apache-2.0 OR BSD-3-Clause |
| Playwright for Python 1.65.0 (`backend/requirements-deep.txt`), frozen into the engine; no browser is downloaded | deep checks drive the person's installed Google Chrome or Microsoft Edge | Apache-2.0 |
| Node.js runtime inside Playwright's driver (`playwright/driver/node`), frozen into the engine with the driver | runs Playwright's driver for the deep checks | MIT, with the third-party licences listed in the driver's own `LICENSE` and `ThirdPartyNotices` files, which ship in the engine folder under `_internal/playwright/driver/` |
| greenlet 3.5.6 | the coroutine switching that Playwright's Python package needs | MIT AND PSF-2.0 |
| FormWeb engine crates 0.27.0 (formweb-model, formweb-engine, formweb-export, formweb-core), vendored unedited in `vendor/formweb-native` with FormWeb's `LICENSE`, Copyright 2026 NodeAgentc, Inc. | `formweb-core`, built by `setup/install_compiler`, opens `.fweb` projects | Apache-2.0, compatible with GPL-3.0-only |
| serde, serde_json, sha2 and their dependencies, pinned in `vendor/formweb-native/Cargo.lock` | `formweb-core` | Apache-2.0 OR MIT |
| pydantic, pydantic-core, annotated-types, typing-extensions, anyio, idna | request models and async I/O, brought in by the packages above | MIT, BSD-3-Clause (typing-extensions PSF-2.0) |
| CPython 3.12, embedded by PyInstaller in the engine folder (`src-tauri/engine`, shipped as the resource folder `engine`) | runs the engine | PSF-2.0 |

The Python rows are the packages in `backend/requirements.txt` and `backend/requirements-deep.txt` and what they install; check `*.dist-info/METADATA` in `backend/venv` for exact licenses and versions of the transitive ones. What PyInstaller freezes is what the engine imports; the build tools below are not frozen.

## Desktop shell: crates under other licences

Tauri links its own dependencies unedited (no `[patch]`, no vendored copy), some under MPL-2.0 or LGPL-2.1-or-later terms as their crates state. The Linux bundles use the system's WebKitGTK, GTK and GLib (LGPL-2.1-or-later) as shared libraries.

## Build and development only (not shipped)

| Component | Use | License |
| --- | --- | --- |
| Vite 8.3.5 | builds the interface | MIT |
| TypeScript 7.0.2 | type checks the interface | Apache-2.0 |
| `@tauri-apps/cli` 2.12.5 | builds the desktop app (`build_app` runs the copy in `frontend/node_modules`) | Apache-2.0 OR MIT |
| PyInstaller 6.22.3 | freezes the engine folder (`setup/freeze_backend`) | GPL-2.0-or-later with the bootloader exception, which permits distributing the frozen program under its own licence |
| uv 0.11.32 | writes the requirement locks (`python setup/lock_requirements.py`); not shipped | Apache-2.0 OR MIT |
| Rust toolchain 1.97.0 (cargo, rustc), pinned in `src-tauri/rust-toolchain.toml` | builds the desktop shell and `formweb-core` from the vendored crates | Apache-2.0 OR MIT |

## Media

The icon art is FormPublisher's own. The only third-party pictures in the repository are inside the bundled demo sites. Every image file the demos ship is listed below, each under its own status; `demo/MEDIA.md` has the same rows with the fonts. Counts: the three site zips hold 35 image files (24, 10 and 1), 22 of them outside pictures (18 different files, because four are in two sites: 17 NASA files, one of them a crop, and the Hubble Ultra Deep Field); Northwind Notes holds 9; there are four card pictures and four copies of the app mark. The copies of the app mark are GPL-3.0-only, like every FormPublisher icon; everything else that is not an outside picture is own work, Apache-2.0.

### Demo images

The three FormWeb demo sites are bundled as FormWeb exported them, so each picture's file name is the SHA-256 of its bytes. The NASA pictures were not downloaded for this repository: each file is byte for byte the file that FormDeck (`frontend/public/demos/nasa/`, credits in its `demo/CREDITS.md`) or Form.md (`demos/views/assets/media/`, credits in its `demos/views/CREDITS.md`) already ships, and the Changes column repeats what those credits record. No picture was retouched; the pages crop with `object-fit`.

Status of the NASA rows: the source pages carry a credit line and no licence text. NASA's media guidelines (https://www.nasa.gov/nasa-brand-center/images-and-media/) say NASA content "generally are not subject to copyright in the United States" and that "NASA should be acknowledged as the source of the material". The rows say "NASA content" for that status: not subject to copyright in the United States (NASA media guidelines); it is not a CC0 dedication. The credit lines are the ones on each picture's own NASA page, read again on 15 November 2026; the NASA Image and Video Library records (images.nasa.gov) have no credit line, only the NASA centre, so those rows say NASA with the centre in brackets. No NASA insignia and no identifiable person is shown.

One picture is not NASA-only: the Hubble Ultra Deep Field is published by ESA/Hubble under Creative Commons Attribution 4.0 International (https://creativecommons.org/licenses/by/4.0/, stated at https://esahubble.org/copyright/), which requires the full credit line to be shown. It was recorded before as public domain on the strength of its Wikimedia Commons page, which is not the original publisher's term. The file is a copy made through Wikimedia Commons (https://commons.wikimedia.org/wiki/File:Hubble_ultra_deep_field.jpg, whose source is the March 2004 NASA/STScI release 2004/07 that ESA/Hubble published as heic0406a), resized to 1400x1400; its tone differs slightly from the ESA/Hubble JPEG. NASA publishes the same picture at https://science.nasa.gov/asset/hubble/hubble-ultra-deep-field-image-reveals-galaxies-galore/ (credit there: "NASA, ESA, S. Beckwith (STScI) and the HUDF Team").

"Own work, Apache-2.0" means the file was made for these demos by the owner's team. A capture of a demo site is own work, and the outside pictures visible in it keep the credit and status of their own rows.

Lowlight (`demo/sites/lowlight.zip`): 24 image files in `assets/`, and the card picture.

| File | Title or subject | Author or credit | Source page | Licence or status as the source states it | Changes |
| --- | --- | --- | --- | --- | --- |
| `a9d3e2fbb94e86f8f6f6f921ebb4b4720c31733fc05a7c5cb1f71d491a1a361c.webp` | Earthrise, Apollo 8 (AS08-14-2383) | NASA/William Anders | https://www.nasa.gov/image-detail/moon-landing-l-7-months-10-apollo-8-earthrise-photo-as08-14-2383 | No licence text; credit line "Image Credit: NASA/William Anders"; NASA content | 3000x1971 JPEG resized to 1400x920 WebP |
| `07bd8a6730b2ece0470109cf888df9df0f5e989d6f3fa9def50322a03362ac3c.webp` | A Breathtaking Earthset from Orion (art002e021278), 6 April 2026 | NASA | https://images.nasa.gov/details/art002e021278 | No licence text; photographer field "NASA"; NASA content | 5568x3712 JPEG resized to 1400x933 WebP |
| `e422ff4c83b944b85a4de501d9f388745fce726dc7021237af70fdda97744239.webp` | Solar System Portrait, Earth as Pale Blue Dot (PIA00452), Voyager 1 | NASA/JPL-Caltech | https://science.nasa.gov/photojournal/solar-system-portrait-earth-as-pale-blue-dot/ | No licence text; credit line as given; NASA content | 453x614 JPEG resized to 334x453 WebP |
| `fde102acb7e70b75710cf2549964c499097a782c68fe6a7d24492acbe94a6d76.webp` | The Day the Earth Smiled (PIA17172) | NASA/JPL-Caltech/SSI | https://science.nasa.gov/photojournal/the-day-the-earth-smiled/ | No licence text; credit line as given; NASA content | 9000x3500 JPEG resized to 1600x622 WebP |
| `955dcecd651529a0deeb544dcb957ed711898c8c60f1a6b74ca5307f24aedaed.webp` | The Greatest Saturn Portrait ...Yet (PIA06193) | NASA/JPL/Space Science Institute | https://science.nasa.gov/photojournal/the-greatest-saturn-portrait-yet/ | No licence text; credit line as given; NASA content | 8888x4544 JPEG resized to 1600x818 WebP |
| `68e6d0d35c06c4154434f53714ee57023c12f9e9705d30aef8d3e000d173dc30.webp` | The Edge of the Night (PIA17199) | NASA/JPL-Caltech/Space Science Institute | https://science.nasa.gov/photojournal/the-edge-of-the-night/ | No licence text; credit line as given; NASA content | 4399x980 grayscale JPEG resized to 1600x356 WebP |
| `b0326209930926f747c37e135d33cb8a5895e5e41916652428330de1d14b9104.webp` | Cassini Jupiter Portrait (PIA04866) | NASA/JPL/Space Science Institute | https://science.nasa.gov/photojournal/cassini-jupiter-portrait/ | No licence text; credit line as given; NASA content | 1920x2400 JPEG resized to 800x1000 WebP |
| `3425fd92e0c61270cdef63533fdedbdb0c1db5855f158a04998252aaf95e2801.webp` | Looking Up at Mars Rover Curiosity in 'Buckskin' Selfie (PIA19808) | NASA/JPL-Caltech/MSSS | https://science.nasa.gov/photojournal/looking-up-at-mars-rover-curiosity-in-buckskin-selfie/ | No licence text; credit line as given; NASA content | 4841x2949 JPEG resized to 1600x975 WebP |
| `87bbfdcfacff6b4eebd20e9a0113a8dd4a7863e45d0b0ae3cc29a09e37b80466.webp` | Curiosity Self-Portrait at 'Mojave' Site on Mount Sharp (PIA19142) | NASA/JPL-Caltech/MSSS | https://science.nasa.gov/photojournal/curiosity-self-portrait-at-mojave-site-on-mount-sharp/ | No licence text; credit line as given; NASA content | 9015x4617 JPEG resized to 1600x819 WebP |
| `3b3a4b4245702d9e66ccd8c8144f2548bf20e51ee29c59f46c1d8e32f395677b.webp` | Perseverance's Selfie with Ingenuity (PIA24542) | NASA/JPL-Caltech/MSSS | https://science.nasa.gov/photojournal/perseverances-selfie-with-ingenuity/ | No licence text; credit line as given; NASA content | 12341x9076 JPEG resized to 1600x1177 WebP |
| `44acd0e9283f496ee74b45befa0d31be06b83544f10942333b3eb7deecc85137.webp` | The same picture, PIA24542, right-hand part of the frame | NASA/JPL-Caltech/MSSS | https://science.nasa.gov/photojournal/perseverances-selfie-with-ingenuity/ | No licence text; credit line as given; NASA content | The 1600x1177 WebP above cropped to 1245x1177 (columns 345 to 1590) and re-encoded as WebP at quality 86 with Pillow, for the tile-cut component |
| `25038129e80fc2501c3bdbfd21ed27399b93dfd3be2919b520ba10e659b1cddd.webp` | Perseverance's Selfie With 'Cheyava Falls' (PIA26344) | NASA/JPL-Caltech/MSSS | https://science.nasa.gov/photojournal/perseverances-selfie-with-cheyava-falls/ | No licence text; credit line as given; NASA content | 10502x7458 JPEG resized to 1400x994 WebP |
| `1978facdbeeed49c548a3f904ae2ab7cf3e106948d925d43511ff8d6e3ef9192.webp` | Hubble Ultra Deep Field (ESA/Hubble heic0406a) | NASA, ESA, and S. Beckwith (STScI) and the HUDF Team | https://esahubble.org/images/heic0406a/ | Creative Commons Attribution 4.0 International, https://creativecommons.org/licenses/by/4.0/ (stated at https://esahubble.org/copyright/); the full credit must be shown; NASA's own copy: https://science.nasa.gov/asset/hubble/hubble-ultra-deep-field-image-reveals-galaxies-galore/ | 3100x3100 JPEG (Wikimedia Commons copy of the March 2004 release) resized to 1400x1400 WebP |
| `adb1b774966e53e636f763b73018e47c7f1ea43e62fbf32f228b340fd732e5f0.webp`, `86196b445b9625808751b98cfa716a616d78cf591572f93ca83da6417fb794f1.webp` | Poster of the starfield component, dark and light | Own work made for the demo | A still of the site's own component running in the exported site | Own work, Apache-2.0; nothing from a third party | None |
| `cb033eaf2d91ec1d97f9c09fa30665c9a6c68f491a014c6e347aaedc3b1a601c.webp`, `fc4a5fbd93d5488245514c631fba9799edc77adb9dab67d38074d07634c77500.webp` | Poster of the specks component, dark and light | Own work made for the demo | A still of the site's own component | Own work, Apache-2.0; nothing from a third party | None |
| `f74dc7cc5be29f41f8ed7e8432592dbbaaaa42cf807aaf405f8fc208d3506297.webp`, `72e06ffd2ad57e3661b569526a4aed03267b8461e5e89d1251b0cbac49079c4a.webp` | Poster of the receipt-printer component, dark and light | Own work made for the demo | A still of the site's own component | Own work, Apache-2.0; nothing from a third party | None |
| `996675ea94a8d7dce0b5c434f3a7ce0afd26a76f3753f81560840a7adb0bab57.webp`, `d7aceb85e4e73254261686ba7818509048b7c9b9577794478f503650b705a79a.webp` | Poster of the orbit-constellation component, dark and light | A still made for the demo; it shows crops of the pictures of the rows above, among them the Hubble Ultra Deep Field | A still of the site's own component | Own work, Apache-2.0 (the still); the pictures in it keep the credit and status of their rows above, including CC BY 4.0 for the Hubble Ultra Deep Field | The pictures appear small, as the component draws them |
| `3c8bd2d2f37614e9647d66aa469d3fe0cfcd84301ae424bb0a34733508c2283a.webp`, `56cca781ae81adbd3a42d60390aacc6aff84c96c43df7093eb27c5971d750f91.webp` | Poster of the tile-cut component, dark and light | A still made for the demo; it shows a NASA picture of the rows above | A still of the site's own component | Own work, Apache-2.0 (the still); the picture in it keeps the credit and status of its row above (NASA/JPL-Caltech/MSSS, NASA content) | The NASA picture appears cut into tiles, as the component draws it |
| `f9eed231b2a45d29e91348bbb0595f22d3837f0c0b001041406a961e3ea09141.png` | Lowlight site icon, 256 px | Own work, drawn with Pillow for the demo | None, drawn here | Own work, Apache-2.0; nothing from a third party | None |
| `frontend/public/demos/lowlight/cover.webp` | The card picture: the top of the Lowlight home page | Own work: a screenshot of the demo site. It shows no photograph | None | Own work, Apache-2.0; nothing from a third party | A 1440x900 screenshot cropped to its top 1440x810 and resized to 640x360 WebP with Pillow |

Looking Back (`demo/sites/looking-back.zip`): 10 image files in `assets/`, and the card picture. The Form.md rows come from the NASA Image and Video Library; credit NASA with the centre in brackets.

| File | Title or subject | Author or credit | Source page | Licence or status as the source states it | Changes |
| --- | --- | --- | --- | --- | --- |
| `a9d3e2fbb94e86f8f6f6f921ebb4b4720c31733fc05a7c5cb1f71d491a1a361c.webp` | Earthrise, Apollo 8 (AS08-14-2383) | NASA/William Anders | https://www.nasa.gov/image-detail/moon-landing-l-7-months-10-apollo-8-earthrise-photo-as08-14-2383 | No licence text; credit line "Image Credit: NASA/William Anders"; NASA content | 3000x1971 JPEG resized to 1400x920 WebP |
| `07bd8a6730b2ece0470109cf888df9df0f5e989d6f3fa9def50322a03362ac3c.webp` | A Breathtaking Earthset from Orion (art002e021278), 6 April 2026 | NASA | https://images.nasa.gov/details/art002e021278 | No licence text; photographer field "NASA"; NASA content | 5568x3712 JPEG resized to 1400x933 WebP |
| `e422ff4c83b944b85a4de501d9f388745fce726dc7021237af70fdda97744239.webp` | Solar System Portrait, Earth as Pale Blue Dot (PIA00452), Voyager 1 | NASA/JPL-Caltech | https://science.nasa.gov/photojournal/solar-system-portrait-earth-as-pale-blue-dot/ | No licence text; credit line as given; NASA content | 453x614 JPEG resized to 334x453 WebP |
| `fde102acb7e70b75710cf2549964c499097a782c68fe6a7d24492acbe94a6d76.webp` | The Day the Earth Smiled (PIA17172) | NASA/JPL-Caltech/SSI | https://science.nasa.gov/photojournal/the-day-the-earth-smiled/ | No licence text; credit line as given; NASA content | 9000x3500 JPEG resized to 1600x622 WebP |
| `f8414ced3bf6ef50809b6442cdafcff6dd41ff95b0e6e46d1503a2bbb9399b0a.webp` | View of the Earth seen by the Apollo 17 crew (as17-148-22727), 1972-12-07 | NASA (JSC) | https://images.nasa.gov/details/as17-148-22727 | No licence text on the record; NASA content | Resized to at most 900 px on the long side and converted to WebP (900x900) |
| `7fdaa80d0e0633d32a1ca3c77808399e0c904fcfc1de69861d580ec9fafe422d.webp` | Apollo 10 view of the Earth (as10-34-5013), 1969-05-18 | NASA (JSC) | https://images.nasa.gov/details/as10-34-5013 | No licence text on the record; NASA content | Resized to at most 900 px on the long side and converted to WebP (900x900) |
| `aa973715ed510102f4255313796fb4b37f6f377cf6783e50ca42236d6fb55784.webp` | Gulf Coast from Atchafalaya Bay to Apalachicola seen from Gemini 11 (s66-54563), 1966-09-14 | NASA (JSC) | https://images.nasa.gov/details/s66-54563 | No licence text on the record; NASA content | Resized to at most 900 px on the long side and converted to WebP (893x900) |
| `703fbb02c672345ac940bae6edc988feeb3b4000c0b82d78c5e4b610008bc402.webp` | GEMINI-TITAN (GT)-9 - EARTH-SKY - AUGMENTED TARGET DOCKING ADAPTER (ATDA) (s66-37923), 1966-06-06 | NASA (JSC) | https://images.nasa.gov/details/s66-37923 | No licence text on the record; NASA content | Resized to at most 900 px on the long side and converted to WebP (900x900) |
| `7d6de2d25625c91f596a4654b84dabf0d717b1f006af3976f31a7c7ef7ce4240.webp` | GEMINI-TITAN (GT)-10 - EARTH SKY - DOCKING - IN-SPACE (s66-46249), 1966-07-18 | NASA (JSC) | https://images.nasa.gov/details/s66-46249 | No licence text on the record; NASA content | Resized to at most 900 px on the long side and converted to WebP (876x900) |
| `9702623b49c69b2b0c09e9b20edcb4452b5ef59ec81b5bd1f437dc9d50a344ae.png` | Looking Back site icon, 256 px | Own work, drawn with Pillow for the demo | None, drawn here | Own work, Apache-2.0; nothing from a third party | None |
| `frontend/public/demos/looking-back/cover.webp` | The card picture: the top of the Looking Back home page. It shows the Apollo 17 picture of the row above | A screenshot of the demo site; the photograph in it is NASA (JSC) | https://images.nasa.gov/details/as17-148-22727 for the photograph | Own work, Apache-2.0 (the screenshot); the photograph keeps its status: no licence text on the record, NASA content | A 1440x900 screenshot cropped to its top 1440x810 and resized to 640x360 WebP with Pillow |

Harbour Ferries (`demo/sites/harbour-ferries.zip`): 1 image file in `assets/`, and the card picture. The site uses no photograph; its map and logo are inline SVG written for the demo.

| File | Title or subject | Author or credit | Source page | Licence or status as the source states it | Changes |
| --- | --- | --- | --- | --- | --- |
| `4f9d2b2f49e082ca924ab65505f8ce44ff14797894c574fd1049308e27da35c1.png` | Harbour Ferries site icon, 256 px | Own work, drawn with Pillow for the demo | None, drawn here | Own work, Apache-2.0; nothing from a third party | None |
| `frontend/public/demos/harbour-ferries/cover.webp` | The card picture: the top of the Harbour Ferries home page | Own work: a screenshot of the demo site. It shows no photograph | None | Own work, Apache-2.0; nothing from a third party | A 1440x900 screenshot cropped to its top 1440x810 and resized to 640x360 WebP with Pillow |

Northwind Notes (`demo/sample-site.zip`, unpacked in `demo/sample-site/`): 9 image files in `assets/`, and the card picture. Every one was drawn for the sample with a Python script using Pillow (rounded rectangles and text set in DejaVu Sans; no photograph, no screenshot of another product, no stock image) and is the owner's own work, Apache-2.0.

| File | Title or subject | Author or credit | Source page | Licence or status as the source states it | Changes |
| --- | --- | --- | --- | --- | --- |
| `f3119a1025aaae4445e18e59a28053d9d5c0a5c761d9390cf9fc5f33dc0645e7.webp` | Notes window, dark | FormPublisher project | None, generated here with Pillow | Own work, Apache-2.0 | None |
| `0d8c8f6a3de880ba0aefe53966ab2ab1b05be126e9d166d48215233c13c45913.webp` | Notes window, light | FormPublisher project | None, generated here with Pillow | Own work, Apache-2.0 | None |
| `289750288b82a4e90d2f1ef234ce998e17939c7f9b4cd0ab6dbe0ed1da55e057.webp` | Notes board, dark | FormPublisher project | None, generated here with Pillow | Own work, Apache-2.0 | None |
| `dca2d4522b477684cd568f9a3b30e6b7eceebd3bffa0384a16a9d0a87e7d220f.webp` | Notes board, light | FormPublisher project | None, generated here with Pillow | Own work, Apache-2.0 | None |
| `d7d316c70b86deb53c0840d24493e777c2f2f1f0268b556ffed404ecb884fd42.webp` | Editor with source and preview, dark | FormPublisher project | None, generated here with Pillow | Own work, Apache-2.0 | None |
| `49e8b23f2b857a60d28b74e4079405d681d4bb6368951936c4087ea66c8e1332.webp` | Editor with source and preview, light | FormPublisher project | None, generated here with Pillow | Own work, Apache-2.0 | None |
| `804db4ff396f33457834bf718b51613bc3e9c4bc9bbd65f966019dbff12fd7a3.webp` | Export view with three progress bars | FormPublisher project | None, generated here with Pillow | Own work, Apache-2.0 | None |
| `9fc1e58401e68cf494ccf91886506414015d54065ef6408933370d1a73a758b0.webp` | Bar chart of notes written each week, dark | FormPublisher project | None, generated here with Pillow | Own work, Apache-2.0 | None |
| `f4779dace2030ee2561c832d6d0a63d25ed90859a3ea52cc51f1003139f6b361.webp` | Same chart, light | FormPublisher project | None, generated here with Pillow | Own work, Apache-2.0 | None |
| `frontend/public/demos/northwind/cover.webp` | The card picture: the Notes window, dark | FormPublisher project | None, made from the first row's file | Own work, Apache-2.0 | The 1600x1000 drawing cropped to its middle 1600x900 and resized to 640x360 WebP |

The offline demo in `demo/` also holds four copies of the FormPublisher mark (`demo/assets/formpublisher.webp`, `formpublisher@2x.webp`, `formpublisher-light.webp` and `formpublisher-light@2x.webp`), the owner's own art listed under "Shipped in the app". Like every FormPublisher icon, they are GPL-3.0-only with this repository, as the "Shipped in the app" row says.

Trademarks: Form app names belong to nodemode. Other product names mentioned in the docs belong to their owners.
