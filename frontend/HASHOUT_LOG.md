# HASHOUT_LOG · frontend · formpublisher

The living log of the FormPublisher frontend. Read it before editing `frontend/`. The code carries no comments; the reasons live here, one entry per file.

Current build version: v0.2.2
Last updated: 2026-11-10 · Phases 37 and 39: the window load measured with no shift, and every window word translates (the translate="no" audit and part18)

---

## Org-navi-map

```
frontend/
├── index.html            pre-paint theme boot, font preloads, style links, #app, #overlay-root, #toast-root
├── package.json          pinned dependencies, scripts dev, build, preview, typecheck
├── tsconfig.json         FormDeck's strict settings
├── vite.config.ts        port 5280, preview 5281, host false, /api proxy with ws to 8280
├── HASHOUT_LOG.md        this file
├── public/
│   └── splash.html       startup splash, window.formpublisherSplashDone()
└── src/
    ├── main.ts           boot order: language, app, ready (capped), reveal
    ├── app.ts            SHELL template, state, App API, live wiring
    ├── app-api.ts        typed App, AppState, Mounts
    ├── events.ts         typed document events, emit and on
    ├── api.ts            typed engine client, normalisers, live socket with reconnect
    ├── version.ts        VERSION
    ├── i18n/
    │   ├── index.ts      runtime and DOM walker
    │   ├── keys/en.json  every English UI string
    │   └── locales/      one folder per language, empty for now
    ├── styles/           fonts, tokens, base, shell, components, scrollbars
    └── ui/               dom, icons, brand, themes, tabs, routes, resizers, path-dialog
```

## Table of contents

