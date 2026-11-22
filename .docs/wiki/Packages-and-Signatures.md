# Packages and signatures

## The build

`site.zip` is deterministic: entries sorted by path, forward slashes, timestamps fixed at 1980-01-01, mode 0644, deflate level 9, no directory entries. The same revision gives the same bytes anywhere. The build id is the first 12 hex digits of the SHA-256 of the site id, a colon and the zip's SHA-256, so the same bytes imported as two sites get two builds.

A build folder, `builds/[site]/[id]/`, holds `site.zip`, `publish.json` (format `formpublisher-site`, version 1: files with SHA-256 and size, routes, redirects, headers, check summary (`null` when no check had run on the revision; older files show an empty `tiers` list instead), source kind and FormWeb version), `build.json` (the library record) and, once signed, `site.zip.sig`. `publish.json` is never inside the zip.

Reproduce rebuilds into a temporary folder and compares the hash.

## Keys and signatures

Ed25519 through `cryptography`. The public key is raw 32 bytes in base64 in `keys/index.json`, with the name, fingerprint and where its secret is kept. The private key is PKCS8 PEM (encrypted with a passphrase when given) and lives in the system password store through keyring 25.7.0: the Keychain on macOS, the Credential Manager on Windows, the Secret Service on Linux. The store is reached only to create, sign, export, import and remove a key; listing never touches it, `keys/index.json` answers. Where there is no store, the secret is a private file in `keys/` that only the person can read, and a PEM file from an earlier version is adopted on first use. Each key shows where its secret is: Password store, Private file or Verify only. The fingerprint is `SHA256:` plus the unpadded base64 of the SHA-256 of the public key.

Removing a key deletes its secret; the Trash keeps only the public half, and a key restored from it can verify but not sign. Export (`./formpublisher run keys --export ID --to FILE [--force]`, or Export... in Preferences, under Signing keys) writes the private key to a `.pem` file that is always encrypted (a passphrase of at least 8 characters, asked twice, or `FORMPUBLISHER_KEY_PASSPHRASE`) and created readable only by the person; Import (`keys --import FILE [--name NAME]`, or Import...) adds a key from such a file. Both are also `POST /api/keys/{id}/export` and `POST /api/keys/import`. No MCP tool does either, on purpose.

`site.zip.sig` is JSON with `algorithm`, `key` (the fingerprint), `publicKey` and `signature`, over the exact zip bytes. Verify checks that the signature holds over the bytes and then whether the public key it carries is one of the person's own keys. Every answer has `valid`, `known` (the signer's key is one of theirs), `trusted` (both), `signer` (the fingerprint, and the key's name when known) and `message`. A changed byte of the zip is not valid. `valid` with `known` false is a warning, "Signed by a key you do not have.": anyone can sign a changed package with a key of their own, so it does not show who made it. The command line's `verify` exits 1 for that unless `--allow-unknown`, and an imported `.fpub` answers with the same fields.

## One build in one file

Save as .fpub on a row of the builds library (or `./formpublisher run fpub BUILD`, the MCP tool `save_fpub`, `GET /api/builds/BUILD/fpub`) writes the build as a `SITE-BUILD.fpub` (the same name from the window, the CLI and the engine): a zip of `fpub.json`, `publish.json`, `site.zip` and, when signed, `site.zip.sig`, in that order, each with the time 1980-01-01, so the same build always gives the same bytes. `fpub.json` records the site, the build, the revision, the SHA-256 and size of `site.zip` and, when signed, the key id, fingerprint and public key. Opening a `.fpub` checks all of that and the signature before it restores the build; see [Importing Sites](Importing-Sites).

## In the window

Package (Mod+Shift+B) builds, reproduces, chooses a key and signs, verifies (three states: verified with your key, signed by a key you do not have, or invalid) and downloads. It does not make, export, import or remove keys: those are in Preferences, under Signing keys (each key with its name, fingerprint, date and where its secret is kept, New key, Import, Export and Remove), and the sheet's Manage keys chip opens that panel. The Builds page in Home lists builds, inspects a file table, compares two builds, saves one as a `.fpub` and deletes. The manual has the file formats in full: `docs/MANUAL.md`.
