# demo/tools

The scripts that made the Northwind Notes sample site and the data the offline demo shows. They are plain Python 3 with no extra dependency except Pillow for the pictures. Every path and port is an argument. Nothing writes into `demo/` unless you run `install_demo.py` and name the folder.

| Script | What it does | Needs |
| --- | --- | --- |
| `gen_images.py OUT_DIR` | Draws the nine `notes-*.webp` pictures (CC0, see `../MEDIA.md`). The output is byte for byte the same on every run. | Pillow, DejaVu Sans fonts |
| `build_site.py --formweb URL --images DIR --out ZIP` | Builds the site in a running FormWeb backend (library sections re-cast with new text, a few native sections, redirects, SEO) and writes the `GET /api/export` zip. | A FormWeb backend |
| `run_demo.py --engine URL --out DIR (--zip ZIP or --bundled) [--name N] [--include-model]` | Imports the site into a FormPublisher engine, runs the static checks, builds the package and prepares all six hosts. Writes `checks.json`, `publish.json`, `prepared.json` and `data.js`. | A FormPublisher engine |
| `install_demo.py --demo DIR [--zip ZIP] [--data DIR]` | Copies the zip to `sample-site.zip`, unpacks it into `sample-site/` and copies the data files into `data/`. The only script that writes into `demo/`. | Nothing |

## Run it end to end into a scratch folder

Use private ports and a private data folder for both apps. `build_site.py` replaces the open document of the FormWeb backend it talks to, and `run_demo.py` adds a site, a build and prepared folders to the engine's data folder.

```
# FormWeb backend (from the formweb repository)
FORMWEB_PORT=8398 FORMWEB_DATA_DIR=/tmp/fw-scratch/data backend/venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8398

# FormPublisher engine (from backend/)
FORMPUBLISHER_HOME=/tmp/fp-scratch/home FORMPUBLISHER_PORT=8393 FORMPUBLISHER_HOST_PORT=8394 FORMPUBLISHER_WATCH_PARENT=0 ./venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8393

# the tools (any folder; scratch/ is yours)
python3 demo/tools/gen_images.py scratch/img
python3 demo/tools/build_site.py --formweb http://127.0.0.1:8398 --images scratch/img --out scratch/site-export.zip
python3 demo/tools/run_demo.py --engine http://127.0.0.1:8393 --zip scratch/site-export.zip --out scratch/data
```

Stop both servers when you are done.

## What differs from the committed demo

A regenerated `data/` is not byte for byte the committed one. Expect these differences, and only these:

- the build id, the site id and the revision (the site id comes from the import source, the revision from the clock) and `preparedAt` times;
- the file hashes of the pages and stylesheets, because FormWeb gives every inserted section a fresh random node id;
- the pictures keep the same hashes;
- host folders no longer hold `site.formweb.json` and `asset-access.json`, since the publish step leaves FormWeb's model files out by default. Pass `--include-model` to `run_demo.py` to keep them. `leftOut` and `includeModel` appear in `prepared.json`.

To refresh the committed demo on purpose, run `install_demo.py --demo demo --zip scratch/site-export.zip --data scratch/data` and update `MEDIA.md` if a picture changed.
