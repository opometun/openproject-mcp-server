from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime


class PaginatedOut(BaseModel):
    items: list
    next_cursor: Optional[str] = None
    truncated: bool = False


class WorkPackageLite(BaseModel):
    id: int
    subject: str
    status: Optional[str] = None
    updated_at: Optional[datetime] = None
    url: Optional[HttpUrl] = None
