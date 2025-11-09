from openproject_mcp.server import build_server

def run():
    server = build_server()
    server.run()
