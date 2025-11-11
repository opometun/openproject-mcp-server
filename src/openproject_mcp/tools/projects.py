from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

# ============================================================================
# Input Models (Request Parameters)
# ============================================================================


class GetProjectMembershipsIn(BaseModel):
    """Input parameters for getting project memberships"""

    project_id: int = Field(..., description="Project ID to get memberships for", gt=0)
    filters: Optional[Dict[str, Any]] = Field(
        None, description="Optional additional filters to apply"
    )
    page_size: int = Field(100, description="Number of results per page", gt=0, le=1000)
    offset: int = Field(1, description="Page offset for pagination", gt=0)
    follow: Optional[int] = Field(
        None, description="Optional: collect across pages up to this many results", gt=0
    )


class ResolveProjectIn(BaseModel):
    """Input parameters for resolving a project by name or identifier"""

    name_or_identifier: str = Field(
        ...,
        description="Project identifier or display name to search for",
        min_length=1,
    )


# ============================================================================
# Output Models (Response Data - Optional but Recommended)
# ============================================================================


class MembershipMetadata(BaseModel):
    """Membership metadata structure"""

    id: Optional[int] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    _type: Optional[str] = None
    _links: Optional[Dict] = None


class MembershipCollection(BaseModel):
    """Collection of memberships"""

    _type: str = "Collection"
    count: int = 0
    total: int = 0
    pageSize: int = 100
    offset: int = 1
    _embedded: Dict = {"elements": []}


class ProjectResolution(BaseModel):
    """Resolved project information"""

    id: Optional[int] = None
    identifier: Optional[str] = None
    name: Optional[str] = None
    href: Optional[str] = None
    disambiguation_needed: Optional[bool] = None
    matches: Optional[list] = None
    error: Optional[str] = None


# ============================================================================
# Tool Registration
# ============================================================================


def register(server: FastMCP):
    """Register all project tools with the MCP server"""

    @server.tool(description="Get memberships (users and roles) for a project")
    async def get_project_memberships(params: GetProjectMembershipsIn) -> dict:
        """
        Retrieve all memberships associated with a project.

        Returns users and their roles for the specified project.
        Supports pagination and optional collection across multiple pages.

        Args:
            params: Validated input with project_id, optional filters, and pagination

        Returns:
            dict: Collection of membership objects

        Note:
            - Always filters by project_id (route is not project-scoped)
            - Additional filters can be provided (e.g., filter by user)
            - When follow parameter is provided, automatically collects results
              across pages up to the specified limit
            - Each membership includes links to user, project, and roles
        """
        return {
            "error": {
                "code": "NotImplemented",
                "message": "get_project_memberships not implemented yet",
                "details": {
                    "project_id": params.project_id,
                    "filters": params.filters,
                    "page_size": params.page_size,
                    "offset": params.offset,
                    "follow": params.follow,
                },
            }
        }

    @server.tool(description="Look up a project by identifier or display name")
    async def resolve_project(params: ResolveProjectIn) -> dict:
        """
        Search for a project by its identifier or name.

        Performs intelligent matching:
        1. Tries exact match on identifier (case-insensitive)
        2. Falls back to partial match on display name
        3. Returns disambiguation list if multiple matches found

        Args:
            params: Validated input with name_or_identifier

        Returns:
            dict: Project details {id, identifier, name, href} or disambiguation list

        Note:
            - Exact identifier match takes precedence
            - Name matching is case-insensitive and partial
            - Returns single result if unambiguous
            - Returns {"disambiguation_needed": true, "matches": [...]} if multiple matches
            - Returns {"error": "..."} if no matches found

        Example responses:
            Single match:
            {
                "id": 123,
                "identifier": "my-project",
                "name": "My Project",
                "href": "/api/v3/projects/123"
            }

            Multiple matches:
            {
                "disambiguation_needed": true,
                "matches": [
                    {"id": 1, "identifier": "proj-1", "name": "Project One", "href": "..."},
                    {"id": 2, "identifier": "proj-2", "name": "Project Two", "href": "..."}
                ]
            }
        """
        return {
            "error": {
                "code": "NotImplemented",
                "message": "resolve_project not implemented yet",
                "details": {"name_or_identifier": params.name_or_identifier},
            }
        }
