import asyncio
import os
import sys
from pathlib import Path
from typing import Annotated, Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from mcp_types.version import HANDSHAKE_PROTOCOL_VERSIONS, MODERN_PROTOCOL_VERSIONS
from pydantic import Field

from app import __version__
from app.cli import Client, OpError
from app.services import paths

REVISIONS = (
    f"This server follows MCP revision {MODERN_PROTOCOL_VERSIONS[-1]} (server/discover and per-request metadata) "
    f"and still answers the initialize handshake for revisions {HANDSHAKE_PROTOCOL_VERSIONS[0]} to {HANDSHAKE_PROTOCOL_VERSIONS[-1]}."
)

INSTRUCTIONS = (
    "FormPublisher turns a site built in FormWeb into something that can be checked, packaged and published. "
    "Start with formpublisher_status. Bring a site in with import_site (a FormWeb site export zip, a publication folder, a .fweb project or a .fpub package), "
    "pull the site open in FormWeb with import_formweb_current, or see what FormWeb sent by itself with receive_status; read the result with list_sites, site_routes, list_revisions and diff_revisions, "
    "and look at a revision in a browser with preview_site, which gives addresses on the local preview host and opens nothing. "
    "Then run_checks, build_package, inspect_build, compare_builds and reproduce_build; to sign, call list_keys and sign_build with a key the person named, then verify_build. "
    "Finish with list_targets and prepare_publish, which writes a folder per host with the commands to run (nothing is uploaded), and verify_prepared to confirm a folder still matches its build. "
    "After the person deployed it themselves and asked for it, check_live_site reads their public site at the address they gave and reports what to fix; it uploads nothing. "
    "To start a new site, list_templates reads the template list the person fetched and start_from_template writes a FormWeb project into a folder they named; editing it happens in FormWeb. "
    "Each tool's _meta carries formpublisher/class: read (reads only), data (writes only inside FormPublisher's data folder) or path (writes to a path the person named). "
    "FormPublisher only reads from FormWeb and never changes it. "
    + REVISIONS
)

TOOL_CLASS = {
    "formpublisher_status": "read",
    "list_sites": "read",
    "import_site": "data",
    "import_formweb_current": "data",
    "list_formweb_projects": "read",
    "receive_status": "read",
    "site_routes": "read",
    "list_revisions": "read",
    "diff_revisions": "read",
    "preview_site": "data",
    "run_checks": "data",
    "get_checks": "read",
    "build_package": "data",
    "list_builds": "read",
    "inspect_build": "read",
    "compare_builds": "read",
    "reproduce_build": "data",
    "save_fpub": "path",
    "list_keys": "read",
    "sign_build": "data",
    "verify_build": "read",
    "list_targets": "read",
    "prepare_publish": "data",
    "get_prepared": "read",
    "verify_prepared": "data",
    "check_live_site": "data",
    "list_templates": "read",
    "start_from_template": "path",
    "list_trash": "read",
    "restore_from_trash": "data",
}
CLASSES = ("read", "data", "path")

BuildId = Annotated[str, Field(description="A build id from list_builds.")]
SiteId = Annotated[str, Field(description="A site id from list_sites.")]
Revision = Annotated[str | None, Field(description="A revision id from list_revisions; leave it out for the latest.")]


