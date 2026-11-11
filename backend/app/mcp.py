import asyncio
import sys
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
    "FormPublisher only reads from FormWeb and never changes it."
)


def build(client: Client | None = None) -> MCPServer:
    link = client or Client()
    server = MCPServer("formpublisher", instructions=INSTRUCTIONS, version=__version__)

    async def run(fn, *args) -> Any:
        try:
            return await asyncio.to_thread(fn, *args)
        except OpError as exc:
            raise ToolError(exc.message) from exc

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
        description="Import a FormWeb site export (a zip with routes.json, sitemap.xml, robots.txt and assets/) or a FormWeb publication folder from an absolute local path. It is unzipped safely into FormPublisher's data folder as a new revision and returns the site record. Importing the same source again adds a revision.",
        annotations=ToolAnnotations(title="Import a site", readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False),
    )
    async def import_site(path: str) -> dict:
        """path: absolute path of a site export zip or a publication folder on this computer."""
        return await run(link.import_path, path)

    @server.tool(
        name="import_formweb_current",
        description="Download the site currently open in FormWeb (its read-only export) and import it as a new revision. Needs FormWeb running; only reads from it.",
        annotations=ToolAnnotations(title="Import the current FormWeb site", readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False),
    )
    async def import_formweb_current() -> dict:
        return await run(link.import_formweb)

    @server.tool(
        name="site_routes",
        description="List the routes of an imported site's latest revision: path, page file, locale, item and stylesheet, read from routes.json or found by walking index.html files. Read only.",
        annotations=ToolAnnotations(title="Site routes", readOnlyHint=True, idempotentHint=True, openWorldHint=False),
    )
    async def site_routes(id: str) -> dict:
        """id: the site id as returned by list_sites."""
        return await run(link.routes, id)

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
