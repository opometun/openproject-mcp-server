from mcp.server.fastmcp import FastMCP


def build_server() -> FastMCP:
    server = FastMCP("openproject")

    @server.tool("system.ping", description="Connectivity check")
    async def ping() -> dict:
        return {"ok": True}

    return server