def build(client: Client | None = None) -> MCPServer:
    link = client or Client()
    server = MCPServer("formpublisher", instructions=INSTRUCTIONS, version=__version__)

    async def run(fn, *args) -> Any:
        try:
            return await asyncio.to_thread(fn, *args)
        except OpError as exc:
            raise ToolError(exc.label()) from exc

    @server.tool(
        name="formpublisher_status",
        description="Report the FormPublisher engine (running engine or in-process), its data folder, how many sites are imported, the settings, and whether FormWeb answers on its loopback address. Read only.",
        annotations=ToolAnnotations(title="FormPublisher status", readOnlyHint=True, idempotentHint=True, openWorldHint=False),
    )
    async def formpublisher_status() -> dict:
        return await run(link.status)

    @server.tool(
        name="list_sites",
        description="List every imported site with its id, name, source, revisions, route count, bytes, redirect counts and import time, newest first. Read only.",
        annotations=ToolAnnotations(title="List sites", readOnlyHint=True, idempotentHint=True, openWorldHint=False),
    )
    async def list_sites() -> dict:
        return await run(link.sites)

    @server.tool(
        name="import_site",
        description="Import a site from an absolute path on this computer: a FormWeb site export zip (routes.json, sitemap.xml, robots.txt and assets/), a FormWeb publication folder, a .fweb project (compiled here with the FormWeb core) or a FormPublisher .fpub package. The source is only read; its files are unpacked safely into FormPublisher's data folder as a new revision and the site record is returned. A .fpub also restores its build (publish.json, site.zip and signature, checked against the key it carries) and the record says so under build; build.signature.known is true only when that key is one of the person's own. Importing the same source again adds a revision.",
        annotations=ToolAnnotations(title="Import a site", readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False),
    )
    async def import_site(path: Annotated[str, Field(description="Absolute path on this computer of one of four inputs: a FormWeb site export .zip, a FormWeb publication folder, a .fweb project file or a .fpub package.")]) -> dict:
        return await run(link.import_path, path)

    @server.tool(
        name="import_formweb_current",
        description="Download the site currently open in FormWeb (its read-only export), or with project one of FormWeb's saved projects (its saved .fweb file, compiled here), and import it into FormPublisher's data folder as a new revision of that project's site. Needs FormWeb running on its loopback address; only reads from it. Returns the site record.",
        annotations=ToolAnnotations(title="Import the current FormWeb site", readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False),
    )
    async def import_formweb_current(project: Annotated[str | None, Field(description="A saved project id from list_formweb_projects; leave it out for the site open in FormWeb.")] = None) -> dict:
        return await run(link.import_formweb, project)

    @server.tool(
        name="list_formweb_projects",
        description="List the running FormWeb's saved projects through its read-only GET /api/projects: id, name, saved time, and which one is open (always first; an open site that was never saved has saved false). Read only.",
        annotations=ToolAnnotations(title="FormWeb projects", readOnlyHint=True, idempotentHint=True, openWorldHint=False),
    )
    async def list_formweb_projects() -> dict:
        return await run(link.formweb_projects)

    @server.tool(
        name="receive_status",
        description="Report FormWeb's Send to FormPublisher inbox: the receive endpoint FormWeb posts to, the inbox folder and whether it is watched, how many files wait in it, auto (whether a site that arrives is checked and built at once, the auto-check and auto-build settings) and the last five receipts (when, how it came, whether it was taken, the file name, and the site and revision it became). Read only.",
        annotations=ToolAnnotations(title="Received from FormWeb", readOnlyHint=True, idempotentHint=True, openWorldHint=False),
    )
    async def receive_status() -> dict:
        return await run(link.receive_status)

    @server.tool(
        name="site_routes",
        description="List the routes of an imported site's latest revision: path, page file, locale, item and stylesheet, read from routes.json or found by walking index.html files. Read only.",
        annotations=ToolAnnotations(title="Site routes", readOnlyHint=True, idempotentHint=True, openWorldHint=False),
    )
    async def site_routes(id: SiteId) -> dict:
        return await run(link.routes, id)

    @server.tool(
        name="list_revisions",
        description="List the revisions of an imported site, newest first: revision id, time, file count, bytes, route count, and how many files were added, removed and changed from the revision before. A site gains a revision each time the same FormWeb project arrives again. Read only.",
        annotations=ToolAnnotations(title="List revisions", readOnlyHint=True, idempotentHint=True, openWorldHint=False),
    )
    async def list_revisions(id: SiteId) -> dict:
        return await run(link.revisions, id)

    @server.tool(
        name="diff_revisions",
        description="Compare two revisions of a site: the added, removed and changed files (path, size, SHA-256), a summary with counts and bytes, and the added and removed routes. Without from_revision and to_revision it compares the latest revision with the one before it. Read only.",
        annotations=ToolAnnotations(title="Diff revisions", readOnlyHint=True, idempotentHint=True, openWorldHint=False),
    )
    async def diff_revisions(
        id: SiteId,
        from_revision: Annotated[str | None, Field(description="The older revision id from list_revisions; default the one before to_revision.")] = None,
        to_revision: Annotated[str | None, Field(description="The newer revision id from list_revisions; default the latest.")] = None,
    ) -> dict:
        return await run(link.diff, id, from_revision, to_revision)

    @server.tool(
        name="preview_site",
        description="Show a site revision on FormPublisher's local preview host (127.0.0.1, the same host the window's Preview uses) and return the address of its home page and one address per route, for the person or a browser tool to open. It opens nothing by itself and writes no file; it replaces whatever revision the preview host was showing, the window's included. Needs the running engine.",
        annotations=ToolAnnotations(title="Preview a site", readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False),
    )
    async def preview_site(id: SiteId, revision: Revision = None) -> dict:
        return await run(link.preview, id, revision)

    @server.tool(
        name="run_checks",
        description="Run the checks on an imported site's revision and return the problems with route, severity, code, message and fix, and a summary of counts per severity. The static tier is offline and always runs; set deep to also drive the installed Chrome at the given widths (slow, needs Playwright) against the site served on this computer only, which adds measures: the largest contentful paint in seconds and the layout shift for each route and width, lab values with the CPU and network slowed. INP is not measured. The result is stored in FormPublisher's data folder, replacing the last result of that revision, for get_checks and the next build_package.",
        annotations=ToolAnnotations(title="Run checks", readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False),
    )
    async def run_checks(
        id: SiteId,
        deep: Annotated[bool, Field(description="Also run the browser tier in the installed Chrome; default false.")] = False,
        widths: Annotated[list[int] | None, Field(description="Viewport widths in CSS pixels for the deep tier; default 1440 and 390.")] = None,
        revision: Revision = None,
    ) -> dict:
        return await run(link.check, id, deep, widths, revision)

    @server.tool(
        name="get_checks",
        description="Read the stored check results of a site's revision (problems, counts per severity, which tiers ran, and the deep tier's measures per route and width) without running anything. Read only.",
        annotations=ToolAnnotations(title="Stored check results", readOnlyHint=True, idempotentHint=True, openWorldHint=False),
    )
    async def get_checks(id: SiteId, revision: Revision = None) -> dict:
        return await run(link.get_checks, id, revision)

    @server.tool(
        name="build_package",
        description="Build the deterministic package for a site's revision in FormPublisher's data folder: site.zip plus publish.json with the SHA-256 and size of every file, the routes, redirects, headers and the summary of the checks stored at that moment. Building the same bytes again returns the same build id with created false. Returns the build record.",
        annotations=ToolAnnotations(title="Build a package", readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False),
    )
    async def build_package(id: SiteId, revision: Revision = None) -> dict:
        return await run(link.build, id, revision)

    @server.tool(
        name="list_builds",
        description="List every build with its id, site, revision, file count, size, signed flag and time, newest first. Read only.",
        annotations=ToolAnnotations(title="List builds", readOnlyHint=True, idempotentHint=True, openWorldHint=False),
    )
    async def list_builds() -> dict:
        return await run(link.builds)

    @server.tool(
        name="inspect_build",
        description="Read one build: its record (site, revision, files, size, created), its publish.json (the package SHA-256 and size, every file with path, size and SHA-256, routes, redirects, headers and the checks summary stored when it was built, null when no checks had run) and signature, the same verdict as verify_build (valid, known, trusted, signer, message, reason). Read only.",
        annotations=ToolAnnotations(title="Inspect a build", readOnlyHint=True, idempotentHint=True, openWorldHint=False),
    )
    async def inspect_build(build: BuildId) -> dict:
        return await run(link.inspect_build, build)

    @server.tool(
        name="compare_builds",
        description="Compare the files of two builds from their publish.json: the paths added and removed from a to b, the changed files with size and SHA-256 on each side, and how many are the same. Read only.",
        annotations=ToolAnnotations(title="Compare builds", readOnlyHint=True, idempotentHint=True, openWorldHint=False),
    )
    async def compare_builds(
        a: Annotated[str, Field(description="The older build id from list_builds.")],
        b: Annotated[str, Field(description="The newer build id from list_builds.")],
    ) -> dict:
        return await run(link.compare_builds, a, b)

    @server.tool(
        name="reproduce_build",
        description="Rebuild a build's site.zip from the site revision it was made from, in a scratch folder inside FormPublisher's data folder that is removed afterwards, and report same (the bytes match publish.json), sha256 (what the rebuild gave) and expected. The build itself is not changed.",
        annotations=ToolAnnotations(title="Reproduce a build", readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False),
    )
    async def reproduce_build(build: BuildId) -> dict:
        return await run(link.reproduce, build)

    @server.tool(
        name="save_fpub",
        description="Save a build as a .fpub package (one file holding the build's publish.json, site.zip and signature) at an absolute path the person named, ending in .fpub, in a folder that exists. The same build gives the same bytes every time. It will not replace an existing file, so a second call with the same path fails. Returns the file, size and SHA-256.",
        annotations=ToolAnnotations(title="Save a build as .fpub", readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False),
    )
    async def save_fpub(build: BuildId, path: Annotated[str, Field(description="Absolute path of the new .fpub file on this computer, in an existing folder; it must not exist yet.")]) -> dict:
        if not Path(path).expanduser().is_absolute():
            raise ToolError("error [invalid]: path must be absolute")
        return await run(link.save_fpub, build, path, False)

    @server.tool(
        name="list_keys",
        description="List the person's signing keys: per key its id (pass it to sign_build), name, fingerprint, created time, encrypted (a passphrase is needed to sign), secret (where the private key is kept: store for the system password store, file for a private file in the data folder, none for a key kept only to verify) and canSign. No private key or passphrase is ever returned. Read only.",
        annotations=ToolAnnotations(title="List signing keys", readOnlyHint=True, idempotentHint=True, openWorldHint=False),
    )
    async def list_keys() -> dict:
        return await run(link.keys)

    @server.tool(
        name="sign_build",
        description="Sign a build's site.zip with one of the person's Ed25519 keys: a detached signature stored beside the zip in FormPublisher's data folder, replacing an earlier one. Call list_keys first and pass the id of the key the person named, one with canSign true; when key is left out and exactly one signing key exists it is used, otherwise the call fails and lists the keys. A key with encrypted true needs its passphrase from the person; never invent one. Returns the build id, the key id and its fingerprint.",
        annotations=ToolAnnotations(title="Sign a build", readOnlyHint=False, destructiveHint=True, idempotentHint=True, openWorldHint=False),
    )
    async def sign_build(
        build: BuildId,
        key: Annotated[str | None, Field(description="The id from list_keys of the key the person named.")] = None,
        passphrase: Annotated[str | None, Field(description="Only for a key with encrypted true, and only the passphrase the person gave.")] = None,
    ) -> dict:
        return await run(link.sign, build, key, passphrase)

    @server.tool(
        name="verify_build",
        description="Verify a build's detached signature against its site.zip bytes and the person's own keys. Returns valid (the signature matches the content with the public key inside the signature file), known (true only when that public key is one of the person's own signing keys or a key they kept as known; anyone can re-sign a changed package with a key of their own, so valid without known is not proof of origin), trusted (valid and known), signer (the fingerprint and, when known, the key's id and name) and a plain message; when valid is false, reason says why (not signed, malformed, or the package does not match). Report valid true with known false to the person as a warning: signed by a key they do not have. Read only.",
        annotations=ToolAnnotations(title="Verify a build", readOnlyHint=True, idempotentHint=True, openWorldHint=False),
    )
    async def verify_build(build: BuildId) -> dict:
        return await run(link.verify, build)

    @server.tool(
        name="list_targets",
        description="List the host targets a build can be prepared for (static-zip, netlify, cloudflare-pages, vercel, github-pages, nginx) with name, description and the local tool that serves each one. Read only.",
        annotations=ToolAnnotations(title="List publish targets", readOnlyHint=True, idempotentHint=True, openWorldHint=False),
    )
    async def list_targets() -> dict:
        return await run(link.targets)

    @server.tool(
        name="prepare_publish",
        description="Prepare a folder per target for a build inside FormPublisher's data folder and return, for each, the folder path, files, the exact commands to run, notes and warnings. Nothing is uploaded; running the commands is up to the person. Preparing again deletes the target's folder and makes it afresh, so anything added to it since (such as a host tool's link files) is gone. FormWeb's model files (site.formweb.json, asset-access.json) are left out of the site folders unless includeModel is true; each result's leftOut lists what was left out.",
        annotations=ToolAnnotations(title="Prepare for publishing", readOnlyHint=False, destructiveHint=True, idempotentHint=True, openWorldHint=False),
    )
    async def prepare_publish(
        build: BuildId,
        targets: Annotated[list[str], Field(description="One or more target ids from list_targets.")],
        includeModel: Annotated[bool, Field(description="Keep FormWeb's model files (site.formweb.json, asset-access.json) in the host folders; default false leaves them out and lists them under leftOut.")] = False,
    ) -> dict:
        return await run(link.prepare, build, targets, includeModel)

    @server.tool(
        name="get_prepared",
        description="Read what is already prepared for a build: per target the folder, files, commands, notes, warnings, preparedAt, includeModel, leftOut and verified (the last verify_prepared verdict, null when it was never verified since it was prepared). Read only.",
        annotations=ToolAnnotations(title="Prepared folders", readOnlyHint=True, idempotentHint=True, openWorldHint=False),
    )
    async def get_prepared(build: BuildId) -> dict:
        return await run(link.prepared, build)

    @server.tool(
        name="verify_prepared",
        description="Check that a prepared folder still matches its build: every site file against publish.json's SHA-256 and the whole folder against a fresh prepare made in a scratch folder (for nginx also nginx -t when nginx is installed). Returns ok, the files checked and the problems (path, what is wrong, and whether publish.json or the fresh prepare found it). It changes nothing in the prepared folder; the verdict is kept in the data folder so get_prepared and the window show when it was last verified.",
        annotations=ToolAnnotations(title="Verify a prepared folder", readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False),
    )
    async def verify_prepared(
        build: BuildId,
        target: Annotated[str, Field(description="The target id the folder was prepared for, as listed by get_prepared.")],
    ) -> dict:
        return await run(link.verify_prepared, build, target)

    @server.tool(
        name="check_live_site",
        description="Read the person's own public site over the internet, at the address they gave, after they deployed it themselves; it uploads nothing and sends nothing but ordinary page requests. Run it only when the person asked for it. It reports whether the bare name and www both answer (DNS and the home page), whether each certificate is valid and not within 7 days of expiry, whether http redirects to https, whether the build's redirects hold, whether an address that does not exist gets 404, and whether up to three non-HTML files match the build's SHA-256. Each problem has code (live.dns, live.tls, live.cert-expiry, live.www, live.http, live.redirect, live.404, live.build), severity, message, fix and guide, the part of docs/HOSTING.md to read (guideTopic names the paragraph in it). The result is kept in FormPublisher's data folder for the window; ok is true when there is no warning or error.",
        annotations=ToolAnnotations(title="Check the live site", readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=True),
    )
    async def check_live_site(
        id: SiteId,
        address: Annotated[str, Field(description="The site's public address the person gave: a domain name or an https address with no path, for example example.com or https://www.example.com. Both the bare name and www are read.")],
        build: Annotated[str | None, Field(description="A build id from list_builds to compare the site online with; default the site's newest build.")] = None,
        target: Annotated[str | None, Field(description="The target id the site is deployed on (from list_targets), so each finding names that host's part of the guide; default the one target prepared for the build, if only one.")] = None,
    ) -> dict:
        return await run(link.live_check, id, address, build, target)

    @server.tool(
        name="list_templates",
        description="List the kept templates a site can start from: the FormWeb whole-site templates of the public formai-templates index, with id, name, description, size, SHA-256, licence and credit, and when the list was fetched. Reads only the list the person already got in the window or with the CLI (templates --fetch); it fetches nothing. fetched false means no list is kept yet. Read only.",
        annotations=ToolAnnotations(title="List templates", readOnlyHint=True, idempotentHint=True, openWorldHint=False),
    )
    async def list_templates() -> dict:
        return await run(link.templates)

    @server.tool(
        name="start_from_template",
        description="Start a site from a kept template: download that one file from the templates repository, keep it only when its size and SHA-256 match the index, open it with the FormWeb core and write it as a new .fweb project into a folder the person named. It will not replace a file. Editing happens in FormWeb (File > Import .fweb or .fpub file...); to publish it, pass the returned project path to import_site.",
        annotations=ToolAnnotations(title="Start a site from a template", readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True),
    )
    async def start_from_template(
        template: Annotated[str, Field(description="A template id from list_templates, for example formweb/demos/lowlight.")],
        folder: Annotated[str, Field(description="Absolute path of an existing folder the person named; the new .fweb file is written into it.")],
        name: Annotated[str | None, Field(description="The project's file name; default the template's name.")] = None,
    ) -> dict:
        if not Path(folder).expanduser().is_absolute():
            raise ToolError("error [invalid]: folder must be absolute")
        return await run(link.start_template, template, folder, name)

    @server.tool(
        name="list_trash",
        description="List what was removed and is waiting in the trash, newest first: per entry its name, kind (site, build, key or prepared), label, where it came from, when it was moved and its size. Read only.",
        annotations=ToolAnnotations(title="List the trash", readOnlyHint=True, idempotentHint=True, openWorldHint=False),
    )
    async def list_trash() -> dict:
        return await run(link.trash)

    @server.tool(
        name="restore_from_trash",
        description="Move a trash entry back to where it came from: the origin the trash recorded, or one worked out from the name and contents of an entry made before the records existed (an old prepared folder is prepared again from its build). It has no origin argument, so an entry whose origin is unknown fails with the reason and is restored by a person with the CLI (trash restore ENTRY --to PATH) or the window. A trashed key whose record is missing is rebuilt from its key file; an encrypted one answers passphrase-required until the person's passphrase is given (never invent one). It also fails when the place is taken. Deleting for good is not offered here.",
        annotations=ToolAnnotations(title="Restore from the trash", readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False),
    )
    async def restore_from_trash(
        entry: Annotated[str, Field(description="The entry name from list_trash.")],
        passphrase: Annotated[str | None, Field(description="Only for an encrypted key whose record is missing, and only the passphrase the person gave.")] = None,
    ) -> dict:
        return await run(link.trash_restore, entry, None, passphrase)

    tools = {tool.name: tool for tool in server._tool_manager.list_tools()}
    if set(tools) != set(TOOL_CLASS) or not set(TOOL_CLASS.values()) <= set(CLASSES):
        raise RuntimeError(f"TOOL_CLASS does not match the tools: missing {sorted(set(tools) - set(TOOL_CLASS))}, extra {sorted(set(TOOL_CLASS) - set(tools))}")
    for name, tool in tools.items():
        tool.meta = {**(tool.meta or {}), "formpublisher/class": TOOL_CLASS[name]}
    return server


def main(argv: list[str] | None = None) -> int:
    args = list(argv or [])
    if args and args[0] in ("-h", "--help"):
        print("formpublisher_engine.py mcp [--tab-key-file PATH]: serve the FormPublisher tools over MCP on stdio.")
        return 0
    client = None
    if args and args[0].startswith("--tab-key-file"):
        given = args[0].partition("=")[2] if "=" in args[0] else (args[1] if len(args) > 1 else "")
        try:
            key = Path(given).read_text(encoding="utf-8").strip() if given else ""
        except OSError:
            key = ""
        if not key:
            print("formpublisher mcp: --tab-key-file needs the path of a readable tab key file.", file=sys.stderr)
            return 2
        client = Client(url=os.environ.get("FORMPUBLISHER_URL") or f"http://127.0.0.1:{paths.port()}", key=key)
    build(client).run("stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
