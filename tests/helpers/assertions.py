"""Custom assertion helpers for tests"""


def assert_error_response(response: dict, error_code: str = None):
    """Assert that response contains an error structure"""
    assert "error" in response, "Response should contain 'error' key"

    if error_code:
        assert (
            response["error"]["code"] == error_code
        ), f"Expected error code '{error_code}', got '{response['error']['code']}'"


def assert_has_links(response: dict, *link_names):
    """Assert that response contains specified _links"""
    assert "_links" in response, "Response should contain '_links' key"

    for link_name in link_names:
        assert (
            link_name in response["_links"]
        ), f"Response should contain link '{link_name}' in _links"
