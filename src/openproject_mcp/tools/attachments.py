from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import httpx
import os
import base64
import mimetypes

from openproject_mcp.config import Settings
from openproject_mcp.client import OpenProjectClient
from openproject_mcp.errors import map_http_error

# ============================================================================
# Input Models (Request Parameters)
# ============================================================================


class AttachFileToWpIn(BaseModel):
    """Input parameters for attaching a file to a work package"""

    wp_id: int = Field(..., description="Work package ID", gt=0)
    file_path: str = Field(..., description="Local file path to attach", min_length=1)
    description: Optional[str] = Field(
        None, description="Optional description for the attachment"
    )


class ListAttachmentsIn(BaseModel):
    """Input parameters for listing attachments"""

    wp_id: int = Field(..., description="Work package ID", gt=0)


class DownloadAttachmentIn(BaseModel):
    """Input parameters for downloading an attachment"""

    attachment_id: int = Field(..., description="Attachment ID", gt=0)
    save_path: Optional[str] = Field(
        None, description="Optional local path to save the downloaded file"
    )


class GetAttachmentContentIn(BaseModel):
    """Input parameters for getting attachment content with preview"""

    attachment_id: int = Field(..., description="Attachment ID", gt=0)
    max_bytes: int = Field(
        1024 * 1024,  # 1MB default
        description="Maximum bytes to retrieve for preview",
        gt=0,
        le=10 * 1024 * 1024,  # Max 10MB
    )
    prefer_range: bool = Field(
        True, description="Use HTTP Range header for partial content retrieval"
    )


# ============================================================================
# Output Models (Response Data - Optional but Recommended)
# ============================================================================


class AttachmentMetadata(BaseModel):
    """Attachment metadata structure"""

    id: Optional[int] = None
    fileName: Optional[str] = None
    fileSize: Optional[int] = None
    contentType: Optional[str] = None
    description: Optional[Dict[str, str]] = None
    digest: Optional[Dict[str, str]] = None
    createdAt: Optional[str] = None
    _links: Optional[Dict] = None


class AttachmentContentResponse(BaseModel):
    """Response for get_attachment_content"""

    metadata: Dict[str, Any]
    content_type: Optional[str] = None
    content_length: Optional[int] = None
    truncated: bool = False
    bytes_retrieved: int = 0
    # Note: actual bytes data is returned separately as it's binary


class AttachmentCollection(BaseModel):
    """Collection of attachments"""

    _type: str = "Collection"
    count: int = 0
    total: int = 0
    _embedded: Dict = {"elements": []}


# ============================================================================
# Tool Registration
# ============================================================================


