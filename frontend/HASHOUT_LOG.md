# HASHOUT_LOG · frontend · formpublisher

The living log of the FormPublisher frontend. Read it before editing `frontend/`. The code carries no comments; the reasons live here, one entry per file.

Current build version: v0.8.0
Last updated: 2026-11-22 · v0.8.0, no window change; v0.7.0, Phase 72: the family's tokens, accent and controls, cards, resizable and foldable columns, Preferences panels for keys and checks, the agent dock; v0.6.0, Phase 71: the window key on every request, where a key's secret is kept, three verify states, key export and import, two lines about the network; v0.5.0, Phase 70: Help opens the bundled manual in the window and a failed deep check shows in Problems; v0.4.1, Phase 69: the 0.4.0 window text in all 26 languages, the guide stays English; v0.4.0, Phase 68: Templates, the Host it yourself guide and What to do with this folder; v0.3.4, no window change: package.json pins the Tauri command line as a dev dependency; v0.3.3, Phase 67: a language switch holds Preferences, the hint strip and the menubar still (the toolbar still shifts once, by decision), Import from FormWeb lists saved projects, the Problems tooltip is translated; Phase 66: the strings of the forms.local-address check and the Import notice that says a revision was added

---

## Org-navi-map

```
frontend/
├── index.html            pre-paint theme boot, font preloads, style links, #app, #overlay-root, #toast-root
├── package.json          pinned dependencies (the Tauri command line, @tauri-apps/cli 2.12.5, is a dev one; see src-tauri/HASHOUT_LOG.md), scripts dev, build, preview, typecheck
├── tsconfig.json         FormDeck's strict settings
├── vite.config.ts        port 5280, preview 5281, host false, /api proxy with ws to 8280
├── HASHOUT_LOG.md        this file
├── public/
│   ├── splash.html       startup splash, window.formpublisherSplashDone()
│   └── demos/            one cover.webp per demo card (lowlight, looking-back, harbour-ferries, northwind)
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

## Phase 43: Save as .fpub and Open takes .fpub · v0.2.4 (2026-11-11)

The window side of the .fpub format; the engine side is in `backend/HASHOUT_LOG.md` (commits c67ba28 and 2592b6f).

- `ui/builds.ts`: each library row gains a Save as .fpub button, an `archive` icon link beside Download, with `href` from `buildsApi.fpubUrl` (`/api/builds/ID/fpub`) and `download` set to `ID.fpub`; the engine's own header names the file `SITE-BUILD.fpub`. `styles/package.css`: the actions column is 120 px instead of 92 and is reserved before data arrives, so the third button does not widen the row when the list fills. `api-builds.ts`: `fpubUrl`.
- `app.ts` and `ui/chrome.ts`: Open (`Mod+O`), the file picker and the drop accept `.fpub` beside `.zip` and `.fweb` and send it through the existing import, with no new route; the drop refusal and the Open description name `.fpub`. `ui/home.ts`: the hero sentence names `.fpub`.
- `i18n/keys/part20.json` (31 keys) in the 25 other languages (commit 2592b6f): Save as .fpub, the Home hero, drop refusal and Open description sentences, and the engine's refusals when a .fpub is opened or saved (the sentences in `services/fpub.py`, with `{0}` and `{1}` for the version numbers and the entry name, so the translator matches them whole).

Checked: the builds library painted five builds with the link and download name in place, the actions cell unclipped and CLS 0 at 4x CPU throttling; `npm run build`. The director's exit run, in German: the builds library showed "Als .fpub speichern", the download started with a zip header, and Open took the .fpub.

## Phase 44: the publish sheet shows the kept verify result · v0.2.4 (2026-11-11)

The sheet used to keep verdicts in memory only (commit df07b7f).

- `api-publish.ts`: a prepared row carries `verified` (`ok`, `problems`, `nginx`, `at`), mapped from the engine's `verifiedAt`, and the verify answer carries `at`.
- `ui/publish-sheet.ts`: `verdictOf` builds a verdict from either a fresh verify or a kept one. When the prepared list loads and no prepare or verify is running, each host's verdict is set from `verified`, or deleted when there is none, so the verdict, its problem rows and the nginx line show again on opening, reopening and reload. The verdict row is now a `fp-pub-vrow` holding the verdict and a muted time (`fp-pub-vtime`, `translate="no"`, `fmtDate`); the time sits in the verdict row's existing 18 px slot, so nothing moves when a result appears. `styles/publish.css`: three lines for the row and the time.
- No new strings: the verdict texts, problem rows and nginx lines were already keyed in parts 12 to 16.

Checked: with two hosts failing and four passing, the verdicts, rows and times showed on first open, on reopening and after a reload; preparing a host cleared only its own result; CLS 0 on open with stored results at 1440 x 900 and 1100 x 800 at 4x CPU throttling; `npm run build`. The director's exit run: the kept results survived an engine restart and were cleared by the next prepare.

## Phase 45: the sweep at two more sizes, and a toolbar that stays in view · v0.2.4 (2026-11-11)

The window was swept in all 26 languages at 1100 x 800 and 760 x 640 and with a live switch in Preferences (English to German, English to Japanese, German to Japanese; the window reloads). No English word was left apart from names, file names and keycaps. The sweep found the open-site toolbar clipping its last controls in every language: Publish and Package at 1100 x 800, and up to eight controls plus the Problems bar's Run checks and Deep check at 760 x 640 (commit 778fa67).

- `styles/shell.css`: `.fp-options` is a size container (`container-type: inline-size`); its overflow and nowrap are unchanged.
- `styles/preview.css`: the route field's minimum is 96 px and the selects' 64 px. Below 1400 px of row the selects may shrink with an ellipsis; below 1240 px Publish and Package are icon-only, their label kept in the DOM as a visually clipped span so it stays the accessible name, beside the translated `title`; below 860 px the gap, the route field, the number inputs and the selects tighten.
- `ui/panel.ts` and `styles/panel.css`: Run checks and Deep check gain an icon, a label span and a `title` with the existing keys; the Problems bar is a size container whose buttons turn icon-only at 520 px and whose selects compress at 300 px.
- No new strings, no new z-index, the tab order is unchanged, and the 1440 x 900 row looks as before.

Checked: English, German, Finnish and Russian at 1440 x 900, 1100 x 800 and 760 x 640, with CPU 4x: no control outside its row and the row's scroll width equal to its width in all 12 cases; CLS 0 opening a site and while resizing between the sizes; `npx tsc --noEmit`; `npm run build`. Known: at 760 px the selects show only the start of their value, with the full label in their title; the bottom panel's tab strip cuts "Network" at 760 px.

## Phase 46: the bottom panel keeps every tab and count whole · v0.2.5 (2026-11-11)

At 760 x 640 the Problems, Console, Network and Revisions strip cut Network and pushed the Revisions badge out in every language (commit 3fd764e).

- `app.ts`: each tab gains an icon (`alert`, `terminal`, `globe`, `archive`), its label in a span and a `title` with the existing key.
- `styles/panel.css`: `.fp-bottom-head` is a size container. The icon is hidden by default. Below 460 px of strip the tabs tighten (6 px padding, 4 px badge margin). Below 360 px they show icon and count badge, and the label span is kept as a visually clipped accessible name. Two rules that targeted the strip from its own container query never applied and were left out.
- No new strings.

Checked: English, German, Finnish and Russian at 1440 x 900, 1100 x 800 and 760 x 640 with CPU 4x, also with every count at 99: nothing cut or overlapping; 1440 x 900 pixel-identical; CLS 0 opening a site, switching tabs and resizing; `npx tsc --noEmit`; `npm run build`. Known: three-digit counts on more than one tab at 760 px would overflow.

## Phase 47: toolbar selects show their whole value · v0.2.5 (2026-11-11)

Turn O kept every control in the row but the selects at 760 x 640 showed only "D..." or "Be..." (commit 184bd71).

- `ui/toolbar.ts`: below 1240 px of row, each select is sized to its value with a hidden probe select, so the engine's own arrow is counted. If the row still overflows it adds `.is-tight`, and then `.is-short`, which swaps in short labels (the value after "Theme:" and similar prefixes, the device name without its size). Option text and keys are unchanged.
- `styles/preview.css`: the probe rule; selects no longer shrink or clip below 1240 px; `.is-tight` drops the separators and turns the route field into an icon that opens as a 300 px overlay on focus without moving the row (Enter navigates, Esc or blur collapses); `.is-short` tightens gaps, number inputs and buttons. Turn O's 860 px block is removed, because a container query cannot style its own container.
- `app.ts`: the route input gains a `title`.
- No new strings.

Checked: English, German, Finnish and Russian at 1440 x 900, 1100 x 800 and 760 x 640 with CPU 4x and every option of every select: whole values, no control outside the row, no scrolling, CLS 0 opening a site and resizing; 1440 x 900 unchanged; `npx tsc --noEmit`; `npm run build`. Known: picking an option resizes the select, so its neighbours move after the user's own pick; the band between 1240 and 1400 px still uses Turn O's shrinking selects.

The director's exit run then found the Problems bar's two filters ("All severities", "All tiers") squeezed to 40 to 52 px at 760 x 640 in every language and cut at 1100 x 800 in Russian (commit d503e8f).

- `styles/panel.css`: the filters keep their own width (`flex: none`, `max-width: 100%`), which counts the engine's arrow, and `.fp-pn-bar` wraps (`flex-wrap`, `min-height: 34px` in place of a fixed height), so the filters and then the icon buttons drop to their own rows when the width cannot hold them. The rows follow the width and the language, never the results. Run checks keeps the right edge with `margin-left: auto`; the progress text takes the free space and, at 300 px or less, is visually hidden but stays in its live region. `container-type` moves from the bar to its page, so Turn O's 300 px rules, which targeted the bar from its own container, now apply.

Checked: the same four languages and three sizes with every option of both filters: whole values, every control inside the bar, Run checks and Deep check reachable; CLS 0 opening a site, resizing and running checks; 1440 x 900 unchanged. Known: at 760 x 640 the bar is 59 px tall instead of 34 (one filter per row in German, Finnish and Russian), and in Russian at 1100 x 800 Deep check wraps to a second row.

## Phase 48: Save as .fpub downloads as SITE-BUILD.fpub · v0.2.5 (2026-11-11)

The Phase 43 link set the download name to `ID.fpub` (commit 35f207d).

- `ui/builds.ts`: the link's `download` is `SITE-BUILD.fpub`, the engine's Content-Disposition name and the CLI default. Chrome already used the server's name, so nothing changed there; a webview that ignores the header would have used the shorter name. Site ids are slugs and build ids hex, so the name needs no cleaning. The site.zip link already matched.

Checked: real Chrome downloads in English and German for builds of sites named Plain, an 80-character name, Café Zürich Über 日本語, my.site.v1.2.final and 日本語, each equal to the engine header and to `formpublisher run fpub` in an empty folder; `npx tsc --noEmit`; `npm run build`.

## Phases 49 and 50: whole toolbar values at every width, and picks that move nothing · v0.2.6 (2026-11-11)

Between 1240 and 1400 px of row Turn O's container rule still let the selects shrink with an ellipsis, and below 1240 px each select was sized to its chosen option, so a pick moved its neighbours (commit 83c2e79).

- `ui/toolbar.ts`: `FIT_BELOW` is 1400. `paint()` sizes each select to its widest option label in the current stage, measured with the hidden probe select (arrow included), and writes the inline width only when it changes. The select `change` listener and the `fit()` call in `paintControls()` are gone: the toolbar fits once at construction and then only on row resize, option or text changes and font loads, never on a pick.
- `styles/preview.css`: the 1400 px container rule no longer shrinks or clips selects (`min-width: 0; max-width: none; text-overflow: clip`); the `.is-short` rule that let the device select shrink is removed; in `.is-short` the number inputs are 34 px (`padding: 0 1px`) and the icon buttons 22 px, so the row still fits at 760 px in German and Russian. Four-digit sizes still show whole.

Checked: English, German, Finnish and Russian at 1440, 1366, 1280, 1100 and 760 px with CPU 4x, cycling every option of every select: no cut value, no control outside the row, no control moved or resized by a pick (before: up to 13 cut selects per case between 1240 and 1400 px, and 11 or 12 picks moving neighbours below 1400 px); CLS 0 opening a site and resizing; 1440 x 900 unchanged; `npx tsc --noEmit`; `npm run build`.

## Phase 51: the Problems bar keeps one row where a short "All" is enough · v0.2.6 (2026-11-11)

Turn P left the bar 59 px tall at 760 x 640 in every language (commits 96d59ec and e858928).

- `ui/panel.ts`: `watchBar()` and `fitBar()`. When the bar would wrap with the full labels (another control sits on a lower row than the severity select), option 0 of both filters gets `option.label = t('All')` and each select's `title` the full option text; if the bar still wraps, the full labels come back. It runs before first paint from a `ResizeObserver` on the Problems page, and on option edits, picks and font loads. Option text and keys are unchanged.
- `styles/panel.css`: the narrow column gap is 2 px.
- `i18n/keys/part21.json`: "All", in all 25 other languages, in a form that stands without a noun.

Checked: English, German, Finnish and Russian at 1440 x 900, 1100 x 800 and 760 x 640 with CPU 4x and every option of both filters: whole values, every control inside the bar, CLS 0 opening a site, resizing and running checks. English at 760 x 640 is one 34 px row again. Known: German, Finnish and Russian still wrap at 760 x 640, and Russian at 1100 x 800, because their widest other options (Warnungen, Varoitukset, Предупреждения; Statisch, Staattinen, Статическая) leave no room with whole values.

## Phase 52: a compact Problems filter · v0.2.7 (2026-11-11)

Phase 51 left German, Finnish and Russian wrapping the Problems bar to 59 px at 760 x 640, and Russian at 1100 x 800 (commits 13aad4d and 7910053).

- `ui/panel.ts`: `fitBar()` now tries three modes in order, `full`, `short` (option 0 reads "All") and `compact`, and keeps the first in which no control sits on a lower row. In `compact` both selects are hidden and the `filterBtn` funnel shows, with `filterDot` while either filter is not All and a title of "Filter problems" plus both current choices. `openMenu()` builds a menu of both groups as radio items; `pickFilter()` sets the hidden select and fires its `change`, so filtering runs through the same path. The menu opens upward near the window bottom; `menuKey()` handles Enter, Space, arrows, Home, End and Escape, and `closeMenu(true)` returns focus to the funnel. The decision is still measured before first paint from the `ResizeObserver`.
- `ui/icons.ts`: `filter`, a funnel.
- `styles/panel.css`: `.fp-pn-filter` (one control size, open state), `.fp-pn-dot`, `.fp-pn-menu-head`.
- `i18n/keys/part22.json`: "Filter problems", in all 25 other languages.

Checked: English, German, Finnish and Russian at 1440 x 900, 1100 x 800 and 760 x 640 with CPU 4x: one 34 px row everywhere; all 16 filter pairs by mouse and by keyboard in compact mode filtered as the selects do; CLS 0 opening a site, running checks, resizing and picking filters; `npx tsc --noEmit`; `npm run build`.

## Phase 53: changing the language without a reload · v0.2.7 (2026-11-11)

`setLanguage()` stored the choice and reloaded the window, which flashed it white and dropped the open dialog, typed text and the preview (commit 2e17a61).

- `i18n/index.ts`: `loadTables()` loads the new tables before anything visible changes; a failed load restores the stored choice, and `wanted` makes the last of several quick picks win. `switchTo()` swaps `exact` and `patterns`, clears the cache, sets `html lang` and the title (from `titleEn`, captured at load), re-translates every node from its recorded English with `rewalk()` (`textEn` and `attrEn` hold the English source and the shown string per text node and attribute), then calls the `onLanguage()` listeners, all in one task. Unrecorded nodes count as English, as on a fresh load. A shown-to-English reverse map was tried and dropped because strings such as "Info" and "About" collide. The observer is created on the first switch away from English or a non-English start. The storage key and `storedLanguage()` are unchanged.
- Listeners repaint what is drawn with `t()` or `locale()` at build time: `app.ts` (the Imported date), `ui/home.ts`, `ui/builds.ts`, `ui/trash.ts`, `ui/revisions.ts`, `ui/publish-sheet.ts` (which also sets each target checkbox's label), `ui/package-sheet.ts`, `ui/command-palette.ts` (`relabel()`), `ui/shortcuts-dialog.ts` and `ui/native-menu.ts` (rebuilds the native menu in the desktop shell). `ui/panel.ts` needs none: `fitBar()` re-fits on option text changes.
- `ui/preferences.ts`: the select resets to `language()` when a load fails; the hint reads "The window changes to the language you choose.", replacing the old key in `i18n/keys/part02.json` and its 25 translations.

Checked (Chrome, 1440 x 900): live switches en>de>ru>en, en>de>en>ru, ru>de>ja>en, en>fr>de>fr, en>ja>zh-Hans>en and en>L>en for all 25 languages against fresh loads: no visible difference, hidden DOM and eight dialogs equal, 0 navigations; the open site, selection, panel, preview iframe (0 loads), Preferences and typed text kept. CPU 4x: one sideways shift of the toolbar selects per switch, 0.002 to 0.008, no blank frame, longest task 61 ms. The native menu rebuild was not run in the lab. `npx tsc --noEmit`; `npm run build`.

## Phase 54: the narrow window in WebKitGTK · v0.2.7 (2026-11-11)

Measured in WebKitGTK 2.52.6 (a minimal GTK 3 WebKit2 4.1 window under Xvfb, since the desktop shell is not built in the lab) beside Chrome, with the same script, at 1440 x 900, 1100 x 800 and 760 x 640 in English and German (commit f83e920). WebKit draws selects about 5 px wider: German at 1440 overflowed the toolbar by 17 px (Package outside the row, the Motion select capped at 170 px and cut by 3 px, because sizing only ran at 1400 px of row and below), and German at 760 by 21 px. English, the tab strip and the Problems bar were whole everywhere.

- `ui/toolbar.ts`: `fit()` starts at stage 1 at 1400 px of row and below, otherwise stage 0, and escalates from either whenever the row scrolls. It sets `is-sized` from stage 1 and `is-micro` at a new stage 4; `paint()` sizes selects from stage 1.
- `styles/preview.css`: `.fp-options.is-sized .fp-tb-select` drops the 170 px cap and minimum width; `.is-micro` gives the row 4 px padding, hides the "x" between width and height and makes the number fields 32 px.

Checked: both engines at all six sizes and languages: no row scroll, nothing outside the row, no cut value, tabs and Problems bar whole; the funnel menu opens inside the window in both. At 760 in English WebKit picks the compact filter where Chrome keeps the short "All", as `fitBar()` measures. Chrome is unchanged apart from the `is-sized` class. Known: at 760 in German the device select keeps the width of its widest option, "Benutzerdefiniert".

## Phase 55: toolbar selects across a language switch, partly landed · v0.2.8 (2026-11-11)

What landed (commit dab7c22): in German at 1440 x 900 the first device pick, even to the same value, widened the select from 145 to 162 px and shrank the route field, because at stage 0 `paint()` removed the inline width and Chrome kept the select's intrinsic width from the English options until the selection changed.

- `ui/toolbar.ts`: `paint(compact)` no longer takes `sized` and writes the probe-measured width of the widest option label at every stage; `fit()` calls `paint(stage >= 3)`. The stage-0 `min-width: 64px` and `max-width: 170px` still apply, and `is-sized` still drives the CSS caps from stage 1.

Checked: English, German, Finnish, Russian and Japanese at 1440 x 900, 1366 x 768, 1100 x 800 and 760 x 640, fresh and after a live switch, CPU 4x, every option of every toolbar select plus a first pick to the current value: 0 of 22 picks moved a control in every case; English boxes identical to 0.2.7 at all four sizes; German at 1440 in WebKitGTK (already at stage 2 there) unchanged. Known: Japanese at 1440 has one value that may be cut in a canvas check, before and after.

What did not land: the switch itself still moves the toolbar once. Measured at 1440 x 900, 1100 x 800 and 760 x 640 with en>de>ru>ja>fi>en, both by a trusted pick in Preferences and programmatically (the same numbers): a switch moved 18 of 18 controls after the route field at 1440, and 12 to 17 at the narrower sizes, 0.002 to 0.017 of CLS per switch, because the route field absorbs every width change, so any select or button that changes width moves everything after it. Zero movement therefore needs widths that do not depend on the language. A working version gave each select and the Publish and Package buttons one slot sized from the English labels and the widest strings across all languages, with short labels where a full one did not fit: 0 controls moved at 1440, but English at 1440 changed (route field 294 to 185 px, Zoom 64 to 104, Publish 87 to 136, Package 96 to 120, with visible blank space), German and Russian showed values without their prefixes, and 1100 and 760 px still moved. It was declined because a switch is a rare, one-time action and English at 1440 x 900 was to stay as in 0.2.7. A session high-water width, measuring all 26 languages at idle (about 3 MB of tables) and anchoring groups were weighed and rejected. The rest of the CLS at 1440 comes from the hint bar, the document title and the Problems bar. The owner decides.

## Phase 57: a shorter device select in the narrowest stages · v0.2.8 (2026-11-11)

At 760 px in German the device select kept the width of its widest option, "Benutzerdefiniert", even while it showed "Desktop" (commit 2f77ade).

- `ui/toolbar.ts`: in the `is-short` and `is-micro` stages `paint()` sizes the device select to the widest of the preset short names (the device name without its size) and the Custom option. `customShort()` gives Custom the short label `t('Other')` only when the translated "Custom" is wider than every preset short name and "Other" is translated, so English, Finnish and Russian keep their labels and a language without the string keeps the full word. `deviceTitle()` sets the title to the device label and the full option text in those stages, and to the plain label otherwise; it runs from `paint()`, `paintControls()` and the device change listener. `measure()` reads a label's width from the probe. A pick still changes no width.
- `i18n/keys/part23.json`: "Other", in all 25 other languages.

Checked: English, German, Finnish and Russian at 1440 x 900, 1100 x 800 and 760 x 640 with CPU 4x and every option of every toolbar select: whole values, one row, no pick moving a control, CLS 0 opening a site; German at 760 from 125 to 96 px in Chrome and from 131 to 103 px in WebKitGTK; English at 1440 and 1100 unchanged; `npx tsc --noEmit`; `npm run build`. Known: Finnish and Russian gain nothing, because a preset name (Kannettava, Компьютер) is as wide as Custom. P3 also found that the first device pick in German at 1440 moved the toolbar once (0.2.7 behaviour), fixed under Phase 55.

## Phase 58: the splash shows the app icon · v0.3.0 (2026-11-15)

- `public/splash.html`: the picture is `favicon.png` (the app icon, as formvis's splash shows) instead of `mark-144.png` (the family mark). Same 72 x 72 box, same alt text, so nothing else on the splash moves. The hand-off to the window is unchanged: the shell reveals the main window after the interface's first frame.

## Phase 59: the menubar is built like formvis's · v0.3.0 (2026-11-15)

One list of menus now feeds the bar in the window and the macOS menu bar, so the two cannot drift apart.

- `ui/chrome.ts`: `menus` is one `MenuDef[]`: File (Home first, then the imports, New Window, Close Tab, Package Site, Publish Site, Preferences), Edit, View, Site, Window (Minimize, Maximize, Full Screen), Help (Documentation, Keyboard Shortcuts, About). `view.home` moved from View to File and keeps `Alt+Mod+H`. `view.menus-in-window` exists only on the macOS desktop (`isMacDesktop`), writes `MENUS_IN_WINDOW_KEY` and says in a toast that it applies from the next start, because the native bar is built once at boot. `window.minimize` and `window.maximize` are enabled only in the desktop shell; `window.fullscreen` uses the page's own fullscreen so it also works in a browser. The window always builds the in-window `MenuBar`; `has-native-menus` hides it, so a failed native build no longer has to rebuild it.
- `ui/menu.ts`: keyboard navigation. F10 opens the first menu; a lone Alt (not on macOS) focuses the bar and underlines first letters (`is-menu-mnemonics`); Alt plus a letter opens the menu that starts with it; on the bar Left, Right, Home and End move, Down, Up, Enter and Space open, Escape returns focus to where it was (`barBack`). In a menu: Up, Down, Home, End, Right into a submenu or to the next menu, Left out of a submenu or to the previous menu, Escape one level at a time, Tab closes, and typing letters within 700 ms (`TYPE_AHEAD_MS`) jumps to the row that starts with them. `MenuDef.items` may be a function, read through `itemsOf()` each time a menu opens. A submenu closes when its parent panel scrolls. Window blur closes everything. The bar is not usable while a dialog is open or the native menus are on.
- `ui/native-menu.ts`: reads the same list. Window's three commands map to the system's predefined Minimize, Maximize and Fullscreen items, Bring All to Front is added, and the Window submenu is registered as the app's windows menu. Services, Hide Others and Show All left the app menu (formvis has none). `refresh()` runs on site, engine and settings events and when focus leaves a text field, so enabled and checked states follow the page.
- `ui/commands.ts`: `Alt+Mod+H` is no longer reserved for the system on macOS, since Hide Others is gone and Home uses it.
- `ui/shortcuts-dialog.ts`: the Window group is listed.
- `styles/shell.css`: a focused bar button looks like a hovered one; the mnemonic underline; the brand is a button that opens Home.
- `i18n/keys/part24.json`: 7 strings, in all 25 other languages.

Checked: every menu by click and the whole keyboard path in English and German, dev and built window, CPU 4x: no layout shift at the moment a menu opens. The macOS menu tree was read from a faked desktop (`navigator.platform` and `__TAURI_INTERNALS__`), not on a Mac.

## Phase 60: Preferences is formvis's window · v0.3.0 (2026-11-15)

- `ui/prefs-shell.ts` (new): `PrefsShell` wraps the existing sections. A rail floats left of the dialog with one tab per section (General, Interface, FormWeb, About); a fold button collapses it to icons and the choice is kept in `formpublisher.prefsRailCollapsed`. Every section is a card with a head that folds it. All sections are in one scrolling page: a click on a tab scrolls to its card (and unfolds it), and a scroll spy marks the card at the top as current. The spy is muted for 700 ms after a click so a smooth scroll does not flicker through the tabs on its way. An SVG wire runs from the active tab to a port on the current card, with 10 px arcs (`ARC`), redrawn on scroll, resize and fold from one animation frame. Up and Down move between tabs.
- `ui/preferences.ts`: builds its sections as before and hands them to the shell; the old tab strip and its paging are gone, so every control keeps its place in the DOM and its listeners.
- `styles/prefs.css` (new): the rail, cards and wire. Below 720 px of window width there is no room beside the dialog, so the rail, the wire and the port are hidden and the dialog takes the window's width; every section is still reached by scrolling the one page (Phase 62).
- `styles/overlays.css`: the old `.fp-prefs-nav`, `.fp-prefs-tab` and page rules are removed.
- `i18n/keys/part25.json`: 5 strings, in all 25 other languages.

Checked: opened by shortcut, gear, File menu and Help > About, every section, arrows, fold, collapse and reload, 1440 x 900, 1000 x 700 and 1000 x 280, English and German, dev and built: layout shifts only with recent input (fold, collapse, resize). One setting of each control type still saves and survives a reload.

## Phase 61: Home has formdeck's structure and its cards hold still · v0.3.0 (2026-11-15)

- `ui/home.ts`: the side panel lists Start, Recent sites, Builds and Trash (Builds and Trash with a count, refreshed on build and trash events), then Import (Open zip, Open folder, Import from FormWeb), Local only and Preferences. Below 720 px the panel gives way to one row of four (`.fp-home-narrow`: Start, Recent, Builds, Trash). Start has the drop zone with its three buttons and the ZIP, FWEB and FPUB format chips, the first row of Recent sites with See all, and Demos. A card's badge names where the site came from (Demo, FormWeb, Zip, Folder, FWEB, FPUB; the last three and FormWeb are never translated). While Home is open, a site that arrives does not push the cards: the order is frozen (`frozen`), a note row says how many arrived and its Show button repaints. The note row and its button are always in the DOM at their final size, so nothing moves when the text appears. Deleting a build or emptying the trash asks in a confirm row inside Home (`ask()`), not in a dialog over it; Escape answers no. `BuildsPage` and `TrashPage` take the confirm function as a constructor argument for that.
- `ui/demos.ts` (new): `DEMOS` is the list of demo cards (id, title, one line, cover, how to open). Each demo is also a command, `demo-<id>`, so Help > Demos and the command palette list the same demos as Home. Only one demo opens at a time: a second request gets the toast "A demo is still opening." and the cards carry `aria-busy`.
- `api-demo.ts`: `openBundled(id)` posts `/api/demo/open/<id>`; `openSample()` keeps `/api/demo/sample`.
- `styles/overlays.css`, `styles/recent.css`, `styles/demo.css`: Home's grid, the reserved sizes and the confirm row. Reserved from measured widths in all 26 languages: the hero text has a fixed line count by its own width (2 lines from 680 px, 3 from 440, 4 from 330, 5 from 265, else 6; the longest translation is 1204 px in one line); the hero buttons share a 208 px column (widest label 200 px); See all is at least 140 px; the Demos title at least 76 px; Show is 104 px. The quick-tour strip sits over the stage column only.
- `public/demos/northwind/cover.webp`: the card's cover, 640 x 360.
- `i18n/keys/part26.json`: 6 strings, in all 25 other languages.

Checked: 1440 x 900, 1000 x 700 and 390 px, English and German, dark and light, empty and with five sites; a language switch in place moves nothing inside Home vertically; a site arriving while Home is open moves no card.

## Phase 62: fifteen fixes from the full review · v0.3.0 (2026-11-15)

The frontend part of the review (the engine's part is in `backend/HASHOUT_LOG.md`, the shell's in `src-tauri/HASHOUT_LOG.md`).

- `index.html`: sets `has-overlay-titlebar` on the macOS desktop before first paint, so the title row is already 38 px tall and indented when the window appears.
- `styles/shell.css`: `:root.has-overlay-titlebar` sets `--fp-titlebar-h: 38px` and the title row gets `padding-left: 78px`, the room the close, minimize and zoom buttons need at the inset the shell gives them (14 px from the left, centred in 38 px). The menubar clips instead of running under the title tools: its grid is `auto minmax(0, auto) minmax(0, 1fr) auto` and the bar has `overflow: hidden` with a 3 px margin and padding trade so focus rings stay whole.
- `app.ts`: the title row, the menubar, the title tools and the document title carry `data-tauri-drag-region`, so the empty parts of the row drag the window on macOS. `openSite()` keeps the routes it already shows when the same site is opened again or Reload Routes runs, keeps the selected route when it still exists, and shows "Loading routes" only when the strip is empty; before, importing the open site again emptied the strip until the engine answered.
- `ui/home.ts`, `styles/overlays.css`: the confirm row stays on one line at the minimum width; a long question ends in an ellipsis and the whole text is in the title. Dialogs fit a narrow window: the grid column is `minmax(0, 1fr)` and the footer wraps.
- `styles/package.css`, `styles/trash.css`: the head buttons of Builds and Trash have fixed minimum widths (144 and 212 px, the widest translations), so a language switch moves nothing; the tables scroll sideways below 640 px instead of hiding the delete button; Inspect and Compare reserve the file list (340 px) and two SHA lines.
- `styles/prefs.css`: the narrow fallback named in Phase 60.
- `styles/panel.css`: the count badge on a bottom tab reserves room for a second digit, but only when the panel is at least 520 px wide (a container query): a plain `min-width` wrapped the tabs at 1024 px in German.
- `i18n/keys/part05.json`: two strings no code uses any more were removed from the key file and from all 25 languages.

Not changed, on purpose: the preview frame keeps `allow-scripts allow-same-origin`. Without `allow-same-origin` the framed site has an opaque origin, its probe messages are dropped, its own storage throws and its web fonts are blocked. The frame is always served from the site host's port, never the window's origin, so it cannot remove its own sandbox; Chrome prints its warning for the two tokens whatever the origins are.

Checked: a 36 step tour of the whole window at 1440 x 900, 1000 x 700 and 390 px with CPU 4x before and after, the fixed surfaces again in German and Finnish at 1024 x 680, and a faked macOS shell in Chrome for the title row geometry. Never run on a Mac.

## Phase 63: four demos · v0.3.0 (2026-11-15)

- `ui/demos.ts`: `DEMOS` lists Lowlight, Looking Back and Harbour Ferries, the three demo sites FormWeb ships, before Northwind Notes. The three open through `openBundled(id)`. Northwind Notes stays as the fourth because it is the one with findings: the three FormWeb sites pass the checks, so a first-time user who opens one and presses Check sees an empty list, and the quick tour, the offline demo (`demo/index.html`) and the screenshots all walk Northwind's 1 error and 2 warnings.
- `public/demos/<id>/cover.webp`: one cover per demo, the top 16:9 of the home page at 640 x 360.
- `i18n/keys/part27.json`: the three card lines, in all 25 other languages. The site names are not translated.

Checked: each card, Help > Demos and the palette at 1440, 1000 and 390 px in English and German; every route of every demo on four devices.

## Phase 64: the live layout-shift and overflow checks stop blaming the preview · v0.3.0 (2026-11-15)

A finished site showed `live.cls` errors on every route after a Device switch, and `live.overflow` could say "41 px wide in a 0 px viewport". Both were the preview's own doing. The probe's part is in `backend/HASHOUT_LOG.md`.

- `styles/preview.css`: a loading frame waits at `opacity: 0.01`, not 0. Measured in Chrome: a frame loaded at `opacity: 0` is not painted in the same process and never records its first layout shift, even after it is shown, so a real shift of a page went unseen; at 0.01 it is painted and records it. `visibility: hidden` is worse: a cross-site frame is render-throttled and applies a resize only seconds later, when it is shown.
- `ui/preview.ts`: `relayout()` writes the device size (`--pv-w`, `--pv-h`) before it computes the fit, so the frame has its device size even when the stage has no room (Home open, a collapsed pane); a frame of width 0 was where the 0 px viewport came from. Each document now names itself in its messages (`doc`); `staleDoc` refuses a message from the document a reused frame is leaving, because such a message arrives with the same `contentWindow` as the new document and used to be credited to the next route.
- `ui/panel.ts`: `live.cls` is reported from 0.001 up (smaller values are rounding noise from sub-pixel moves) and `live.overflow` only when the frame has a width.

Checked: the four demos, every route, seven Device switches per route, English and German, 1440 x 900 and 1000 x 700, CPU 4x, built and dev window: no `live.cls` and no `live.overflow`. A deliberately broken site (a late banner, a 2600 px wide element, rows added on a timer) still gets both findings on the right routes.

## Phase 65: a site sent from FormWeb names FormWeb as its source · v0.3.0 (2026-11-15)

- `api.ts`: `sourceLabel()` shows "FormWeb" when a site's source address starts with `receive:`. A site sent from FormWeb is keyed by FormWeb's project id (`receive:site-...`), and the inspector's Source row showed that key. Found while testing the hand-off with FormWeb 0.21.0 in both directions; the engine's two fixes from the same test are in `backend/HASHOUT_LOG.md`, Phase 66.

## Phase 66: the strings of the forms.local-address check and the revision notice · v0.3.1 (2026-11-15)

The engine's part (the check, the project id on Import, `project_site()`) is in `backend/HASHOUT_LOG.md`, Phase 67. The window changes in two places.

- `i18n/keys/part28.json` (new), in all 25 other languages: the message of `forms.local-address` ("The form on {0} sends to {1}, which will not answer once the site is published, so the form will not send."), its fix ("In FormWeb, give the form a scripted reply (Motion > Script, trigger Submit), or point its action at a form service on the web.") and the toast "Added a revision to {0}". The two check strings are the engine's own text with the page and the address as `{0}` and `{1}`, the form every translated problem message already takes, so the Problems panel shows them in the window's language. The row's tooltip still shows the engine's English message and fix for every check, as before; this was not changed here.
- `app.ts`, `flow()`: after an import it said "Imported [name]" whatever happened. Import from FormWeb now files a site under the FormWeb project it came from, so the same project imported again, or sent before, gains a revision of its site and no new site appears; a notice that says "Imported" would be false then. The wrapper reads the record's `revisions` count: more than one gives "Added a revision to [name]", one gives "Imported [name]" as before. The count is the one `toSite()` already makes from the record. The wrapper serves every import path (zip, folder, FormWeb), so opening a zip again, which also adds a revision, says the same.
- `api.ts` is unchanged: a site imported from the open FormWeb project is keyed `receive:<project id>`, so `sourceLabel()` (Phase 65) already shows "FormWeb" as its source, the same as a site that was sent.

## Phase 67: a language switch holds Preferences, the hint strip and the menubar still; Import lists FormWeb's projects; the tooltip is translated · v0.3.3 (2026-11-15)

The engine's part of the same release (demo refresh, adoption, the project routes, `external.request`, the null checks summary) is in `backend/HASHOUT_LOG.md`, Phase 68.

- `ui/reserve.ts` and `ui/reserve-labels.ts` (new), `styles/shell.css`, `styles/demo.css`, and one line each in `ui/chrome.ts`, `ui/hint-strip.ts` and `ui/preferences.ts`. Phase 55 measured that a language switch moves the toolbar, the hint strip, the document title and the Problems bar, and a measurement of the whole window at 1440, 1100 and 760 px added Preferences (up to 0.13 of layout shift at 760 over a six-language chain) to the list. The cause is always the same: a box takes the width or height of the text it holds, and the text changes at the switch, so what follows it moves. The fix is to reserve the largest size over all 26 languages before the switch, so nothing depends on the language. `reserve-labels.ts` holds the 29 strings involved in every language (`RESERVE_KEYS` and `RESERVE_LABELS`, 26 rows), taken from the running app's own `t()`; it is generated data, written once by a throwaway script that is not in the repository, so when the English of one of those strings or its translation changes it must be written again, and nothing checks that automatically. `reserve.ts` measures hidden clones ("ghosts": `translate="no"`, `aria-hidden`, absolutely positioned, `visibility: hidden`, ids removed, taken out again at once) with each language's strings and writes the largest result as a CSS variable or a `min-height`; it writes only when the value changes.
- `reserveMenubar()`: the whole menubar is measured as a `max-content` clone in each language and `--fp-menubar-w` is its widest; `.fp-menubar` takes that width with `max-width: 100%`, so in a narrow window it is still clipped at the title tools as before. The bar is measured again when fonts finish loading (`loadingdone`). Why the whole bar and not each button: the title row is a grid, so a bar whose width follows its labels moves the site name and the tools beside it at every switch. Known and left: the six buttons still move inside the bar at a switch, by a few pixels, because each button takes its own label's width; reserving each slot would make the English menubar about 1.8 times as wide.
- `reserveHint()` (the quick tour strip), run each time the strip is shown: the width of the counter ("Step 1 of 4" to "Step 4 of 4"), of the title (Preview, Checks, Package, Publish), of Back and of Next and Done together (`--fp-hint-count-w`, `--fp-hint-title-w`, `--fp-hint-back-w`, `--fp-hint-next-w`), each the widest string in any language, measured with a ghost of the same markup so the font and padding match.
- `reservePrefs()` (Preferences), run each time the dialog opens: each row or block with a hint gets a `min-height` of whole lines, the tallest its hint takes in any language at the row's current width (a ghost row of the same width gets each language's name and hint in turn, and the height is rounded to the line height), and Done gets the width of its widest translation. A `ResizeObserver` on the pages measures again when their width changes, once per element. A row whose hint is not one of the known strings (the FormWeb row after Test shows a result in that place) is skipped. Why heights and not widths: the hint wraps to two or three lines in German or Finnish, and every row below it moved.
- Checked (Chrome, CPU 4x, Lowlight open with Preferences open, the chain en, de, ja, ru, fi, fr, en, total layout shift with and without the reserve): at 1440 px 0.0145 to 0.0067, at 1100 px 0.0203 to 0.0092, at 760 px 0.1398 to 0.0049; Preferences alone 0.0001, 0.0002 and 0.0424 to 0 at every width; the hint strip 0.0014 and 0.0017 to 0 at 1440 and 1100 and 0.0019 to 0.0001 at 760; the title row 0.0026 to 0.0009 at 1440. What is left in the total comes from the bottom Checks panel (its buttons, the filter select and the tab counts), the routes strip count and the menu buttons inside the bar. The window was not driven in a desktop shell.
- Toolbar, by decision: it still shifts once at the moment a new language is picked. Zero movement needs every control sized for the widest of the 26 languages, as Phase 55 found: a version was built again for this release (each select and the Publish and Package buttons sized from the widest label in any language, with short labels where a full one does not fit, generated into `ui/toolbar-labels.ts`) and it moved 0 toolbar controls at 1440, 1366, 1100, 900 and 760 px in eight languages, but at 1440 in English it narrows the route field from 294 to 177 px and widens Zoom, Publish and Package, the same cost for which the approach was declined at 0.2.8 (Phase 55). The owner was asked; by default the toolbar was left as it is, so `ui/toolbar.ts`, `styles/preview.css` and the manual's toolbar paragraph are as in 0.3.2. That version is kept outside the repository (`/home/claude/work/scratch/formpublisher/turn5/toolbar-option-a/`: `toolbar.ts`, `toolbar-labels.ts`, `preview.css`) in case the owner chooses it. Release chores found that `docs/MANUAL.md` had been written for that version (it said a switch never moves a control); it is back to the 0.3.2 text with one sentence saying the toolbar moves once at a switch.
- `ui/formweb-picker.ts` and `styles/formweb-picker.css` (new), `app.ts` `importFromFormWeb()`, `api.ts` (`formwebProjects()`, `formwebImportCurrent(project)`, the `FormWebProject` type): Import from FormWeb asks the engine for FormWeb's projects first (a failure counts as none, so Import never fails for want of the list). Only when there is more than the open site does a dialog open, a radio list with the open site first and chosen ("Unsaved site" when it has no saved project name, "Open in FormWeb" as its line; the others with "Saved" and a date from `Intl.DateTimeFormat` in the window's language, a project name never translated), Enter or a double click imports, Cancel and Escape import nothing. The open site's radio has an empty value, which means "no project": the engine then reads FormWeb's export, so unsaved changes come along; any other row sends its project id. `flow()` does the rest as for every import, including "Added a revision to [name]". With one project or an older FormWeb the dialog never opens and Import behaves as in 0.3.1. The list is a `max-height: 320px` scroll box, every size and colour from tokens, no z-index of its own (the dialog layer is the shared one). Strings: `i18n/keys/part29.json` (new), 5 strings in all 25 other languages: the check message for a URL used more than once ("The site loads {0} from another host: {1} references on {2}."), "Choose the FormWeb project to import.", "Unsaved site", "Open in FormWeb" and "Saved {0}".
- `ui/panel.ts`, `i18n/index.ts`: the Problems row tooltip showed the engine's English message and fix for every check (known since 0.3.1), because it joined them with a space and the lookup had no entry for the joined text. It now joins them with " · ", and `lookup()` splits a string on " · " and translates each half; that split now runs before the pattern lookup. Reason for the order: a pattern ends in a lazy `([\s\S]*?)` before a final full stop, so a message such as "The site loads {0} from another host: {1} references on {2}." matched the whole joined text with the fix swallowed into `{2}`, and the fix stayed English. Checked in German and Japanese for `link.broken`, `heading.h1`, `sitemap.missing`, `forms.local-address` and `external.request` (single and grouped), and after live switches en, de, ja, ru, fi, fr, en.
- `api-builds.ts`, `toDetail()`: a `publish.json` whose `checks` has an empty `tiers` list (written by 0.3.2 or earlier, or by this release with no check run) gives `checks: null`, the same as the new `"checks": null`, so no clean result is shown for a build that ran no check.

## Phase 68: Templates, the Host it yourself guide, What to do with this folder · v0.4.0 (2026-11-22)

- `ui/templates-sheet.ts`, `api-templates.ts`, `styles/templates.css`: a Dialog opened by `file.templates` (File menu, Home's Import list and Start hero). The intro says where the list comes from and that nothing is fetched until asked, as static text, so no late sentence moves it. Three skeleton cards hold the grid's height until a list is kept; the status line reserves two lines; the result box below holds its text, path and the two buttons (Edit in FormWeb, Publish it, disabled until a start) from the first paint. Cards are patched by key. Preview images are present from the start at opacity 0 and shown on `load` (a `hidden` lazy image never loads). Edit in FormWeb opens Preferences' FormWeb address; Publish it closes the sheet and imports the project through `importFolder`, the existing import flow.
- `ui/hosting-sheet.ts`, `styles/hosting.css`: `docs/HOSTING.md` imported with `?raw` and rendered by a small renderer (headings with `fp-host-` ids, paragraphs, lists, tables, code, in-page links; everything escaped first), so the window and the repository carry one text. `openHosting(part)` keeps one sheet and scrolls to the part; `HOSTING_PART` maps target ids to headings.
- `ui/publish-sheet.ts`: each prepared host's card has What to do with this folder in its template, opening the guide at that host.
- `ui/icons.ts`: `template`. The new labels are English only; they are not yet in the 26 language files.
- Seen in a browser at 1280 by 800 under a 4x CPU throttle: layout shift 0 on Home, the sheet before and after Get the templates, after a start, the Publish sheet and the guide.

## Phase 69: the 0.4.0 window text in all 26 languages · v0.4.1 (2026-11-22)

- `i18n/keys/part30.json` (new) and `i18n/locales/<language>/part30.json` in the 25 other languages: 47 strings, 29 of the window and 18 of the engine. The window's: Templates, Start from a template, Start from a Template..., Host It Yourself, Host it yourself, The guide is in English., the intro, Get the templates, Check again, Start a site from this, the empty-list line, Reading the list, the kept-list line (`Kept list from {0}: {1}.`), 1 whole site, {0} whole sites, the two sentences about the parts that are not offered (one and many), the two could-not-be-read lines, the line a template without a description shows, the line before a start, Downloading {0} and checking its SHA-256, the result (`Made a FormWeb project from {0} ({1}).`), The site could not be started, Edit in FormWeb, Publish it, the hint about opening the project in FormWeb, What to do with this folder and the line beside it. The engine's: the 18 messages of `services/templates.py` and `routers/templates.py` that the sheet shows through `e.message`, keyed by the engine's own English with `{0}` and `{1}` where it puts a value in, as the earlier engine messages are, lowercase first. The two `description:` strings of the new commands are not keyed: a description is only the palette's search text and is never shown, and the earlier commands' are not keyed either. A count written into a sentence reuses the existing `1 file` and `{0} files` keys through the captured value (`lookup(v) ?? v`), so `42 files` is `42 Dateien` inside the result sentence; `{0} whole sites` has the plural forms in ru, uk, pl and cs, the others a single form.
- The wording of each file follows that language's earlier files (de Sie, es and es-MX tú, fr and fr-CA vous, nl je, ru, uk and cs vy, pl and it the imperative); es-MX and fr-CA have their own file and follow their own word choices where they differ from es and fr. FormWeb's menu names inside the hint sentence (File, Import .fweb or .fpub file) and the word for a template are those in FormWeb's own translation tables (`i18n/family` and `i18n/locales` in the FormWeb repository), read, not copied. Product names, file names and commands (`.fweb`, `.fpub`, SHA-256, formai-templates, GitHub, formweb-core) stay as written. No speaker of any of the 25 languages has read them.
- `ui/templates-sheet.ts`: the status line is two spans (`said` and `more`), so the date-and-count sentence and the sentence about the parts are two lookups and the second can be empty; the two sentences of the parts, one and many, replace the earlier single `${n} more ...` text, which read "1 more are parts"; `when()` is gone: it wrote the date in the system's locale (`toLocaleString(undefined, ...)`), not the window's, and the counts as `1 whole sites` and `1 files`; the date now comes from `fmtDate` (`Intl.DateTimeFormat` in `locale()`) and the counts from `fmtCount`, both from `ui/builds.ts`, as Builds does. The runtime keeps the English text of a node and translates it again at a switch, so a date written in German stayed written in German after a switch to Japanese, and its length wrapped the status to a third line; `sayKept()` writes the sentence again from the kept list on `onLanguage`, and `say()` forgets the kept list so an error or `Reading the list` is never overwritten.
- `ui/hosting-sheet.ts`, `styles/hosting.css`: the article has `lang="en"` and `translate="no"`, so the runtime leaves the guide as `docs/HOSTING.md` has it (it has no key for its text and never will) and a screen reader reads it as English. The one-line note beside Close, `.fp-host-note`, takes the room left of Close (`flex: 1 1 0`, one line, ellipsis), is hidden in English with `:root[lang^="en"]` (it stays in the layout, so the footer does not differ) and fits in all 26 languages (no clipping in the sweep at 1280).
- `styles/publish.css`: `.fp-pub-guide` is a grid, the button above its note, and the note wraps with a `min-height` of two lines instead of one line cut with an ellipsis. In 0.4.0 it needed 556 px and had 425 in English, so it was cut already, and in the translations it needed up to 708 px of the 357 to 498 it had. Two lines at the card's width hold the longest of the 26 languages; the card is the same height in all of them.
- `styles/templates.css`: the intro takes `min-height` of three lines and the result sentence of two, from a measurement of all 26 languages at the sheet's 726 px (intro 2 lines, German and Russian 3; the sentence before a start 1 or 2 lines, after a start 1; the status 2 in all, after shortening the Russian sentences; the hint 2 in all, after shortening the Hungarian one). The sheet's body is 674 px high in every language and in all three states. Cost: at a window 800 px high the sheet (86vh, 688 px) scrolls by 90 px, in English too (52 px before this release); from 1000 px high, where the sheet is 780 px, it does not scroll.
- Shortened after the 26-language sweep, because they did not fit: the Home hero label in es-MX and nl (5 px over the 208 px column), the card button in sv (224 px, outside its card), the two Russian sentences about the parts (the status took a third line), the Hungarian hint (a third line).
- Checked. A script outside the repository (the repository has no check of the language files) read every `part30.json`: valid JSON, the keys of `keys/part30.json` in the same order, the same `{n}` placeholders in the value as in the key, no empty value, no em dash, a plural form set in ru, uk, pl and cs: 0 problems in 25 files. A browser (Chrome, no throttle) over all 26 languages, the engine serving `frontend/dist` and a local copy of formai-templates, with `POST /api/templates/start` answered by a stub, because `formweb-core` was not built: the Home hero, the sheet before, with a list and after a start, the guide's footer and the Publish card's guide row. Nothing added in this release is clipped or outside its box in any of the 26. Left as they were: the credit line of a template (two lines, by design, ending in an ellipsis) and "Recent sites" in the Home list in de, fi, sv and hu (cut at 123 px, from 0.3.x). With a 4x CPU throttle at 1280 by 1000 in de, ja and th: the sheet before, with a list and after a start, the guide, and the Publish card; layout shift 0 and no console error in the 15 pictures; the ja and th pictures were read for overflow and a clipped button and show none. A live switch with the sheet in the state after a start, by script (en to de, ja, th, ru, en): none of the dialog, intro, status bar, grid, card, card button, result box, button row and footer moved up or down or sideways as a box; the two moves that are left are inside the bar and the row, as the Changelog says, layout shift 0.005 to 0.010.
- Not done: the window was not driven in the desktop shell, on Windows or on macOS; the real start (`formweb-core`) was not run in this release; the list came from a local copy of the repository, not from GitHub.

## Phase 70: Help opens the bundled manual, and a failed deep check says so · v0.5.0 (2026-11-22)

- `ui/manual-sheet.ts` (new) and `ui/chrome.ts`: Help, Documentation opened the manual on GitHub, which is a 404 while the repository is private and nothing at all offline. `ManualSheet` is a `Dialog` with the hosting sheet's classes; it fetches `/api/docs/manual` from the engine before it is shown, fills its article once (English, `translate="no"`) and only then opens, so the sheet never shows an empty frame. A failed fetch shows "The manual could not be loaded." and the next open tries again. `DOCS_URL` and `openExternal` are deleted from `chrome.ts`; nothing else used them.
- `ui/hosting-sheet.ts` `renderGuide` takes an id prefix (`fp-host` by default, `fp-man` for the manual). Headings get ids that match GitHub's anchors, table rows whose first cell is only codes get `data-code`, an image line becomes a figure with a dark and a light picture at a reserved 16 by 10 box (every manual picture has that shape), a link to another `.md` becomes a `data-doc` link, and any other outside link becomes plain text. An image line it cannot read is skipped; the paragraph rule looped on it before.
- `ui/notice-step.ts`: the `core-missing` step's Open the manual passes its code, and the sheet opens scrolled to that code's row in the Error codes table with the row marked.
- `styles/hosting.css`: the marked row, h3, the figures and the failure line. No `z-index`.
- `ui/panel.ts`: the live event `checks.failed` ends the deep run (the two buttons are enabled again; before, a failed run left them disabled until the 15 minute timer) and keeps one client-side problem, `deep.failed`, severity error, "The deep check could not finish: {0}". It goes through `merged()` and the existing `patchList` rows, so the Problems list, its count, the badge and the status dot show it in place; `publish()` skips it so no route is marked. It is cleared when a deep run starts, when progress arrives and when the site is imported again. `run()` raises `deepRun` from `pending` to the run id only while it is still `pending`, so a failure that arrives before the start request returns is not overwritten.
- Strings: `keys/part31.json` (new) with Manual, The manual is in English., The manual could not be loaded. and the installed app's browser advice; one key added to `part03.json` for the failure row. All 25 locale folders carry them; `python setup/i18n_check.py` counts 775 strings, complete.
- `package.json` and the lock: `engines.node` is `>=22.12`, the one minimum every script and message now names.
- Checked in headless Chrome 1440 by 900 with the CPU throttled 4 times, against the engine serving the built window: load, Find a Command, Documentation, the sheet open with 36 heading ids and 7 figures, Escape, open again: layout shift 0 at load and 0 in total, no console error. Not checked: the failure row in a browser (the event was forced only in the engine, by a throwaway script), the 25 translations by a reader of each language, the desktop shell, Windows, macOS.

## Phase 71: the window key, where a key's secret is kept, three verify states, key export and import, two lines about the network · v0.6.0 (2026-11-22)

- `src/window-key.ts` (new; FormDeck's `io/window-key.ts` in shape): `loadWindowKey` takes `window.__FORMPUBLISHER_WINDOW_KEY`, which the desktop shell set before any script ran, and deletes it; in a browser tab it tries the key kept in `sessionStorage` against `POST /api/window/check` and otherwise claims one from `POST /api/window/key`. `attach` wraps `window.fetch` once so every request to this origin's `/api/` carries `X-FormPublisher-Key`; nothing else in the window had to change, because every request already goes through `fetch` with a relative path. `main.ts` awaits it before the language and the app start. The static demo build has no engine: the claim fails quietly and the page runs without a key.
- `ui/package-sheet.ts`, `api-builds.ts`: each key in the list says where its secret is kept (Password store, Private file, Verify only); a verify-only key is a disabled option. Verify has three states in a line that holds two lines of room from first paint (`.is-verify`, min-height 2.8em): verified with your key and its name, signed by a key you do not have with the fingerprint in the warning colour, and invalid as an error.
- `ui/key-transfer.ts` (new): the Export key and Import key dialogs on the existing `Dialog`. Export asks for a full path ending in `.pem` and has the engine write the file, since the window's policy gives a page no way to save a private key by itself and a download would leave it in the browser's folder; the passphrase is typed twice. Password fields are emptied before each request returns and again on close; each dialog's error line keeps its height. The two buttons sit on the New key line from first paint; Export is enabled only for a key that can sign.
- `ui/preview.ts`, `ui/panel.ts`, `styles/preview.css`, `styles/panel.css`: one muted line in each pane, there from first paint. Preview: "Previewing loads whatever the site itself loads from other hosts." in a foot under the stage (`.fp-preview` became a flex column so the stage's fit excludes the foot). Problems: "The deep check loads the site as a browser would, including what it loads from other hosts." between the toolbar and the list. Each has a fixed height, one line and two below a container width, the same in every language; at the 760 px minimum window the Problems line clamps to two lines with the full text in its tooltip. The bottom panel's list is 23 px shorter at its default height.
- Strings: `part32.json` (32, keys) and `part33.json` (2, the network lines), in all 25 locale folders; `python setup/i18n_check.py` counts 809.
- Checked in headless Chrome at 1440 by 900 with the CPU throttled 4 times: the built window under the content policy loaded, imported a site through the wrapped `fetch` (200) and opened the manual with no console error and layout shift 0; a demo opened and the static and deep checks ran with layout shift 0; the two network lines measured in 26 languages at five widths. Not checked: the Package sheet's verify states and the two key dialogs in a live window (type check and build only), the desktop shell, Windows, macOS, the translations by a reader of each language.

## Phase 72: the family look, Preferences as the home of keys and settings, and the agent dock · v0.7.0 (2026-11-22)

Compared by reading against FormVis 2.8.1 (ca3b435) `frontend/src/styles/tokens.css`, `styles/panels.css`, `styles/dialogs.css` 162 to 184, `ui/app-dialogs.ts` and `ui/home.ts` 36 to 76, and FormDeck 0.46.3 (96b8e0e) `ui/home.ts` 74 to 113 and `ui/dialogs-file.ts` 1810 to 2157; the formai-design-lang scripts were not used, by the owner's choice.

- Tokens (cbb4294). `--fp-9` to `--fp-18` are `--fs-9` to `--fs-18`, with FormVis's values (they were already equal), in 18 sheets, by hand, no alias left. The title bar, tabs, options and status heights take FormVis's names `--cv-titlebar-h`, `--cv-tabs-h`, `--cv-options-h`, `--cv-status-h` and keep this window's values (44, 32, 44, 28 px; FormVis 40, 34, 40, 28), because the window's layout is drawn to them. `--fp-strip-w`, `--fp-props-w`, `--fp-bottom-h`, `--fp-pasteboard` stay: FormVis has no name for the same thing. `--cv-rail-w` (52 px, FormVis's value) is new for the folded strip. `--text-muted` stays #8a8a8b where FormVis has #717072; the owner did not ask for it. Every local variable (`--pv-*`, `--sw-*`, `--ac`, `--fp-hint-*-w`, `--fp-dialog-w`, `--fp-menubar-w`, `--fp-home-nav-w`, `--toast-y`) has a declared default on the block that owns it; `shortcuts.css` named a token that did not exist (`--accent`), so the recording border fell back to the text colour. `--shadow-inset` names the one inset that recurred; the six raw colours left occur once each, and FormVis keeps the same two scrim and dialog values raw. The danger button's text is `--text-on-danger` (white, 4.8 to 1 on the red), not `--text-on-accent`, which became a dark ink. Pixel check: the old and new builds rendered side by side at 1440 by 900, 0 differing pixels in seven views and the same anti-aliasing noise in two that two runs of the old build show against each other.
- The accent (cbb4294, b5d9d08). #5fe07a, the owner's Q3, which formtray and formai.studio already show. `themes.ts` and the pre-paint boot agree: `--text-on-accent` is #0b1a10 on a light accent (10.6 to 1; white was 1.7 to 1) and white on a dark one (relative luminance 0.2 is the crossover). On the light themes `--accent-ink` is the accent mixed toward black until it reads at 4.5 to 1 on every light surface (#2e6c3b for the default, 4.6 to 5.8 to 1; the accent itself was 1.2 to 1.6), and every accent-coloured label and icon uses the ink; fills, borders, glows and rings keep the accent. A stored #f97316 (the old default) moves to green once, marked by `formpublisher.accentMoved`; after that orange, which is back in the palette, is a real choice.
- Controls (b5d9d08). `ui/dropdown.ts`: FormVis's dropdown in this window's classes. Its button holds a hidden stack of every option's label, so its width is final before first paint and never changes with the value; the list is in the top layer and flips up; options are created once per set and patched; keyboard and list box semantics as the family's. It replaces the toolbar's five choosers, the two Problems filters, the Package key chooser, the Publish build chooser and the language chooser. Menus draw a shortcut as one `kbd.fp-kbd` per key from the shortcuts dialog's formatter, so both say the same keys. A language switch widens the toolbar's dropdowns to the new longest label: a shift of 0.006 right after the person's own choice, which the browser does not count against layout stability.
- Panels (b5d9d08). Routes, builds, revisions, Trash, the FormWeb picker, recent sites and Home's open sites are rounded cards with a hairline border, and the current one has FormVis's `.cv-layer.is-active` treatment: the accent line and the gradient glow (the same rule and tokens; the green reads stronger than lavender at the same 30 percent). `ui/resizers.ts` keeps the strip, the inspector and the bottom panel sizes and the strip's fold in `formpublisher.layout`, applied in the constructor while `#app` is still hidden, so the first paint has them; each separator is a focusable `role="separator"` with its values, 16 px arrow steps, Home, End and a double-click reset; dragging writes once per frame under pointer capture with text selection and the preview's pointer events off. Dragging the strip below 110 px folds it to the rail. The bottom panel's pages are in the shell's markup from first paint (`panelPagesHtml`); the builds compare keeps its last result per pair and the FormWeb picker its last list, each patched in place.
- Home (b5d9d08). Read against FormVis's and FormDeck's: a nav column with the brand, Start, Recent sites, Builds and Trash with counts, and a foot with Local only and Preferences; every page built once and only shown or hidden afterwards; counts by `setText`, lists by `patchList`. Two fixes: a new open site got its active mark late, and the open site's recent card is now marked.
- Preferences (1ae52c5). It already was the family's node-wire dialog (the rail outside the dialog's left edge, one wire from the chosen tab to a port, every panel a card in one scroller). New panels: Checks (`prefs-checks.ts`: the browser for the deep check) and Signing keys (`prefs-keys.ts`). `openPreferences(section)` sets the scroll position, chooses the tab and draws the wire before the dialog is shown, and there is one dialog for the window (`bindPreferences`). The Package sheet keeps the key chooser, the passphrase, Sign and Verify, with a Manage keys chip; the two chip labels share one grid cell so it never changes width. The deep.unavailable row and the FormWeb unreachable notice carry Open Preferences.
- The agent dock (55c6b42). `frontend/src/dock/` is FormVis's module 2.2.1, 15 files, byte for byte (`setup/dock_check.py`), compiled by `tsconfig.dock.json` with the seven strict flags its contract names. `dock-adapter.ts` is this window's part: typed `DockAdapter<'antigravity'>`, words for a site, `tabs()` from the engine's `available` list plus Claude Code whenever a shell is available (so the ask line and the install note show when it is missing), no Chat, consent or stored choice, the chord read from the View command's current keys, `onTheme` on `fp:ui-settings-changed`, errors mapped to the module's kinds, channels that buy a ticket before opening the stream, status from `/api/agent-programs`. `app.ts` reserves the dock's grid row or column before the shell mounts (`reserveDock`), and `chrome.ts` mounts it, adds View, Agent Dock and the title bar button, and keeps the dock usable over Home, whose `lock()` makes the root's children inert. `dock-tokens.css` maps the module's tokens; `--dock-accent` is the accent ink. xterm loads as its own chunk.
- Strings: part35 (5), part36 (50), part37 (21), in all 25 locale folders; 885 strings.
- Checked in headless Chrome 1440 by 900 with the CPU throttled 4 times, every agent program a stand-in: each view above, every dropdown by mouse and keyboard, menus, a light theme, the strip folded and reloaded folded, keyboard resizing, the compare and the picker opened twice, Preferences at each panel from its chip, keys created, exported, removed and imported, a browser path saved and cleared, the dock at the bottom and on the right restored on reload, a shell round trip and a Claude Code tab from the ask line: layout shift 0, no console error. Not checked: dragging with a real pointer, reduced motion, the desktop web views, the macOS key caps, the dock's words after a language switch without a reload, the translations by a reader of each language. One run of the lead's before the stand-ins were forced may have let the finder run the real `claude` installed in this workspace for its version and sign-in status (no session); the rehearsal tool now points every program at a stand-in.

