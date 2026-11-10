"""Copy regenerated sample files into a demo/ folder. This is the only script that writes into demo/, and only when you name it.

Usage: python3 install_demo.py --demo DEMO_DIR [--zip SITE_ZIP] [--data DATA_DIR]

--demo  the demo folder to update (for example ../ from here). Required, so nothing lands there by accident.
--zip   an export zip from build_site.py: becomes DEMO_DIR/sample-site.zip and replaces DEMO_DIR/sample-site/ (unpacked).
--data  a folder from run_demo.py: its checks.json, publish.json, prepared.json and data.js replace DEMO_DIR/data/.
At least one of --zip and --data is needed. Update MEDIA.md by hand when the pictures change.
"""

import argparse
import shutil
import sys
import zipfile
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--demo", required=True)
ap.add_argument("--zip")
ap.add_argument("--data")
ARGS = ap.parse_args()
demo = Path(ARGS.demo).resolve()
if not demo.is_dir():
    sys.exit(f"the demo folder does not exist: {demo}")
if not ARGS.zip and not ARGS.data:
    sys.exit("give --zip, --data or both")

if ARGS.zip:
    archive = Path(ARGS.zip).resolve()
    if not archive.is_file():
        sys.exit(f"the zip does not exist: {archive}")
    shutil.copyfile(archive, demo / "sample-site.zip")
    target = demo / "sample-site"
    if target.exists():
        shutil.rmtree(target)
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            name = Path(info.filename)
            if name.is_absolute() or ".." in name.parts:
                sys.exit(f"the zip holds an unsafe path: {info.filename!r}")
        zf.extractall(target)
    print("wrote", demo / "sample-site.zip", "and", target)

if ARGS.data:
    source = Path(ARGS.data).resolve()
    names = ("checks.json", "publish.json", "prepared.json", "data.js")
    missing = [n for n in names if not (source / n).is_file()]
    if missing:
        sys.exit(f"missing in {source}: {', '.join(missing)}")
    (demo / "data").mkdir(exist_ok=True)
    for n in names:
        shutil.copyfile(source / n, demo / "data" / n)
    print("wrote", demo / "data")
