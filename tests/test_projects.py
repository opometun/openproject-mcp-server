"""
Unit tests for project tools.

Tests project memberships and project resolution in OpenProject.
Uses respx for HTTP mocking to avoid real API calls.
"""

import pytest
import respx
import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from openproject_mcp.tools import projects


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def server(mock_settings):
    """FastMCP server with project tools registered."""
    server = FastMCP("test-openproject")
    projects.register(server, mock_settings)
    return server


@pytest.fixture
def base_url(mock_settings):
    """Base URL for API endpoints."""
    return str(mock_settings.url).rstrip("/") + "/api/v3"


# ============================================================================
# Test: get_project_memberships
# ============================================================================


class TestGetProjectMemberships:
    """Test suite for get_project_memberships tool."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_memberships_basic(self, server, base_url):
        """Test getting project memberships."""
        import json

        expected_response = {
            "_type": "Collection",
            "count": 3,
            "total": 3,
            "_embedded": {
                "elements": [
                    {
                        "id": 1,
                        "_type": "Membership",
                        "createdAt": "2025-01-01T12:00:00Z",
                        "_links": {
                            "user": {"href": "/api/v3/users/10"},
                            "project": {"href": "/api/v3/projects/123"},
                            "roles": [{"href": "/api/v3/roles/5"}],
                        },
                    },
                    {
                        "id": 2,
                        "_type": "Membership",
                        "createdAt": "2025-01-02T12:00:00Z",
                        "_links": {
                            "user": {"href": "/api/v3/users/20"},
                            "project": {"href": "/api/v3/projects/123"},
                            "roles": [{"href": "/api/v3/roles/6"}],
                        },
                    },
                    {
                        "id": 3,
                        "_type": "Membership",
                        "createdAt": "2025-01-03T12:00:00Z",
                        "_links": {
                            "user": {"href": "/api/v3/users/30"},
                            "project": {"href": "/api/v3/projects/123"},
                            "roles": [
                                {"href": "/api/v3/roles/5"},
                                {"href": "/api/v3/roles/6"},
                            ],
                        },
                    },
                ]
            },
        }

        route = respx.get(f"{base_url}/memberships").mock(
            return_value=httpx.Response(200, json=expected_response)
        )

        result = await server.call_tool(
            "get_project_memberships", {"params": {"project_id": 123}}
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["count"] == 3
        assert len(response_data["_embedded"]["elements"]) == 3

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_memberships_with_pagination(self, server, base_url):
        """Test membership retrieval with pagination."""
        import json

        expected_response = {
            "_type": "Collection",
            "count": 2,
            "total": 5,
            "pageSize": 2,
            "offset": 2,
            "_embedded": {
                "elements": [
                    {"id": 3, "_type": "Membership"},
                    {"id": 4, "_type": "Membership"},
                ]
            },
        }

        route = respx.get(f"{base_url}/memberships").mock(
            return_value=httpx.Response(200, json=expected_response)
        )

        result = await server.call_tool(
            "get_project_memberships",
            {"params": {"project_id": 123, "page_size": 2, "offset": 2}},
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["count"] == 2
        assert response_data["offset"] == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_memberships_with_follow(self, server, base_url):
        """Test membership retrieval with follow parameter (multi-page collection)."""
        import json

        page1_response = {
            "_type": "Collection",
            "count": 2,
            "total": 5,
            "pageSize": 2,
            "offset": 1,
            "_embedded": {
                "elements": [
                    {"id": 1, "_type": "Membership"},
                    {"id": 2, "_type": "Membership"},
                ]
            },
        }

        page2_response = {
            "_type": "Collection",
            "count": 2,
            "total": 5,
            "pageSize": 2,
            "offset": 2,
            "_embedded": {
                "elements": [
                    {"id": 3, "_type": "Membership"},
                    {"id": 4, "_type": "Membership"},
                ]
            },
        }

        page3_response = {
            "_type": "Collection",
            "count": 1,
            "total": 5,
            "pageSize": 2,
            "offset": 3,
            "_embedded": {"elements": [{"id": 5, "_type": "Membership"}]},
        }

        route = respx.get(f"{base_url}/memberships").mock(
            side_effect=[
                httpx.Response(200, json=page1_response),
                httpx.Response(200, json=page2_response),
                httpx.Response(200, json=page3_response),
            ]
        )

        result = await server.call_tool(
            "get_project_memberships", {"params": {"project_id": 123, "follow": 5}}
        )

        assert route.call_count == 3
        response_data = json.loads(result[0].text)
        assert response_data["count"] == 5
        assert len(response_data["_embedded"]["elements"]) == 5

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_memberships_with_follow_trim(self, server, base_url):
        """Test follow parameter trims results to exact limit."""
        import json

        page1_response = {
            "_type": "Collection",
            "count": 3,
            "total": 10,
            "pageSize": 3,
            "offset": 1,
            "_embedded": {
                "elements": [
                    {"id": 1, "_type": "Membership"},
                    {"id": 2, "_type": "Membership"},
                    {"id": 3, "_type": "Membership"},
                ]
            },
        }

        page2_response = {
            "_type": "Collection",
            "count": 3,
            "total": 10,
            "pageSize": 3,
            "offset": 2,
            "_embedded": {
                "elements": [
                    {"id": 4, "_type": "Membership"},
                    {"id": 5, "_type": "Membership"},
                    {"id": 6, "_type": "Membership"},
                ]
            },
        }

        route = respx.get(f"{base_url}/memberships").mock(
            side_effect=[
                httpx.Response(200, json=page1_response),
                httpx.Response(200, json=page2_response),
            ]
        )

        result = await server.call_tool(
            "get_project_memberships", {"params": {"project_id": 123, "follow": 5}}
        )

        assert route.call_count == 2
        response_data = json.loads(result[0].text)
        assert response_data["count"] == 5  # Trimmed to 5
        assert len(response_data["_embedded"]["elements"]) == 5

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_memberships_empty(self, server, base_url):
        """Test getting memberships when none exist."""
        import json

        expected_response = {
            "_type": "Collection",
            "count": 0,
            "total": 0,
            "_embedded": {"elements": []},
        }

        route = respx.get(f"{base_url}/memberships").mock(
            return_value=httpx.Response(200, json=expected_response)
        )

        result = await server.call_tool(
            "get_project_memberships", {"params": {"project_id": 123}}
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["count"] == 0

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_memberships_project_not_found(self, server, base_url):
        """Test error when project doesn't exist."""
        route = respx.get(f"{base_url}/memberships").mock(
            return_value=httpx.Response(404, json={"message": "Project not found"})
        )

        with pytest.raises(ToolError) as exc_info:
            await server.call_tool(
                "get_project_memberships", {"params": {"project_id": 99999}}
            )

        assert route.called
        assert "Resource not found" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_memberships_unauthorized(self, server, base_url):
        """Test error when user lacks permission."""
        route = respx.get(f"{base_url}/memberships").mock(
            return_value=httpx.Response(403, json={"message": "Forbidden"})
        )

        with pytest.raises(ToolError) as exc_info:
            await server.call_tool(
                "get_project_memberships", {"params": {"project_id": 123}}
            )

        assert route.called
        assert "Permission denied" in str(exc_info.value)


