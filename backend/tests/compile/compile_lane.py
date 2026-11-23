import importlib.util
import io
import zipfile
from pathlib import Path

_spec = importlib.util.spec_from_file_location("formpublisher_shared_conftest", Path(__file__).resolve().parent.parent / "conftest.py")
shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shared)
DEMO = shared.DEMO
asgi_call = shared.asgi_call
core_path = shared.core_path
write_fweb = shared.write_fweb


def entries_of(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        return [(info.filename, archive.read(info)) for info in archive.infolist()]


def pack(entries):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, payload in entries:
            archive.writestr(name, payload)
    return out.getvalue()
