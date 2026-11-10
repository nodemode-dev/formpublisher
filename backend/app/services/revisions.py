import threading
from datetime import datetime, timezone
from pathlib import Path

from app.services import intake, package

_lock = threading.RLock()
# A revision folder never changes after import, so its file table is computed once per process.
_tables: dict[tuple[str, str], dict[str, dict]] = {}
_routes: dict[tuple[str, str], dict[str, dict]] = {}


def _table(site_id: str, root: Path) -> dict[str, dict]:
    key = (site_id, root.name)
    with _lock:
        hit = _tables.get(key)
    if hit is not None:
        return hit
    rows = {rel: {"path": rel, "size": path.stat().st_size, "sha256": package.sha256_file(path)} for rel, path in package.collect(root)}
    with _lock:
        _tables[key] = rows
    return rows


def _route_table(site_id: str, root: Path) -> dict[str, dict]:
    key = (site_id, root.name)
    with _lock:
        hit = _routes.get(key)
    if hit is not None:
        return hit
    rows = {row["path"]: row for row in intake.routes_of(root)[1]}
    with _lock:
        _routes[key] = rows
    return rows


def _stamp_iso(revision: str) -> str | None:
    try:
        return datetime.strptime(revision[:16], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None


def _compare(left: dict[str, dict], right: dict[str, dict]) -> dict:
    added = [right[p] for p in sorted(set(right) - set(left))]
    removed = [left[p] for p in sorted(set(left) - set(right))]
    changed = []
    same = 0
    for path in sorted(set(left) & set(right)):
        if left[path]["sha256"] == right[path]["sha256"]:
            same += 1
        else:
            changed.append(
                {
                    "path": path,
                    "from": {"size": left[path]["size"], "sha256": left[path]["sha256"]},
                    "to": {"size": right[path]["size"], "sha256": right[path]["sha256"]},
                }
            )
    return {"added": added, "removed": removed, "changed": changed, "same": same}


def _revisions_of(site_id: str) -> list[str]:
    record = intake.get_site(site_id)
    return [r for r in (record.get("revisions") or []) if isinstance(r, str)]


def list_revisions(site_id: str) -> dict:
    names = _revisions_of(site_id)
    latest = intake.get_site(site_id).get("revision") or (names[-1] if names else "")
    rows = []
    previous: dict[str, dict] | None = None
    for name in names:
        root = intake.revision_root(site_id, name)
        table = _table(site_id, root)
        row = {
            "revision": name,
            "at": _stamp_iso(name),
            "files": len(table),
            "bytes": sum(item["size"] for item in table.values()),
            "routes": len(_route_table(site_id, root)),
            "latest": name == latest,
            "changes": None,
        }
        if previous is not None:
            delta = _compare(previous, table)
            row["changes"] = {"added": len(delta["added"]), "removed": len(delta["removed"]), "changed": len(delta["changed"])}
        rows.append(row)
        previous = table
    rows.reverse()
    return {"id": site_id, "count": len(rows), "latest": latest, "revisions": rows}


def diff(site_id: str, left: str | None = None, right: str | None = None) -> dict:
    names = _revisions_of(site_id)
    if not names:
        raise intake.IntakeError("this site has no revisions", 404)
    to = right or intake.get_site(site_id).get("revision") or names[-1]
    if to not in names:
        raise intake.IntakeError(f"revision {to} not found", 404)
    if left:
        frm = left
    else:
        index = names.index(to)
        if index == 0:
            raise intake.IntakeError("there is no earlier revision to compare with; this site has one revision", 400)
        frm = names[index - 1]
    if frm not in names:
        raise intake.IntakeError(f"revision {frm} not found", 404)
    root_a = intake.revision_root(site_id, frm)
    root_b = intake.revision_root(site_id, to)
    files = _compare(_table(site_id, root_a), _table(site_id, root_b))
    routes_a = _route_table(site_id, root_a)
    routes_b = _route_table(site_id, root_b)
    routes = {
        "added": sorted(set(routes_b) - set(routes_a)),
        "removed": sorted(set(routes_a) - set(routes_b)),
        "from": len(routes_a),
        "to": len(routes_b),
    }
    table_a = _table(site_id, root_a)
    table_b = _table(site_id, root_b)
    return {
        "id": site_id,
        "from": frm,
        "to": to,
        **files,
        "routes": routes,
        "summary": {
            "added": len(files["added"]),
            "removed": len(files["removed"]),
            "changed": len(files["changed"]),
            "same": files["same"],
            "bytesFrom": sum(item["size"] for item in table_a.values()),
            "bytesTo": sum(item["size"] for item in table_b.values()),
            "identical": not (files["added"] or files["removed"] or files["changed"]),
        },
    }
