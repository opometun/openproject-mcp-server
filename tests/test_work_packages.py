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
