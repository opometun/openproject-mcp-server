"""
Unit tests for wiki tools.

Tests wiki page retrieval and attachment management in OpenProject.
Uses respx for HTTP mocking to avoid real API calls.
"""

import pytest
import respx
import httpx
import tempfile
import os
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from openproject_mcp.tools import wiki


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def server(mock_settings):
    """FastMCP server with wiki tools registered."""
    server = FastMCP("test-openproject")
    wiki.register(server, mock_settings)
    return server


@pytest.fixture
def base_url(mock_settings):
    """Base URL for API endpoints."""
    return str(mock_settings.url).rstrip("/") + "/api/v3"


@pytest.fixture
def temp_file():
    """Create a temporary file for upload tests."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("Test wiki attachment content\n")
        f.write("Line 2 of test file")
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


# ============================================================================
# Test: get_wiki_page
# ============================================================================


class TestGetWikiPage:
    """Test suite for get_wiki_page tool."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_wiki_page_basic(self, server, base_url):
        """Test getting wiki page details."""
        import json

        expected_response = {
            "id": 123,
            "_type": "WikiPage",
            "title": "Project Documentation",
            "slug": "project-documentation",
            "version": 5,
            "createdAt": "2025-01-01T12:00:00Z",
            "updatedAt": "2025-01-15T14:30:00Z",
            "_links": {
                "self": {"href": "/api/v3/wiki_pages/123"},
                "project": {"href": "/api/v3/projects/10"},
                "attachments": {"href": "/api/v3/wiki_pages/123/attachments"},
                "author": {"href": "/api/v3/users/5"},
            },
        }

        route = respx.get(f"{base_url}/wiki_pages/123").mock(
            return_value=httpx.Response(200, json=expected_response)
        )

        result = await server.call_tool("get_wiki_page", {"params": {"page_id": 123}})

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["id"] == 123
        assert response_data["title"] == "Project Documentation"
        assert response_data["slug"] == "project-documentation"
        assert response_data["version"] == 5

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_wiki_page_with_parent(self, server, base_url):
        """Test getting wiki page with parent page reference."""
        import json

        expected_response = {
            "id": 456,
            "_type": "WikiPage",
            "title": "Subpage",
            "slug": "documentation/subpage",
            "version": 2,
            "createdAt": "2025-01-10T10:00:00Z",
            "updatedAt": "2025-01-10T10:00:00Z",
            "_links": {
                "self": {"href": "/api/v3/wiki_pages/456"},
                "project": {"href": "/api/v3/projects/10"},
                "parent": {"href": "/api/v3/wiki_pages/123"},
                "attachments": {"href": "/api/v3/wiki_pages/456/attachments"},
            },
        }

        route = respx.get(f"{base_url}/wiki_pages/456").mock(
            return_value=httpx.Response(200, json=expected_response)
        )

        result = await server.call_tool("get_wiki_page", {"params": {"page_id": 456}})

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["id"] == 456
        assert "parent" in response_data["_links"]

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_wiki_page_not_found(self, server, base_url):
        """Test error when wiki page doesn't exist."""
        route = respx.get(f"{base_url}/wiki_pages/99999").mock(
            return_value=httpx.Response(404, json={"message": "Wiki page not found"})
        )

        with pytest.raises(ToolError) as exc_info:
            await server.call_tool("get_wiki_page", {"params": {"page_id": 99999}})

        assert route.called
        assert "Resource not found" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_wiki_page_unauthorized(self, server, base_url):
        """Test error when user is not authenticated."""
        route = respx.get(f"{base_url}/wiki_pages/123").mock(
            return_value=httpx.Response(401, json={"message": "Unauthorized"})
        )

        with pytest.raises(ToolError) as exc_info:
            await server.call_tool("get_wiki_page", {"params": {"page_id": 123}})

        assert route.called
        assert "Authentication failed" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_wiki_page_forbidden(self, server, base_url):
        """Test error when user lacks permission."""
        route = respx.get(f"{base_url}/wiki_pages/123").mock(
            return_value=httpx.Response(403, json={"message": "Forbidden"})
        )

        with pytest.raises(ToolError) as exc_info:
            await server.call_tool("get_wiki_page", {"params": {"page_id": 123}})

        assert route.called
        assert "Permission denied" in str(exc_info.value)


# ============================================================================
# Test: attach_file_to_wiki
# ============================================================================


