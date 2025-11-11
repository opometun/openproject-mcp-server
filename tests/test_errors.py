import pytest
from src.openproject_mcp.errors import (
    map_http_error,
    AuthError,
    PermissionError,
    NotFound,
    ValidationError,
    RateLimited,
    ServerError,
    OpError,
)


class TestMapHttpError:
    """Unit tests for error mapping from HTTP status codes."""

    @pytest.mark.parametrize(
        "status,exc_type",
        [
            (401, AuthError),
            (403, PermissionError),
            (404, NotFound),
            (422, ValidationError),
            (429, RateLimited),
            (500, ServerError),
            (503, ServerError),
        ],
    )
    def test_raises_correct_exception(self, status, exc_type):
        """map_http_error should raise the correct exception for each status."""
        with pytest.raises(exc_type):
            map_http_error(status, "some message")

    def test_trims_long_messages(self):
        """map_http_error should trim overly long or unsafe messages."""
        long_msg = "x" * 1000
        with pytest.raises(ValidationError) as excinfo:
            map_http_error(422, long_msg)
        msg = str(excinfo.value)
        # Message should be safe and concise
        assert len(msg) < 400
        assert "Validation failed" in msg

    def test_unmapped_status_raises_nothing(self):
        """Unmapped status codes should not raise custom errors."""
        # Example: 204 or 418 should not raise
        for status in [204, 418]:
            try:
                map_http_error(status, "ignored")
            except OpError:
                pytest.fail(f"Unexpected error for status {status}")
