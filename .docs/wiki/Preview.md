# Preview

Opening a site mounts a revision on the site host, a second listener at 127.0.0.1:8281 (`FORMPUBLISHER_HOST_PORT`). It serves the files the way a production static host does, on its own origin, so the site has its own storage and cannot call the engine's `/api` routes. One site is mounted at a time.

## What the host does

- Resolves `/a/b` to the file, then `a/b/index.html`, then `a/b.html`; `/` is `index.html`.
- Applies `redirects.json` when no file matches (301, 302, 307, 308, or a 200 rewrite; a trailing `*` maps to `:splat`).
- Answers a missing path with the root `404.html`, or with `404/index.html` when there is no `404.html`. For that fallback it makes the page's URLs root-absolute, as the publish targets do.
- Supports single-range requests, sets `Cache-Control: no-store`, and accepts only `GET` and `HEAD` for its own Host.

## The options toolbar

Route field, device presets (Desktop 1440 by 900, Laptop 1280 by 800, Tablet 834 by 1112, Phone 390 by 844, Custom), rotate, zoom (Fit, 50, 75, 100 percent), theme (Auto, Dark, Light), motion (Auto, Reduce), network (None, Fast, Slow), Reload and Open in browser.

Theme, motion and network remount the site and reload the frame; size and zoom never reload. A navigation loads a hidden second frame and swaps it in once loaded, so the page never blanks.

In narrow windows the toolbar keeps every control in its row. Below 1240 px Publish and Package are icon-only and each select is sized to its value. If the row still overflows, the route field becomes an icon that opens as an overlay when focused (Enter navigates, Escape or blur collapses it), and then the selects show short labels (the value after "Theme:", the device name without its size). The bottom panel's tabs show icon and count under 360 px of strip, with the label kept as the accessible name.

## The probe

While previewing, the host injects a small probe script after `<head>`. It emulates the theme and reduced motion, and reports the console, errors, requests, layout shift and overflow to the window. It is never part of a package. See [Checks](Checks) for how those reports become problems.

The full details are in the manual, `docs/MANUAL.md`.
