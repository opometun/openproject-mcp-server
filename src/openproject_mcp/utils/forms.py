from openproject_mcp.client import OpenProjectClient
from openproject_mcp.errors import map_http_error
import httpx


async def validate_and_commit(
    client: OpenProjectClient, form_path: str, commit_path: str, payload: dict
):
    try:
        r = await client.post(form_path, json=payload)
        if r.status_code == 200:
            # sometimes 200 means valid and contains normalized payload/links
            pass
        elif r.status_code == 422:
            # extract a few field errors from body (structure depends on API)
            details = r.text[:300]
            map_http_error(422, f"Form validation failed: {details}")
        r2 = await client.post(commit_path, json=payload)
        if r2.status_code >= 400:
            map_http_error(r2.status_code, r2.text[:300])
        return r2.json()
    except httpx.HTTPStatusError as e:
        map_http_error(e.response.status_code, e.response.text[:300])
