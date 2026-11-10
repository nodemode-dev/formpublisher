# Importing Sites

FormPublisher imports sites made by FormWeb. It reads them and never changes them.

## A site export

FormWeb's export produces a `site-export.zip`. Drop it on Home, or run `./formpublisher run import path/to/site-export.zip`. The export carries `routes.json` (each route has a path, a page, a locale, an item and a stylesheet), `sitemap.xml`, `robots.txt` and, when the site has any, `redirects.json` and `site.webmanifest`.

## A publication folder

A FormWeb publication lives in a folder shaped `publications/[slug]/[version]/`. Choose the folder in the file dialog, or run `./formpublisher run import path/to/that/folder`. It carries the same files as an export.

## The site open in FormWeb

With FormWeb running on the same computer, FormPublisher can import the site FormWeb currently has open. It asks FormWeb's engine for `GET /api/export` over loopback and imports the zip it gets back. FormWeb's read-only routes are the only ones FormPublisher uses; it never calls `/api/load`, which would replace the document FormWeb has open.

## A .fweb project

A `.fweb` file (the envelope with format `com.nodemode.formweb`) imports like a zip or a folder, with source kind `fweb`. FormPublisher exports it through `formweb-core`, built from the vendored FormWeb crates by `./setup/install_compiler` (it needs Rust; `./formpublisher_oc_install` runs it when `cargo` is present). Without the binary the import answers 422 and names that command. `FORMPUBLISHER_FORMWEB_CORE` points to a binary elsewhere.

## After an import

The site appears in Home and in a tab. The routes strip lists every route, and the inspector shows the page, locale, item and stylesheet of the selected one. Re-importing a newer export of the same site adds a new revision rather than overwriting the old one.

## When an import fails

The message names the reason, for example that the file is not a zip, that `routes.json` is missing, or that no FormWeb answered on loopback. Nothing is written for a failed import. Next: [Preview](Preview) and [Checks](Checks).
