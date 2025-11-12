"""
Unit tests for user tools.

Tests user search and retrieval in OpenProject.
Uses respx for HTTP mocking to avoid real API calls.
"""

import pytest
import respx
import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from openproject_mcp.tools import users


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def server(mock_settings):
    """FastMCP server with user tools registered."""
    server = FastMCP("test-openproject")
    users.register(server, mock_settings)
    return server


@pytest.fixture
def base_url(mock_settings):
    """Base URL for API endpoints."""
    return str(mock_settings.url).rstrip("/") + "/api/v3"


# ============================================================================
# Test: resolve_user
# ============================================================================


class TestResolveUser:
    """Test suite for resolve_user tool."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_resolve_user_basic(self, server, base_url):
        """Test basic user search."""
        import json

        expected_response = {
            "_type": "Collection",
            "count": 2,
            "total": 2,
            "_embedded": {
                "elements": [
                    {
                        "id": 1,
                        "_type": "User",
                        "name": "John Smith",
                        "email": "john.smith@example.com",
                        "firstName": "John",
                        "lastName": "Smith",
                        "status": "active",
                        "createdAt": "2025-01-01T12:00:00Z",
                        "_links": {"self": {"href": "/api/v3/users/1"}},
                    },
                    {
                        "id": 2,
                        "_type": "User",
                        "name": "Jane Smith",
                        "email": "jane.smith@example.com",
                        "firstName": "Jane",
                        "lastName": "Smith",
                        "status": "active",
                        "createdAt": "2025-01-02T12:00:00Z",
                        "_links": {"self": {"href": "/api/v3/users/2"}},
                    },
                ]
            },
        }

        route = respx.get(f"{base_url}/principals").mock(
            return_value=httpx.Response(200, json=expected_response)
        )

        result = await server.call_tool(
            "resolve_user", {"params": {"search_term": "Smith"}}
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["count"] == 2
        assert len(response_data["_embedded"]["elements"]) == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_resolve_user_single_match(self, server, base_url):
        """Test user search with single result."""
        import json

        expected_response = {
            "_type": "Collection",
            "count": 1,
            "total": 1,
            "_embedded": {
                "elements": [
                    {
                        "id": 123,
                        "_type": "User",
                        "name": "Alice Johnson",
                        "email": "alice@example.com",
                        "firstName": "Alice",
                        "lastName": "Johnson",
                        "status": "active",
                    }
                ]
            },
        }

        route = respx.get(f"{base_url}/principals").mock(
            return_value=httpx.Response(200, json=expected_response)
        )

        result = await server.call_tool(
            "resolve_user", {"params": {"search_term": "Alice"}}
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["count"] == 1
        assert response_data["_embedded"]["elements"][0]["name"] == "Alice Johnson"

    @respx.mock
    @pytest.mark.asyncio
    async def test_resolve_user_with_limit(self, server, base_url):
        """Test user search with custom limit."""
        import json

        expected_response = {
            "_type": "Collection",
            "count": 5,
            "total": 10,
            "_embedded": {
                "elements": [
                    {"id": i, "_type": "User", "name": f"User {i}"} for i in range(1, 6)
                ]
            },
        }

        route = respx.get(f"{base_url}/principals").mock(
            return_value=httpx.Response(200, json=expected_response)
        )

        result = await server.call_tool(
            "resolve_user", {"params": {"search_term": "User", "limit": 5}}
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["count"] == 5

    @respx.mock
    @pytest.mark.asyncio
    async def test_resolve_user_no_results(self, server, base_url):
        """Test user search with no matches."""
        import json

        expected_response = {
            "_type": "Collection",
            "count": 0,
            "total": 0,
            "_embedded": {"elements": []},
        }

        route = respx.get(f"{base_url}/principals").mock(
            return_value=httpx.Response(200, json=expected_response)
        )

        result = await server.call_tool(
            "resolve_user", {"params": {"search_term": "nonexistent"}}
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["count"] == 0
        assert len(response_data["_embedded"]["elements"]) == 0

    @respx.mock
    @pytest.mark.asyncio
    async def test_resolve_user_partial_name(self, server, base_url):
        """Test user search with partial name matching."""
        import json

        expected_response = {
            "_type": "Collection",
            "count": 3,
            "total": 3,
            "_embedded": {
                "elements": [
                    {"id": 1, "_type": "User", "name": "Bob Brown"},
                    {"id": 2, "_type": "User", "name": "Bobby Johnson"},
                    {"id": 3, "_type": "User", "name": "Robert Smith"},
                ]
            },
        }

        route = respx.get(f"{base_url}/principals").mock(
            return_value=httpx.Response(200, json=expected_response)
        )

        result = await server.call_tool(
            "resolve_user", {"params": {"search_term": "Bob"}}
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["count"] == 3

    @respx.mock
    @pytest.mark.asyncio
    async def test_resolve_user_by_email(self, server, base_url):
        """Test user search by email."""
        import json

        expected_response = {
            "_type": "Collection",
            "count": 1,
            "total": 1,
            "_embedded": {
                "elements": [
                    {
                        "id": 99,
                        "_type": "User",
                        "name": "Test User",
                        "email": "test@example.com",
                    }
                ]
            },
        }

        route = respx.get(f"{base_url}/principals").mock(
            return_value=httpx.Response(200, json=expected_response)
        )

        result = await server.call_tool(
            "resolve_user", {"params": {"search_term": "test@example.com"}}
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["count"] == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_resolve_user_unauthorized(self, server, base_url):
        """Test error when user is not authenticated."""
        route = respx.get(f"{base_url}/principals").mock(
            return_value=httpx.Response(401, json={"message": "Unauthorized"})
        )

        with pytest.raises(ToolError) as exc_info:
            await server.call_tool("resolve_user", {"params": {"search_term": "test"}})

        assert route.called
        assert "Authentication failed" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_resolve_user_forbidden(self, server, base_url):
        """Test error when user lacks permission."""
        route = respx.get(f"{base_url}/principals").mock(
            return_value=httpx.Response(403, json={"message": "Forbidden"})
        )

        with pytest.raises(ToolError) as exc_info:
            await server.call_tool("resolve_user", {"params": {"search_term": "test"}})

        assert route.called
        assert "Permission denied" in str(exc_info.value)


# ============================================================================
# Test: get_user_by_id
# ============================================================================


class TestGetUserById:
    """Test suite for get_user_by_id tool."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_user_by_id_basic(self, server, base_url):
        """Test getting user by ID."""
        import json

        expected_response = {
            "id": 123,
            "_type": "User",
            "name": "John Doe",
            "email": "john.doe@example.com",
            "firstName": "John",
            "lastName": "Doe",
            "status": "active",
            "createdAt": "2025-01-01T12:00:00Z",
            "updatedAt": "2025-01-15T14:30:00Z",
            "_links": {
                "self": {"href": "/api/v3/users/123"},
                "memberships": {"href": "/api/v3/users/123/memberships"},
            },
        }

        route = respx.get(f"{base_url}/users/123").mock(
            return_value=httpx.Response(200, json=expected_response)
        )

        result = await server.call_tool("get_user_by_id", {"params": {"user_id": 123}})

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["id"] == 123
        assert response_data["name"] == "John Doe"
        assert response_data["email"] == "john.doe@example.com"

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_user_by_id_complete_info(self, server, base_url):
        """Test getting user with complete information."""
        import json

        expected_response = {
            "id": 456,
            "_type": "User",
            "name": "Jane Smith",
            "email": "jane.smith@example.com",
            "firstName": "Jane",
            "lastName": "Smith",
            "status": "active",
            "createdAt": "2024-06-15T08:00:00Z",
            "updatedAt": "2025-01-20T10:15:00Z",
            "admin": False,
            "language": "en",
            "_links": {
                "self": {"href": "/api/v3/users/456"},
                "memberships": {"href": "/api/v3/users/456/memberships"},
                "showUser": {"href": "/users/456"},
            },
        }

        route = respx.get(f"{base_url}/users/456").mock(
            return_value=httpx.Response(200, json=expected_response)
        )

        result = await server.call_tool("get_user_by_id", {"params": {"user_id": 456}})

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["id"] == 456
        assert response_data["admin"] is False
        assert response_data["language"] == "en"

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, server, base_url):
        """Test error when user doesn't exist."""
        route = respx.get(f"{base_url}/users/99999").mock(
            return_value=httpx.Response(404, json={"message": "User not found"})
        )

        with pytest.raises(ToolError) as exc_info:
            await server.call_tool("get_user_by_id", {"params": {"user_id": 99999}})

        assert route.called
        assert "Resource not found" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_user_by_id_unauthorized(self, server, base_url):
        """Test error when not authenticated."""
        route = respx.get(f"{base_url}/users/123").mock(
            return_value=httpx.Response(401, json={"message": "Unauthorized"})
        )

        with pytest.raises(ToolError) as exc_info:
            await server.call_tool("get_user_by_id", {"params": {"user_id": 123}})

        assert route.called
        assert "Authentication failed" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_user_by_id_forbidden(self, server, base_url):
        """Test error when user lacks permission."""
        route = respx.get(f"{base_url}/users/123").mock(
            return_value=httpx.Response(403, json={"message": "Forbidden"})
        )

        with pytest.raises(ToolError) as exc_info:
            await server.call_tool("get_user_by_id", {"params": {"user_id": 123}})

        assert route.called
        assert "Permission denied" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_user_by_id_locked_user(self, server, base_url):
        """Test getting information about a locked user."""
        import json

        expected_response = {
            "id": 789,
            "_type": "User",
            "name": "Locked User",
            "email": "locked@example.com",
            "status": "locked",
            "createdAt": "2024-01-01T12:00:00Z",
            "updatedAt": "2024-12-31T23:59:59Z",
        }

        route = respx.get(f"{base_url}/users/789").mock(
            return_value=httpx.Response(200, json=expected_response)
        )

        result = await server.call_tool("get_user_by_id", {"params": {"user_id": 789}})

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["id"] == 789
        assert response_data["status"] == "locked"

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_user_by_id_admin_user(self, server, base_url):
        """Test getting information about an admin user."""
        import json

        expected_response = {
            "id": 1,
            "_type": "User",
            "name": "Admin User",
            "email": "admin@example.com",
            "firstName": "Admin",
            "lastName": "User",
            "status": "active",
            "admin": True,
            "createdAt": "2020-01-01T00:00:00Z",
        }

        route = respx.get(f"{base_url}/users/1").mock(
            return_value=httpx.Response(200, json=expected_response)
        )

        result = await server.call_tool("get_user_by_id", {"params": {"user_id": 1}})

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["id"] == 1
        assert response_data["admin"] is True

    @pytest.mark.asyncio
    async def test_get_user_by_id_invalid_id_negative(self, server):
        """Test validation error for negative user ID."""
        with pytest.raises(ToolError) as exc_info:
            await server.call_tool("get_user_by_id", {"params": {"user_id": -1}})

        assert "validation" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_user_by_id_invalid_id_zero(self, server):
        """Test validation error for zero user ID."""
        with pytest.raises(ToolError) as exc_info:
            await server.call_tool("get_user_by_id", {"params": {"user_id": 0}})

        assert "validation" in str(exc_info.value).lower()
