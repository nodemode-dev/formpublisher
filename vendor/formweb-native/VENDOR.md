# Vendored FormWeb engine crates

FormPublisher builds `formweb-core` from these crates to open `.fweb` projects. They are copied unedited from FormWeb, Copyright 2026 NodeAgentc, Inc., licensed Apache-2.0 (`LICENSE` in this folder), which is compatible with FormPublisher's GPL-3.0-only.

| Field | Value |
| --- | --- |
| Source | `nodemode-dev/formweb`, the `native/` workspace |
| Version | 0.19.1 |
| Branch | `feat/ui-motion-inspector` |
| Tree of `native/` | `37de46c3c454a1ce886f8abcce78d6296fb6e59b` |
| `crates/formweb-model` | `717dbe88427801e2b47c25e086a6899dfa87722a` |
| `crates/formweb-engine` | `8160708e08027f960a202aee6c44a8fb8ad59673` |
| `crates/formweb-export` | `3c1a7a952e5ea5e257e36368b30f3ad399dc2820` |
| `crates/formweb-core` | `915277609ad50b7407636927d589bdd48d9f6504` |
| Left out | `crates/formweb-render` (its own workspace, a GPU renderer FormPublisher does not use) and `target/` |

Tree hashes stay the same when FormWeb's commits are re-signed, so they identify the source even though commit hashes change. To check: `git -C <formweb> rev-parse <commit>:native` must print the tree above.

To update, copy FormWeb's `native/` (without `crates/formweb-render` and `target/`) and its `LICENSE` over this folder unchanged, update this table, then run `./setup/install_compiler` and the engine CI job. Never edit files here; changes go to FormWeb first.
