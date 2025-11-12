from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import Optional, Literal

import httpx
from openproject_mcp.config import Settings
from openproject_mcp.client import OpenProjectClient
from openproject_mcp.errors import map_http_error

# ============================================================================
# Input Models (Request Parameters)
# ============================================================================


class AddCommentIn(BaseModel):
    """Input parameters for adding a comment to a work package"""

    id: int = Field(..., description="Work package ID", gt=0)
    comment: str = Field(..., description="Comment text in markdown", min_length=1)
    notify: bool = Field(False, description="Send email notifications to watchers")


class SearchContentIn(BaseModel):
    """Input parameters for searching OpenProject content"""

    query: str = Field(..., description="Search query text", min_length=1)
    scope: Optional[Literal["work_packages", "projects"]] = Field(
        None, description="Search scope: 'work_packages', 'projects', or None for both"
    )
    limit: int = Field(100, description="Maximum results to return", gt=0, le=1000)
    include_attachments: bool = Field(
        False, description="Include attachment content/filenames in search"
    )


class GetWorkPackageStatusesIn(BaseModel):
    """Input parameters for getting work package statuses (no params needed)"""

    pass  # This tool takes no parameters


class GetWorkPackageTypesIn(BaseModel):
    """Input parameters for getting work package types"""

    project_id: Optional[int] = Field(
        None, description="Optional project ID to filter types by project", gt=0
    )


class ResolveStatusIn(BaseModel):
    """Input parameters for resolving a status name to ID"""

    name: str = Field(
        ...,
        description="Status name to resolve (e.g., 'In Progress', 'Closed')",
        min_length=1,
    )


class AppendWorkPackageDescriptionIn(BaseModel):
    """Input parameters for appending to a work package description"""

    wp_id: int = Field(..., description="Work package ID to update", gt=0)
    markdown: str = Field(
        ..., description="Markdown text to append to the description", min_length=1
    )


class ResolveTypeIn(BaseModel):
    """Input parameters for resolving a type name to ID"""

    project_id: int = Field(..., description="Project ID context", gt=0)
    name: str = Field(
        ...,
        description="Type name to resolve (e.g., 'Task', 'Bug', 'Milestone')",
        min_length=1,
    )


# ============================================================================
# Output Models (Response Data - Optional but Recommended)
# ============================================================================


class StatusInfo(BaseModel):
    """Resolved status information"""

    id: Optional[int] = None
    name: Optional[str] = None
    isClosed: Optional[bool] = None
    isDefault: Optional[bool] = None
    disambiguation_needed: Optional[bool] = None
    matches: Optional[list] = None
    error: Optional[str] = None


class TypeInfo(BaseModel):
    """Resolved type information"""

    id: Optional[int] = None
    name: Optional[str] = None
    available_in_project: Optional[bool] = None
    is_milestone: Optional[bool] = None
    is_default: Optional[bool] = None
    note: Optional[str] = None
    error: Optional[str] = None


class CollectionResponse(BaseModel):
    """OpenProject Collection response structure"""

    _type: str = "Collection"
    count: int = 0
    total: int = 0
    _embedded: dict = {"elements": []}


# ============================================================================
# Tool Registration
# ============================================================================


