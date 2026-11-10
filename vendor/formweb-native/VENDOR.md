# Vendored FormWeb engine crates

FormPublisher builds `formweb-core` from these crates to open `.fweb` projects. They are copied unedited from FormWeb, Copyright 2026 NodeAgentc, Inc., licensed Apache-2.0 (`LICENSE` in this folder), which is compatible with FormPublisher's GPL-3.0-only.

| Field | Value |
| --- | --- |
| Source | `nodemode-dev/formweb`, the `native/` workspace |
| Version | 0.20.2 |
| Branch | `feat/stale-stage-dialog-ids` |
| Tree of `native/` | `34b3b1e14e24bbaaae5f515d0e6f8e2cff916960` |
| `crates/formweb-model` | `655a2c9b7ae71e7bc4a32a820d89f0db63df3b71` |
| `crates/formweb-engine` | `0d7eb4eba5c3ee690650a4dc6756efd6413d467e` |
| `crates/formweb-export` | `51e428757798b51d8895dd32b679a529a633d34e` |
| `crates/formweb-core` | `9a192034c2f2de1d5739855370dbd910062b1550` |
| Left out | `crates/formweb-render` (its own workspace, a GPU renderer FormPublisher does not use) and `target/` |

Tree hashes stay the same when FormWeb's commits are re-signed, so they identify the source even though commit hashes change. To check: `git -C <formweb> rev-parse <commit>:native` must print the tree above.

To update, copy FormWeb's `native/` (without `crates/formweb-render` and `target/`) and its `LICENSE` over this folder unchanged, update this table, stage the folder with `git add vendor/formweb-native`, then run `./setup/install_compiler` (which runs `./formpublisher vendor --check`) and the engine CI job. Never edit files here; changes go to FormWeb first.
