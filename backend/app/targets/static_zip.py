import hashlib
import shutil
from pathlib import Path

from app.targets._common import PreparedInput, PreparedResult, put

ID = "static-zip"
NAME = "Static zip"
DESCRIPTION = "The signed-ready site.zip with checksums, for any host that takes a folder or an archive."
LOCAL_TOOL = "python3 -m http.server -d site 8080"

README = """FormPublisher static package: {name}

site.zip      the deterministic package, byte for byte what FormPublisher built
publish.json  the manifest: every file with its SHA-256, the routes, redirects and headers
SHA256SUMS    checksums for site.zip and publish.json

Check it:       sha256sum -c SHA256SUMS
Unpack it:      unzip site.zip -d site
Look at it:     python3 -m http.server -d site 8080   then open http://127.0.0.1:8080/

Upload the contents of site/ to any static host. Redirects and headers are listed in
publish.json; the other targets in FormPublisher turn them into a host's own files.
"""


def prepare(inp: PreparedInput, out: Path) -> PreparedResult:
    result = PreparedResult()
    shutil.copyfile(inp.zip_path, out / "site.zip")
    put(out, "publish.json", inp.publish_bytes)
    sums = []
    for name in ("publish.json", "site.zip"):
        sums.append(f"{hashlib.sha256((out / name).read_bytes()).hexdigest()}  {name}")
    put(out, "SHA256SUMS", "\n".join(sums) + "\n")
    put(out, "README.txt", README.format(name=inp.site_name))
    result.command("Unpack the package", "unzip site.zip -d site")
    result.command("Serve it locally", "python3 -m http.server -d site 8080")
    result.notes.append("site.zip is the build's own bytes, so its hash matches publish.json and any signature.")
    result.notes.append("This host has no server rules: redirects and headers in publish.json are not applied by a plain file server.")
    return result
