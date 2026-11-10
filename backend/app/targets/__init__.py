"""Host adapters, discovered by module the way the routers are.

A target module exposes ID, NAME, DESCRIPTION, LOCAL_TOOL and prepare(inp, out) -> PreparedResult.
Modules whose names start with an underscore are helpers and are not targets.
"""

import importlib
import logging
import pkgutil
from types import ModuleType

log = logging.getLogger("formpublisher")
ORDER = ("static-zip", "netlify", "cloudflare-pages", "vercel", "github-pages", "nginx")
_cache: dict[str, ModuleType] | None = None


def registry() -> dict[str, ModuleType]:
    global _cache
    if _cache is not None:
        return _cache
    found: dict[str, ModuleType] = {}
    for info in pkgutil.iter_modules(__path__):
        if info.name.startswith("_"):
            continue
        try:
            module = importlib.import_module(f"{__name__}.{info.name}")
        except Exception:
            log.exception("target %s failed to import", info.name)
            continue
        ident = getattr(module, "ID", None)
        if isinstance(ident, str) and callable(getattr(module, "prepare", None)):
            found[ident] = module
    ordered = {k: found[k] for k in ORDER if k in found}
    ordered.update({k: found[k] for k in sorted(found) if k not in ordered})
    _cache = ordered
    return ordered


def get(target_id: str) -> ModuleType | None:
    return registry().get(target_id)


def describe() -> list[dict]:
    return [
        {
            "id": m.ID,
            "name": getattr(m, "NAME", m.ID),
            "description": getattr(m, "DESCRIPTION", ""),
            "localTool": getattr(m, "LOCAL_TOOL", None),
        }
        for m in registry().values()
    ]