class TestAttachFileToWiki:
    """Test suite for attach_file_to_wiki tool."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_attach_file_basic(self, server, base_url, temp_file):
        """Test attaching a file to wiki page."""
        import json

        expected_response = {
            "id": 789,
            "_type": "Attachment",
            "fileName": os.path.basename(temp_file),
            "fileSize": os.path.getsize(temp_file),
            "contentType": "text/plain",
            "createdAt": "2025-01-20T15:00:00Z",
            "_links": {
                "self": {"href": "/api/v3/attachments/789"},
                "container": {"href": "/api/v3/wiki_pages/123"},
                "downloadLocation": {"href": "/api/v3/attachments/789/content"},
            },
        }

        route = respx.post(f"{base_url}/wiki_pages/123/attachments").mock(
            return_value=httpx.Response(201, json=expected_response)
        )

        result = await server.call_tool(
            "attach_file_to_wiki",
            {"params": {"page_id": 123, "file_path": temp_file}},
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["id"] == 789
        assert response_data["fileName"] == os.path.basename(temp_file)
        assert response_data["contentType"] == "text/plain"

    @respx.mock
    @pytest.mark.asyncio
    async def test_attach_file_with_description(self, server, base_url, temp_file):
        """Test attaching a file with description."""
        import json

        expected_response = {
            "id": 790,
            "_type": "Attachment",
            "fileName": os.path.basename(temp_file),
            "fileSize": os.path.getsize(temp_file),
            "contentType": "text/plain",
            "description": {"raw": "Important documentation"},
            "createdAt": "2025-01-20T15:00:00Z",
        }

        route = respx.post(f"{base_url}/wiki_pages/123/attachments").mock(
            return_value=httpx.Response(201, json=expected_response)
        )

        result = await server.call_tool(
            "attach_file_to_wiki",
            {
                "params": {
                    "page_id": 123,
                    "file_path": temp_file,
                    "description": "Important documentation",
                }
            },
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["description"]["raw"] == "Important documentation"

    @pytest.mark.asyncio
    async def test_attach_file_not_found(self, server):
        """Test error when file doesn't exist."""
        import json

        result = await server.call_tool(
            "attach_file_to_wiki",
            {"params": {"page_id": 123, "file_path": "/nonexistent/file.txt"}},
        )

        response_data = json.loads(result[0].text)
        assert "error" in response_data
        assert "File not found" in response_data["error"]

    @respx.mock
    @pytest.mark.asyncio
    async def test_attach_file_wiki_page_not_found(self, server, base_url, temp_file):
        """Test error when wiki page doesn't exist."""
        route = respx.post(f"{base_url}/wiki_pages/99999/attachments").mock(
            return_value=httpx.Response(404, json={"message": "Wiki page not found"})
        )

        with pytest.raises(ToolError) as exc_info:
            await server.call_tool(
                "attach_file_to_wiki",
                {"params": {"page_id": 99999, "file_path": temp_file}},
            )

        assert route.called
        assert "Resource not found" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_attach_file_forbidden(self, server, base_url, temp_file):
        """Test error when user lacks permission to attach files."""
        route = respx.post(f"{base_url}/wiki_pages/123/attachments").mock(
            return_value=httpx.Response(403, json={"message": "Forbidden"})
        )

        with pytest.raises(ToolError) as exc_info:
            await server.call_tool(
                "attach_file_to_wiki",
                {"params": {"page_id": 123, "file_path": temp_file}},
            )

        assert route.called
        assert "Permission denied" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_attach_file_validation_error(self, server, base_url, temp_file):
        """Test error for invalid attachment."""
        route = respx.post(f"{base_url}/wiki_pages/123/attachments").mock(
            return_value=httpx.Response(422, json={"message": "File is too large"})
        )

        with pytest.raises(ToolError) as exc_info:
            await server.call_tool(
                "attach_file_to_wiki",
                {"params": {"page_id": 123, "file_path": temp_file}},
            )

        assert route.called
        assert "Validation failed" in str(exc_info.value)


# ============================================================================
# Test: list_wiki_page_attachments
# ============================================================================


