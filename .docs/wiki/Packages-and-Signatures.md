# Packages and signatures

## The build

`site.zip` is deterministic: entries sorted by path, forward slashes, timestamps fixed at 1980-01-01, mode 0644, deflate level 9, no directory entries. The same revision gives the same bytes anywhere. The build id is the first 12 hex digits of the zip's SHA-256.

A build folder, `builds/[site]/[id]/`, holds `site.zip`, `publish.json` (format `formpublisher-site`, version 1: files with SHA-256 and size, routes, redirects, headers, check summary, source kind and FormWeb version), `build.json` (the library record) and, once signed, `site.zip.sig`. `publish.json` is never inside the zip.

Reproduce rebuilds into a temporary folder and compares the hash.

## Keys and signatures

Ed25519 through `cryptography`. The private key is PKCS8 PEM in `keys/[id].pem` (mode 0600, encrypted with a passphrase when given); the public key is raw 32 bytes in base64 in `keys/index.json`. The fingerprint is `SHA256:` plus the unpadded base64 of the SHA-256 of the public key.

`site.zip.sig` is JSON with `algorithm`, `key` (the fingerprint), `publicKey` and `signature`, over the exact zip bytes. Verify answers `valid` and fails if any byte of the zip changed.

## In the window

Package (Mod+Shift+B) builds, reproduces, signs, verifies and downloads. The Builds page in Home lists builds, inspects a file table, compares two builds and deletes. The manual has the file formats in full: `docs/MANUAL.md`.
