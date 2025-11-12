"""
Unit tests for work package tools.

Tests the add_comment tool and placeholders for unimplemented tools.
Uses respx for HTTP mocking to avoid real API calls.
"""

import pytest
import respx
import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from openproject_mcp.tools import work_packages

from tests.helpers.mocks import mock_activity

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def server(mock_settings):
    """FastMCP server with work package tools registered."""
    server = FastMCP("test-openproject")
    work_packages.register(server, mock_settings)
    return server


@pytest.fixture
def base_url(mock_settings):
    """Base URL for API endpoints (matching what OpenProjectClient uses)."""
    return str(mock_settings.url).rstrip("/") + "/api/v3"


# ============================================================================
# Test: add_comment
# ============================================================================


class TestAddComment:
    """Test suite for add_comment tool."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_add_comment_success(self, server, base_url):
        """Test successful comment addition returns activity data."""
        import json

        expected_response = mock_activity(456, "Test comment")

        route = respx.post(
            f"{base_url}/work_packages/123/activities", params={"notify": "false"}
        ).mock(return_value=httpx.Response(201, json=expected_response))

        result = await server.call_tool(
            "add_comment",
            {"params": {"id": 123, "comment": "Test comment", "notify": False}},
        )

        assert route.called, "API endpoint was not called"

        # FastMCP returns list[TextContent], extract the actual response
        assert isinstance(result, list), "Result should be a list"
        assert len(result) > 0, "Result should not be empty"

        # FastMCP wraps dict responses in TextContent objects
        response_data = json.loads(result[0].text)
        assert response_data["id"] == 456, "Activity ID mismatch"
        assert response_data["comment"]["raw"] == "Test comment"

    @respx.mock
    @pytest.mark.asyncio
    async def test_add_comment_with_notify(self, server, base_url):
        """Test comment addition with email notifications enabled."""
        import json

        expected_response = mock_activity(789, "Important update")

        route = respx.post(
            f"{base_url}/work_packages/456/activities", params={"notify": "true"}
        ).mock(return_value=httpx.Response(201, json=expected_response))

        result = await server.call_tool(
            "add_comment",
            {"params": {"id": 456, "comment": "Important update", "notify": True}},
        )

        assert route.called, "API endpoint was not called"
        response_data = json.loads(result[0].text)
        assert response_data["id"] == 789
        assert response_data["comment"]["raw"] == "Important update"

    @respx.mock
    @pytest.mark.asyncio
    async def test_add_comment_markdown_formatting(self, server, base_url):
        """Test comment with markdown formatting is preserved."""
        import json

        markdown_text = "# Header\n\n- Item 1\n- Item 2\n\n**Bold text**"
        expected_response = mock_activity(999, markdown_text)

        route = respx.post(
            f"{base_url}/work_packages/123/activities", params={"notify": "false"}
        ).mock(return_value=httpx.Response(201, json=expected_response))

        result = await server.call_tool(
            "add_comment",
            {"params": {"id": 123, "comment": markdown_text, "notify": False}},
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["comment"]["raw"] == markdown_text

    @respx.mock
    @pytest.mark.asyncio
    async def test_add_comment_work_package_not_found(self, server, base_url):
        """Test error handling when work package doesn't exist."""
        route = respx.post(
            f"{base_url}/work_packages/99999/activities", params={"notify": "false"}
        ).mock(
            return_value=httpx.Response(404, json={"message": "Work package not found"})
        )

        with pytest.raises(ToolError) as exc_info:
            await server.call_tool(
                "add_comment",
                {"params": {"id": 99999, "comment": "Test", "notify": False}},
            )

        assert route.called
        assert "Resource not found" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_add_comment_unauthorized(self, server, base_url):
        """Test error handling for unauthorized access."""
        route = respx.post(
            f"{base_url}/work_packages/123/activities", params={"notify": "false"}
        ).mock(return_value=httpx.Response(401, json={"message": "Unauthorized"}))

        with pytest.raises(ToolError) as exc_info:
            await server.call_tool(
                "add_comment",
                {"params": {"id": 123, "comment": "Test", "notify": False}},
            )

        assert route.called
        assert "Authentication failed" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_add_comment_forbidden(self, server, base_url):
        """Test error handling when user lacks permission."""
        route = respx.post(
            f"{base_url}/work_packages/123/activities", params={"notify": "false"}
        ).mock(return_value=httpx.Response(403, json={"message": "Forbidden"}))

        with pytest.raises(ToolError) as exc_info:
            await server.call_tool(
                "add_comment",
                {"params": {"id": 123, "comment": "Test", "notify": False}},
            )

        assert route.called
        assert "Permission denied" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_add_comment_validation_error(self, server, base_url):
        """Test error handling for invalid comment data."""
        route = respx.post(
            f"{base_url}/work_packages/123/activities", params={"notify": "false"}
        ).mock(
            return_value=httpx.Response(
                422, json={"message": "Comment cannot be empty"}
            )
        )

        with pytest.raises(ToolError) as exc_info:
            await server.call_tool(
                "add_comment",
                {"params": {"id": 123, "comment": "Test", "notify": False}},
            )

        assert route.called
        assert "Validation failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_add_comment_invalid_id_negative(self, server):
        """Test validation error for negative work package ID."""
        with pytest.raises(ToolError) as exc_info:
            await server.call_tool(
                "add_comment",
                {"params": {"id": -1, "comment": "Test", "notify": False}},
            )

        # Pydantic validation should catch this before making the request
        assert "validation" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_add_comment_invalid_id_zero(self, server):
        """Test validation error for zero work package ID."""
        with pytest.raises(ToolError) as exc_info:
            await server.call_tool(
                "add_comment", {"params": {"id": 0, "comment": "Test", "notify": False}}
            )

        assert "validation" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_add_comment_empty_comment(self, server):
        """Test validation error for empty comment text."""
        with pytest.raises(ToolError) as exc_info:
            await server.call_tool(
                "add_comment", {"params": {"id": 123, "comment": "", "notify": False}}
            )

        assert "validation" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_add_comment_missing_required_params(self, server):
        """Test validation error when required parameters are missing."""
        with pytest.raises(ToolError):
            await server.call_tool(
                "add_comment",
                {"params": {"id": 123}},  # Missing 'comment'
            )

    @respx.mock
    @pytest.mark.asyncio
    async def test_add_comment_default_notify_false(self, server, base_url):
        """Test that notify defaults to false when not specified."""
        import json

        expected_response = mock_activity(111, "Test")

        route = respx.post(
            f"{base_url}/work_packages/123/activities", params={"notify": "false"}
        ).mock(return_value=httpx.Response(201, json=expected_response))

        # Don't specify notify parameter
        result = await server.call_tool(
            "add_comment", {"params": {"id": 123, "comment": "Test"}}
        )

        assert route.called, "Should default to notify=false"
        response_data = json.loads(result[0].text)
        assert response_data["id"] == 111

    @respx.mock
    @pytest.mark.asyncio
    async def test_add_comment_server_error_retry(self, server, base_url):
        """Test that server errors are retried according to settings."""
        route = respx.post(
            f"{base_url}/work_packages/123/activities", params={"notify": "false"}
        ).mock(
            side_effect=[
                httpx.Response(500, json={"message": "Internal Server Error"}),
                httpx.Response(500, json={"message": "Internal Server Error"}),
                httpx.Response(500, json={"message": "Internal Server Error"}),
            ]
        )

        with pytest.raises(ToolError):
            await server.call_tool(
                "add_comment",
                {"params": {"id": 123, "comment": "Test", "notify": False}},
            )

        # Should retry up to max_retries (3 times in mock_settings)
        assert route.call_count == 3

    @respx.mock
    @pytest.mark.asyncio
    async def test_add_comment_unicode_content(self, server, base_url):
        """Test comment with unicode characters."""
        import json

        unicode_text = "Hello 世界 🌍 Привет مرحبا"
        expected_response = mock_activity(777, unicode_text)

        route = respx.post(
            f"{base_url}/work_packages/123/activities", params={"notify": "false"}
        ).mock(return_value=httpx.Response(201, json=expected_response))

        result = await server.call_tool(
            "add_comment",
            {"params": {"id": 123, "comment": unicode_text, "notify": False}},
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["comment"]["raw"] == unicode_text

    @respx.mock
    @pytest.mark.asyncio
    async def test_add_comment_long_text(self, server, base_url):
        """Test comment with very long text."""
        import json

        long_text = "A" * 5000  # 5000 characters
        expected_response = mock_activity(888, long_text)

        route = respx.post(
            f"{base_url}/work_packages/123/activities", params={"notify": "false"}
        ).mock(return_value=httpx.Response(201, json=expected_response))

        result = await server.call_tool(
            "add_comment",
            {"params": {"id": 123, "comment": long_text, "notify": False}},
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert len(response_data["comment"]["raw"]) == 5000


# ============================================================================
# Test: get_work_package_statuses
# ============================================================================


class TestGetWorkPackageStatuses:
    """Test suite for get_work_package_statuses tool."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_statuses_success(self, server, base_url):
        """Test successful retrieval of all statuses."""
        import json

        expected_response = {
            "_type": "Collection",
            "count": 3,
            "total": 3,
            "_embedded": {
                "elements": [
                    {"id": 1, "name": "New", "isClosed": False, "isDefault": True},
                    {
                        "id": 2,
                        "name": "In Progress",
                        "isClosed": False,
                        "isDefault": False,
                    },
                    {"id": 3, "name": "Closed", "isClosed": True, "isDefault": False},
                ]
            },
        }

        route = respx.get(f"{base_url}/statuses").mock(
            return_value=httpx.Response(200, json=expected_response)
        )

        result = await server.call_tool("get_work_package_statuses", {"params": {}})

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["count"] == 3
        assert len(response_data["_embedded"]["elements"]) == 3

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_statuses_unauthorized(self, server, base_url):
        """Test error handling for unauthorized access."""
        route = respx.get(f"{base_url}/statuses").mock(
            return_value=httpx.Response(401, json={"message": "Unauthorized"})
        )

        with pytest.raises(ToolError) as exc_info:
            await server.call_tool("get_work_package_statuses", {"params": {}})

        assert route.called
        assert "Authentication failed" in str(exc_info.value)


# ============================================================================
# Test: get_work_package_types
# ============================================================================


class TestGetWorkPackageTypes:
    """Test suite for get_work_package_types tool."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_types_all(self, server, base_url):
        """Test retrieval of all types without project filter."""
        import json

        expected_response = {
            "_type": "Collection",
            "count": 3,
            "total": 3,
            "_embedded": {
                "elements": [
                    {"id": 1, "name": "Task", "isMilestone": False, "isDefault": True},
                    {"id": 2, "name": "Bug", "isMilestone": False, "isDefault": False},
                    {
                        "id": 3,
                        "name": "Milestone",
                        "isMilestone": True,
                        "isDefault": False,
                    },
                ]
            },
        }

        route = respx.get(f"{base_url}/types").mock(
            return_value=httpx.Response(200, json=expected_response)
        )

        result = await server.call_tool("get_work_package_types", {"params": {}})

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["count"] == 3

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_types_by_project(self, server, base_url):
        """Test retrieval of types filtered by project."""
        import json

        expected_response = {
            "_type": "Collection",
            "count": 2,
            "total": 2,
            "_embedded": {
                "elements": [
                    {"id": 1, "name": "Task", "isMilestone": False},
                    {"id": 2, "name": "Bug", "isMilestone": False},
                ]
            },
        }

        route = respx.get(f"{base_url}/projects/123/types").mock(
            return_value=httpx.Response(200, json=expected_response)
        )

        result = await server.call_tool(
            "get_work_package_types", {"params": {"project_id": 123}}
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["count"] == 2


# ============================================================================
# Test: resolve_status
# ============================================================================


class TestResolveStatus:
    """Test suite for resolve_status tool."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_resolve_status_exact_match(self, server, base_url):
        """Test exact status name match."""
        import json

        statuses_response = {
            "_embedded": {
                "elements": [
                    {"id": 1, "name": "New", "isClosed": False, "isDefault": True},
                    {
                        "id": 2,
                        "name": "In Progress",
                        "isClosed": False,
                        "isDefault": False,
                    },
                ]
            }
        }

        route = respx.get(f"{base_url}/statuses").mock(
            return_value=httpx.Response(200, json=statuses_response)
        )

        result = await server.call_tool(
            "resolve_status", {"params": {"name": "In Progress"}}
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["id"] == 2
        assert response_data["name"] == "In Progress"
        assert response_data["isClosed"] is False

    @respx.mock
    @pytest.mark.asyncio
    async def test_resolve_status_case_insensitive(self, server, base_url):
        """Test case-insensitive matching."""
        import json

        statuses_response = {
            "_embedded": {
                "elements": [
                    {"id": 1, "name": "New", "isClosed": False, "isDefault": True},
                ]
            }
        }

        route = respx.get(f"{base_url}/statuses").mock(
            return_value=httpx.Response(200, json=statuses_response)
        )

        result = await server.call_tool("resolve_status", {"params": {"name": "new"}})

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["id"] == 1
        assert response_data["name"] == "New"

    @respx.mock
    @pytest.mark.asyncio
    async def test_resolve_status_partial_match(self, server, base_url):
        """Test partial name matching."""
        import json

        statuses_response = {
            "_embedded": {
                "elements": [
                    {
                        "id": 2,
                        "name": "In Progress",
                        "isClosed": False,
                        "isDefault": False,
                    },
                ]
            }
        }

        route = respx.get(f"{base_url}/statuses").mock(
            return_value=httpx.Response(200, json=statuses_response)
        )

        result = await server.call_tool(
            "resolve_status", {"params": {"name": "Progress"}}
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["id"] == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_resolve_status_disambiguation(self, server, base_url):
        """Test disambiguation when multiple matches found."""
        import json

        statuses_response = {
            "_embedded": {
                "elements": [
                    {"id": 1, "name": "Closed", "isClosed": True, "isDefault": False},
                    {
                        "id": 2,
                        "name": "Closed",
                        "isClosed": True,
                        "isDefault": False,
                    },  # Duplicate name
                ]
            }
        }

        route = respx.get(f"{base_url}/statuses").mock(
            return_value=httpx.Response(200, json=statuses_response)
        )

        result = await server.call_tool(
            "resolve_status", {"params": {"name": "Closed"}}
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["disambiguation_needed"] is True
        assert len(response_data["matches"]) == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_resolve_status_not_found(self, server, base_url):
        """Test error when status not found."""
        import json

        statuses_response = {"_embedded": {"elements": []}}

        route = respx.get(f"{base_url}/statuses").mock(
            return_value=httpx.Response(200, json=statuses_response)
        )

        result = await server.call_tool(
            "resolve_status", {"params": {"name": "NonExistent"}}
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert "error" in response_data


# ============================================================================
# Test: resolve_type
# ============================================================================


class TestResolveType:
    """Test suite for resolve_type tool."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_resolve_type_exact_match(self, server, base_url):
        """Test exact type name match in project context."""
        import json

        types_response = {
            "_embedded": {
                "elements": [
                    {"id": 1, "name": "Task", "isMilestone": False, "isDefault": True},
                    {"id": 2, "name": "Bug", "isMilestone": False, "isDefault": False},
                ]
            }
        }

        route = respx.get(f"{base_url}/projects/123/types").mock(
            return_value=httpx.Response(200, json=types_response)
        )

        result = await server.call_tool(
            "resolve_type", {"params": {"project_id": 123, "name": "Bug"}}
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["id"] == 2
        assert response_data["name"] == "Bug"
        assert response_data["available_in_project"] is True

    @respx.mock
    @pytest.mark.asyncio
    async def test_resolve_type_case_insensitive(self, server, base_url):
        """Test case-insensitive type matching."""
        import json

        types_response = {
            "_embedded": {
                "elements": [
                    {"id": 1, "name": "Task", "isMilestone": False, "isDefault": True},
                ]
            }
        }

        route = respx.get(f"{base_url}/projects/123/types").mock(
            return_value=httpx.Response(200, json=types_response)
        )

        result = await server.call_tool(
            "resolve_type", {"params": {"project_id": 123, "name": "task"}}
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["id"] == 1
        assert response_data["name"] == "Task"

    @respx.mock
    @pytest.mark.asyncio
    async def test_resolve_type_not_in_project(self, server, base_url):
        """Test type exists globally but not in project."""
        import json

        project_types_response = {"_embedded": {"elements": []}}

        global_types_response = {
            "_embedded": {
                "elements": [
                    {"id": 5, "name": "Epic", "isMilestone": False, "isDefault": False},
                ]
            }
        }

        project_route = respx.get(f"{base_url}/projects/123/types").mock(
            return_value=httpx.Response(200, json=project_types_response)
        )

        global_route = respx.get(f"{base_url}/types").mock(
            return_value=httpx.Response(200, json=global_types_response)
        )

        result = await server.call_tool(
            "resolve_type", {"params": {"project_id": 123, "name": "Epic"}}
        )

        assert project_route.called
        assert global_route.called
        response_data = json.loads(result[0].text)
        assert response_data["available_in_project"] is False
        assert "not available in project" in response_data["note"]

    @respx.mock
    @pytest.mark.asyncio
    async def test_resolve_type_disambiguation(self, server, base_url):
        """Test disambiguation when multiple types match."""
        import json

        types_response = {
            "_embedded": {
                "elements": [
                    {
                        "id": 1,
                        "name": "Feature",
                        "isMilestone": False,
                        "isDefault": False,
                    },
                    {
                        "id": 2,
                        "name": "Feature",
                        "isMilestone": False,
                        "isDefault": False,
                    },  # Duplicate name
                ]
            }
        }

        route = respx.get(f"{base_url}/projects/123/types").mock(
            return_value=httpx.Response(200, json=types_response)
        )

        result = await server.call_tool(
            "resolve_type", {"params": {"project_id": 123, "name": "Feature"}}
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["disambiguation_needed"] is True
        assert len(response_data["matches"]) == 2


# ============================================================================
# Test: append_work_package_description
# ============================================================================


class TestAppendWorkPackageDescription:
    """Test suite for append_work_package_description tool."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_append_description_success(self, server, base_url):
        """Test successful description append."""
        import json

        current_wp = {
            "id": 123,
            "description": {"raw": "Original description"},
            "lockVersion": 5,
        }

        updated_wp = {
            "id": 123,
            "description": {"raw": "Original description\n\nNew content"},
            "lockVersion": 6,
        }

        get_route = respx.get(f"{base_url}/work_packages/123").mock(
            return_value=httpx.Response(200, json=current_wp)
        )

        patch_route = respx.patch(f"{base_url}/work_packages/123").mock(
            return_value=httpx.Response(200, json=updated_wp)
        )

        result = await server.call_tool(
            "append_work_package_description",
            {"params": {"wp_id": 123, "markdown": "New content"}},
        )

        assert get_route.called
        assert patch_route.called
        response_data = json.loads(result[0].text)
        assert "Original description" in response_data["description"]["raw"]
        assert "New content" in response_data["description"]["raw"]

    @respx.mock
    @pytest.mark.asyncio
    async def test_append_description_empty_existing(self, server, base_url):
        """Test appending to work package with no existing description."""
        import json

        current_wp = {"id": 123, "description": {"raw": ""}, "lockVersion": 1}

        updated_wp = {
            "id": 123,
            "description": {"raw": "New content"},
            "lockVersion": 2,
        }

        get_route = respx.get(f"{base_url}/work_packages/123").mock(
            return_value=httpx.Response(200, json=current_wp)
        )

        patch_route = respx.patch(f"{base_url}/work_packages/123").mock(
            return_value=httpx.Response(200, json=updated_wp)
        )

        result = await server.call_tool(
            "append_work_package_description",
            {"params": {"wp_id": 123, "markdown": "New content"}},
        )

        assert get_route.called
        assert patch_route.called
        response_data = json.loads(result[0].text)
        assert response_data["description"]["raw"] == "New content"

    @respx.mock
    @pytest.mark.asyncio
    async def test_append_description_work_package_not_found(self, server, base_url):
        """Test error when work package doesn't exist."""
        route = respx.get(f"{base_url}/work_packages/99999").mock(
            return_value=httpx.Response(404, json={"message": "Not found"})
        )

        with pytest.raises(ToolError) as exc_info:
            await server.call_tool(
                "append_work_package_description",
                {"params": {"wp_id": 99999, "markdown": "Test"}},
            )

        assert route.called
        assert "Resource not found" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_append_description_conflict(self, server, base_url):
        """Test handling of edit conflict (stale lockVersion)."""
        current_wp = {
            "id": 123,
            "description": {"raw": "Original"},
            "lockVersion": 5,
        }

        get_route = respx.get(f"{base_url}/work_packages/123").mock(
            return_value=httpx.Response(200, json=current_wp)
        )

        patch_route = respx.patch(f"{base_url}/work_packages/123").mock(
            return_value=httpx.Response(
                409, json={"message": "Resource was updated since you started editing"}
            )
        )

        with pytest.raises(ToolError):
            await server.call_tool(
                "append_work_package_description",
                {"params": {"wp_id": 123, "markdown": "New"}},
            )

        assert get_route.called
        assert patch_route.called
