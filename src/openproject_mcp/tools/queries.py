from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

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


def register(server: FastMCP):
    """Register all query tools with the MCP server"""

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
        return {
            "error": {
                "code": "NotImplemented",
                "message": "list_queries not implemented yet",
                "details": {"project_id": params.project_id},
            }
        }

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
        return {
            "error": {
                "code": "NotImplemented",
                "message": "run_query not implemented yet",
                "details": {"query_id": params.query_id, "overrides": params.overrides},
            }
        }
