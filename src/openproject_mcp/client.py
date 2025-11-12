import asyncio
import logging
import random
from contextlib import asynccontextmanager
import httpx

from openproject_mcp.config import Settings
from openproject_mcp.errors import AuthError, NotFound, ValidationError

log = logging.getLogger(__name__)

RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


def _build_timeout(settings: Settings) -> httpx.Timeout:
    # You only have connect/read in Settings. Provide all four explicitly to httpx.
    return httpx.Timeout(
        connect=settings.connect_timeout,
        read=settings.read_timeout,
        write=settings.read_timeout,  # sensible default
        pool=settings.connect_timeout,  # sensible default
    )


def _raise_mapped(res: httpx.Response) -> None:
    # Map to the exceptions your tests expect
    sc = res.status_code
    if sc == 401:
        raise AuthError("Authentication failed")
    if sc == 403:
        # tests parametrize with builtin PermissionError
        raise PermissionError("Permission denied")
    if sc == 404:
        raise NotFound("Resource not found")
    if sc == 422:
        raise ValidationError("Validation failed")
    # Anything else: let httpx provide details
    res.raise_for_status()


class OpenProjectClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: httpx.AsyncClient | None = None
        # Ensure no double slashes in base_url
        base = str(self.settings.url).rstrip("/")
        self.base_url = f"{base}/api/v3"

    @property
    def headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.settings.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @asynccontextmanager
    async def session(self):
        async with httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=_build_timeout(self.settings),
        ) as s:
            yield s

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        retries = self.settings.max_retries
        backoff = 0.5

        for attempt in range(retries):
            async with self.session() as s:
                try:
                    res = await s.request(method, path, **kwargs)

                    if res.is_success:
                        return res

                    # Retry transient server/limit errors
                    if res.status_code in RETRYABLE_STATUSES and attempt < retries - 1:
                        await asyncio.sleep(backoff + random.random() * 0.2)
                        backoff *= 2
                        continue

                    # Non-retryable: raise mapped domain errors
                    _raise_mapped(
                        res
                    )  # will raise or fall through to res.raise_for_status()
                    return res

                except (httpx.ConnectError, httpx.ReadTimeout):
                    if attempt < retries - 1:
                        await asyncio.sleep(backoff)
                        backoff *= 2
                        continue
                    raise

    async def get(self, path: str, **kwargs):
        return await self._request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs):
        return await self._request("POST", path, **kwargs)

    async def patch(self, path: str, **kwargs):
        return await self._request("PATCH", path, **kwargs)

    async def delete(self, path: str, **kwargs):
        return await self._request("DELETE", path, **kwargs)