def register(server: FastMCP, settings: Settings | None = None):
    """Register all attachment tools with the MCP server"""
    settings = settings or Settings()
    client = OpenProjectClient(settings)

    @server.tool("attach_file_to_wp", description="Attach a file to a work package")
    async def attach_file_to_wp(params: AttachFileToWpIn) -> dict:
        """
        Upload and attach a local file to a work package.

        Args:
            params: Validated input with wp_id, file_path, and optional description

        Returns:
            dict: Attachment metadata from API response

        Raises:
            FileNotFoundError: If the specified file doesn't exist
            Exception: If upload fails
        """
        try:
            # Check if file exists
            if not os.path.exists(params.file_path):
                raise FileNotFoundError(f"File not found: {params.file_path}")

            # Detect MIME type
            content_type, _ = mimetypes.guess_type(params.file_path)
            if not content_type:
                content_type = "application/octet-stream"

            # Prepare metadata
            metadata = {"fileName": os.path.basename(params.file_path)}

            if params.description:
                metadata["description"] = {"raw": params.description}

            # Read file content
            with open(params.file_path, "rb") as f:
                file_content = f.read()

            # Upload using multipart/form-data
            files = {
                "metadata": (None, str(metadata), "application/json"),
                "file": (
                    os.path.basename(params.file_path),
                    file_content,
                    content_type,
                ),
            }

            res = await client.post(
                f"/work_packages/{params.wp_id}/attachments", files=files
            )
            return res.json()

        except FileNotFoundError as e:
            return {"error": str(e)}
        except httpx.HTTPStatusError as e:
            map_http_error(e.response.status_code, e.response.text[:300])

    @server.tool(
        "list_attachments", description="List all attachments for a work package"
    )
    async def list_attachments(params: ListAttachmentsIn) -> dict:
        """
        Retrieve all attachments associated with a work package.

        Args:
            params: Validated input with wp_id

        Returns:
            dict: Collection of attachment objects
        """
        try:
            res = await client.get(f"/work_packages/{params.wp_id}/attachments")
            return res.json()
        except httpx.HTTPStatusError as e:
            map_http_error(e.response.status_code, e.response.text[:300])

    @server.tool(
        "download_attachment", description="Download attachment binary content"
    )
    async def download_attachment(params: DownloadAttachmentIn) -> dict:
        """
        Download the raw binary content of an attachment.

        Args:
            params: Validated input with attachment_id and optional save_path

        Returns:
            dict: Download status and file information

        Note:
            When save_path is provided, the file is saved to disk.
            Otherwise, raw bytes are returned (base64 encoded for JSON transport).
        """
        try:
            # Get attachment metadata first
            metadata_res = await client.get(f"/attachments/{params.attachment_id}")
            metadata = metadata_res.json()

            # Get download URL from links
            download_url = (
                metadata.get("_links", {}).get("downloadLocation", {}).get("href")
            )

            if not download_url:
                return {"error": "Download URL not found in attachment metadata"}

            # Download the file content
            # Note: download_url is relative, need to construct full URL
            download_res = await client.get(download_url)
            content = download_res.content

            result = {
                "fileName": metadata.get("fileName"),
                "fileSize": len(content),
                "contentType": metadata.get("contentType"),
            }

            if params.save_path:
                # Save to disk
                with open(params.save_path, "wb") as f:
                    f.write(content)
                result["saved_to"] = params.save_path
            else:
                # Return base64 encoded content
                result["content_base64"] = base64.b64encode(content).decode("utf-8")

            return result

        except httpx.HTTPStatusError as e:
            map_http_error(e.response.status_code, e.response.text[:300])

    @server.tool(
        "get_attachment_content",
        description="Get attachment metadata and content preview",
    )
    async def get_attachment_content(params: GetAttachmentContentIn) -> dict:
        """
        Retrieve attachment metadata plus a preview of the content.

        Uses HTTP Range header when possible to limit bandwidth usage.
        Useful for previewing text files, images, etc. without downloading
        the entire file.

        Args:
            params: Validated input with attachment_id, max_bytes, and prefer_range

        Returns:
            dict: Metadata, content type, and preview bytes (base64 encoded)
        """
        try:
            # Get attachment metadata
            metadata_res = await client.get(f"/attachments/{params.attachment_id}")
            metadata = metadata_res.json()

            # Get download URL
            download_url = (
                metadata.get("_links", {}).get("downloadLocation", {}).get("href")
            )

            if not download_url:
                return {"error": "Download URL not found in attachment metadata"}

            # Download with range header if preferred
            headers = {}
            if params.prefer_range:
                headers["Range"] = f"bytes=0-{params.max_bytes - 1}"

            download_res = await client.get(download_url, headers=headers)
            content = download_res.content

            # Limit content if range not supported
            truncated = False
            if len(content) > params.max_bytes:
                content = content[: params.max_bytes]
                truncated = True

            return {
                "metadata": {
                    "id": metadata.get("id"),
                    "fileName": metadata.get("fileName"),
                    "fileSize": metadata.get("fileSize"),
                    "contentType": metadata.get("contentType"),
                    "createdAt": metadata.get("createdAt"),
                },
                "content_type": metadata.get("contentType"),
                "content_length": metadata.get("fileSize"),
                "bytes_retrieved": len(content),
                "truncated": truncated,
                "content_base64": base64.b64encode(content).decode("utf-8"),
            }

        except httpx.HTTPStatusError as e:
            map_http_error(e.response.status_code, e.response.text[:300])
