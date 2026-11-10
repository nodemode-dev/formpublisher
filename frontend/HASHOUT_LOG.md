# HASHOUT_LOG · frontend · formpublisher

The living log of the FormPublisher frontend. Read it before editing `frontend/`. The code carries no comments; the reasons live here, one entry per file.

Current build version: v0.1.0
Last updated: 2026-11-10 · Phase 3 shell in FormDeck's UI (foundation and window shell)

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
