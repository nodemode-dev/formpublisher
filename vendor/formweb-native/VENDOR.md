# Vendored FormWeb engine crates

FormPublisher builds `formweb-core` from these crates to open `.fweb` projects. They are copied unedited from FormWeb, Copyright 2026 NodeAgentc, Inc., licensed Apache-2.0 (`LICENSE` in this folder), which is compatible with FormPublisher's GPL-3.0-only.

| Field | Value |
| --- | --- |
| Source | `nodemode-dev/formweb`, the `native/` workspace |
| Version | 0.19.8 |
| Branch | `feat/404-pages-agent-clips` |
| Tree of `native/` | `e6cd48b224849a9916c67b4119eddd28ddd8e21d` |
| `crates/formweb-model` | `655a2c9b7ae71e7bc4a32a820d89f0db63df3b71` |
| `crates/formweb-engine` | `7f6b0b258290aeef28b394c434e58ad50d83e757` |
| `crates/formweb-export` | `51e428757798b51d8895dd32b679a529a633d34e` |
| `crates/formweb-core` | `9a192034c2f2de1d5739855370dbd910062b1550` |
| Left out | `crates/formweb-render` (its own workspace, a GPU renderer FormPublisher does not use) and `target/` |

Tree hashes stay the same when FormWeb's commits are re-signed, so they identify the source even though commit hashes change. To check: `git -C <formweb> rev-parse <commit>:native` must print the tree above.

To update, copy FormWeb's `native/` (without `crates/formweb-render` and `target/`) and its `LICENSE` over this folder unchanged, update this table, then run `./setup/install_compiler` and the engine CI job. Never edit files here; changes go to FormWeb first.
