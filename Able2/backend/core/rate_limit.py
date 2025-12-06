"""
Rate limiting module for Able2.

Uses SlowAPI to enforce request rate limits per IP address.
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import Request, FastAPI

from .config import settings
from .logger import api_logger


def get_key_func(request: Request) -> str:
    """
    Get rate limit key from request.

    Uses API key if present, otherwise falls back to IP address.
    This allows per-user rate limiting when authenticated.
    """
    # Try to get API key from header or query
    api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")

    if api_key:
        # Use API key as identifier (hashed for privacy in logs)
        return f"key:{api_key[:8]}..."

    # Fall back to IP address
    return get_remote_address(request)


# Create limiter instance
limiter = Limiter(
    key_func=get_key_func,
    enabled=settings.rate_limit_enabled,
    default_limits=[f"{settings.rate_limit_per_minute}/minute"],
    storage_uri="memory://",  # Use Redis in production: settings.redis_url
)


def setup_rate_limiting(app: FastAPI) -> None:
    """
    Configure rate limiting for the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    if not settings.rate_limit_enabled:
        api_logger.warning("Rate limiting is DISABLED")
        return

    # Add limiter to app state
    app.state.limiter = limiter

    # Add exception handler for rate limit exceeded
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Add middleware
    app.add_middleware(SlowAPIMiddleware)

    api_logger.info(
        f"Rate limiting ENABLED: "
        f"{settings.rate_limit_per_minute}/min (default), "
        f"{settings.rate_limit_chat_per_minute}/min (chat), "
        f"{settings.rate_limit_upload_per_minute}/min (upload)"
    )


# Rate limit decorators for different endpoint types
def limit_default():
    """Default rate limit decorator."""
    return limiter.limit(f"{settings.rate_limit_per_minute}/minute")


def limit_chat():
    """Rate limit for chat endpoints (more expensive - LLM calls)."""
    return limiter.limit(f"{settings.rate_limit_chat_per_minute}/minute")


def limit_upload():
    """Rate limit for upload endpoints (resource intensive)."""
    return limiter.limit(f"{settings.rate_limit_upload_per_minute}/minute")


def limit_custom(rate: str):
    """
    Custom rate limit decorator.

    Args:
        rate: Rate limit string (e.g., "10/minute", "100/hour")
    """
    return limiter.limit(rate)


__all__ = [
    "limiter",
    "setup_rate_limiting",
    "limit_default",
    "limit_chat",
    "limit_upload",
    "limit_custom",
]
