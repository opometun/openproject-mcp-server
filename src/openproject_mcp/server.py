from mcp.server.fastmcp import FastMCP
from openproject_mcp.tools import (
    work_packages,
    attachments,
    queries,
    time_entries,
    users,
    wiki,
    projects,
)


def build_server() -> FastMCP:
    server = FastMCP("openproject")

    @server.tool("system_ping", description="Connectivity check")
    async def ping() -> dict:
        return {"ok": True}

    # Register stubs
    work_packages.register(server)
    attachments.register(server)
    queries.register(server)
    time_entries.register(server)
    users.register(server)
    wiki.register(server)
    projects.register(server)
    return server
