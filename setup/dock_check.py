import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCK = ROOT / "frontend" / "src" / "dock"
MANIFEST = DOCK / "MANIFEST.json"


def main() -> int:
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"[formpublisher] dock: MANIFEST.json cannot be read: {exc}", file=sys.stderr)
        return 1
    listed = manifest.get("files") if isinstance(manifest, dict) else None
    if not isinstance(listed, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in listed.items()):
        print("[formpublisher] dock: MANIFEST.json has no files table", file=sys.stderr)
        return 1
    present = {p.name for p in DOCK.iterdir() if p.name != MANIFEST.name}
    problems: list[str] = []
    for name in sorted(set(listed) | present):
        if name not in present:
            problems.append(f"{name}: listed in MANIFEST.json but missing")
        elif name not in listed:
            problems.append(f"{name}: not listed in MANIFEST.json (extra file)")
        elif not (DOCK / name).is_file():
            problems.append(f"{name}: not a file")
        elif hashlib.sha256((DOCK / name).read_bytes()).hexdigest() != listed[name]:
            problems.append(f"{name}: differs from MANIFEST.json (the shared dock module changes only as a whole new version)")
    for problem in problems:
        print(f"[formpublisher] dock: {problem}", file=sys.stderr)
    if problems:
        return 1
    print(f"[formpublisher] dock module {manifest.get('version', '?')}: {len(listed)} files match MANIFEST.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
