# Checks

Checks produce problems with a stable id (a deep problem's id does not depend on the host's port, so it is the same on every run), a tier (`static`, `live`, `deep`), a severity (`error`, `warning`, `info`), a code, a route, a message and a fix. The Problems tab lists them, filters by severity and tier, and selects the route of a clicked row.

## Static

Runs offline on the revision's files. Codes: `link.broken`, `link.anchor`, `asset.missing`, `redirect.loop`, `redirect.chain`, `redirect.target`, `sitemap.missing`, `sitemap.extra`, `robots.sitemap`, `robots.blocks`, `meta.title`, `meta.description`, `meta.lang`, `img.size`, `img.alt`, `heading.h1`, `heading.order`, `external.request`, `budget.file` and `budget.page`. Each code's rule and severity is a table in the manual.

## Live

From the preview probe: console errors, page errors and failed requests are errors; console warnings are warnings; layout shift of 0.001 or more is a warning and 0.1 or more an error; overflow is an error. A shift within 500 ms of the preview frame changing size, or before the page's first paint, is the preview's doing and is not counted. Live problems reach the engine at most once a second.

## Deep

Serves the revision through the same site host as the preview and drives the Chrome you already have installed with Playwright, at 1440 and 390 wide, with a 4x CPU slowdown and a slow network. Codes: `deep.console`, `deep.pageerror`, `deep.request`, `deep.external`, `deep.cls`, `deep.overflow`, and `deep.unavailable` (info) when Playwright or Chrome is missing. It saves a thumbnail per route under `checks/[site]/[revision]/thumbs/`. FormPublisher never downloads a browser; the optional requirements are in `backend/requirements-deep.txt`.

## Storing results

Static and deep results are kept per revision in `checks/[site]/[revision]/results.json`. Live results are merged in memory.
