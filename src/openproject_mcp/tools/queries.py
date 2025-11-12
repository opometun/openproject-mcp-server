from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import httpx

from openproject_mcp.config import Settings
from openproject_mcp.client import OpenProjectClient
from openproject_mcp.errors import map_http_error

# ============================================================================
# Input Models (Request Parameters)
# ============================================================================


class ListQueriesIn(BaseModel):
    """Input parameters for listing saved queries"""

    project_id: Optional[int] = Field(
        None, description="Optional project ID to filter queries", gt=0
    )


class RunQueryIn(BaseModel):
    """Input parameters for running a saved query"""

    query_id: int = Field(..., description="Query ID to execute", gt=0)
    overrides: Optional[Dict[str, Any]] = Field(
        None, description="Optional filter overrides to apply to the query"
    )


# ============================================================================
# Output Models (Response Data - Optional but Recommended)
# ============================================================================


class QueryMetadata(BaseModel):
    """Query metadata structure"""

    id: Optional[int] = None
    name: Optional[str] = None
    filters: Optional[list] = None
    columns: Optional[list] = None
    sortBy: Optional[list] = None
    groupBy: Optional[str] = None
    displaySums: Optional[bool] = None
    public: Optional[bool] = None
    starred: Optional[bool] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    _links: Optional[Dict] = None


class QueryCollection(BaseModel):
    """Collection of queries"""

    _type: str = "Collection"
    count: int = 0
    total: int = 0
    _embedded: Dict = {"elements": []}


class QueryResultsResponse(BaseModel):
    """Response for query execution results"""

    _type: str = "WorkPackageCollection"
    count: int = 0
    total: int = 0
    _embedded: Dict = {"elements": []}


# ============================================================================
# Tool Registration
# ============================================================================


def register(server: FastMCP, settings: Settings | None = None):
    """Register all query tools with the MCP server"""
    settings = settings or Settings()
    client = OpenProjectClient(settings)

    @server.tool(
        "list_queries",
        description="List saved queries (views) with optional project filter",
    )
    async def list_queries(params: ListQueriesIn) -> dict:
        """
        Retrieve all saved queries, optionally filtered by project.

        Args:
            params: Validated input with optional project_id

        Returns:
            dict: Collection of query objects with metadata

        Note:
            Queries represent saved views/filters in OpenProject.
            They can be project-specific or global.
        """
        try:
            if params.project_id:
                # Get project-specific queries
                res = await client.get(f"/projects/{params.project_id}/queries")
            else:
                # Get all queries
                res = await client.get("/queries")
            return res.json()
        except httpx.HTTPStatusError as e:
            map_http_error(e.response.status_code, e.response.text[:300])

    @server.tool(
        "run_query",
        description="Execute a saved query and return matching work packages",
    )
    async def run_query(params: RunQueryIn) -> dict:
        """
        Execute a saved query to retrieve matching work packages.

        This tool allows you to run predefined queries (views) and optionally
        override their filters. Useful for getting filtered work package lists
        based on saved criteria.

        Args:
            params: Validated input with query_id and optional overrides

        Returns:
            dict: Work packages matching the query criteria

        Example overrides:
            {
                "status": {"operator": "o", "values": []},  # Open status
                "assignee": {"operator": "=", "values": ["123"]}
            }
        """
        try:
            # First, get the query to retrieve its configuration
            query_res = await client.get(f"/queries/{params.query_id}")
            query_data = query_res.json()

            # Build the payload for executing the query
            payload = {
                "filters": query_data.get("filters", []),
                "sortBy": query_data.get("sortBy", []),
                "groupBy": query_data.get("groupBy"),
                "columns": query_data.get("columns", []),
            }

            # Apply overrides if provided
            if params.overrides:
                # Merge overrides into filters
                existing_filters = {f.get("id"): f for f in payload["filters"]}

                for filter_id, filter_config in params.overrides.items():
                    if isinstance(filter_config, dict) and "operator" in filter_config:
                        # Override or add new filter
                        existing_filters[filter_id] = {
                            "id": filter_id,
                            "operator": filter_config["operator"],
                            "values": filter_config.get("values", []),
                        }

                payload["filters"] = list(existing_filters.values())

            # Execute the query by posting to the query results endpoint
            # Use the _links.results href if available, otherwise construct it
            results_href = query_data.get("_links", {}).get("results", {}).get("href")

            if results_href:
                # Strip /api/v3 prefix if present since client adds it
                if results_href.startswith("/api/v3"):
                    results_href = results_href[7:]  # Remove "/api/v3"
                res = await client.get(results_href)
            else:
                # Fall back to posting the query configuration
                res = await client.post("/queries/default", json=payload)

            return res.json()

        except httpx.HTTPStatusError as e:
            map_http_error(e.response.status_code, e.response.text[:300])
