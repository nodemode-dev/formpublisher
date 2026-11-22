import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
UV_VERSION = "0.11.32"
PYTHON = "3.12"
LOCKS = {
    "requirements.lock": ("requirements.txt", "requirements-deep.txt", "requirements-build.txt"),
    "requirements-test.lock": ("requirements.txt", "requirements-deep.txt", "requirements-build.txt", "requirements-test.txt"),
}
EXTRA = BACKEND / "requirements-extra-hashes.json"
PIN = re.compile(r"^([A-Za-z0-9_.-]+==[^ \;]+)")


def uv() -> list[str]:
    found = shutil.which("uv")
    if found:
        said = subprocess.run([found, "--version"], capture_output=True, text=True).stdout.split()
        if len(said) > 1 and said[1] == UV_VERSION:
            return [found]
    raise SystemExit(f"uv {UV_VERSION} is needed to write the locks: python -m pip install uv=={UV_VERSION}")


def add_extra(text: str) -> str:
    extra = json.loads(EXTRA.read_text(encoding="utf-8"))
    out: list[str] = []
    current = ""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = PIN.match(line)
        if match:
            current = match.group(1)
        last_hash = line.lstrip().startswith("--hash=") and not line.rstrip().endswith("\\")
        if last_hash and current in extra:
            out.append(line.rstrip() + " \\")
            hashes = sorted(extra[current])
            for at, value in enumerate(hashes):
                out.append(f"    --hash=sha256:{value}" + (" \\" if at < len(hashes) - 1 else ""))
            current = ""
            continue
        out.append(line)
    return "\n".join(out) + "\n"


def compile_lock(sources: tuple[str, ...]) -> str:
    with tempfile.TemporaryDirectory() as folder:
        target = Path(folder) / "lock.txt"
        command = [*uv(), "pip", "compile", "--universal", "--python-version", PYTHON, "--generate-hashes", "--no-header", "--no-annotate", "--quiet", *sources, "-o", str(target)]
        done = subprocess.run(command, cwd=BACKEND, capture_output=True, text=True)
        if done.returncode != 0:
            raise SystemExit(done.stderr.strip() or "uv could not resolve the requirements")
        return add_extra(target.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Write backend/requirements.lock and requirements-test.lock with hashes, or check them.")
    parser.add_argument("--check", action="store_true", help="fail when a lock does not hold exactly the pins of its requirement files")
    args = parser.parse_args()
    if not args.check:
        for name, sources in LOCKS.items():
            (BACKEND / name).write_text(compile_lock(sources), encoding="utf-8")
            print(f"[formpublisher] wrote backend/{name}")
        return 0
    problems = []
    for name, sources in LOCKS.items():
        lock = (BACKEND / name).read_text(encoding="utf-8") if (BACKEND / name).is_file() else ""
        locked = {m.group(1).lower().replace("_", "-") for m in (PIN.match(line) for line in lock.splitlines()) if m}
        for source in sources:
            for raw in (BACKEND / source).read_text(encoding="utf-8").splitlines():
                pin = re.sub(r"\[[^\]]*\]", "", raw.split("#", 1)[0].split(";", 1)[0].strip()).lower().replace("_", "-")
                if pin and not pin.startswith("#") and pin not in locked:
                    problems.append(f"backend/{name} does not hold {raw.strip()} from backend/{source}")
        if "--hash=sha256:" not in lock:
            problems.append(f"backend/{name} has no hashes")
    for problem in problems:
        print(f"[formpublisher] {problem}", file=sys.stderr)
    if problems:
        print("[formpublisher] run: python setup/lock_requirements.py", file=sys.stderr)
        return 1
    print("[formpublisher] the requirement locks hold every pin")
    return 0


if __name__ == "__main__":
    sys.exit(main())