## Phase 73: the Speed block in the Problems tab · v0.9.0 (2026-11-22)

`api-checks.ts`: `Measure` (route, width, cls, lcp, lcpElement, contrast, notes) and `ContrastCount`, read by `toMeasure()` with the same defensive checks as `thumbs`; `fetchResults` returns `measures`.

`ui/panel.ts`: `SPEED_HTML`, `SPEED_ROW` and `SPEED_CELL` are built once in the constructor; the section is appended to the problems list without a `data-key`, so `patchList` over the problem rows never removes or moves it (it skips unkeyed children and inserts keyed rows before the cursor, which leaves the section last). `paintSpeed()` hides it when there are no measures or the tier filter is Static or Live, sets `--fp-speed-n` to the width count, and patches the width headings, one row per route and one cell per width in place. Marks reuse `.fp-pn-sev` with the alert and close icons, `role="img"` and a translated aria-label, at deep.py's lines: LCP over 2.5 s warning, over 4 s error; CLS above 0 warning, 0.1 or more error. A null value shows "-". The cell's title names the largest element and any note. With every problem filtered out, the empty line moves to a 26 px band (`is-speed-only`) so it does not cover the block.

`styles/panel.css`: the row style and spacing tokens of the list, `--fs-font-mono` with tabular figures; below 520 px a row takes two lines.

i18n part38: "Speed", the note, "Largest element: {0}", "Not measured", "Warning", "Error" in 25 languages; 891 strings in 36 key files.

Checked here: tsc and vite build; i18n_check; a deep run on Northwind Notes in Chrome with the CPU at 4x, watched with a MutationObserver and a layout-shift observer: the block appeared in one paint with 4 rows and 8 cells and nothing above it moved (the one shift, 0.008, came from deep problems sorted in among the existing rows, as before). Screenshots at 1280 and 390 in dark, light and sand, in German, and the warning and error marks with values substituted in the page. Not checked: the desktop web views, a screen reader reading the marks, the translations by a reader of each language.
