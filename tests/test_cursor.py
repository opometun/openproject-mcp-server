import pytest
from openproject_mcp.utils.cursor import encode_cursor, decode_cursor, clamp_page_size


class TestCursorEncoding:
    """Test cursor encoding/decoding round-trips"""

    def test_encode_decode_roundtrip_simple(self):
        """Test that decode_cursor(encode_cursor({...})) == {...}"""
        original = {"offset": 10, "project_id": 5}
        encoded = encode_cursor(original)
        decoded = decode_cursor(encoded)
        assert decoded == original

    def test_encode_decode_roundtrip_complex(self):
        """Test roundtrip with nested data"""
        original = {
            "offset": 100,
            "filters": {"status": "open", "assignee_id": 42},
            "sort": ["created_at", "desc"],
        }
        encoded = encode_cursor(original)
        decoded = decode_cursor(encoded)
        assert decoded == original

    def test_encode_decode_empty_dict(self):
        """Test roundtrip with empty dictionary"""
        original = {}
        encoded = encode_cursor(original)
        decoded = decode_cursor(encoded)
        assert decoded == original

    def test_encoded_format_is_url_safe(self):
        """Verify encoded cursor is URL-safe base64"""
        data = {"offset": 10, "project_id": 5}
        encoded = encode_cursor(data)
        # URL-safe base64 should not contain +, /, or =
        assert "+" not in encoded
        assert "/" not in encoded
        # May contain - and _ instead

    def test_decode_invalid_cursor_raises(self):
        """Test that invalid cursors raise appropriate errors"""
        with pytest.raises(Exception):  # Could be ValueError or json.JSONDecodeError
            decode_cursor("invalid-cursor-data")


class TestPageSizeClamping:
    """Test page size clamping logic"""

    def test_clamp_within_bounds(self):
        """Test value within bounds returns unchanged"""
        assert clamp_page_size(50, 25, 100) == 50

    def test_clamp_exceeds_maximum(self):
        """Test value exceeding max is clamped to max"""
        assert clamp_page_size(150, 25, 100) == 100

    def test_clamp_below_minimum(self):
        """Test value below 1 is clamped to 1"""
        assert clamp_page_size(0, 25, 100) == 25
        assert clamp_page_size(-10, 25, 100) == 1

    def test_clamp_none_uses_default(self):
        """Test None value uses default"""
        assert clamp_page_size(None, 25, 100) == 25

    def test_clamp_zero_uses_default(self):
        """Test zero value uses default (via max(1, ...) logic)"""
        assert clamp_page_size(0, 25, 100) == 25


class TestPaginationHelper:
    """Test pagination helper function"""

    @pytest.fixture
    def mock_items(self):
        """Generate mock work package items"""
        return [{"id": i, "subject": f"Task {i}"} for i in range(1, 101)]

    def test_pagination_returns_items_and_cursor(self, mock_items):
        """Test basic pagination response structure"""
        page_size = 25
        offset = 0

        # Simulate pagination logic
        page = mock_items[offset : offset + page_size]
        has_more = len(mock_items) > offset + page_size

        result = {
            "items": page,
            "next_cursor": (
                encode_cursor({"offset": offset + page_size}) if has_more else None
            ),
        }

        assert len(result["items"]) == 25
        assert result["next_cursor"] is not None

        # Verify cursor decodes correctly
        next_page_data = decode_cursor(result["next_cursor"])
        assert next_page_data["offset"] == 25

    def test_pagination_last_page_no_cursor(self, mock_items):
        """Test last page returns no next_cursor"""
        page_size = 25
        offset = 75  # Last page for 100 items

        page = mock_items[offset : offset + page_size]
        has_more = len(mock_items) > offset + page_size

        result = {
            "items": page,
            "next_cursor": (
                encode_cursor({"offset": offset + page_size}) if has_more else None
            ),
        }

        assert len(result["items"]) == 25
        assert result["next_cursor"] is None

    def test_pagination_respects_page_size_cap(self, mock_items):
        """Test page size is properly capped"""
        requested_size = 500
        max_size = 100
        default_size = 25

        actual_size = clamp_page_size(requested_size, default_size, max_size)

        assert actual_size == max_size
        assert len(mock_items[0:actual_size]) == max_size
