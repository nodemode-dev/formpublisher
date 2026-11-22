# Vendored FormWeb engine crates

FormPublisher builds `formweb-core` from these crates to open `.fweb` projects. They are copied unedited from FormWeb, Copyright 2026 NodeAgentc, Inc., licensed Apache-2.0 (`LICENSE` in this folder), which is compatible with FormPublisher's GPL-3.0-only.

| Field | Value |
| --- | --- |
| Source | `nodemode-dev/formweb`, the `native/` workspace |
| Version | 0.27.0 |
| Branch | tag `v0.27.0` (the 0.27.0 release commit) |
| Tree of `native/` | `7f03a72dfa12c23fc4fd05f1fa6d1e2721c51a38` |
| `crates/formweb-model` | `54605f901cdefb3b69a9c413760e59e65ea648fd` |
| `crates/formweb-engine` | `e0bc7316e6038f7264c47dca3773e03f5de8a045` |
| `crates/formweb-export` | `44091cb16e0211fb7b2322d68727b6c58a813484` |
| `crates/formweb-core` | `9a192034c2f2de1d5739855370dbd910062b1550` |
| Left out | `crates/formweb-render` (its own workspace, a GPU renderer FormPublisher does not use) and `target/` |

Tree hashes stay the same when FormWeb's commits are re-signed, so they identify the source even though commit hashes change. To check: `git -C <formweb> rev-parse <commit>:native` must print the tree above.

To update, copy FormWeb's `native/` (without `crates/formweb-render` and `target/`) and its `LICENSE` over this folder unchanged, update this table, stage the folder with `git add vendor/formweb-native`, then run `./setup/install_compiler` (which runs `./formpublisher vendor --check`) and the engine CI job. Never edit files here; changes go to FormWeb first.
