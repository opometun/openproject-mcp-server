"""
Unit tests for time entry tools.

Tests listing and logging time entries in OpenProject.
Uses respx for HTTP mocking to avoid real API calls.
"""

import pytest
import respx
import httpx
from datetime import date
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from openproject_mcp.tools import time_entries


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def server(mock_settings):
    """FastMCP server with time entry tools registered."""
    server = FastMCP("test-openproject")
    time_entries.register(server, mock_settings)
    return server


@pytest.fixture
def base_url(mock_settings):
    """Base URL for API endpoints."""
    return str(mock_settings.url).rstrip("/") + "/api/v3"


# ============================================================================
# Test: list_time_entries
# ============================================================================


class TestListTimeEntries:
    """Test suite for list_time_entries tool."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_list_time_entries_no_filters(self, server, base_url):
        """Test listing all time entries without filters."""
        import json

        expected_response = {
            "_type": "Collection",
            "count": 3,
            "total": 3,
            "_embedded": {
                "elements": [
                    {
                        "id": 1,
                        "hours": "PT2H30M",
                        "spentOn": "2025-01-10",
                        "comment": {"raw": "Development work"},
                        "createdAt": "2025-01-10T16:00:00Z",
                    },
                    {
                        "id": 2,
                        "hours": "PT1H0M",
                        "spentOn": "2025-01-11",
                        "comment": {"raw": "Bug fixing"},
                        "createdAt": "2025-01-11T10:00:00Z",
                    },
                    {
                        "id": 3,
                        "hours": "PT3H15M",
                        "spentOn": "2025-01-12",
                        "comment": {"raw": "Code review"},
                        "createdAt": "2025-01-12T14:00:00Z",
                    },
                ]
            },
        }

        route = respx.get(f"{base_url}/time_entries").mock(
            return_value=httpx.Response(200, json=expected_response)
        )

        result = await server.call_tool("list_time_entries", {"params": {}})

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["count"] == 3
        assert len(response_data["_embedded"]["elements"]) == 3

    @respx.mock
    @pytest.mark.asyncio
    async def test_list_time_entries_by_project(self, server, base_url):
        """Test listing time entries filtered by project."""
        import json

        expected_response = {
            "_type": "Collection",
            "count": 2,
            "total": 2,
            "_embedded": {
                "elements": [
                    {"id": 1, "hours": "PT2H0M", "spentOn": "2025-01-10"},
                    {"id": 2, "hours": "PT1H30M", "spentOn": "2025-01-11"},
                ]
            },
        }

        route = respx.get(f"{base_url}/time_entries").mock(
            return_value=httpx.Response(200, json=expected_response)
        )

        result = await server.call_tool(
            "list_time_entries", {"params": {"project_id": 123}}
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["count"] == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_list_time_entries_by_work_package(self, server, base_url):
        """Test listing time entries filtered by work package."""
        import json

        expected_response = {
            "_type": "Collection",
            "count": 1,
            "total": 1,
            "_embedded": {
                "elements": [
                    {"id": 5, "hours": "PT4H0M", "spentOn": "2025-01-15"},
                ]
            },
        }

        route = respx.get(f"{base_url}/time_entries").mock(
            return_value=httpx.Response(200, json=expected_response)
        )

        result = await server.call_tool("list_time_entries", {"params": {"wp_id": 456}})

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["count"] == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_list_time_entries_by_user(self, server, base_url):
        """Test listing time entries filtered by user."""
        import json

        expected_response = {
            "_type": "Collection",
            "count": 5,
            "total": 5,
            "_embedded": {
                "elements": [
                    {"id": i, "hours": "PT1H0M", "spentOn": "2025-01-10"}
                    for i in range(1, 6)
                ]
            },
        }

        route = respx.get(f"{base_url}/time_entries").mock(
            return_value=httpx.Response(200, json=expected_response)
        )

        result = await server.call_tool(
            "list_time_entries", {"params": {"user_id": 789}}
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["count"] == 5

    @respx.mock
    @pytest.mark.asyncio
    async def test_list_time_entries_date_range(self, server, base_url):
        """Test listing time entries with date range filter."""
        import json

        expected_response = {
            "_type": "Collection",
            "count": 2,
            "total": 2,
            "_embedded": {
                "elements": [
                    {"id": 1, "hours": "PT2H0M", "spentOn": "2025-01-10"},
                    {"id": 2, "hours": "PT3H0M", "spentOn": "2025-01-11"},
                ]
            },
        }

        route = respx.get(f"{base_url}/time_entries").mock(
            return_value=httpx.Response(200, json=expected_response)
        )

        result = await server.call_tool(
            "list_time_entries",
            {"params": {"from_date": "2025-01-10", "to_date": "2025-01-12"}},
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["count"] == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_list_time_entries_from_date_only(self, server, base_url):
        """Test listing time entries with from_date filter only."""

        expected_response = {
            "_type": "Collection",
            "count": 3,
            "total": 3,
            "_embedded": {"elements": []},
        }

        route = respx.get(f"{base_url}/time_entries").mock(
            return_value=httpx.Response(200, json=expected_response)
        )

        await server.call_tool(
            "list_time_entries", {"params": {"from_date": "2025-01-01"}}
        )

        assert route.called

    @respx.mock
    @pytest.mark.asyncio
    async def test_list_time_entries_to_date_only(self, server, base_url):
        """Test listing time entries with to_date filter only."""

        expected_response = {
            "_type": "Collection",
            "count": 2,
            "total": 2,
            "_embedded": {"elements": []},
        }

        route = respx.get(f"{base_url}/time_entries").mock(
            return_value=httpx.Response(200, json=expected_response)
        )

        await server.call_tool(
            "list_time_entries", {"params": {"to_date": "2025-01-31"}}
        )

        assert route.called

    @respx.mock
    @pytest.mark.asyncio
    async def test_list_time_entries_multiple_filters(self, server, base_url):
        """Test listing time entries with multiple filters."""
        import json

        expected_response = {
            "_type": "Collection",
            "count": 1,
            "total": 1,
            "_embedded": {
                "elements": [
                    {"id": 10, "hours": "PT5H0M", "spentOn": "2025-01-15"},
                ]
            },
        }

        route = respx.get(f"{base_url}/time_entries").mock(
            return_value=httpx.Response(200, json=expected_response)
        )

        result = await server.call_tool(
            "list_time_entries",
            {
                "params": {
                    "project_id": 123,
                    "wp_id": 456,
                    "user_id": 789,
                    "from_date": "2025-01-01",
                    "to_date": "2025-01-31",
                }
            },
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["count"] == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_list_time_entries_pagination(self, server, base_url):
        """Test time entry listing with pagination."""
        import json

        expected_response = {
            "_type": "Collection",
            "count": 50,
            "total": 150,
            "_embedded": {"elements": [{"id": i} for i in range(1, 51)]},
        }

        route = respx.get(f"{base_url}/time_entries").mock(
            return_value=httpx.Response(200, json=expected_response)
        )

        result = await server.call_tool(
            "list_time_entries", {"params": {"page_size": 50, "offset": 2}}
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["count"] == 50

    @respx.mock
    @pytest.mark.asyncio
    async def test_list_time_entries_empty(self, server, base_url):
        """Test listing time entries when none exist."""
        import json

        expected_response = {
            "_type": "Collection",
            "count": 0,
            "total": 0,
            "_embedded": {"elements": []},
        }

        route = respx.get(f"{base_url}/time_entries").mock(
            return_value=httpx.Response(200, json=expected_response)
        )

        result = await server.call_tool("list_time_entries", {"params": {}})

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["count"] == 0

    @respx.mock
    @pytest.mark.asyncio
    async def test_list_time_entries_unauthorized(self, server, base_url):
        """Test error when user is not authenticated."""
        route = respx.get(f"{base_url}/time_entries").mock(
            return_value=httpx.Response(401, json={"message": "Unauthorized"})
        )

        with pytest.raises(ToolError) as exc_info:
            await server.call_tool("list_time_entries", {"params": {}})

        assert route.called
        assert "Authentication failed" in str(exc_info.value)


# ============================================================================
# Test: log_time
# ============================================================================


class TestLogTime:
    """Test suite for log_time tool."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_log_time_basic(self, server, base_url):
        """Test basic time logging."""
        import json

        expected_response = {
            "id": 123,
            "_type": "TimeEntry",
            "hours": "PT2H30M",
            "spentOn": date.today().isoformat(),
            "comment": {"raw": "Development work"},
            "createdAt": "2025-01-10T16:00:00Z",
            "_links": {
                "workPackage": {"href": "/api/v3/work_packages/456"},
                "activity": {"href": "/api/v3/time_entries/activities/1"},
            },
        }

        route = respx.post(f"{base_url}/time_entries").mock(
            return_value=httpx.Response(201, json=expected_response)
        )

        result = await server.call_tool(
            "log_time",
            {"params": {"wp_id": 456, "hours": 2.5, "comment": "Development work"}},
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["id"] == 123
        assert response_data["hours"] == "PT2H30M"

        # Verify payload
        request_body = route.calls[0].request.content
        payload = json.loads(request_body)
        assert payload["hours"] == "PT2H30M"
        assert payload["_links"]["workPackage"]["href"] == "/api/v3/work_packages/456"

    @respx.mock
    @pytest.mark.asyncio
    async def test_log_time_with_date(self, server, base_url):
        """Test logging time with specific date."""
        import json

        expected_response = {
            "id": 124,
            "hours": "PT1H0M",
            "spentOn": "2025-01-15",
        }

        route = respx.post(f"{base_url}/time_entries").mock(
            return_value=httpx.Response(201, json=expected_response)
        )

        result = await server.call_tool(
            "log_time",
            {"params": {"wp_id": 456, "hours": 1.0, "spent_on": "2025-01-15"}},
        )

        assert route.called
        response_data = json.loads(result[0].text)
        assert response_data["spentOn"] == "2025-01-15"

    @respx.mock
    @pytest.mark.asyncio
    async def test_log_time_decimal_hours(self, server, base_url):
        """Test various decimal hour conversions."""
        import json

        test_cases = [
            (1.0, "PT1H0M"),
            (0.5, "PT0H30M"),
            (2.25, "PT2H15M"),
            (3.75, "PT3H45M"),
            (0.25, "PT0H15M"),
            (8.5, "PT8H30M"),
        ]

        for hours, expected_duration in test_cases:
            expected_response = {
                "id": 125,
                "hours": expected_duration,
                "spentOn": date.today().isoformat(),
            }

            route = respx.post(f"{base_url}/time_entries").mock(
                return_value=httpx.Response(201, json=expected_response)
            )

            await server.call_tool(
                "log_time", {"params": {"wp_id": 456, "hours": hours}}
            )

            assert route.called
            request_body = route.calls[-1].request.content
            payload = json.loads(request_body)
            assert payload["hours"] == expected_duration, f"Failed for {hours} hours"

    @respx.mock
    @pytest.mark.asyncio
    async def test_log_time_with_activity(self, server, base_url):
        """Test logging time with specific activity."""
        import json

        expected_response = {
            "id": 126,
            "hours": "PT2H0M",
            "_links": {"activity": {"href": "/api/v3/time_entries/activities/5"}},
        }

        route = respx.post(f"{base_url}/time_entries").mock(
            return_value=httpx.Response(201, json=expected_response)
        )

        await server.call_tool(
            "log_time", {"params": {"wp_id": 456, "hours": 2.0, "activity_id": 5}}
        )

        assert route.called
        request_body = route.calls[0].request.content
        payload = json.loads(request_body)
        assert (
            payload["_links"]["activity"]["href"] == "/api/v3/time_entries/activities/5"
        )

    @respx.mock
    @pytest.mark.asyncio
    async def test_log_time_for_other_user(self, server, base_url):
        """Test logging time for another user."""
        import json

        expected_response = {
            "id": 127,
            "hours": "PT3H0M",
            "_links": {"user": {"href": "/api/v3/users/999"}},
        }

        route = respx.post(f"{base_url}/time_entries").mock(
            return_value=httpx.Response(201, json=expected_response)
        )

        await server.call_tool(
            "log_time",
            {"params": {"wp_id": 456, "hours": 3.0, "user_id": 999}},
        )

        assert route.called
        request_body = route.calls[0].request.content
        payload = json.loads(request_body)
        assert payload["_links"]["user"]["href"] == "/api/v3/users/999"

    @respx.mock
    @pytest.mark.asyncio
    async def test_log_time_with_start_end_times(self, server, base_url):
        """Test logging time with start and end times."""
        import json

        expected_response = {
            "id": 128,
            "hours": "PT2H0M",
            "startTime": "2025-01-10T09:00:00Z",
            "endTime": "2025-01-10T11:00:00Z",
        }

        route = respx.post(f"{base_url}/time_entries").mock(
            return_value=httpx.Response(201, json=expected_response)
        )

        await server.call_tool(
            "log_time",
            {
                "params": {
                    "wp_id": 456,
                    "hours": 2.0,
                    "start_time": "2025-01-10T09:00:00Z",
                    "end_time": "2025-01-10T11:00:00Z",
                }
            },
        )

        assert route.called
        request_body = route.calls[0].request.content
        payload = json.loads(request_body)
        assert payload["startTime"] == "2025-01-10T09:00:00Z"
        assert payload["endTime"] == "2025-01-10T11:00:00Z"

    @respx.mock
    @pytest.mark.asyncio
    async def test_log_time_work_package_not_found(self, server, base_url):
        """Test error when work package doesn't exist."""
        route = respx.post(f"{base_url}/time_entries").mock(
            return_value=httpx.Response(404, json={"message": "Work package not found"})
        )

        with pytest.raises(ToolError) as exc_info:
            await server.call_tool(
                "log_time", {"params": {"wp_id": 99999, "hours": 1.0}}
            )

        assert route.called
        assert "Resource not found" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_log_time_forbidden(self, server, base_url):
        """Test error when user lacks permission."""
        route = respx.post(f"{base_url}/time_entries").mock(
            return_value=httpx.Response(403, json={"message": "Forbidden"})
        )

        with pytest.raises(ToolError) as exc_info:
            await server.call_tool("log_time", {"params": {"wp_id": 456, "hours": 1.0}})

        assert route.called
        assert "Permission denied" in str(exc_info.value)

    @respx.mock
    @pytest.mark.asyncio
    async def test_log_time_validation_error(self, server, base_url):
        """Test error for invalid time entry data."""
        route = respx.post(f"{base_url}/time_entries").mock(
            return_value=httpx.Response(422, json={"message": "Activity is invalid"})
        )

        with pytest.raises(ToolError) as exc_info:
            await server.call_tool(
                "log_time", {"params": {"wp_id": 456, "hours": 1.0, "activity_id": 999}}
            )

        assert route.called
        assert "Validation failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_log_time_invalid_hours_negative(self, server):
        """Test validation error for negative hours."""
        with pytest.raises(ToolError) as exc_info:
            await server.call_tool(
                "log_time", {"params": {"wp_id": 456, "hours": -1.0}}
            )

        assert "validation" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_log_time_invalid_hours_zero(self, server):
        """Test validation error for zero hours."""
        with pytest.raises(ToolError) as exc_info:
            await server.call_tool("log_time", {"params": {"wp_id": 456, "hours": 0.0}})

        assert "validation" in str(exc_info.value).lower()
