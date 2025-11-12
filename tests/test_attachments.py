"""
Unit tests for attachment tools.

Tests attachment upload, listing, downloading, and content preview.
Uses respx for HTTP mocking and temporary files for upload tests.
"""

import pytest
import respx
import httpx
import base64
import tempfile
import os
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from openproject_mcp.tools import attachments


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def server(mock_settings):
    """FastMCP server with attachment tools registered."""
    server = FastMCP("test-openproject")
    attachments.register(server, mock_settings)
    return server


@pytest.fixture
def base_url(mock_settings):
    """Base URL for API endpoints."""
    return str(mock_settings.url).rstrip("/") + "/api/v3"


@pytest.fixture
def temp_file():
    """Create a temporary file for upload tests."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("Test file content\nLine 2\nLine 3")
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


# ============================================================================
# Test: list_attachments
# ============================================================================


class TestListAttachments:
    """Test suite for list_attachments tool."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_list_attachments_success(self, server, base_url):
        """Test successful listing of attachments."""
        import json

        expected_response = {
            "_type": "Collection",
            "count": 2,
            "total": 2,
            "_embedded": {
                "elements": [
                    {
                        "id": 1,
                        "fileName": "document.pdf",
                        "fileSize": 12345,
                        "contentType": "application/pdf",
                        "createdAt": "2025-01-01T12:00:00Z",
                    },
                    {
                        "id": 2,
                        "fileName": "image.png",
                        "fileSize": 54321,
                        "contentType": "image/png",
                        "createdAt": "2025-01-02T12:00:00Z",
                    },
                ]
            },
        }

        route = respx.get(f"{base_url}/work_packages/123/attachments").mock(
            return_value=httpx.Response(200, json=expected_response)
        )

        result = await server.call_tool("list_attachments", {"params": {"wp_id": 123}})

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

        route = respx.get(f"{base_url}/work_packages/123/attachments").mock(
            return_value=httpx.Response(200, json=expected_response)
        )

        result = await server.call_tool("list_attachments", {"params": {"wp_id": 123}})

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["count"] == 0

    @respx.mock
    @pytest.mark.asyncio
    async def test_list_attachments_not_found(self, server, base_url):
        """Test error when work package doesn't exist."""
        route = respx.get(f"{base_url}/work_packages/99999/attachments").mock(
            return_value=httpx.Response(404, json={"message": "Not found"})
        )

        with pytest.raises(ToolError) as exc_info:
            await server.call_tool("list_attachments", {"params": {"wp_id": 99999}})

        assert route.called
        assert "Resource not found" in str(exc_info.value)


# ============================================================================
# Test: attach_file_to_wp
# ============================================================================


class TestAttachFileToWp:
    """Test suite for attach_file_to_wp tool."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_attach_file_success(self, server, base_url, temp_file):
        """Test successful file attachment."""
        import json

        expected_response = {
            "id": 123,
            "fileName": os.path.basename(temp_file),
            "fileSize": os.path.getsize(temp_file),
            "contentType": "text/plain",
            "createdAt": "2025-01-01T12:00:00Z",
        }

        route = respx.post(f"{base_url}/work_packages/456/attachments").mock(
            return_value=httpx.Response(201, json=expected_response)
        )

        result = await server.call_tool(
            "attach_file_to_wp",
            {"params": {"wp_id": 456, "file_path": temp_file}},
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["id"] == 123
        assert response_data["fileName"] == os.path.basename(temp_file)

    @respx.mock
    @pytest.mark.asyncio
    async def test_attach_file_with_description(self, server, base_url, temp_file):
        """Test file attachment with description."""
        import json

        expected_response = {
            "id": 124,
            "fileName": os.path.basename(temp_file),
            "description": {"raw": "Important document"},
        }

        route = respx.post(f"{base_url}/work_packages/456/attachments").mock(
            return_value=httpx.Response(201, json=expected_response)
        )

        result = await server.call_tool(
            "attach_file_to_wp",
            {
                "params": {
                    "wp_id": 456,
                    "file_path": temp_file,
                    "description": "Important document",
                }
            },
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["description"]["raw"] == "Important document"

    @pytest.mark.asyncio
    async def test_attach_file_not_found(self, server):
        """Test error when file doesn't exist."""
        import json

        result = await server.call_tool(
            "attach_file_to_wp",
            {"params": {"wp_id": 456, "file_path": "/nonexistent/file.txt"}},
        )

        response_data = json.loads(result[0].text)
        assert "error" in response_data
        assert "File not found" in response_data["error"]

    @respx.mock
    @pytest.mark.asyncio
    async def test_attach_file_unauthorized(self, server, base_url, temp_file):
        """Test error when user lacks permission."""
        route = respx.post(f"{base_url}/work_packages/456/attachments").mock(
            return_value=httpx.Response(403, json={"message": "Forbidden"})
        )

        with pytest.raises(ToolError) as exc_info:
            await server.call_tool(
                "attach_file_to_wp",
                {"params": {"wp_id": 456, "file_path": temp_file}},
            )

        assert route.called
        assert "Permission denied" in str(exc_info.value)


# ============================================================================
# Test: download_attachment
# ============================================================================


