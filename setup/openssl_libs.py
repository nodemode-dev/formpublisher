"""Print the OpenSSL libraries that cryptography's binding links dynamically, one path a line.

    python -I setup/openssl_libs.py

setup/freeze_backend passes each one to PyInstaller with --add-binary, so the
engine folder holds the OpenSSL cryptography was built against. PyInstaller
keeps the first library of a given name it meets, and the python.org Python's
own _ssl brings an older libssl.3.dylib (OpenSSL 3.0) that lacks symbols a
cryptography built against OpenSSL 3.2 or later needs. Given first, the newer
libraries win, and Python's _ssl runs on them too (OpenSSL keeps one ABI across
3.x). A cryptography wheel with OpenSSL built in, as on PyPI, prints nothing.
"""

import os
import sys

NAMES = ("libssl", "libcrypto")


def main() -> int:
    try:
        from PyInstaller.depend import bindepend
        import cryptography.hazmat.bindings._rust as binding
    except Exception:
        return 0
    for name, path in bindepend.get_imports(binding.__file__):
        if path and os.path.basename(name or "").startswith(NAMES) and os.path.isfile(path):
            print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