1. [index.html](#indexhtml)
2. [src/app.ts](#srcappts)
3. [src/app-api.ts](#srcapp-apits)
4. [src/events.ts](#srceventsts)
5. [src/api.ts](#srcapits)
6. [src/i18n](#srci18n)
7. [src/styles](#srcstyles)
8. [src/ui/dom.ts](#srcuidomts)
9. [src/ui/brand.ts](#srcuibrandts)
10. [src/ui/themes.ts](#srcuithemests)
11. [src/ui/tabs.ts, routes.ts, resizers.ts, path-dialog.ts](#srcui-widgets)
12. [public/splash.html](#publicsplashhtml)

---

## index.html

Reads `nodemode_ui_settings` before first paint and writes the profile variables on `<html>`, density class `fp-density-*`, `has-native-menus` on Tauri macOS, and `theme-light` on the body the moment it exists. `#app` stays `visibility: hidden` until `body.app-ready`. Muted text values use the final `themes.ts` values (FormDeck's boot table differs from its theme table and shifts colour after JS runs; here they agree so nothing changes at hydration). Font preloads are rewritten by Vite in a build.

## src/app.ts

The shell is built once with `mountOnce`; every later change patches text, classes, attributes and keyed lists. Tabs persist in `formpublisher.tabs` and paint synchronously from storage, so the first frame already has the tab, title and route field space. Reveal waits for health, sites and the active site (capped at 900 ms in `main.ts`). Seams: `getApp()`, `Mounts`, and cancelable events `fp:theme-toggle`, `fp:new-tab`, `fp:pick-folder` that let a later agent replace the built-in behaviour.

## src/app-api.ts

Types only: the public App surface, read-only state snapshot and the mount points.

## src/events.ts

One typed event map on `document`. `emit(name, detail, cancelable)` returns false when a listener called `preventDefault()`.

## src/api.ts

Normalisers accept the engine's record shape (`routes` count, `bytes`, `importedAt`, `source{kind,path|url}`) and tolerate renamed fields. The live socket reconnects with 0.5 s doubling to 8 s.

## src/i18n

FormDeck's runtime with key `formpublisher_lang`. Parts are `keys/<part>.json` arrays paired with `locales/<code>/<part>.json`; a value may be keyed by index or by the English string. Missing locales fall back to English. Elements marked `translate="no"` (site names, paths, versions) are skipped.

## src/styles

`tokens.css` carries FormDeck's tokens under `--fp-*` sizes, and the single z-index scale. No rule uses a numeric z-index. `base.css` holds the dark and light brand-art swap (`.fp-art-dark`, `.fp-art-light`, keyed on `body.theme-light`). `scrollbars.css` hides all scrollbars.

## src/ui/dom.ts

`revealApp()` loads the four font faces, decodes every image in `#app` (both marks, not only visible ones, so the first theme swap never decodes), waits two frames, adds `app-ready`, then calls `app_ready` in Tauri.

## src/ui/brand.ts

`brandMark(size)` returns two `<img>` with 1x and 2x srcset and fixed width and height, so the theme swap is a class change.

## src/ui/themes.ts

FormDeck's 14 profiles, density, accent and `setTheme`. `nextToggleTheme` flips studio and light.

## src/ui widgets

`tabs.ts` keyed tab list with middle-click close; `routes.ts` listbox with roving tabindex and arrow, Home, End, Page keys; `resizers.ts` drag and edge-tab collapse state persisted in `formpublisher.layout`; `path-dialog.ts` the temporary folder path field a Tauri dialog will replace.

## public/splash.html

FormDeck's splash re-authored: 360 by 200 window content, `mark-144.png`, "Starting FormPublisher", `window.formpublisherSplashDone()`.

---

## Phase 3 window: commands, menus, palette, dialogs, toasts, Preferences, Home (2026-11-10)

### src/ui/commands.ts
`Command {id, label, keys, icon, run, enabled, checked, group, menu, description, mutates, risky, native}`. `Commands` holds the registry, applies rebinds from `formpublisher_shortcuts` on `add`, `setKeys` steals a combo from its previous owner and persists. `comboOf` names modifiers Alt, Shift, Mod in that order (Mod is Cmd on macOS, Ctrl elsewhere) and reads `e.code` so Shift does not change the key. One `keydown` listener (`installShortcuts`) ignores typing in fields unless the combo has Mod, always `preventDefault`s a matched combo and runs only when enabled. `native: true` (Edit commands) shows keys but leaves the keystroke to the browser. Command descriptions are metadata for agents and are not translated.

### src/ui/chrome.ts
Single wiring point called from `main.ts` before `revealApp()`: builds Home (visible when no tab is active), the registry, menus, shortcuts, toast and drop wiring. Palette, Preferences and Shortcuts are built on first use, once. Hooks: `fp:palette`, `fp:preferences`, `fp:home` run their commands; `fp:theme-toggle` is cancelled and runs `view.theme` with the target; `fp:new-tab` is cancelled and shows Home (the tab beneath stays); `fp:notice` shows a toast. A .zip dropped anywhere imports through `app.importZip`, one after another. Commands: file.open-zip, file.open-folder, file.import-formweb, file.new-window, file.close-tab, edit.undo, edit.redo, edit.cut, edit.copy, edit.paste, edit.select-all, view.home, view.palette, view.theme, view.density-compact, view.density-regular, view.density-comfortable, view.toggle-routes, view.toggle-inspector, view.toggle-bottom, view.problems, view.console, view.network, site.reload-routes, site.remove, site.reveal-folder, app.preferences, help.shortcuts, help.about, help.docs. `site.reload-routes` reuses `app.openSite`, which clears the route list for a moment (user-initiated). `site.reveal-folder` calls `plugin:shell|open` on `<data folder>/sites/<id>`; the Tauri capability currently allows only URLs there, so the Rust side needs a path scope or a reveal command.

### src/ui/dialogs.ts, toast.ts
`Dialog` builds its scrim once, hidden, in `#overlay-root`; `open` and `close` flip `hidden`, trap Tab, restore focus, and stop key events reaching the global handler. `confirmAction` is one shared dialog. Toasts follow FormDeck: 3600 ms, 6000 ms for errors, at most 4, identical text refreshes its timer (compared on the English text so translation does not break it).

### src/ui/menu.ts, native-menu.ts
`PopupMenu` and `MenuBar` after FormDeck's, glass surface from `.fp-menu`; added arrow, Home, End, Left, Right, Escape and Enter navigation, items keep tabindex -1, pointerdown on the panel is cancelled so the focused field keeps focus for Edit commands, and the previous focus is restored before a command runs. `NativeMenus` mirrors FormDeck (app menu, Window menu, Help menu, text-edit predefined items while typing); `wantsNativeMenus()` is false outside Tauri on macOS, and a failed build removes `has-native-menus` and falls back to the in-window bar.

### src/ui/command-palette.ts, shortcuts-dialog.ts
Palette rows are built once for every command and only reordered and shown or hidden when filtering; disabled commands are hidden; the list has a fixed height of 12 rows. Shortcuts dialog lists every command with its combo, grouped, patched on open.

### src/ui/preferences.ts
General (26 languages, reload on change), Interface (all `THEMES` profiles, 15 today, preset and custom accent, intensity, density), FormWeb (PUT `formwebUrl`, Test saves a changed address then GET `/api/formweb/status`), About (version, engine, GPL-3.0-only, Copyright 2026 NodeAgentc, Inc.). Fixed height so switching sections never resizes the dialog.

### src/ui/home.ts
`.fp-home` appended to `#app` before reveal, `inert` on the shell while open. Skeleton card until the first `fp:sites-changed` (or engine down), then cards or the empty card at the same height. FormWeb status refreshes on show, on settings or engine events and every 15 s while open. The engine has no trash listing endpoint, so Trash shows only the explanation. Nav width and collapse persist in `formpublisher.homeNav` and `formpublisher.homeNavHidden`.

### src/ui/icons-extra.ts, styles/overlays.css, i18n/keys/part02.json
Extra icons are merged into `ICONS` at import. `overlays.css` holds menu, dialog, toast, palette, shortcuts, Preferences and Home rules. `part02.json` is picked up by the existing glob. `base.css`: `#overlay-root` now sits at `--z-overlay` and `#toast-root` at `--z-overlay-modal` so dialogs and toasts rise above Home (`--z-home`).

## Phases 4 to 6: preview, checks panel, packages and builds · v0.1.1 (2026-11-10)

### src/ui/preview.ts, src/ui/toolbar.ts, src/api-host.ts, src/styles/preview.css
Two stacked frames on the host origin (`allow-scripts allow-forms allow-same-origin allow-popups`, `no-referrer`); Chrome logs its usual warning that this sandbox combination can escape, which is expected because the frame's origin is the site host, not the window's. A navigation loads the hidden frame, which waits at `opacity: 0` (not `visibility: hidden`, so a hidden cross-origin frame is not render-throttled); after `load` plus two animation frames it becomes the front frame, and the old one stays visible for two more frames before going idle, so the stage never shows a blank frame. Probe messages from the loading frame are buffered and judged against the acceptance rule at the swap; accepted ones are re-emitted as `fp:probe` with `siteId`. Routes are compared after stripping query, hash, trailing slash and `index.html`, so a `nav` message never triggers a second load. Size and zoom changes resize the box and never reload; theme, motion and network remount and reload, and Reload remounts, bumping the generation. The toolbar uses selects to fit the 44 px bar; editing W or H switches the device to Custom; its state persists in `formpublisher.preview`. `api.ts` does not export its request helper, so `api-host.ts`, `api-checks.ts` and `api-builds.ts` each carry a small copy that uses `ApiError`.

### src/ui/routes.ts
Rows are fixed at 50 px with a 64 by 40 thumbnail box that is always present; an `img` is added only when a thumbnail exists and fades in on load. The dot follows `fp:checks`; the route-row rules live in `preview.css` under `.fp-route-list .fp-route`, so the older `.fp-route` rules in `shell.css` are partly unused.

### src/ui/panel.ts, src/api-checks.ts, src/styles/panel.css
Each page is filled once; lists sit in an absolutely positioned container under a 34 px toolbar and are patched by key; empty states are overlays toggled in place. Console, Network and live problems are kept per site in a `Map`, so switching tabs keeps them; lists cap at 500 entries and follow the end only when already near it. Live problem ids are route plus a text hash, so repeated errors collapse into one row; CLS and overflow are one row per route. Problem routes from the engine (`/index.html`) and the strip's route paths (`index.html`, from FormWeb's `routes.json`) are matched by `routeFor`, which strips leading slashes, `index.html` and trailing slashes, for the status dots, the thumbnails and row clicks. A deep-run guard disables both buttons until `checks.done`, with a 15 minute fallback. The site's revision comes from `GET /api/sites/<id>` because `Site` in `api.ts` has no revision field.

### src/ui/package-sheet.ts, src/ui/builds.ts, src/api-builds.ts, src/styles/package.css, home.ts, chrome.ts
The sheet, the Builds page and the Inspect and Compare dialogs are each built once and every block reserves its height before data arrives. `el()` returns only the first root element, so each multi-block dialog body is wrapped in one `fp-pkg-wrap`. Compare orders the two chosen builds by list order so the older one is `a`. The sticky file header uses `--z-raised`. Commands: `site.package` (Shift+Mod+B, File), `site.check` and `site.check-deep` (Site), `view.builds` (View, opens Home on Builds). Dropping a `.fweb` file imports it like a zip.

## Phases 7 to 9: Publish sheet, receive toast, demo and tour · v0.1.2 (2026-11-10)

### src/ui/publish-sheet.ts, src/api-publish.ts, src/styles/publish.css, toolbar.ts, chrome.ts, package-sheet.ts, events.ts, toast.ts
The sheet extends `Dialog` with a fixed height (`min(86vh, 780px)`), `scrollbar-gutter: stable` and skeleton host cards swapped for the real ones in one frame, so opening, building, preparing and rendering results cause no layout shift. Results and ticks are kept per build in memory and the ticks in localStorage. `publish.open` is registered in `chrome.ts`, where the command registry lives (`commands.ts` only holds the class), with no shortcut because Ctrl+Shift+U is taken by Linux input methods. `toast.ts` takes an optional action, used by the receive toast's Open. Server problem text from verify is shown as `path: problem`, not translated.

### src/ui/home.ts, src/app.ts, src/ui/hint-strip.ts, src/api-demo.ts, src/styles/demo.css
Home refreshes Recent on `sites.received`; a new card pushes older ones down, the one layout shift left, inherent to newest-first order. The Demos row's card calls `POST /api/demo/sample` (idempotent) and opens the site. The tour strip is absolutely positioned at the top of `.fp-main`, walks four steps and stores `formpublisher.hints = done`. Keys for the sheet and toast are in `keys/part04.json`, for the demo and tour in `keys/part05.json`.

## Phases 10 to 12: model files, revisions and receive settings · v0.1.3 (2026-11-10)

The executor spec is `TURN_D_SPEC.md` in the 0.1.3 planning sidecar.

### src/ui/publish-sheet.ts, src/api-publish.ts, src/styles/publish.css
The sheet has a "Keep FormWeb's model files" checkbox, off by default and remembered in `localStorage` as `formpublisher.publish.model` (reads and writes in try/catch, falling back to off). It is disabled while busy or before a build exists and is sent as `includeModel` with prepare. Each host card gains a note row listing what was left out; the row is hidden when empty, so cards keep their height. Keys are in `keys/part06.json`.

### src/ui/revisions.ts, src/api-revisions.ts, src/styles/revisions.css, src/ui/home.ts, src/ui/panel.ts
`RevisionsView` renders the revision list and the diff of any two rows; `RevisionsDialog` wraps it for Home, where each site card carries a revisions chip (click, Enter or Space opens the dialog without opening the site). The site panel has a Revisions tab with a count badge; it loads only while visible (a `MutationObserver` on the page's `hidden`) and reloads on `fp:sites-changed`. Home's skeleton card carries the chip's space, so cards do not move when the counts arrive; CLS measured 0 opening the dialog and the tab.

### src/ui/preferences.ts
Two rows, "Check a site when it arrives" and "Build a site when it arrives", write `receive.autoCheck` and `receive.autoBuild` through the settings route, and a failed save puts the box back. Keys for the revisions and receive strings are in `keys/part07.json`; parts 06 and 07 are translated into all 25 locales, with plural forms for pl, cs, ru and uk.

## Phases 13 to 15: Trash, desktop folder panel and reveal, shortcut rebinding · v0.1.4 (2026-11-10)

The executor spec is `TURN_E_SPEC.md` in the 0.1.4 planning sidecar.

### src/ui/trash.ts, src/api-trash.ts, src/styles/trash.css, src/ui/home.ts
`TrashPage` follows the BuildsPage pattern and replaces the explanation-only note. Three skeleton rows and the empty state share a 120 px minimum, so the list arriving moves nothing. Rows show a kind icon, label, kind, moved time and size, with Restore and Delete for good; Delete and Empty Trash confirm through `confirmAction`; 409 reasons from the engine show as error notices; a restored site also calls `app.refreshSites()`. It refreshes on `trash.changed` and the remove and create events, only while visible. Keys in `keys/part08.json`. Home's Recent grid still shifts when a new site arrives, as noted in v0.1.2.

### src/app.ts pickFolder, src/ui/chrome.ts site.reveal-folder
In the desktop app Open Folder calls `invoke('plugin:dialog|open', { options: { directory: true, multiple: false, title } })` from `@tauri-apps/api/core`, because the plugin's npm package is not a dependency; the command and option names come from tauri-plugin-dialog 2.8.4 (`api-iife.js`, `src/commands.rs`). Cancel returns null; a failure falls back to the typed path dialog, which the browser keeps. Reveal Site Folder builds `<home>/sites/<id>` from `GET /api/settings` and calls the shell's `reveal_path`; its refusal string is rethrown so `commands.onError` shows it.

### src/ui/commands.ts, src/ui/shortcuts-dialog.ts, src/styles/shortcuts.css, src/ui/native-menu.ts
Change records through a capture-phase keydown on the dialog scrim, because the Dialog's own bubbling handler stops propagation and closes on Escape; nothing runs while recording. `rejectCombo` refuses combinations without a modifier (bare F1 to F12 allowed), a static list the browser or system keeps (browsers cannot report them), and the native text commands, whose rows cannot change. A combination held elsewhere names the other command with Replace or Cancel in a fixed 34 px note bar, and Reset keeps its column with `visibility:hidden`, so no state shifts layout. `remember` drops an override equal to the default, so Reset leaves storage clean. `commands.onChange` repaints the dialog and rebuilds the desktop app's native menus so their accelerators follow; the in-window menus and the palette re-read keys when opened. Keys in `keys/part10.json`; parts 08 and 10 are in all 25 locales. `builds.ts` now refreshes on `builds.removed`, the event the engine emits (it listened for `builds.deleted`).

Checked: `npm run build`. In headless Chrome at 4x CPU the Trash page listed a removed site without a click and restored, deleted and emptied with CLS 0; Open Folder was rebound, ran from its new keys, showed in the palette, survived reload, and conflicts and resets behaved as above with CLS 0. Not run: the system folder panel itself (no portal under xvfb) and the native menu rebuild on macOS.

## Phases 16 and 17: the Trash origin dialog, Recent sites and Home under the title bar · v0.1.5 (2026-11-10)

The executor spec is `TURN_F_SPEC.md` in the 0.1.5 planning sidecar.

### src/api-trash.ts, src/ui/trash.ts, src/styles/trash.css
`failure()` turns a 409 whose `code` is `origin-unknown` (top level or inside `detail`) into `OriginUnknownError`, and `restore(entry, origin?)` posts `{origin}`. Only that error opens `OriginDialog` ("Where does it go"): the kind's folder (`TRASH_ROOT`: `sites/`, `builds/`, `keys/`, `prepared/`) is a fixed read-only prefix, the name is typed (a key gets `.pem` if missing), Enter or Restore retries, and the engine's refusal shows inline in a reserved 36 px line with the dialog kept open. Other 409s stay notices.

### src/ui/home.ts, src/styles/recent.css
Each Recent grid has a 32 px notice row above it, always reserved: `visibility: hidden` when idle with its Show button disabled (so it cannot take focus), visible with `.is-on`. `paint(resort = false)` keeps the displayed order while a Recent list is on screen (`recentOnScreen()`: Home open, loaded, on Start or Recent sites), counting new ids into "N new sites arrived" while existing cards still update in place; Show, `select()` and `show()` call `paint(true)`. The button comes before the text because text-first moved the button (CLS 9e-6). Off screen the lists update as before. This ends the shift noted under Phases 7 to 9. Keys in `keys/part11.json`, in all 25 locales.

### src/styles/overlays.css `.fp-home`, src/ui/home.ts `lock`
`.fp-home` was `position: fixed; inset: 0` (z-home 10000) over the whole window while `home.ts` made the whole app root inert, so the in-window menubar under it could not take a click (`elementFromPoint` on File returned the Home brand). Home now starts at `var(--fp-titlebar-h)` and `Home.lock(on)` makes every `.fp-app` child inert except `.fp-titlebar`, so the brand, menubar, theme and Preferences stay live above Home and Home's content sits one title bar lower (38, 44 or 50 px by density). The brand and nav rules are unchanged.

Checked: `npm run build`. In headless Chrome at 1280x800 and 4x CPU, two sites received over `/api/receive/formweb` with Recent visible left every card still, showed "2 new sites arrived" and gave CLS 0; Show re-sorted newest first and cleared the notice; a real mouse click opened the File menu in dark and light; an unparseable trash entry opened the dialog, `../evil` was refused inline and a valid name restored it; no page errors.

## Phases 19 and 21: ApiError codes and the Trash origin dialog for every kind · v0.1.6 (2026-11-10)

The executor spec is `TURN_G_SPEC.md` in the 0.1.6 planning sidecar.

`api.ts`: `ApiError` carries `code`, from the answer's body or, when absent, from the status (the same defaults as the engine's `services/codes.py`, plus `unreachable` for status 0); `failure()` reads it. `api-host.ts`, `api-publish.ts`, `api-builds.ts` and `api-revisions.ts` pass it through the same way. `api-trash.ts` already read `code` (or `detail.code`) and is unchanged. Notice text is the detail as before, so the window reads the same.

`ui/trash.ts`: `shapeError(kind, name)` (with `SITE_ID`, `HEX12`, `HEX16`) checks the typed name in `OriginDialog.submit` before any request, with the four part12 sentences; the engine applies the same rule (`place-invalid`), so the client check only saves a round trip. The error line already reserves its 36 px, so a refusal shifts nothing. Key entries with a readable `entry.json` restore without the dialog; a damaged one answers `entry-damaged`, which the dialog cannot fix, so it stays a notice.

Checked: `npm run build`. Headless Chrome at 1280x800 on a lab data folder with an unparseable build, prepared folder, site and key: wrong names were refused inline for each kind, the right ones restored, the build downloaded (377,852 bytes), the prepared folder verified (4 files), the key signed and verified; CLS 0; only the expected 409 console lines. `docs/images/trash-origin-dark.webp` and `-light.webp` show the dialog with an inline refusal.

## Phase 23: the window acts on codes · v0.1.7 (2026-11-10)

The executor spec is `TURN_H_SPEC.md` in the 0.1.7 planning sidecar.

`ui/notice-step.ts` (new): `refuse()`, `refuseStep()` and `stepFor(code)`, which maps a code to one action: Open the trash for `build-missing` or `site-missing`, only after `/api/trash` shows the item there; Try again for `formweb-unreachable`; Show the running check for `check-running`; Open the manual at `#error-codes` for `core-missing`; Enter the passphrase for `passphrase-required` or `passphrase-wrong` when signing. `events.ts`: `fp:notice` carries optional `code`, `ref` and `run`. `ui/chrome.ts` resolves the step and shows it through the existing toast action; `app.ts`, `ui/panel.ts`, `ui/package-sheet.ts`, `ui/publish-sheet.ts` and `ui/builds.ts` pass codes, and Sign clears the passphrase field after every attempt. `api-trash.ts` and `api-checks.ts` were dropping `code` and keep it now; `restore(entry, origin?, passphrase?)`. `ui/trash.ts`: `PassphraseDialog` (password field, autocomplete off, cleared after use, never stored) opens on `passphrase-required`, retries, and shows `passphrase-wrong` inline. `styles/overlays.css`: the action is 16.8 px high, the notice line height, so a notice is the same height with or without it. Nine keys in `i18n/keys/part13.json` and all locales.

Checked: `npm run build`. Headless Chrome against lab engines: each action appeared for its real refusal and did its step, keyboard reachable; `site-missing` was not seen live because the window closes a removed site first, and it runs the same code as `build-missing`. The trash dialog restored a locked key whose record was deleted, against the key rescue engine, with a wrong passphrase refused inline first; the passphrase was found only in restore bodies, not in local or session storage. CLS 0, notice heights 34.8 px and 51.6 px with or without an action, no page errors beyond the expected refusals. `docs/images/notice-action-dark.webp` and `-light.webp`.

## Phases 25 to 27: one restore dialog, Restore from the notice, the nginx line · v0.1.8 (2026-11-10)

The executor spec is `TURN_I_SPEC.md` in the 0.1.8 planning sidecar.

`ui/trash.ts`: `OriginDialog` and `PassphraseDialog` are one `RestoreDialog` (title Restore from the trash). It holds a place box and a passphrase box, always in the DOM, each with its own 36 px reserved error line; `ask(item, reason)` sets which are hidden and the lead text before `open()`, so no row appears while it is open. The place box shows on `origin-unknown` or for a non-key entry with no origin; the passphrase box for a key on `passphrase-required`. One `trashApi.restore(entry, origin, passphrase)` sends both; `passphrase-required` and `passphrase-wrong` go to the passphrase row, `place-taken` and `place-invalid` to the place row, and the passphrase is cleared on close, on every refusal and on success. `trash.restore` in the engine never asks for both today, since a key without a usable record is rebuilt without a place; the dialog still handles both.

`ui/notice-step.ts`: `StepHost.refreshSites`; `stepFor` matches trash rows of the code's kind by label or by the last part of their origin, exactly (the build id or site id the caller passes), instead of a substring. Exactly one match gives Restore, which runs `restoreFromNotice`: `trashApi.restore(entry)` with no origin, an ok notice Restored and the label, `refreshSites` for a site, then the caller's `run`. A refused restore calls `openTrash` and shows the refusal. Several matches, or only a loose match, keep Open the trash. `ui/chrome.ts`: `openTrash` first clicks the close button of any open dialog scrim in `#overlay-root`, because the Publish and Package sheets are modal and hid the Trash page. `ui/publish-sheet.ts` prepare and `ui/package-sheet.ts` verify and reproduce pass their own retry, so `formweb-unreachable` there also offers Try again.

`api-publish.ts`: `NginxCheck` and `VerifyReport.nginx`. `ui/publish-sheet.ts`: `nginxLine` turns it into one line (passed with the version, failed with nginx's first `[emerg]` or `[alert]` line, or not installed); the result card has a `data-f="nginx"` row, shown only for the nginx target, so its space exists before verify runs. `styles/publish.css`: `.fp-pub-nginx` is a fixed 18 px single line with an ellipsis. Six keys in `i18n/keys/part14.json` and all 25 locale folders.

Checked: `npm run build`. Headless Chrome against lab engines: a site entry with no origin restored with a typed place after an inline place-taken refusal, and a locked key with a damaged record restored after a wrong passphrase, in one dialog with the panel unchanged; a build removed under an open Publish sheet came back from the notice and the prepare ran again; a removed site came back and listed; a build whose place was taken opened the Trash page with the reason; the nginx line kept its top and height for passed and failed results. CLS 0 throughout, in dark and light. `docs/images/restore-dialog-dark.webp`, `-light.webp`, `notice-restore-dark.webp` and `-light.webp`.

## Phase 29: the Publish sheet in every language · v0.1.9 (2026-11-10)

The executor spec is `TURN_J_SPEC.md` in the 0.1.9 planning sidecar.

`i18n/keys/part15.json` (new, 65 keys): every description, command label, note and warning that `backend/app/targets/*.py`, `_common.py` (`netlify_style`, the `copy_site` fallback notes) and the nginx check can answer, written for the translator's matching rules in `i18n/index.ts` (exact keys first, then `{n}` patterns anchored at both ends, each placeholder matching any text; a trailing period or colon is retried without it). Paths, file names, counts, rule text, versions and nginx's own messages are `{0}` to `{2}`; the GitHub Pages splat note's `{2}` is filled with one of three keyed phrases (the site's base URL, the canonical link of the 404 page, the default), which the translator translates on their own. No component changed: the target description, the command labels, and the note and warning list items were already plain text outside `translate="no"`, and the command lines themselves sit in `.fp-pub-code` marked `translate="no"`, which the translator skips. The 25 locale folders hold `part15.json`, es-MX and fr-CA as full maps; languages that inflect keep counts and names standing alone.

Checked: three FormWeb exports (a 404 page with exact and splat rules, an older export with only `404/index.html`, no 404 page) prepared on all six targets gave 52 distinct strings and a direct run of the target modules over rare cases 61, each matching exactly one key under the translator's rules (P2); the director's run matched all 45 strings one prepare answered and found all 65 keys in all 25 folders with their placeholders; `npm run build`.

## Phase 32: verify in every language · v0.2.0 (2026-11-10)

The executor spec is `TURN_K_SPEC.md` in the 0.2.0 planning sidecar.

`ui/publish-sheet.ts`: the verify problem `li` loses `translate="no"`, so the row (one text node, `path: problem` as `publishApi.verify` builds it) reaches the translator; the path and nginx's message are placeholders, so they stay as they are. `i18n/keys/part16.json` (12 keys): the five problem rows (`{0}: missing`, `{0}: hash differs from publish.json`, `{0}: extra file`, `{0}: differs from a fresh prepare`, `{0}: nginx -t: {1}`), the three verify refusals the sheet shows as its verdict, and the four nginx prepare notes; the verdicts and the nginx line were already keyed in earlier parts. All 25 locale folders hold `part16.json`.

Checked: every problem kind made for real on a lab engine gave 21 texts, each matching exactly one key; the director's run matched 48 strings (notes, warnings, labels and three real problem rows) to exactly one key each; CLS 0 with the CPU throttled 4x while failed verifies painted; `npm run build`.

## Every window word translates · v0.2.2 (2026-11-10)

`i18n/index.ts` is unchanged; the DOM translator already skips the whole subtree under `translate="no"` and an element's own title, placeholder and aria-label, so the audit was of the markers. About 75 were read. Names, paths, hashes, ids, commands, versions and URLs stay marked.

- `ui/package-sheet.ts`: the key select no longer carries the marker; only the options that show a key's name and fingerprint do, so "Choose a key" and "No keys yet" translate. `ui/publish-sheet.ts`: the same for the build select; only options showing a build's id carry it, so "No builds yet" translates.
- `ui/preferences.ts`: the language select keeps native names untranslated on its options while its label translates.
- `ui/hint-strip.ts` (the quick-tour step count), `ui/home.ts` (the FormWeb status line), `ui/toolbar.ts` (the width and height inputs), `app.ts` (the route field), `ui/trash.ts` (the place input) lose the marker; `ui/builds.ts` translates the file count in the Size cell.
- `i18n/keys/part18.json` (3 keys: "Choose a key", "No keys yet", "Signing key"), in all 26 languages.

Checked: no layout shift at window load, measured at 1440x900 and 1100x800, dark and light, English and German, with the CPU throttled 4x, in three data states, three runs each: every run CLS 0 with no entries. Turn L's 0.0007 did not reproduce, so nothing changed for it. `npm run build`.

## The publish sheet holds still, and host names translate · v0.2.3 (2026-11-11)

With three real builds and four prepared hosts at 4x CPU throttling, opening the publish sheet shifted the prepared-folders section, the model checkbox, the prepare note and the progress bar by 4 px (0.0003) in both sizes and themes: skeleton host cards were 84 px and a real card with a three-line description 88.4 px (commit 8d65622).

- `styles/publish.css`: host cards have a fixed 90 px height, and the name is one line, clipped.
- `ui/publish-sheet.ts`: host names pass through `t()` as text and as aria-label, while the name keeps `translate="no"`, so the generic "Static zip" translates and Netlify, Cloudflare Pages, Vercel, GitHub Pages and nginx stay as written. The callbacks no longer shadow `t`.
- `i18n/keys/part19.json` (1 key: "Static zip"), in all 26 languages, keeping zip as each locale writes it (commit eb9a8b6).

The language sweep: the built window was opened in all 25 other languages over every main surface (Home, the open site and its panels, menus, the command palette, Preferences, shortcuts, the package sheet, the publish sheet with a failed verify, the trash page). "Static zip" was the only interface word left in English.

Checked: at 1440x900 and 1100x800, dark and light, CLS 0 opening and filling, switching between builds (including one with nothing prepared), Prepare and two Verify runs; every part19.json loads as JSON with the key and a non-empty value; `npm run build`.
