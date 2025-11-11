from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import Optional, Dict

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


def register(server: FastMCP):
    """Register all wiki tools with the MCP server"""

    @server.tool(description="Get wiki page details by page ID")
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
        return {
            "error": {
                "code": "NotImplemented",
                "message": "get_wiki_page not implemented yet",
                "details": {"page_id": params.page_id},
            }
        }

    @server.tool(description="Attach a file to a wiki page")
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
        return {
            "error": {
                "code": "NotImplemented",
                "message": "attach_file_to_wiki not implemented yet",
                "details": {
                    "page_id": params.page_id,
                    "file_path": params.file_path,
                    "description": params.description,
                },
            }
        }

    @server.tool(description="List all attachments for a wiki page")
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
        return {
            "error": {
                "code": "NotImplemented",
                "message": "list_wiki_page_attachments not implemented yet",
                "details": {"page_id": params.page_id},
            }
        }
