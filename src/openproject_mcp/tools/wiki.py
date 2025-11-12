from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import Optional, Dict
import httpx
import os
import mimetypes

from openproject_mcp.config import Settings
from openproject_mcp.client import OpenProjectClient
from openproject_mcp.errors import map_http_error

# ============================================================================
# Input Models (Request Parameters)
# ============================================================================


class GetWikiPageIn(BaseModel):
    """Input parameters for getting a wiki page"""

    page_id: int = Field(..., description="Wiki page ID", gt=0)


class AttachFileToWikiIn(BaseModel):
    """Input parameters for attaching a file to a wiki page"""

    page_id: int = Field(..., description="Wiki page ID", gt=0)
    file_path: str = Field(..., description="Local file path to attach", min_length=1)
    description: Optional[str] = Field(
        None, description="Optional description for the attachment"
    )


class ListWikiPageAttachmentsIn(BaseModel):
    """Input parameters for listing wiki page attachments"""

    page_id: int = Field(..., description="Wiki page ID", gt=0)


# ============================================================================
# Output Models (Response Data - Optional but Recommended)
# ============================================================================


class WikiPageMetadata(BaseModel):
    """Wiki page metadata structure"""

    id: Optional[int] = None
    title: Optional[str] = None
    slug: Optional[str] = None
    version: Optional[int] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    _type: Optional[str] = None
    _links: Optional[Dict] = None


class WikiAttachmentMetadata(BaseModel):
    """Wiki attachment metadata structure"""

    id: Optional[int] = None
    fileName: Optional[str] = None
    fileSize: Optional[int] = None
    contentType: Optional[str] = None
    description: Optional[Dict[str, str]] = None
    digest: Optional[Dict[str, str]] = None
    createdAt: Optional[str] = None
    _type: Optional[str] = None
    _links: Optional[Dict] = None


class WikiAttachmentCollection(BaseModel):
    """Collection of wiki attachments"""

    _type: str = "Collection"
    count: int = 0
    total: int = 0
    _embedded: Dict = {"elements": []}


# ============================================================================
# Tool Registration
# ============================================================================


def register(server: FastMCP, settings: Settings | None = None):
    """Register all wiki tools with the MCP server"""
    settings = settings or Settings()
    client = OpenProjectClient(settings)

    @server.tool("get_wiki_page", description="Get wiki page details by page ID")
    async def get_wiki_page(params: GetWikiPageIn) -> dict:
        """
        Retrieve detailed information about a wiki page.

        Args:
            params: Validated input with page_id

        Returns:
            dict: Wiki page details including title, id, project reference,
                and links to attachments

        Note:
            Returns complete wiki page metadata including:
            - Page title and slug
            - Version information
            - Creation and update timestamps
            - Links to project, author, and attachments
            - Parent page reference (if applicable)
        """
        try:
            res = await client.get(f"/wiki_pages/{params.page_id}")
            return res.json()
        except httpx.HTTPStatusError as e:
            map_http_error(e.response.status_code, e.response.text[:300])

    @server.tool("attach_file_to_wiki", description="Attach a file to a wiki page")
    async def attach_file_to_wiki(params: AttachFileToWikiIn) -> dict:
        """
        Upload and attach a local file to a wiki page.

        Uses multipart/form-data with two parts:
        1. metadata (JSON): fileName and optional description
        2. file (binary): The actual file content

        Args:
            params: Validated input with page_id, file_path, and optional description

        Returns:
            dict: Attachment metadata from API response

        Raises:
            FileNotFoundError: If the specified file doesn't exist
            Exception: If upload fails (HTTP 4xx/5xx)

        Note:
            - Automatically detects MIME type from file extension
            - Falls back to 'application/octet-stream' if type cannot be determined
            - Removes Content-Type header to let aiohttp set multipart boundary
            - Description is sent as {"raw": "text"} format
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
                f"/wiki_pages/{params.page_id}/attachments", files=files
            )
            return res.json()

        except FileNotFoundError as e:
            return {"error": str(e)}
        except httpx.HTTPStatusError as e:
            map_http_error(e.response.status_code, e.response.text[:300])

    @server.tool(
        "list_wiki_page_attachments", description="List all attachments for a wiki page"
    )
    async def list_wiki_page_attachments(params: ListWikiPageAttachmentsIn) -> dict:
        """
        Retrieve all attachments associated with a wiki page.

        Args:
            params: Validated input with page_id

        Returns:
            dict: Collection of attachments with _embedded.elements array

        Note:
            Each attachment object includes:
            - id, fileName, fileSize, contentType
            - description (formatted text)
            - digest (MD5 hash)
            - createdAt timestamp
            - author information
            - downloadLocation link

        Raises:
            404: If wiki page doesn't exist or insufficient permissions
        """
        try:
            res = await client.get(f"/wiki_pages/{params.page_id}/attachments")
            return res.json()
        except httpx.HTTPStatusError as e:
            map_http_error(e.response.status_code, e.response.text[:300])
