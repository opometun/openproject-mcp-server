"""Mock response factories for tests"""


def mock_activity(
    activity_id: int = 456, comment_text: str = "Test comment", user_id: int = 1
) -> dict:
    """Create a mock activity response from OpenProject API"""
    return {
        "id": activity_id,
        "_type": "Activity::Comment",
        "createdAt": "2025-01-15T10:30:00Z",
        "comment": {
            "format": "markdown",
            "raw": comment_text,
            "html": f"<p>{comment_text}</p>",
        },
        "_links": {
            "self": {"href": f"/api/v3/activities/{activity_id}"},
            "workPackage": {"href": "/api/v3/work_packages/123"},
            "user": {"href": f"/api/v3/users/{user_id}", "title": "Test User"},
        },
    }


def mock_work_package(
    wp_id: int = 123, subject: str = "Test Work Package", status: str = "New"
) -> dict:
    """Create a mock work package response"""
    return {
        "id": wp_id,
        "_type": "WorkPackage",
        "subject": subject,
        "description": {
            "format": "markdown",
            "raw": "Test description",
            "html": "<p>Test description</p>",
        },
        "_links": {
            "self": {"href": f"/api/v3/work_packages/{wp_id}"},
            "status": {"href": "/api/v3/statuses/1", "title": status},
            "type": {"href": "/api/v3/types/1", "title": "Task"},
        },
    }
