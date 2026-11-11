# Vendored FormWeb engine crates

FormPublisher builds `formweb-core` from these crates to open `.fweb` projects. They are copied unedited from FormWeb, Copyright 2026 NodeAgentc, Inc., licensed Apache-2.0 (`LICENSE` in this folder), which is compatible with FormPublisher's GPL-3.0-only.

| Field | Value |
| --- | --- |
| Source | `nodemode-dev/formweb`, the `native/` workspace |
| Version | 0.19.3 |
| Branch | `feat/mcp-motion-handoff` |
| Tree of `native/` | `b6af8bddf1a1d2d38c90dbec2cc1dc9f075499d9` |
| `crates/formweb-model` | `17b814c06c416f61ab6d481d8a8bf2cf850d09e0` |
| `crates/formweb-engine` | `30db6ad9f7cc222040621909e754f32b6d11ddb3` |
| `crates/formweb-export` | `a19c6996bb4f2854fcaa87cc8e096c1bce9281d5` |
| `crates/formweb-core` | `915277609ad50b7407636927d589bdd48d9f6504` |
| Left out | `crates/formweb-render` (its own workspace, a GPU renderer FormPublisher does not use) and `target/` |

Tree hashes stay the same when FormWeb's commits are re-signed, so they identify the source even though commit hashes change. To check: `git -C <formweb> rev-parse <commit>:native` must print the tree above.

To update, copy FormWeb's `native/` (without `crates/formweb-render` and `target/`) and its `LICENSE` over this folder unchanged, update this table, then run `./setup/install_compiler` and the engine CI job. Never edit files here; changes go to FormWeb first.
