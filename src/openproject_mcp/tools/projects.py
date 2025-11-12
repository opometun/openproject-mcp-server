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


def register(server: FastMCP, settings: Settings | None = None):
    """Register all project tools with the MCP server"""
    settings = settings or Settings()
    client = OpenProjectClient(settings)

    @server.tool(
        "get_project_memberships",
        description="Get memberships (users and roles) for a project",
    )
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
        try:
            # Build filters
            filters = [
                {"project": {"operator": "=", "values": [str(params.project_id)]}}
            ]

            # Add any additional filters
            if params.filters:
                for filter_id, filter_config in params.filters.items():
                    if isinstance(filter_config, dict) and "operator" in filter_config:
                        filters.append(
                            {
                                filter_id: {
                                    "operator": filter_config["operator"],
                                    "values": filter_config.get("values", []),
                                }
                            }
                        )

            # Build query parameters
            query_params = {
                "pageSize": params.page_size,
                "offset": params.offset,
                "filters": str(filters),
            }

            # If follow parameter is provided, collect across pages
            if params.follow:
                all_elements = []
                current_offset = params.offset

                while len(all_elements) < params.follow:
                    query_params["offset"] = current_offset
                    res = await client.get("/memberships", params=query_params)
                    data = res.json()

                    elements = data.get("_embedded", {}).get("elements", [])
                    if not elements:
                        break

                    all_elements.extend(elements)

                    # Check if we have more pages
                    if len(all_elements) >= data.get("total", 0):
                        break

                    current_offset += 1

                # Trim to follow limit
                all_elements = all_elements[: params.follow]

                return {
                    "_type": "Collection",
                    "count": len(all_elements),
                    "total": len(all_elements),
                    "pageSize": params.page_size,
                    "offset": params.offset,
                    "_embedded": {"elements": all_elements},
                }
            else:
                # Single page request
                res = await client.get("/memberships", params=query_params)
                return res.json()

        except httpx.HTTPStatusError as e:
            map_http_error(e.response.status_code, e.response.text[:300])

    @server.tool(
        "resolve_project", description="Look up a project by identifier or display name"
    )
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
        try:
            # Get all projects
            res = await client.get("/projects", params={"pageSize": 1000})
            projects_data = res.json()
            projects = projects_data.get("_embedded", {}).get("elements", [])

            # Normalize search term
            search_term = params.name_or_identifier.lower().strip()

            # First, try exact match on identifier
            exact_identifier_matches = [
                p for p in projects if p.get("identifier", "").lower() == search_term
            ]

            if len(exact_identifier_matches) == 1:
                project = exact_identifier_matches[0]
                return {
                    "id": project.get("id"),
                    "identifier": project.get("identifier"),
                    "name": project.get("name"),
                    "href": project.get("_links", {}).get("self", {}).get("href"),
                }

            if len(exact_identifier_matches) > 1:
                return {
                    "disambiguation_needed": True,
                    "matches": [
                        {
                            "id": p.get("id"),
                            "identifier": p.get("identifier"),
                            "name": p.get("name"),
                            "href": p.get("_links", {}).get("self", {}).get("href"),
                        }
                        for p in exact_identifier_matches
                    ],
                }

            # Try partial match on name
            name_matches = [
                p for p in projects if search_term in p.get("name", "").lower()
            ]

            if len(name_matches) == 1:
                project = name_matches[0]
                return {
                    "id": project.get("id"),
                    "identifier": project.get("identifier"),
                    "name": project.get("name"),
                    "href": project.get("_links", {}).get("self", {}).get("href"),
                }

            if len(name_matches) > 1:
                return {
                    "disambiguation_needed": True,
                    "matches": [
                        {
                            "id": p.get("id"),
                            "identifier": p.get("identifier"),
                            "name": p.get("name"),
                            "href": p.get("_links", {}).get("self", {}).get("href"),
                        }
                        for p in name_matches
                    ],
                }

            # Try partial match on identifier
            identifier_matches = [
                p for p in projects if search_term in p.get("identifier", "").lower()
            ]

            if len(identifier_matches) == 1:
                project = identifier_matches[0]
                return {
                    "id": project.get("id"),
                    "identifier": project.get("identifier"),
                    "name": project.get("name"),
                    "href": project.get("_links", {}).get("self", {}).get("href"),
                }

            if len(identifier_matches) > 1:
                return {
                    "disambiguation_needed": True,
                    "matches": [
                        {
                            "id": p.get("id"),
                            "identifier": p.get("identifier"),
                            "name": p.get("name"),
                            "href": p.get("_links", {}).get("self", {}).get("href"),
                        }
                        for p in identifier_matches
                    ],
                }

            return {"error": f"No project found matching '{params.name_or_identifier}'"}

        except httpx.HTTPStatusError as e:
            map_http_error(e.response.status_code, e.response.text[:300])
