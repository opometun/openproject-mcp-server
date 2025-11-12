from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

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


def register(server: FastMCP):
    """Register all attachment tools with the MCP server"""

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
        return {
            "error": {
                "code": "NotImplemented",
                "message": "attach_file_to_wp not implemented yet",
                "details": {
                    "wp_id": params.wp_id,
                    "file_path": params.file_path,
                    "description": params.description,
                },
            }
        }

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
        return {
            "error": {
                "code": "NotImplemented",
                "message": "list_attachments not implemented yet",
                "details": {"wp_id": params.wp_id},
            }
        }

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
        return {
            "error": {
                "code": "NotImplemented",
                "message": "download_attachment not implemented yet",
                "details": {
                    "attachment_id": params.attachment_id,
                    "save_path": params.save_path,
                },
            }
        }

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
        return {
            "error": {
                "code": "NotImplemented",
                "message": "get_attachment_content not implemented yet",
                "details": {
                    "attachment_id": params.attachment_id,
                    "max_bytes": params.max_bytes,
                    "prefer_range": params.prefer_range,
                },
            }
        }
