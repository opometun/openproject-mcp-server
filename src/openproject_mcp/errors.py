import re


class OpError(Exception):
    pass


class AuthError(OpError):
    pass  # 401


class PermissionError(OpError):
    pass  # 403


class NotFound(OpError):
    pass  # 404


class ValidationError(OpError):
    pass  # 422


class RateLimited(OpError):
    pass  # 429


class TimeoutError(OpError):
    pass


class ServerError(OpError):
    pass


# Alias for consistency
OpenProjectError = OpError


def _sanitize_message(msg: str, max_length: int = 300) -> str:
    """
    Sanitize error messages to prevent leaking secrets.

    ACCEPTANCE CHECKS:
    - Truncates to max_length
    - Removes common secret patterns (API keys, tokens, passwords)

    Args:
        msg: Raw error message
        max_length: Maximum message length (default: 300)

    Returns:
        Sanitized and truncated message
    """
    # Truncate first
    msg = msg[:max_length]

    # Patterns to redact (case-insensitive)
    secret_patterns = [
        # API keys
        (r'apikey["\s:=]+[a-zA-Z0-9_\-\.]+', "[REDACTED_API_KEY]"),
        (r'api_key["\s:=]+[a-zA-Z0-9_\-\.]+', "[REDACTED_API_KEY]"),
        # Passwords
        (r'password["\s:=]+[^\s"\']+', "[REDACTED_PASSWORD]"),
        # Generic tokens
        (r'token["\s:=]+[a-zA-Z0-9_\-\.]+', "[REDACTED_TOKEN]"),
        (r'secret["\s:=]+[^\s"\']+', "[REDACTED_SECRET]"),
        # Authorization headers
        (r'authorization["\s:=]+[^\s"\']+', "[REDACTED_AUTH]"),
        (r"bearer\s+[a-zA-Z0-9_\-\.]+", "[REDACTED_BEARER_TOKEN]"),
        # Base64-encoded credentials
        (r"Basic\s+[A-Za-z0-9+/=]+", "[REDACTED_BASIC_AUTH]"),
        # GitHub/GitLab tokens
        (r"ghp_[a-zA-Z0-9]+", "[REDACTED_TOKEN]"),
        (r"glpat-[a-zA-Z0-9_\-]+", "[REDACTED_TOKEN]"),
        # AWS keys
        (r"AKIA[0-9A-Z]{16}", "[REDACTED_AWS_KEY]"),
        # Generic secret-like patterns (long alphanumeric strings after common keywords)
        (r"sk_live_[a-zA-Z0-9]+", "[REDACTED_SECRET_KEY]"),
    ]

    for pattern, replacement in secret_patterns:
        msg = re.sub(pattern, replacement, msg, flags=re.IGNORECASE)

    return msg


def map_http_error(status_code: int, message: str = "") -> None:
    """Map HTTP status codes to custom exceptions."""
    if status_code == 401:
        raise AuthError("Authentication failed")
    elif status_code == 403:
        raise PermissionError("Permission denied")
    elif status_code == 404:
        raise NotFound("Resource not found")
    elif status_code == 409:
        raise ValidationError(f"Edit conflict: {message}")
    elif status_code == 422:
        raise ValidationError("Validation failed")
    else:
        raise Exception(f"HTTP {status_code}: {message}")
