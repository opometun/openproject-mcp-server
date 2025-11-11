import pytest
from openproject_mcp.utils.forms import validate_and_commit
from openproject_mcp.errors import ValidationError


class DummyResponse:
    """Minimal fake response object for testing."""

    def __init__(self, status_code, text=""):
        self.status_code = status_code
        self.text = text

    def json(self):
        return {"ok": True}


class DummyClient:
    """Fake HTTP client to simulate OpenProject API behavior."""

    async def post(self, path, json):
        if "invalid" in json:
            # Simulate 422 validation error from OpenProject
            return DummyResponse(422, "stacktrace secret")
        # Simulate successful validation or commit
        return DummyResponse(200)


@pytest.mark.asyncio
async def test_validate_and_commit_raises_validation_error():
    """422 should raise ValidationError with a safe, trimmed message."""
    client = DummyClient()
    with pytest.raises(ValidationError) as excinfo:
        await validate_and_commit(client, "/validate", "/commit", {"invalid": True})
    msg = str(excinfo.value)
    assert "Form validation failed" in msg
    assert "secret" not in msg  # Sensitive info should be trimmed


@pytest.mark.asyncio
async def test_validate_and_commit_success_returns_json():
    """Successful commit should return JSON response."""
    client = DummyClient()
    result = await validate_and_commit(client, "/validate", "/commit", {"valid": True})
    assert result == {"ok": True}
