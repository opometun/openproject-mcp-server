import asyncio
import httpx
import logging
import random
from contextlib import asynccontextmanager
from openproject_mcp.config import Settings

log = logging.getLogger(__name__)


class OpenProjectClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: httpx.AsyncClient | None = None

    @asynccontextmanager
    async def session(self):
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=str(self.settings.url).rstrip("/"),
                headers={"Authorization": f"Bearer {self.settings.api_key}"},
                timeout=httpx.Timeout(
                    connect=self.settings.connect_timeout,
                    read=self.settings.read_timeout,
                ),
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            )
        try:
            yield self._client
        finally:
            pass

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        retries = self.settings.max_retries
        backoff = 0.5
        for attempt in range(retries):
            async with self.session() as s:
                try:
                    res = await s.request(method, path, **kwargs)
                    if res.status_code in (429, 500, 502, 503, 504):
                        raise httpx.HTTPStatusError(
                            "retryable", request=res.request, response=res
                        )
                    return res
                except httpx.HTTPStatusError as e:
                    if attempt < retries - 1 and e.response.status_code in (
                        429,
                        500,
                        502,
                        503,
                        504,
                    ):
                        await asyncio.sleep(backoff + random.random() * 0.2)
                        backoff *= 2
                        continue
                    raise
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
