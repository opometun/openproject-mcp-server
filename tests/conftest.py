"""Shared pytest fixtures for all tests"""

import pytest
from openproject_mcp.config import Settings


@pytest.fixture
def mock_settings():
    """Mock OpenProject settings"""
    return Settings(url="https://test.openproject.com", api_key="test_api_key_12345")


@pytest.fixture
def base_url(mock_settings):
    """Base URL for API requests"""
    return f"{mock_settings.url}/api/v3"


@pytest.fixture
def mock_http_success():
    """Mock successful HTTP response helper"""

    def _create_response(status=200, json_data=None):
        import httpx

        return httpx.Response(status, json=json_data or {"ok": True})

    return _create_response