def register(server: FastMCP, settings: Settings | None = None):
    """Register all work package tools with the MCP server"""
    settings = settings or Settings()
    client = OpenProjectClient(settings)

    @server.tool("add_comment", description="Add a comment to a work package")
    async def add_comment(params: AddCommentIn) -> dict:
        """
        Add a comment to a work package.
        """
        try:
            endpoint = f"/work_packages/{params.id}/activities"
            payload = {"comment": {"raw": params.comment}}
            res = await client.post(
                endpoint,
                params={"notify": "true" if params.notify else "false"},
                json=payload,
            )
            return res.json()
        except httpx.HTTPStatusError as e:
            map_http_error(e.response.status_code, e.response.text[:300])

    @server.tool(
        "search_content",
        description="Search OpenProject content (work packages, projects, attachments)",
    )
    async def search_content(params: SearchContentIn) -> dict:
        """
        Search across work packages, projects, and optionally attachments.

        Args:
            params: Validated search parameters

        Returns:
            dict: Collection(s) of search results
        """
        try:
            filters = []

            # Scope filter
            if params.scope == "work_packages":
                filters.append(
                    {"scope": {"operator": "=", "values": ["work_packages"]}}
                )
            elif params.scope == "projects":
                filters.append({"scope": {"operator": "=", "values": ["projects"]}})

            # Include attachments if requested
            if params.include_attachments:
                filters.append({"attachments": {"operator": "=", "values": ["1"]}})

            payload = {
                "q": params.query,
                "pageSize": params.limit,
            }

            if filters:
                payload["filters"] = filters

            res = await client.post("/queries/default", json=payload)
            return res.json()
        except httpx.HTTPStatusError as e:
            map_http_error(e.response.status_code, e.response.text[:300])

    @server.tool(
        "append_work_package_description",
        description="Append markdown text to a work package description",
    )
    async def append_work_package_description(
        params: AppendWorkPackageDescriptionIn,
    ) -> dict:
        """
        Append markdown text to an existing work package's description.

        Args:
            params: Validated input with wp_id and markdown text

        Returns:
            dict: Updated work package data
        """
        try:
            # First, get the current work package to retrieve existing description
            get_res = await client.get(f"/work_packages/{params.wp_id}")
            wp_data = get_res.json()

            # Get current description or empty string
            current_desc = wp_data.get("description", {}).get("raw", "")

            # Append new markdown
            new_desc = (
                current_desc + "\n\n" + params.markdown
                if current_desc
                else params.markdown
            )

            # Update the work package
            payload = {
                "description": {"raw": new_desc},
                "lockVersion": wp_data.get("lockVersion", 0),
            }

            update_res = await client.patch(
                f"/work_packages/{params.wp_id}", json=payload
            )
            return update_res.json()
        except httpx.HTTPStatusError as e:
            map_http_error(e.response.status_code, e.response.text[:300])

    @server.tool(
        "get_work_package_statuses",
        description="Get all available work package statuses",
    )
    async def get_work_package_statuses() -> dict:
        """
        Retrieve all available work package statuses.

        Note: This tool takes no parameters.

        Returns:
            dict: Collection of status objects
        """
        try:
            res = await client.get("/statuses")
            return res.json()
        except httpx.HTTPStatusError as e:
            map_http_error(e.response.status_code, e.response.text[:300])

    @server.tool(
        "get_work_package_types",
        description="Get available work package types, optionally filtered by project",
    )
    async def get_work_package_types(params: GetWorkPackageTypesIn) -> dict:
        """
        Retrieve available work package types.

        Args:
            params: Optional project_id to filter types

        Returns:
            dict: Collection of type objects
        """
        try:
            if params.project_id:
                # Get types available for a specific project
                res = await client.get(f"/projects/{params.project_id}/types")
            else:
                # Get all types
                res = await client.get("/types")
            return res.json()
        except httpx.HTTPStatusError as e:
            map_http_error(e.response.status_code, e.response.text[:300])

    @server.tool(
        "resolve_status", description="Resolve a status name to status ID and details"
    )
    async def resolve_status(params: ResolveStatusIn) -> dict:
        """
        Map a status name to status_id with disambiguation support.

        Args:
            params: Status name to resolve

        Returns:
            dict: Status details or disambiguation options
        """
        try:
            res = await client.get("/statuses")
            statuses_data = res.json()
            statuses = statuses_data.get("_embedded", {}).get("elements", [])

            # Normalize search term
            search_term = params.name.lower().strip()

            # Look for exact match (case-insensitive)
            exact_matches = [
                s for s in statuses if s.get("name", "").lower() == search_term
            ]

            # If multiple exact matches, return disambiguation
            if len(exact_matches) > 1:
                return {
                    "disambiguation_needed": True,
                    "matches": [
                        {
                            "id": s.get("id"),
                            "name": s.get("name"),
                            "isClosed": s.get("isClosed"),
                            "isDefault": s.get("isDefault"),
                        }
                        for s in exact_matches
                    ],
                }

            # Single exact match
            if len(exact_matches) == 1:
                status = exact_matches[0]
                return {
                    "id": status.get("id"),
                    "name": status.get("name"),
                    "isClosed": status.get("isClosed"),
                    "isDefault": status.get("isDefault"),
                }

            # Look for partial matches
            partial_matches = [
                s for s in statuses if search_term in s.get("name", "").lower()
            ]

            if len(partial_matches) == 1:
                status = partial_matches[0]
                return {
                    "id": status.get("id"),
                    "name": status.get("name"),
                    "isClosed": status.get("isClosed"),
                    "isDefault": status.get("isDefault"),
                }

            if len(partial_matches) > 1:
                return {
                    "disambiguation_needed": True,
                    "matches": [
                        {
                            "id": s.get("id"),
                            "name": s.get("name"),
                            "isClosed": s.get("isClosed"),
                            "isDefault": s.get("isDefault"),
                        }
                        for s in partial_matches
                    ],
                }

            return {"error": f"No status found matching '{params.name}'"}

        except httpx.HTTPStatusError as e:
            map_http_error(e.response.status_code, e.response.text[:300])

    @server.tool(
        "resolve_type",
        description="Resolve a type name to type ID within project context",
    )
    async def resolve_type(params: ResolveTypeIn) -> dict:
        """
        Map a type name to type_id, respecting project-specific availability.

        Args:
            params: Project ID and type name to resolve

        Returns:
            dict: Type details including project availability
        """
        try:
            # Get types available for the project
            res = await client.get(f"/projects/{params.project_id}/types")
            types_data = res.json()
            types = types_data.get("_embedded", {}).get("elements", [])

            # Normalize search term
            search_term = params.name.lower().strip()

            # Look for exact match (case-insensitive)
            exact_matches = [
                t for t in types if t.get("name", "").lower() == search_term
            ]

            # If multiple exact matches, return disambiguation
            if len(exact_matches) > 1:
                return {
                    "disambiguation_needed": True,
                    "matches": [
                        {
                            "id": t.get("id"),
                            "name": t.get("name"),
                            "is_milestone": t.get("isMilestone", False),
                            "is_default": t.get("isDefault", False),
                        }
                        for t in exact_matches
                    ],
                }

            # Single exact match
            if len(exact_matches) == 1:
                type_obj = exact_matches[0]
                return {
                    "id": type_obj.get("id"),
                    "name": type_obj.get("name"),
                    "available_in_project": True,
                    "is_milestone": type_obj.get("isMilestone", False),
                    "is_default": type_obj.get("isDefault", False),
                }

            # Look for partial matches
            partial_matches = [
                t for t in types if search_term in t.get("name", "").lower()
            ]

            if len(partial_matches) == 1:
                type_obj = partial_matches[0]
                return {
                    "id": type_obj.get("id"),
                    "name": type_obj.get("name"),
                    "available_in_project": True,
                    "is_milestone": type_obj.get("isMilestone", False),
                    "is_default": type_obj.get("isDefault", False),
                }

            if len(partial_matches) > 1:
                return {
                    "disambiguation_needed": True,
                    "matches": [
                        {
                            "id": t.get("id"),
                            "name": t.get("name"),
                            "is_milestone": t.get("isMilestone", False),
                            "is_default": t.get("isDefault", False),
                        }
                        for t in partial_matches
                    ],
                }

            # Check if type exists globally but not in project
            global_res = await client.get("/types")
            global_types = global_res.json().get("_embedded", {}).get("elements", [])

            global_match = next(
                (t for t in global_types if t.get("name", "").lower() == search_term),
                None,
            )

            if global_match:
                return {
                    "id": global_match.get("id"),
                    "name": global_match.get("name"),
                    "available_in_project": False,
                    "note": f"Type exists but is not available in project {params.project_id}",
                }

            return {"error": f"No type found matching '{params.name}'"}

        except httpx.HTTPStatusError as e:
            map_http_error(e.response.status_code, e.response.text[:300])
