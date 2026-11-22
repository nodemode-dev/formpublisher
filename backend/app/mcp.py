import asyncio
import sys
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from app import __version__
from app.cli import Client, OpError

INSTRUCTIONS = (
    "FormPublisher turns a site built in FormWeb into something that can be checked, packaged and published. "
    "Start with formpublisher_status, then import a FormWeb export zip or publication folder with import_site, "
    "or pull the current FormWeb export with import_formweb_current, and read the result with list_sites and site_routes. "
    "A .fpub package (save_fpub) can be opened elsewhere with import_site. "
    "Then run_checks, build_package, sign_build (with a key the person named) and verify_build, and finish with list_targets and prepare_publish, "
    "which writes a folder per host with the commands to run; nothing is uploaded. "
    "To start a new site, list_templates reads the template list the person fetched and start_from_template writes a FormWeb project into a folder they named; editing it happens in FormWeb. "
    "FormPublisher only reads from FormWeb and never changes it."
)


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
        description="Import a FormWeb site export (a zip with routes.json, sitemap.xml, robots.txt and assets/), a .fweb project, a FormPublisher .fpub package or a FormWeb publication folder from an absolute local path. It is unzipped safely into FormPublisher's data folder as a new revision and returns the site record. A .fpub also restores its build (publish.json, site.zip and signature, checked against the key it carries) and the record says so under build; build.signature.known is true only when that key is one of the person's own. Importing the same source again adds a revision.",
        annotations=ToolAnnotations(title="Import a site", readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False),
    )
    async def import_site(path: str) -> dict:
        """path: absolute path of a site export zip or a publication folder on this computer."""
        return await run(link.import_path, path)

    @server.tool(
        name="import_formweb_current",
        description="Download the site currently open in FormWeb (its read-only export), or with project one of FormWeb's saved projects (its saved .fweb file, compiled here), and import it as a new revision of that project's site. Needs FormWeb running; only reads from it.",
        annotations=ToolAnnotations(title="Import the current FormWeb site", readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False),
    )
    async def import_formweb_current(project: str | None = None) -> dict:
        """project: a saved project id from list_formweb_projects; leave it out for the site open in FormWeb."""
        return await run(link.import_formweb, project)

    @server.tool(
        name="list_formweb_projects",
        description="List the running FormWeb's saved projects through its read-only GET /api/projects: id, name, saved time, and which one is open (always first; an open site that was never saved has saved false). Read only.",
        annotations=ToolAnnotations(title="FormWeb projects", readOnlyHint=True, idempotentHint=True, openWorldHint=False),
    )
    async def list_formweb_projects() -> dict:
        return await run(link.formweb_projects)

    @server.tool(
        name="site_routes",
        description="List the routes of an imported site's latest revision: path, page file, locale, item and stylesheet, read from routes.json or found by walking index.html files. Read only.",
        annotations=ToolAnnotations(title="Site routes", readOnlyHint=True, idempotentHint=True, openWorldHint=False),
    )
    async def site_routes(id: str) -> dict:
        """id: the site id as returned by list_sites."""
        return await run(link.routes, id)

    @server.tool(
        name="list_revisions",
        description="List the revisions of an imported site, newest first: revision id, time, file count, bytes, route count, and how many files were added, removed and changed from the revision before. A site gains a revision each time the same FormWeb project arrives again. Read only.",
        annotations=ToolAnnotations(title="List revisions", readOnlyHint=True, idempotentHint=True, openWorldHint=False),
    )
    async def list_revisions(id: str) -> dict:
        """id: the site id as returned by list_sites."""
        return await run(link.revisions, id)

    @server.tool(
        name="diff_revisions",
        description="Compare two revisions of a site: the added, removed and changed files (path, size, SHA-256) and the added and removed routes. Without from and to it compares the latest revision with the one before it. Read only.",
        annotations=ToolAnnotations(title="Diff revisions", readOnlyHint=True, idempotentHint=True, openWorldHint=False),
    )
    async def diff_revisions(id: str, from_revision: str | None = None, to_revision: str | None = None) -> dict:
        """id: site id from list_sites. from_revision: the older revision id from list_revisions. to_revision: the newer one, default the latest."""
        return await run(link.diff, id, from_revision, to_revision)

    @server.tool(
        name="run_checks",
        description="Run the checks on an imported site's revision and return the problems with route, severity, code, message and fix. The static tier is offline and always runs; set deep to also drive the installed Chrome at the given widths (slow, needs Playwright). Stores the result for get_checks.",
        annotations=ToolAnnotations(title="Run checks", readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False),
    )
    async def run_checks(id: str, deep: bool = False, widths: list[int] | None = None, revision: str | None = None) -> dict:
        """id: site id from list_sites. deep: also run the browser tier. widths: viewport widths for the deep tier, default 1440 and 390. revision: default the latest."""
        return await run(link.check, id, deep, widths, revision)

    @server.tool(
        name="get_checks",
        description="Read the stored check results of a site's revision (problems, counts per severity, which tiers ran) without running anything. Read only.",
        annotations=ToolAnnotations(title="Stored check results", readOnlyHint=True, idempotentHint=True, openWorldHint=False),
    )
    async def get_checks(id: str, revision: str | None = None) -> dict:
        """id: site id from list_sites. revision: default the latest."""
        return await run(link.get_checks, id, revision)

    @server.tool(
        name="build_package",
        description="Build the deterministic package for a site's revision: site.zip plus publish.json with the SHA-256 and size of every file. Building the same site twice returns the same build id. Returns the build record.",
        annotations=ToolAnnotations(title="Build a package", readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False),
    )
    async def build_package(id: str, revision: str | None = None) -> dict:
        """id: site id from list_sites. revision: default the latest."""
        return await run(link.build, id, revision)

    @server.tool(
        name="list_builds",
        description="List every build with its id, site, revision, file count, size, signed flag and time, newest first. Read only.",
        annotations=ToolAnnotations(title="List builds", readOnlyHint=True, idempotentHint=True, openWorldHint=False),
    )
    async def list_builds() -> dict:
        return await run(link.builds)

    @server.tool(
        name="save_fpub",
        description="Save a build as a .fpub package (one file holding the build's publish.json, site.zip and signature) at an absolute path ending in .fpub. The same build gives the same bytes every time. It will not replace an existing file. Returns the file, size and SHA-256.",
        annotations=ToolAnnotations(title="Save a build as .fpub", readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False),
    )
    async def save_fpub(build: str, path: str) -> dict:
        """build: build id from list_builds. path: absolute path of the new .fpub file on this computer."""
        if not Path(path).expanduser().is_absolute():
            raise ToolError("error [invalid]: path must be absolute")
        return await run(link.save_fpub, build, path, False)

    @server.tool(
        name="sign_build",
        description="Sign a build's site.zip with an Ed25519 key (a detached signature stored beside the zip). Name the key; when key is omitted and exactly one key exists it is used, otherwise the call fails. Never invent a passphrase.",
        annotations=ToolAnnotations(title="Sign a build", readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False),
    )
    async def sign_build(build: str, key: str | None = None, passphrase: str | None = None) -> dict:
        """build: build id from list_builds. key: key id the person named. passphrase: only if the key has one and the person gave it."""
        return await run(link.sign, build, key, passphrase)

    @server.tool(
        name="verify_build",
        description="Verify a build's detached signature against its site.zip bytes and the person's own keys. Returns valid (the signature matches the content with the public key inside the signature file), known (true only when that public key is one of the person's own signing keys or a key they kept as known; anyone can re-sign a changed package with a key of their own, so valid without known is not proof of origin), trusted (valid and known), signer (the fingerprint and, when known, the key's id and name) and a plain message; when valid is false, reason says why (not signed, malformed, or the package does not match). Report valid true with known false to the person as a warning: signed by a key they do not have. Read only.",
        annotations=ToolAnnotations(title="Verify a build", readOnlyHint=True, idempotentHint=True, openWorldHint=False),
    )
    async def verify_build(build: str) -> dict:
        """build: build id from list_builds."""
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
        description="Prepare a folder per target for a build and return, for each, the folder path, files, the exact commands to run, notes and warnings. Nothing is uploaded; running the commands is up to the person. Preparing again replaces the folder. FormWeb's model files (site.formweb.json, asset-access.json) are left out of the site folders unless includeModel is true; each result's leftOut lists what was left out.",
        annotations=ToolAnnotations(title="Prepare for publishing", readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False),
    )
    async def prepare_publish(build: str, targets: list[str], includeModel: bool = False) -> dict:
        """build: build id from list_builds. targets: target ids from list_targets. includeModel: keep FormWeb's model files (site.formweb.json, asset-access.json) in the host folders; default false leaves them out and the result lists them under leftOut."""
        return await run(link.prepare, build, targets, includeModel)

    @server.tool(
        name="get_prepared",
        description="Read what is already prepared for a build: per target the folder, files, commands, notes and warnings. Read only.",
        annotations=ToolAnnotations(title="Prepared folders", readOnlyHint=True, idempotentHint=True, openWorldHint=False),
    )
    async def get_prepared(build: str) -> dict:
        """build: build id from list_builds."""
        return await run(link.prepared, build)

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
    async def start_from_template(template: str, folder: str, name: str | None = None) -> dict:
        """template: an id from list_templates. folder: absolute path of an existing folder the person named. name: the project's file name, default the template's name."""
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
    async def restore_from_trash(entry: str, passphrase: str | None = None) -> dict:
        """entry: the entry name from list_trash. passphrase: only for an encrypted key whose record is missing, and only if the person gave it."""
        return await run(link.trash_restore, entry, None, passphrase)

    return server


def main(argv: list[str] | None = None) -> int:
    args = list(argv or [])
    if args and args[0] in ("-h", "--help"):
        print("formpublisher_engine.py mcp: serve the FormPublisher tools over MCP on stdio.")
        return 0
    build().run("stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
