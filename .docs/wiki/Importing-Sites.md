# Importing Sites

FormPublisher imports sites made by FormWeb. It reads them and never changes them.

## A site export

FormWeb's export produces a `site-export.zip`. Drop it on Home, or run `./formpublisher run import path/to/site-export.zip`. The export carries `routes.json` (each route has a path, a page, a locale, an item and a stylesheet), `sitemap.xml`, `robots.txt` and, when the site has any, `redirects.json` and `site.webmanifest`.

## A publication folder

A FormWeb publication lives in a folder shaped `publications/[slug]/[version]/`. Choose the folder in the file dialog, or run `./formpublisher run import path/to/that/folder`. It carries the same files as an export.

## The site open in FormWeb

With FormWeb running on the same computer, FormPublisher can import the site FormWeb currently has open. It asks FormWeb's engine for `GET /api/export` over loopback and imports the zip it gets back. FormWeb's read-only routes are the only ones FormPublisher uses; it never calls `/api/load`, which would replace the document FormWeb has open.

## A .fweb project

A `.fweb` file (the envelope with format `com.nodemode.formweb`) imports like a zip or a folder, with source kind `fweb`. FormPublisher exports it through `formweb-core`, built from the vendored FormWeb crates by `./setup/install_compiler` (it needs Rust; `./formpublisher_oc_install` runs it when `cargo` is present). It first runs `./formpublisher vendor --check` (`setup\install_compiler.bat` runs `setup\vendor_check.py --check` on Windows), which refuses to build when the vendored crates are out of step with `vendor/formweb-native/VENDOR.md`, `Cargo.lock` or the staged tree. Without the binary the import answers 422 and names that command. `FORMPUBLISHER_FORMWEB_CORE` points to a binary elsewhere.

FormWeb 0.19.4 writes a version 2 `.fweb`, a zip with `project.json` first and the assets stored as `assets/[id]`, when a project is too big for the JSON envelope. It imports the same way, up to 512 MiB, after FormWeb's own checks (at most 500 assets, every member listed, digests and mime types matching). A bad file is refused with the reason, and a version 2 zip is recognised even without the `.fweb` extension.

## A .fpub package

A `.fpub` is one build saved from FormPublisher: a zip holding `fpub.json`, `publish.json`, `site.zip` and, when the build was signed, `site.zip.sig`. Open it from Home's Open, the file picker or a drop, with `./formpublisher run import FILE.fpub`, with the MCP tool `import_site`, or by posting it to `POST /api/sites/import`. It is recognised first, by its name or by `fpub.json` being the first entry.

Before anything is written, FormPublisher checks the format and version, the exact entries, the size and SHA-256 of `site.zip` against `fpub.json` and `publish.json`, and the signature against the Ed25519 key the file carries. Then it imports `site.zip` as a revision of the same site id and restores the build under its id. If that id is already taken (for example, opening the same file twice), the build gets a new id and the answer says it was remapped. A file that fails a check is refused with the reason and changes nothing. The limit is 512 MiB. The entries and the `fpub.json` fields are in `docs/MANUAL.md`, under The .fpub format.

## After an import

The site appears in Home and in a tab. The routes strip lists every route, and the inspector shows the page, locale, item and stylesheet of the selected one. Re-importing a newer export of the same site adds a new revision rather than overwriting the old one.

## When an import fails

The message names the reason, for example that the file is not a zip, that `routes.json` is missing, or that no FormWeb answered on loopback. Nothing is written for a failed import. Next: [Preview](Preview) and [Checks](Checks).
