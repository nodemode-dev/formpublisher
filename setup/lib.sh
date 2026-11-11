#!/usr/bin/env bash
FORMPUBLISHER_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export FORMPUBLISHER_ROOT
fp_say() { printf '[formpublisher] %s\n' "$*"; }
fp_die() { printf '[formpublisher] error: %s\n' "$*" >&2; exit 1; }
fp_os() {
  case "$(uname -s 2>/dev/null)" in
    Darwin) echo macos ;;
    Linux) echo linux ;;
    MINGW*|MSYS*|CYGWIN*|*_NT-*) echo windows ;;
    *) echo unknown ;;
  esac
}
fp_python() {
  local c
  for c in python3.13 python3.12 python3 python; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c "import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 12) else 1)" 2>/dev/null; then
      echo "$c"
      return 0
    fi
  done
  return 1
}
fp_rust_env() {
  [ -d "$HOME/.cargo/bin" ] && PATH="$HOME/.cargo/bin:$PATH"
  export PATH
  unset RUSTC RUSTC_WORKSPACE_WRAPPER RUSTFLAGS CARGO_ENCODED_RUSTFLAGS CARGO_BUILD_RUSTFLAGS CARGO_BUILD_TARGET CARGO_TARGET_DIR CARGO_BUILD_TARGET_DIR CARGO_BUILD_RUSTC
  export RUSTC_WRAPPER="" CARGO_BUILD_RUSTC_WRAPPER=""
  if command -v rustup >/dev/null 2>&1 && rustup toolchain list 2>/dev/null | grep -q '^stable'; then
    export RUSTUP_TOOLCHAIN="${FORMPUBLISHER_RUST_TOOLCHAIN:-stable}"
  fi
}
fp_rust_fresh() {
  local target="${CARGO_TARGET_DIR:-$FORMPUBLISHER_ROOT/src-tauri/target}" now
  now="$(rustc -vV 2>/dev/null | tr '\n' ' ')"
  if [ -d "$target/release" ] && [ "$(cat "$target/.formpublisher-rustc" 2>/dev/null)" != "$now" ]; then
    fp_say "the Rust compiler differs from the one that built the Rust folder; cleaning it"
    ( cd "$FORMPUBLISHER_ROOT/src-tauri" && cargo clean )
  fi
  mkdir -p "$target"
  printf '%s' "$now" > "$target/.formpublisher-rustc"
}
