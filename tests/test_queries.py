"""
Unit tests for query tools.

Tests listing and executing saved queries (views) in OpenProject.
Uses respx for HTTP mocking to avoid real API calls.
"""

import pytest
import respx
import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from openproject_mcp.tools import queries


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def server(mock_settings):
    """FastMCP server with query tools registered."""
    server = FastMCP("test-openproject")
    queries.register(server, mock_settings)
    return server


@pytest.fixture
def base_url(mock_settings):
    """Base URL for API endpoints."""
    return str(mock_settings.url).rstrip("/") + "/api/v3"


# ============================================================================
# Test: list_queries
# ============================================================================


class TestListQueries:
    """Test suite for list_queries tool."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_list_queries_all(self, server, base_url):
        """Test listing all queries without project filter."""
        import json

        expected_response = {
            "_type": "Collection",
            "count": 3,
            "total": 3,
            "_embedded": {
                "elements": [
                    {
                        "id": 1,
                        "name": "All open work packages",
                        "public": True,
                        "starred": False,
                        "filters": [{"id": "status", "operator": "o", "values": []}],
                        "createdAt": "2025-01-01T12:00:00Z",
                    },
                    {
                        "id": 2,
                        "name": "My assigned tasks",
                        "public": False,
                        "starred": True,
                        "filters": [
                            {"id": "assignee", "operator": "=", "values": ["me"]}
                        ],
                        "createdAt": "2025-01-02T12:00:00Z",
                    },
                    {
                        "id": 3,
                        "name": "High priority bugs",
                        "public": True,
                        "starred": False,
                        "filters": [
                            {"id": "type", "operator": "=", "values": ["Bug"]},
                            {"id": "priority", "operator": "=", "values": ["High"]},
                        ],
                        "createdAt": "2025-01-03T12:00:00Z",
                    },
                ]
            },
        }

        route = respx.get(f"{base_url}/queries").mock(
            return_value=httpx.Response(200, json=expected_response)
        )

        result = await server.call_tool("list_queries", {"params": {}})

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["count"] == 3
        assert len(response_data["_embedded"]["elements"]) == 3
        assert (
            response_data["_embedded"]["elements"][0]["name"]
            == "All open work packages"
        )

    @respx.mock
    @pytest.mark.asyncio
    async def test_list_queries_by_project(self, server, base_url):
        """Test listing queries filtered by project."""
        import json

        expected_response = {
            "_type": "Collection",
            "count": 2,
            "total": 2,
            "_embedded": {
                "elements": [
                    {
                        "id": 10,
                        "name": "Project tasks",
                        "public": True,
                        "starred": False,
                    },
                    {
                        "id": 11,
                        "name": "Project bugs",
                        "public": True,
                        "starred": False,
                    },
                ]
            },
        }

        route = respx.get(f"{base_url}/projects/123/queries").mock(
            return_value=httpx.Response(200, json=expected_response)
        )

        result = await server.call_tool("list_queries", {"params": {"project_id": 123}})

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["count"] == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_list_queries_empty(self, server, base_url):
        """Test listing queries when none exist."""
        import json

        expected_response = {
            "_type": "Collection",
            "count": 0,
            "total": 0,
            "_embedded": {"elements": []},
        }

        route = respx.get(f"{base_url}/queries").mock(
            return_value=httpx.Response(200, json=expected_response)
        )

        result = await server.call_tool("list_queries", {"params": {}})

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["count"] == 0

    @respx.mock
    @pytest.mark.asyncio
    async def test_list_queries_project_not_found(self, server, base_url):
        """Test error when project doesn't exist."""
        route = respx.get(f"{base_url}/projects/99999/queries").mock(
            return_value=httpx.Response(404, json={"message": "Project not found"})
        )

        with pytest.raises(ToolError) as exc_info:
            await server.call_tool("list_queries", {"params": {"project_id": 99999}})

        assert route.called
        assert "Resource not found" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_list_queries_unauthorized(self, server, base_url):
        """Test error when user is not authenticated."""
        route = respx.get(f"{base_url}/queries").mock(
            return_value=httpx.Response(401, json={"message": "Unauthorized"})
        )

        with pytest.raises(ToolError) as exc_info:
            await server.call_tool("list_queries", {"params": {}})

        assert route.called
        assert "Authentication failed" in str(exc_info.value)


