"""Run the sample site through a FormPublisher engine and write the data the offline demo shows.

Usage: python3 run_demo.py --engine http://127.0.0.1:PORT --key-file HOME/engine.key --out OUT_DIR (--zip SITE_ZIP | --bundled) [--name NAME] [--include-model]

--engine         a running FormPublisher engine (use a private data folder: it gets a site, a build and prepared folders).
--key-file       the engine.key in that engine's data folder, so the engine accepts the requests as its command line's.
--zip            the export zip to import (from build_site.py, or demo/sample-site.zip). It must be readable by the engine.
--bundled        instead of --zip, open the sample site bundled with the engine (POST /api/demo/sample).
--name           site name for --zip (default northwind-notes).
--include-model  keep FormWeb's model files in the prepared host folders (default: leave them out).
--out            folder for checks.json, publish.json, prepared.json and data.js. Created when missing. Never demo/ unless you say so.
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--engine", required=True)
ap.add_argument("--out", required=True)
src = ap.add_mutually_exclusive_group(required=True)
src.add_argument("--zip")
src.add_argument("--bundled", action="store_true")
ap.add_argument("--name", default="northwind-notes")
ap.add_argument("--include-model", action="store_true")
ap.add_argument("--key-file", required=True)
ARGS = ap.parse_args()
B = ARGS.engine.rstrip("/")
KEY = json.loads(Path(ARGS.key_file).read_text(encoding="utf-8"))["key"]
OUT = Path(ARGS.out)


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"x-formpublisher-key": KEY, **({"content-type": "application/json"} if data else {})}
    req = urllib.request.Request(B + path, data=data, method=method, headers=headers)
    try:
        return json.loads(urllib.request.urlopen(req, timeout=300).read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{method} {path} failed {e.code}: {e.read()[:500].decode(errors='replace')}")
    except urllib.error.URLError as e:
        raise SystemExit(f"the engine is not reachable at {B}: {e.reason}")


if ARGS.bundled:
    site = call("POST", "/api/demo/sample")["site"]
else:
    zip_path = Path(ARGS.zip).resolve()
    if not zip_path.is_file():
        sys.exit(f"the zip does not exist: {zip_path}")
    site = call("POST", "/api/sites/import", {"path": str(zip_path), "name": ARGS.name})
    site = site.get("site", site)
sid, rev = site["id"], site["revision"]
print("site", sid, "revision", rev)
call("POST", "/api/checks/run", {"site": sid, "revision": rev, "tiers": ["static"]})
checks = None
for _ in range(60):
    try:
        checks = call("GET", f"/api/checks/{sid}/{rev}")
        break
    except SystemExit:
        time.sleep(0.5)
if checks is None:
    sys.exit("the checks did not finish")
build = call("POST", "/api/builds", {"site": sid})
bid = build.get("id") or build.get("build", {}).get("id")
targets = call("GET", "/api/targets")
ids = [t["id"] for t in (targets["targets"] if isinstance(targets, dict) else targets)]
prep = call("POST", "/api/publish/prepare", {"build": bid, "targets": ids, "includeModel": ARGS.include_model})

OUT.mkdir(parents=True, exist_ok=True)
parts = {"checks": checks, "publish": build, "prepared": prep}
for key, name in (("checks", "checks.json"), ("publish", "publish.json"), ("prepared", "prepared.json")):
    (OUT / name).write_text(json.dumps(parts[key], indent=2, sort_keys=True), encoding="utf-8")
(OUT / "data.js").write_text(
    "/* Generated from checks.json, publish.json and prepared.json (real runs of the engine). Loaded as a script so the demo opens from disk. */\nwindow.FP_DEMO = "
    + json.dumps(parts, indent=1, sort_keys=True)
    + ";\n",
    encoding="utf-8",
)
print("build", bid, "targets", ids, "->", OUT)
