"""
OpenProject MCP Server

A Model Context Protocol (MCP) server for OpenProject integration.
Provides tools for managing work packages, comments, and project data.
"""

# from openproject_mcp.main import run
from openproject_mcp.config import Settings
from openproject_mcp.client import OpenProjectClient
from openproject_mcp.server import build_server

__version__ = "0.1.0"
__author__ = "Oleksandr Pometun"
__all__ = [
    "run",
    "Settings",
    "OpenProjectClient",
    "build_server",
]