# ============================================================================
# Test: run_query
# ============================================================================


class TestRunQuery:
    """Test suite for run_query tool."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_run_query_basic(self, server, base_url):
        """Test running a query without overrides."""
        import json

        query_response = {
            "id": 123,
            "name": "All open tasks",
            "filters": [{"id": "status", "operator": "o", "values": []}],
            "sortBy": [["id", "asc"]],
            "groupBy": None,
            "columns": ["id", "subject", "status"],
            "_links": {"results": {"href": "/api/v3/queries/123/results"}},
        }

        results_response = {
            "_type": "WorkPackageCollection",
            "count": 2,
            "total": 2,
            "_embedded": {
                "elements": [
                    {"id": 1, "subject": "Task 1", "status": {"name": "In Progress"}},
                    {"id": 2, "subject": "Task 2", "status": {"name": "New"}},
                ]
            },
        }

        query_route = respx.get(f"{base_url}/queries/123").mock(
            return_value=httpx.Response(200, json=query_response)
        )

        results_route = respx.get(f"{base_url}/queries/123/results").mock(
            return_value=httpx.Response(200, json=results_response)
        )

        result = await server.call_tool("run_query", {"params": {"query_id": 123}})

        assert query_route.called
        assert results_route.called
        response_data = json.loads(result[0].text)
        assert response_data["count"] == 2
        assert len(response_data["_embedded"]["elements"]) == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_run_query_with_overrides(self, server, base_url):
        """Test running a query with filter overrides."""
        import json

        query_response = {
            "id": 123,
            "name": "All tasks",
            "filters": [{"id": "type", "operator": "=", "values": ["Task"]}],
            "sortBy": [["id", "asc"]],
            "groupBy": None,
            "columns": ["id", "subject"],
            "_links": {},  # No results link, will use default endpoint
        }

        results_response = {
            "_type": "WorkPackageCollection",
            "count": 1,
            "total": 1,
            "_embedded": {
                "elements": [
                    {"id": 5, "subject": "High priority task"},
                ]
            },
        }

        query_route = respx.get(f"{base_url}/queries/123").mock(
            return_value=httpx.Response(200, json=query_response)
        )

        # Expect POST to /queries/default with merged filters
        default_route = respx.post(f"{base_url}/queries/default").mock(
            return_value=httpx.Response(200, json=results_response)
        )

        overrides = {"priority": {"operator": "=", "values": ["High"]}}

        await server.call_tool(
            "run_query",
            {"params": {"query_id": 123, "overrides": overrides}},
        )

        assert query_route.called
        assert default_route.called

        # Verify the payload includes both original and override filters
        request_body = default_route.calls[0].request.content
        payload = json.loads(request_body)
        filter_ids = {f["id"] for f in payload["filters"]}
        assert "type" in filter_ids  # Original filter
        assert "priority" in filter_ids  # Override filter

    @respx.mock
    @pytest.mark.asyncio
    async def test_run_query_replace_existing_filter(self, server, base_url):
        """Test overriding an existing filter in the query."""
        import json

        query_response = {
            "id": 123,
            "name": "Open tasks",
            "filters": [{"id": "status", "operator": "o", "values": []}],
            "sortBy": [],
            "groupBy": None,
            "columns": [],
            "_links": {},
        }

        results_response = {
            "_type": "WorkPackageCollection",
            "count": 1,
            "total": 1,
            "_embedded": {"elements": [{"id": 10, "subject": "Closed task"}]},
        }

        query_route = respx.get(f"{base_url}/queries/123").mock(
            return_value=httpx.Response(200, json=query_response)
        )

        default_route = respx.post(f"{base_url}/queries/default").mock(
            return_value=httpx.Response(200, json=results_response)
        )

        # Override the status filter to show closed instead of open
        overrides = {
            "status": {"operator": "c", "values": []}  # Closed
        }

        await server.call_tool(
            "run_query",
            {"params": {"query_id": 123, "overrides": overrides}},
        )

        assert query_route.called
        assert default_route.called

        # Verify the status filter was replaced
        request_body = default_route.calls[0].request.content
        payload = json.loads(request_body)
        status_filter = next(
            (f for f in payload["filters"] if f["id"] == "status"), None
        )
        assert status_filter is not None
        assert status_filter["operator"] == "c"  # Changed to closed

    @respx.mock
    @pytest.mark.asyncio
    async def test_run_query_not_found(self, server, base_url):
        """Test error when query doesn't exist."""
        route = respx.get(f"{base_url}/queries/99999").mock(
            return_value=httpx.Response(404, json={"message": "Query not found"})
        )

        with pytest.raises(ToolError) as exc_info:
            await server.call_tool("run_query", {"params": {"query_id": 99999}})

        assert route.called
        assert "Resource not found" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_run_query_forbidden(self, server, base_url):
        """Test error when user lacks permission to run query."""
        route = respx.get(f"{base_url}/queries/123").mock(
            return_value=httpx.Response(403, json={"message": "Forbidden"})
        )

        with pytest.raises(ToolError) as exc_info:
            await server.call_tool("run_query", {"params": {"query_id": 123}})

        assert route.called
        assert "Permission denied" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_run_query_empty_results(self, server, base_url):
        """Test running a query that returns no results."""
        import json

        query_response = {
            "id": 123,
            "name": "Empty query",
            "filters": [],
            "sortBy": [],
            "groupBy": None,
            "columns": [],
            "_links": {"results": {"href": "/api/v3/queries/123/results"}},
        }

        results_response = {
            "_type": "WorkPackageCollection",
            "count": 0,
            "total": 0,
            "_embedded": {"elements": []},
        }

        query_route = respx.get(f"{base_url}/queries/123").mock(
            return_value=httpx.Response(200, json=query_response)
        )

        results_route = respx.get(f"{base_url}/queries/123/results").mock(
            return_value=httpx.Response(200, json=results_response)
        )

        result = await server.call_tool("run_query", {"params": {"query_id": 123}})

        assert query_route.called
        assert results_route.called
        response_data = json.loads(result[0].text)
        assert response_data["count"] == 0
        assert len(response_data["_embedded"]["elements"]) == 0

    @respx.mock
    @pytest.mark.asyncio
    async def test_run_query_complex_filters(self, server, base_url):
        """Test running a query with complex filter configuration."""
        import json

        query_response = {
            "id": 456,
            "name": "Complex query",
            "filters": [
                {"id": "status", "operator": "o", "values": []},
                {"id": "assignee", "operator": "=", "values": ["me"]},
                {"id": "priority", "operator": "=", "values": ["High", "Urgent"]},
            ],
            "sortBy": [["priority", "desc"], ["dueDate", "asc"]],
            "groupBy": "project",
            "columns": ["id", "subject", "priority", "dueDate"],
            "_links": {"results": {"href": "/api/v3/queries/456/results"}},
        }

        results_response = {
            "_type": "WorkPackageCollection",
            "count": 5,
            "total": 5,
            "_embedded": {
                "elements": [{"id": i, "subject": f"Task {i}"} for i in range(1, 6)]
            },
        }

        query_route = respx.get(f"{base_url}/queries/456").mock(
            return_value=httpx.Response(200, json=query_response)
        )

        results_route = respx.get(f"{base_url}/queries/456/results").mock(
            return_value=httpx.Response(200, json=results_response)
        )

        result = await server.call_tool("run_query", {"params": {"query_id": 456}})

        assert query_route.called
        assert results_route.called
        response_data = json.loads(result[0].text)
        assert response_data["count"] == 5
