import os
import secrets

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

API_KEY_HEADER_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=False)

# Configurable via environment variable; defaults to a secure dev token
API_KEY_SECRET = os.getenv("API_KEY", "prod-secret-lead-ingest-key-2026")


async def verify_api_key(api_key: str | None = Security(api_key_header)) -> str:
    """Validate client API key using constant-time comparison."""
    if not api_key or not secrets.compare_digest(api_key, API_KEY_SECRET):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return api_key