class TestListWikiPageAttachments:
    """Test suite for list_wiki_page_attachments tool."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_list_attachments_basic(self, server, base_url):
        """Test listing wiki page attachments."""
        import json

        expected_response = {
            "_type": "Collection",
            "count": 2,
            "total": 2,
            "_embedded": {
                "elements": [
                    {
                        "id": 1,
                        "_type": "Attachment",
                        "fileName": "document.pdf",
                        "fileSize": 102400,
                        "contentType": "application/pdf",
                        "description": {"raw": "Project specifications"},
                        "createdAt": "2025-01-15T10:00:00Z",
                        "_links": {
                            "downloadLocation": {
                                "href": "/api/v3/attachments/1/content"
                            }
                        },
                    },
                    {
                        "id": 2,
                        "_type": "Attachment",
                        "fileName": "diagram.png",
                        "fileSize": 51200,
                        "contentType": "image/png",
                        "createdAt": "2025-01-16T14:30:00Z",
                        "_links": {
                            "downloadLocation": {
                                "href": "/api/v3/attachments/2/content"
                            }
                        },
                    },
                ]
            },
        }

        route = respx.get(f"{base_url}/wiki_pages/123/attachments").mock(
            return_value=httpx.Response(200, json=expected_response)
        )

        result = await server.call_tool(
            "list_wiki_page_attachments", {"params": {"page_id": 123}}
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["count"] == 2
        assert len(response_data["_embedded"]["elements"]) == 2
        assert response_data["_embedded"]["elements"][0]["fileName"] == "document.pdf"

    @respx.mock
    @pytest.mark.asyncio
    async def test_list_attachments_empty(self, server, base_url):
        """Test listing attachments when none exist."""
        import json

        expected_response = {
            "_type": "Collection",
            "count": 0,
            "total": 0,
            "_embedded": {"elements": []},
        }

        route = respx.get(f"{base_url}/wiki_pages/123/attachments").mock(
            return_value=httpx.Response(200, json=expected_response)
        )

        result = await server.call_tool(
            "list_wiki_page_attachments", {"params": {"page_id": 123}}
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["count"] == 0

    @respx.mock
    @pytest.mark.asyncio
    async def test_list_attachments_with_digest(self, server, base_url):
        """Test listing attachments with MD5 digest information."""
        import json

        expected_response = {
            "_type": "Collection",
            "count": 1,
            "total": 1,
            "_embedded": {
                "elements": [
                    {
                        "id": 100,
                        "_type": "Attachment",
                        "fileName": "file.zip",
                        "fileSize": 1024000,
                        "contentType": "application/zip",
                        "digest": {
                            "algorithm": "md5",
                            "hash": "5d41402abc4b2a76b9719d911017c592",
                        },
                        "createdAt": "2025-01-20T12:00:00Z",
                    }
                ]
            },
        }

        route = respx.get(f"{base_url}/wiki_pages/456/attachments").mock(
            return_value=httpx.Response(200, json=expected_response)
        )

        result = await server.call_tool(
            "list_wiki_page_attachments", {"params": {"page_id": 456}}
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["_embedded"]["elements"][0]["digest"]["algorithm"] == "md5"

    @respx.mock
    @pytest.mark.asyncio
    async def test_list_attachments_page_not_found(self, server, base_url):
        """Test error when wiki page doesn't exist."""
        route = respx.get(f"{base_url}/wiki_pages/99999/attachments").mock(
            return_value=httpx.Response(404, json={"message": "Wiki page not found"})
        )

        with pytest.raises(ToolError) as exc_info:
            await server.call_tool(
                "list_wiki_page_attachments", {"params": {"page_id": 99999}}
            )

        assert route.called
        assert "Resource not found" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_list_attachments_unauthorized(self, server, base_url):
        """Test error when user is not authenticated."""
        route = respx.get(f"{base_url}/wiki_pages/123/attachments").mock(
            return_value=httpx.Response(401, json={"message": "Unauthorized"})
        )

        with pytest.raises(ToolError) as exc_info:
            await server.call_tool(
                "list_wiki_page_attachments", {"params": {"page_id": 123}}
            )

        assert route.called
        assert "Authentication failed" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_list_attachments_forbidden(self, server, base_url):
        """Test error when user lacks permission."""
        route = respx.get(f"{base_url}/wiki_pages/123/attachments").mock(
            return_value=httpx.Response(403, json={"message": "Forbidden"})
        )

        with pytest.raises(ToolError) as exc_info:
            await server.call_tool(
                "list_wiki_page_attachments", {"params": {"page_id": 123}}
            )

        assert route.called
        assert "Permission denied" in str(exc_info.value)
