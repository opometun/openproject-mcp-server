from openproject_mcp.utils.logging import configure_logging
from openproject_mcp.config import Settings
from openproject_mcp.server import build_server


def run():
    # print("Server is confgured and running!")
    configure_logging()
    _ = Settings()
    server = build_server()
    server.run()


if __name__ == "__main__":
    run()
