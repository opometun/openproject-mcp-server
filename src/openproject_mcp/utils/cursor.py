import base64
import json


def encode_cursor(d: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(d).encode()).decode()


def decode_cursor(s: str) -> dict:
    return json.loads(base64.urlsafe_b64decode(s.encode()).decode())


def clamp_page_size(requested: int, default: int, maximum: int) -> int:
    return max(1, min(requested or default, maximum))