# ============================================================================
# Test: resolve_project
# ============================================================================


class TestResolveProject:
    """Test suite for resolve_project tool."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_resolve_project_exact_identifier(self, server, base_url):
        """Test exact identifier match."""
        import json

        projects_response = {
            "_embedded": {
                "elements": [
                    {
                        "id": 123,
                        "identifier": "my-project",
                        "name": "My Project",
                        "_links": {"self": {"href": "/api/v3/projects/123"}},
                    },
                    {
                        "id": 456,
                        "identifier": "other-project",
                        "name": "Other Project",
                        "_links": {"self": {"href": "/api/v3/projects/456"}},
                    },
                ]
            }
        }

        route = respx.get(f"{base_url}/projects").mock(
            return_value=httpx.Response(200, json=projects_response)
        )

        result = await server.call_tool(
            "resolve_project", {"params": {"name_or_identifier": "my-project"}}
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["id"] == 123
        assert response_data["identifier"] == "my-project"
        assert response_data["name"] == "My Project"

    @respx.mock
    @pytest.mark.asyncio
    async def test_resolve_project_case_insensitive(self, server, base_url):
        """Test case-insensitive identifier matching."""
        import json

        projects_response = {
            "_embedded": {
                "elements": [
                    {
                        "id": 123,
                        "identifier": "My-Project",
                        "name": "My Project",
                        "_links": {"self": {"href": "/api/v3/projects/123"}},
                    }
                ]
            }
        }

        route = respx.get(f"{base_url}/projects").mock(
            return_value=httpx.Response(200, json=projects_response)
        )

        result = await server.call_tool(
            "resolve_project", {"params": {"name_or_identifier": "my-project"}}
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["id"] == 123

    @respx.mock
    @pytest.mark.asyncio
    async def test_resolve_project_by_name(self, server, base_url):
        """Test project resolution by name."""
        import json

        projects_response = {
            "_embedded": {
                "elements": [
                    {
                        "id": 123,
                        "identifier": "proj-123",
                        "name": "Awesome Project",
                        "_links": {"self": {"href": "/api/v3/projects/123"}},
                    }
                ]
            }
        }

        route = respx.get(f"{base_url}/projects").mock(
            return_value=httpx.Response(200, json=projects_response)
        )

        result = await server.call_tool(
            "resolve_project", {"params": {"name_or_identifier": "Awesome"}}
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["id"] == 123
        assert response_data["name"] == "Awesome Project"

    @respx.mock
    @pytest.mark.asyncio
    async def test_resolve_project_partial_identifier(self, server, base_url):
        """Test partial identifier matching."""
        import json

        projects_response = {
            "_embedded": {
                "elements": [
                    {
                        "id": 123,
                        "identifier": "myproject-2025",
                        "name": "My Project 2025",
                        "_links": {"self": {"href": "/api/v3/projects/123"}},
                    }
                ]
            }
        }

        route = respx.get(f"{base_url}/projects").mock(
            return_value=httpx.Response(200, json=projects_response)
        )

        result = await server.call_tool(
            "resolve_project", {"params": {"name_or_identifier": "myproject"}}
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["id"] == 123

    @respx.mock
    @pytest.mark.asyncio
    async def test_resolve_project_disambiguation_identifiers(self, server, base_url):
        """Test disambiguation when multiple identifiers match."""
        import json

        projects_response = {
            "_embedded": {
                "elements": [
                    {
                        "id": 1,
                        "identifier": "project",
                        "name": "Project One",
                        "_links": {"self": {"href": "/api/v3/projects/1"}},
                    },
                    {
                        "id": 2,
                        "identifier": "project",  # Duplicate identifier (edge case)
                        "name": "Project Two",
                        "_links": {"self": {"href": "/api/v3/projects/2"}},
                    },
                ]
            }
        }

        route = respx.get(f"{base_url}/projects").mock(
            return_value=httpx.Response(200, json=projects_response)
        )

        result = await server.call_tool(
            "resolve_project", {"params": {"name_or_identifier": "project"}}
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["disambiguation_needed"] is True
        assert len(response_data["matches"]) == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_resolve_project_disambiguation_names(self, server, base_url):
        """Test disambiguation when multiple names match."""
        import json

        projects_response = {
            "_embedded": {
                "elements": [
                    {
                        "id": 1,
                        "identifier": "alpha-project",
                        "name": "Alpha Project",
                        "_links": {"self": {"href": "/api/v3/projects/1"}},
                    },
                    {
                        "id": 2,
                        "identifier": "alpha-project-2",
                        "name": "Alpha Project 2",
                        "_links": {"self": {"href": "/api/v3/projects/2"}},
                    },
                ]
            }
        }

        route = respx.get(f"{base_url}/projects").mock(
            return_value=httpx.Response(200, json=projects_response)
        )

        result = await server.call_tool(
            "resolve_project", {"params": {"name_or_identifier": "Alpha"}}
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["disambiguation_needed"] is True
        assert len(response_data["matches"]) == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_resolve_project_not_found(self, server, base_url):
        """Test error when project doesn't exist."""
        import json

        projects_response = {"_embedded": {"elements": []}}

        route = respx.get(f"{base_url}/projects").mock(
            return_value=httpx.Response(200, json=projects_response)
        )

        result = await server.call_tool(
            "resolve_project", {"params": {"name_or_identifier": "nonexistent"}}
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert "error" in response_data
        assert "No project found" in response_data["error"]

    @respx.mock
    @pytest.mark.asyncio
    async def test_resolve_project_unauthorized(self, server, base_url):
        """Test error when user is not authenticated."""
        route = respx.get(f"{base_url}/projects").mock(
            return_value=httpx.Response(401, json={"message": "Unauthorized"})
        )

        with pytest.raises(ToolError) as exc_info:
            await server.call_tool(
                "resolve_project", {"params": {"name_or_identifier": "test"}}
            )

        assert route.called
        assert "Authentication failed" in str(exc_info.value)
