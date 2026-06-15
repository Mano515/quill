"""API key authentication."""

import os
import secrets
from pathlib import Path

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

_KEY_FILE = Path(__file__).parent.parent.parent / ".quill_api_key"
_header_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


def _load_or_create_key() -> str:
    env_key = os.environ.get("QUILL_API_KEY")
    if env_key:
        return env_key
    if _KEY_FILE.exists():
        return _KEY_FILE.read_text().strip()
    key = secrets.token_urlsafe(32)
    _KEY_FILE.write_text(key)
    return key


API_KEY: str = _load_or_create_key()


def require_key(key: str | None = Security(_header_scheme)) -> str:
    if key is None or not secrets.compare_digest(key, API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return key
