"""
Authentication module for Able2.

Provides API key authentication for securing endpoints.
"""

import secrets
from typing import Optional
from fastapi import HTTPException, Security, Depends
from fastapi.security import APIKeyHeader, APIKeyQuery
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from .config import settings
from .logger import api_logger


# Support API key in header or query parameter
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
API_KEY_QUERY = APIKeyQuery(name="api_key", auto_error=False)


def _verify_api_key(api_key: str) -> bool:
    """
    Verify an API key using constant-time comparison.

    Args:
        api_key: The API key to verify

    Returns:
        True if valid, False otherwise
    """
    if not settings.api_key:
        # No API key configured - this is a security issue
        api_logger.warning("No API key configured! Set ABLE2_API_KEY environment variable.")
        return False

    # Use constant-time comparison to prevent timing attacks
    return secrets.compare_digest(api_key, settings.api_key)


async def verify_api_key(
    header_key: Optional[str] = Security(API_KEY_HEADER),
    query_key: Optional[str] = Security(API_KEY_QUERY),
) -> str:
    """
    Verify API key from header or query parameter.

    This is a FastAPI dependency that can be added to endpoints.

    Args:
        header_key: API key from X-API-Key header
        query_key: API key from api_key query parameter

    Returns:
        The verified API key

    Raises:
        HTTPException: If API key is missing or invalid
    """
    # Check if authentication is disabled (development only)
    if not settings.api_key_enabled:
        api_logger.warning("API key authentication is DISABLED")
        return "auth-disabled"

    # Get API key from header or query
    api_key = header_key or query_key

    if not api_key:
        api_logger.warning("API request without API key")
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide X-API-Key header or api_key query parameter.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not _verify_api_key(api_key):
        api_logger.warning("Invalid API key attempted")
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return api_key


async def optional_api_key(
    header_key: Optional[str] = Security(API_KEY_HEADER),
    query_key: Optional[str] = Security(API_KEY_QUERY),
) -> Optional[str]:
    """
    Optional API key verification - doesn't raise if missing.

    Useful for endpoints that work differently with/without auth.

    Returns:
        The API key if valid, None if missing or invalid
    """
    if not settings.api_key_enabled:
        return "auth-disabled"

    api_key = header_key or query_key

    if api_key and _verify_api_key(api_key):
        return api_key

    return None


def generate_api_key() -> str:
    """
    Generate a secure random API key.

    Returns:
        A 32-character URL-safe random string
    """
    return secrets.token_urlsafe(32)


# Export the main dependency for use in endpoints
__all__ = [
    "verify_api_key",
    "optional_api_key",
    "generate_api_key",
]
