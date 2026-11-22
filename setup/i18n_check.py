import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
I18N = ROOT / "frontend" / "src" / "i18n"
PLACEHOLDER = re.compile(r"\{[^{}]*\}")
LANGUAGE_LIST = re.compile(r"\['([A-Za-z-]+)', '")
EM_DASH = "—"


def placeholders(text: str) -> list[str]:
    return sorted({found[1:-1].split(":", 1)[0] for found in PLACEHOLDER.findall(text)})


def main() -> int:
    problems: list[str] = []
    parts = sorted((I18N / "keys").glob("*.json"))
    listed = [code for code in LANGUAGE_LIST.findall((I18N / "index.ts").read_text(encoding="utf-8").split("];", 1)[0]) if code != "en"]
    folders = sorted(folder.name for folder in (I18N / "locales").iterdir() if folder.is_dir())
    for code in sorted(set(listed) ^ set(folders)):
        problems.append(f"{code}: listed in index.ts or present in locales, not both")
    seen: dict[str, str] = {}
    total = 0
    for part in parts:
        keys = json.loads(part.read_text(encoding="utf-8"))
        if not isinstance(keys, list) or not all(isinstance(key, str) for key in keys):
            problems.append(f"keys/{part.name}: must be a list of strings")
            continue
        total += len(keys)
        for key in keys:
            if EM_DASH in key:
                problems.append(f"keys/{part.name}: an em dash in {key!r}")
            seen.setdefault(key, part.name)
        for code in folders:
            target = I18N / "locales" / code / part.name
            if not target.is_file():
                problems.append(f"locales/{code}/{part.name}: missing")
                continue
            table = json.loads(target.read_text(encoding="utf-8"))
            for key in keys:
                value = table.get(key)
                if not isinstance(value, str) or not value.strip():
                    problems.append(f"locales/{code}/{part.name}: no translation for {key!r}")
                    continue
                if EM_DASH in value:
                    problems.append(f"locales/{code}/{part.name}: an em dash in the translation of {key!r}")
                if placeholders(value) != placeholders(key):
                    problems.append(f"locales/{code}/{part.name}: placeholders differ for {key!r}")
            for extra in sorted(set(table) - set(keys)):
                problems.append(f"locales/{code}/{part.name}: {extra!r} is not a key")
    for code in folders:
        for stray in sorted(set(p.name for p in (I18N / "locales" / code).glob("*.json")) - set(p.name for p in parts)):
            problems.append(f"locales/{code}/{stray}: no keys file of that name")
    for problem in problems[:200]:
        print(f"[formpublisher] {problem}", file=sys.stderr)
    if problems:
        print(f"[formpublisher] {len(problems)} language problems", file=sys.stderr)
        return 1
    print(f"[formpublisher] {total} strings in {len(parts)} key files, complete in {len(folders)} languages beside English")
    return 0


if __name__ == "__main__":
    sys.exit(main())
