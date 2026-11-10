# Vendored FormWeb engine crates

FormPublisher builds `formweb-core` from these crates to open `.fweb` projects. They are copied unedited from FormWeb, Copyright 2026 NodeAgentc, Inc., licensed Apache-2.0 (`LICENSE` in this folder), which is compatible with FormPublisher's GPL-3.0-only.

| Field | Value |
| --- | --- |
| Source | `nodemode-dev/formweb`, the `native/` workspace |
| Version | 0.19.6 |
| Branch | `feat/fragments-look-assets` |
| Tree of `native/` | `9296c40dbb65e4ce45d28c5ee6eb9b91bf009336` |
| `crates/formweb-model` | `272ba3b3a7d2aa19abee23d4dc930281c113ec5e` |
| `crates/formweb-engine` | `dc4514fb27e730a96cfd04a84b4f57fe3a155513` |
| `crates/formweb-export` | `f33bd34dbc902fdd7b8aa9ddcfb92c499d600f11` |
| `crates/formweb-core` | `9a192034c2f2de1d5739855370dbd910062b1550` |
| Left out | `crates/formweb-render` (its own workspace, a GPU renderer FormPublisher does not use) and `target/` |

Tree hashes stay the same when FormWeb's commits are re-signed, so they identify the source even though commit hashes change. To check: `git -C <formweb> rev-parse <commit>:native` must print the tree above.

To update, copy FormWeb's `native/` (without `crates/formweb-render` and `target/`) and its `LICENSE` over this folder unchanged, update this table, then run `./setup/install_compiler` and the engine CI job. Never edit files here; changes go to FormWeb first.