class TestDownloadAttachment:
    """Test suite for download_attachment tool."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_download_attachment_to_memory(self, server, base_url):
        """Test downloading attachment to memory (base64)."""
        import json

        metadata_response = {
            "id": 123,
            "fileName": "test.txt",
            "fileSize": 100,
            "contentType": "text/plain",
            "_links": {"downloadLocation": {"href": "/attachments/123/content"}},
        }

        file_content = b"Test file content"

        metadata_route = respx.get(f"{base_url}/attachments/123").mock(
            return_value=httpx.Response(200, json=metadata_response)
        )

        download_route = respx.get(f"{base_url}/attachments/123/content").mock(
            return_value=httpx.Response(200, content=file_content)
        )

        result = await server.call_tool(
            "download_attachment", {"params": {"attachment_id": 123}}
        )

        assert metadata_route.called
        assert download_route.called
        response_data = json.loads(result[0].text)
        assert response_data["fileName"] == "test.txt"
        assert response_data["fileSize"] == len(file_content)
        assert "content_base64" in response_data
        # Decode and verify content
        decoded = base64.b64decode(response_data["content_base64"])
        assert decoded == file_content

    @respx.mock
    @pytest.mark.asyncio
    async def test_download_attachment_to_file(self, server, base_url):
        """Test downloading attachment to file."""
        import json

        metadata_response = {
            "id": 123,
            "fileName": "test.txt",
            "contentType": "text/plain",
            "_links": {"downloadLocation": {"href": "/attachments/123/content"}},
        }

        file_content = b"Test file content"

        metadata_route = respx.get(f"{base_url}/attachments/123").mock(
            return_value=httpx.Response(200, json=metadata_response)
        )

        download_route = respx.get(f"{base_url}/attachments/123/content").mock(
            return_value=httpx.Response(200, content=file_content)
        )

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            temp_path = tmp.name

        try:
            result = await server.call_tool(
                "download_attachment",
                {"params": {"attachment_id": 123, "save_path": temp_path}},
            )

            assert metadata_route.called
            assert download_route.called
            response_data = json.loads(result[0].text)
            assert response_data["saved_to"] == temp_path

            # Verify file was written
            with open(temp_path, "rb") as f:
                assert f.read() == file_content
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @respx.mock
    @pytest.mark.asyncio
    async def test_download_attachment_not_found(self, server, base_url):
        """Test error when attachment doesn't exist."""
        route = respx.get(f"{base_url}/attachments/99999").mock(
            return_value=httpx.Response(404, json={"message": "Not found"})
        )

        with pytest.raises(ToolError) as exc_info:
            await server.call_tool(
                "download_attachment", {"params": {"attachment_id": 99999}}
            )

        assert route.called
        assert "Resource not found" in str(exc_info.value)


# ============================================================================
# Test: get_attachment_content
# ============================================================================


class TestGetAttachmentContent:
    """Test suite for get_attachment_content tool."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_attachment_content_preview(self, server, base_url):
        """Test getting attachment content preview with range."""
        import json

        metadata_response = {
            "id": 123,
            "fileName": "test.txt",
            "fileSize": 1000,
            "contentType": "text/plain",
            "createdAt": "2025-01-01T12:00:00Z",
            "_links": {"downloadLocation": {"href": "/attachments/123/content"}},
        }

        file_content = b"A" * 500  # 500 bytes

        metadata_route = respx.get(f"{base_url}/attachments/123").mock(
            return_value=httpx.Response(200, json=metadata_response)
        )

        download_route = respx.get(f"{base_url}/attachments/123/content").mock(
            return_value=httpx.Response(200, content=file_content)
        )

        result = await server.call_tool(
            "get_attachment_content",
            {"params": {"attachment_id": 123, "max_bytes": 1024 * 1024}},
        )

        assert metadata_route.called
        assert download_route.called
        response_data = json.loads(result[0].text)
        assert response_data["metadata"]["fileName"] == "test.txt"
        assert response_data["bytes_retrieved"] == 500
        assert response_data["truncated"] is False

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_attachment_content_truncated(self, server, base_url):
        """Test content preview with truncation."""
        import json

        metadata_response = {
            "id": 123,
            "fileName": "large.txt",
            "fileSize": 5000,
            "contentType": "text/plain",
            "_links": {"downloadLocation": {"href": "/attachments/123/content"}},
        }

        file_content = b"A" * 5000  # 5000 bytes

        metadata_route = respx.get(f"{base_url}/attachments/123").mock(
            return_value=httpx.Response(200, json=metadata_response)
        )

        download_route = respx.get(f"{base_url}/attachments/123/content").mock(
            return_value=httpx.Response(200, content=file_content)
        )

        result = await server.call_tool(
            "get_attachment_content",
            {"params": {"attachment_id": 123, "max_bytes": 1000}},
        )

        assert metadata_route.called
        assert download_route.called
        response_data = json.loads(result[0].text)
        assert response_data["bytes_retrieved"] == 1000
        assert response_data["truncated"] is True

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_attachment_content_without_range(self, server, base_url):
        """Test content preview without range header."""
        import json

        metadata_response = {
            "id": 123,
            "fileName": "test.txt",
            "fileSize": 100,
            "contentType": "text/plain",
            "_links": {"downloadLocation": {"href": "/attachments/123/content"}},
        }

        file_content = b"Small content"

        metadata_route = respx.get(f"{base_url}/attachments/123").mock(
            return_value=httpx.Response(200, json=metadata_response)
        )

        download_route = respx.get(f"{base_url}/attachments/123/content").mock(
            return_value=httpx.Response(200, content=file_content)
        )

        result = await server.call_tool(
            "get_attachment_content",
            {"params": {"attachment_id": 123, "prefer_range": False}},
        )

        assert metadata_route.called
        assert download_route.called
        response_data = json.loads(result[0].text)
        assert response_data["bytes_retrieved"] == len(file_content)
