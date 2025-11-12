from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import Optional, Dict

# ============================================================================
# Input Models (Request Parameters)
# ============================================================================


class ResolveUserIn(BaseModel):
    """Input parameters for resolving/searching users"""

    search_term: str = Field(
        ...,
        description="Search term to match against user names (any_name_attribute)",
        min_length=1,
    )
    limit: int = Field(
        10, description="Maximum number of results to return", gt=0, le=100
    )


class GetUserByIdIn(BaseModel):
    """Input parameters for getting a user by ID"""

    user_id: int = Field(..., description="User ID to retrieve", gt=0)


# ============================================================================
# Output Models (Response Data - Optional but Recommended)
# ============================================================================


class UserMetadata(BaseModel):
    """User metadata structure"""

    id: Optional[int] = None
    name: Optional[str] = None
    email: Optional[str] = None
    login: Optional[str] = None  # May not be available in v3
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    status: Optional[str] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    _type: Optional[str] = None
    _links: Optional[Dict] = None


class UserCollection(BaseModel):
    """Collection of users (principals)"""

    _type: str = "Collection"
    count: int = 0
    total: int = 0
    _embedded: Dict = {"elements": []}


# ============================================================================
# Tool Registration
# ============================================================================


def register(server: FastMCP):
    """Register all user tools with the MCP server"""

    @server.tool(
        "resolve_user", description="Search for users by name (resolve user identity)"
    )
    async def resolve_user(params: ResolveUserIn) -> dict:
        """
        Search for active users matching a search term.

        Uses the /principals endpoint with filters to find users by name.
        Only returns active users (status = 1).

        Args:
            params: Validated input with search_term and limit

        Returns:
            dict: Collection of matching user objects

        Note:
            - Searches using 'any_name_attribute' operator '~' (contains)
            - Filters by type='User' and status='1' (active)
            - Uses select parameter to limit returned fields (id, name, email)
            - Falls back to select=* if server doesn't support field selection
            - v3 API may not return 'login' field
        """
        return {
            "error": {
                "code": "NotImplemented",
                "message": "resolve_user not implemented yet",
                "details": {"search_term": params.search_term, "limit": params.limit},
            }
        }

    @server.tool("get_user_by_id", description="Get a single user by their ID")
    async def get_user_by_id(params: GetUserByIdIn) -> dict:
        """
        Retrieve detailed information about a specific user.

        Args:
            params: Validated input with user_id

        Returns:
            dict: User object with full details

        Raises:
            Exception: If the user doesn't exist or cannot be accessed

        Note:
            Returns complete user information including email, status,
            creation date, and links to related resources.
        """
        return {
            "error": {
                "code": "NotImplemented",
                "message": "get_user_by_id not implemented yet",
                "details": {"user_id": params.user_id},
            }
        }
