from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import httpx
from datetime import date

from openproject_mcp.config import Settings
from openproject_mcp.client import OpenProjectClient
from openproject_mcp.errors import map_http_error

# ============================================================================
# Input Models (Request Parameters)
# ============================================================================


class ListTimeEntriesIn(BaseModel):
    """Input parameters for listing time entries"""

    project_id: Optional[int] = Field(
        None, description="Optional project ID to filter time entries", gt=0
    )
    wp_id: Optional[int] = Field(
        None, description="Optional work package ID to filter time entries", gt=0
    )
    user_id: Optional[int] = Field(
        None, description="Optional user ID to filter time entries", gt=0
    )
    from_date: Optional[str] = Field(
        None,
        description="Start date for filtering (YYYY-MM-DD format)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    to_date: Optional[str] = Field(
        None,
        description="End date for filtering (YYYY-MM-DD format)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    page_size: int = Field(100, description="Number of results per page", gt=0, le=1000)
    offset: int = Field(1, description="Page offset for pagination", gt=0)


class LogTimeIn(BaseModel):
    """Input parameters for logging time"""

    wp_id: int = Field(..., description="Work package ID to log time against", gt=0)
    hours: float = Field(
        ..., description="Hours to log (e.g., 1.5 for 1 hour 30 minutes)", gt=0
    )
    activity_id: int = Field(
        1, description="Activity ID (e.g., 1 for development)", gt=0
    )
    comment: str = Field(
        "", description="Optional comment/description for the time entry"
    )
    spent_on: Optional[str] = Field(
        None,
        description="Date when time was spent (YYYY-MM-DD, defaults to today)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    user_id: Optional[int] = Field(
        None, description="Optional user ID to log time for (requires permission)", gt=0
    )
    start_time: Optional[str] = Field(
        None,
        description="Optional start time in ISO datetime format (if start/end tracking enabled)",
    )
    end_time: Optional[str] = Field(
        None,
        description="Optional end time in ISO datetime format (if start/end tracking enabled)",
    )


# ============================================================================
# Output Models (Response Data - Optional but Recommended)
# ============================================================================


class TimeEntryMetadata(BaseModel):
    """Time entry metadata structure"""

    id: Optional[int] = None
    hours: Optional[str] = None  # ISO 8601 duration (e.g., "PT1H30M")
    spentOn: Optional[str] = None
    comment: Optional[Dict[str, Any]] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    startTime: Optional[str] = None
    endTime: Optional[str] = None
    _links: Optional[Dict] = None


class TimeEntryCollection(BaseModel):
    """Collection of time entries"""

    _type: str = "Collection"
    count: int = 0
    total: int = 0
    _embedded: Dict = {"elements": []}


class LogTimeResponse(BaseModel):
    """Response for logging time"""

    id: Optional[int] = None
    hours: Optional[str] = None
    spentOn: Optional[str] = None
    _type: str = "TimeEntry"
    _links: Optional[Dict] = None


# ============================================================================
# Tool Registration
# ============================================================================


def register(server: FastMCP, settings: Settings | None = None):
    """Register all time entry tools with the MCP server"""
    settings = settings or Settings()
    client = OpenProjectClient(settings)

    @server.tool(
        "list_time_entries",
        description="List time entries with optional filtering by project, work package, user, and date range",
    )
    async def list_time_entries(params: ListTimeEntriesIn) -> dict:
        """
        Retrieve time entries with flexible filtering options.

        This tool supports filtering by:
        - Project ID
        - Work package ID
        - User ID
        - Date range (from_date and/or to_date)

        Args:
            params: Validated input with optional filters and pagination

        Returns:
            dict: Collection of time entry objects

        Note:
            Uses entity_type and entity_id filters for work package scoping.
            Falls back to legacy 'work_package' filter for older API versions.
            Date filters use operators: >=d (from), <=d (to), <>d (range).
        """
        try:
            filters = []

            # Project filter
            if params.project_id:
                filters.append(
                    {"project": {"operator": "=", "values": [str(params.project_id)]}}
                )

            # Work package filter
            if params.wp_id:
                filters.append(
                    {"work_package": {"operator": "=", "values": [str(params.wp_id)]}}
                )

            # User filter
            if params.user_id:
                filters.append(
                    {"user": {"operator": "=", "values": [str(params.user_id)]}}
                )

            # Date range filters
            if params.from_date and params.to_date:
                # Date range filter
                filters.append(
                    {
                        "spent_on": {
                            "operator": "<>d",
                            "values": [params.from_date, params.to_date],
                        }
                    }
                )
            elif params.from_date:
                # From date only
                filters.append(
                    {"spent_on": {"operator": ">=d", "values": [params.from_date]}}
                )
            elif params.to_date:
                # To date only
                filters.append(
                    {"spent_on": {"operator": "<=d", "values": [params.to_date]}}
                )

            # Build query parameters
            query_params = {
                "pageSize": params.page_size,
                "offset": params.offset,
            }

            if filters:
                query_params["filters"] = str(filters)

            res = await client.get("/time_entries", params=query_params)
            return res.json()

        except httpx.HTTPStatusError as e:
            map_http_error(e.response.status_code, e.response.text[:300])

    @server.tool("log_time", description="Log time on a work package")
    async def log_time(params: LogTimeIn) -> dict:
        """
        Create a time entry on a work package.

        Converts decimal hours to ISO 8601 duration format (PT{H}H{M}M).
        For example: 1.5 hours becomes "PT1H30M"

        Args:
            params: Validated input with wp_id, hours, and optional metadata

        Returns:
            dict: Created time entry object

        Note:
            - hours: Decimal hours (e.g., 1.5 for 1 hour 30 minutes)
            - spent_on: Defaults to today if not provided
            - activity_id: Defaults to 1 (typically "Development")
            - user_id: Requires 'Log time for other users' permission
            - start_time/end_time: Only when tracking start/end times is enabled

        Example:
            Log 2.5 hours on work package 123:
            {
                "wp_id": 123,
                "hours": 2.5,
                "activity_id": 1,
                "comment": "Code review and bug fixes",
                "spent_on": "2025-11-11"
            }
        """
        try:
            # Convert decimal hours to ISO 8601 duration format
            total_minutes = int(params.hours * 60)
            hours_part = total_minutes // 60
            minutes_part = total_minutes % 60

            duration = f"PT{hours_part}H{minutes_part}M"

            # Build payload
            payload = {
                "_links": {
                    "workPackage": {"href": f"/api/v3/work_packages/{params.wp_id}"},
                    "activity": {
                        "href": f"/api/v3/time_entries/activities/{params.activity_id}"
                    },
                },
                "hours": duration,
            }

            # Add optional fields
            if params.spent_on:
                payload["spentOn"] = params.spent_on
            else:
                # Default to today
                payload["spentOn"] = date.today().isoformat()

            if params.comment:
                payload["comment"] = {"raw": params.comment}

            if params.user_id:
                payload["_links"]["user"] = {"href": f"/api/v3/users/{params.user_id}"}

            if params.start_time:
                payload["startTime"] = params.start_time

            if params.end_time:
                payload["endTime"] = params.end_time

            res = await client.post("/time_entries", json=payload)
            return res.json()

        except httpx.HTTPStatusError as e:
            map_http_error(e.response.status_code, e.response.text[:300])
