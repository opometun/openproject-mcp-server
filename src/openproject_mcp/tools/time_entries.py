from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

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


def register(server: FastMCP):
    """Register all time entry tools with the MCP server"""

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
        return {
            "error": {
                "code": "NotImplemented",
                "message": "list_time_entries not implemented yet",
                "details": {
                    "project_id": params.project_id,
                    "wp_id": params.wp_id,
                    "user_id": params.user_id,
                    "from_date": params.from_date,
                    "to_date": params.to_date,
                    "page_size": params.page_size,
                    "offset": params.offset,
                },
            }
        }

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
        return {
            "error": {
                "code": "NotImplemented",
                "message": "log_time not implemented yet",
                "details": {
                    "wp_id": params.wp_id,
                    "hours": params.hours,
                    "activity_id": params.activity_id,
                    "comment": params.comment,
                    "spent_on": params.spent_on,
                    "user_id": params.user_id,
                    "start_time": params.start_time,
                    "end_time": params.end_time,
                },
            }
        }
