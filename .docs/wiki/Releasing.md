# Releasing

1. Versions are `X.Y.Z`. Raise the version in every site in one commit: `frontend/package.json`, `frontend/src/version.ts`, `backend/app/__init__.py`, `src-tauri/tauri.conf.json` and `src-tauri/Cargo.toml`, plus the README badge, the lockfiles and `CHANGELOG.md`.
2. `./formpublisher build`, then `setup/freeze_backend` (its self-check must pass) and `./formpublisher desktop build`.
3. Commits have one author and committer, `nodemode-ai <mackin@nodemode.ai>`, and no trailers. The release commit is `chore(release): X.Y.Z`.
4. Every shipped dependency has its row in `NOTICE.md`; GPL stays out of the bundle.
5. The repository starts at 0.0.0 (the foundations); the first release is 0.1.0.
