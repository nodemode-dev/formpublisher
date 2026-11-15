# Vendored FormWeb engine crates

FormPublisher builds `formweb-core` from these crates to open `.fweb` projects. They are copied unedited from FormWeb, Copyright 2026 NodeAgentc, Inc., licensed Apache-2.0 (`LICENSE` in this folder), which is compatible with FormPublisher's GPL-3.0-only.

| Field | Value |
| --- | --- |
| Source | `nodemode-dev/formweb`, the `native/` workspace |
| Version | 0.21.0 |
| Branch | `release/0.21.0` (the 0.21.0 release commit) |
| Tree of `native/` | `300cd1f1d32adbf893ecc224d50c45484a87efb1` |
| `crates/formweb-model` | `09910f36785387a642c839b5bafbf01f6318cf6e` |
| `crates/formweb-engine` | `cfdc5638bd26f84615d89f9246c511796dd59ee5` |
| `crates/formweb-export` | `f1c38ad884d013cccd6395b81c86acd8d79f5d41` |
| `crates/formweb-core` | `9a192034c2f2de1d5739855370dbd910062b1550` |
| Left out | `crates/formweb-render` (its own workspace, a GPU renderer FormPublisher does not use) and `target/` |

Tree hashes stay the same when FormWeb's commits are re-signed, so they identify the source even though commit hashes change. To check: `git -C <formweb> rev-parse <commit>:native` must print the tree above.

To update, copy FormWeb's `native/` (without `crates/formweb-render` and `target/`) and its `LICENSE` over this folder unchanged, update this table, stage the folder with `git add vendor/formweb-native`, then run `./setup/install_compiler` (which runs `./formpublisher vendor --check`) and the engine CI job. Never edit files here; changes go to FormWeb first.
