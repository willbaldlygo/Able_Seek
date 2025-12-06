"""
Request logging middleware for Able2 API.

Provides structured logging for all HTTP requests with:
- Request timing and latency
- Client identification (IP, user agent)
- Security events (auth failures, rate limits)
- Request tracing via unique IDs
"""

import time
import uuid
from typing import Callable
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .logger import request_logger, security_logger


def mask_api_key(api_key: str | None) -> str:
    """Mask API key for safe logging, showing only first 4 chars."""
    if not api_key:
        return "none"
    if len(api_key) <= 8:
        return "****"
    return f"{api_key[:4]}...{api_key[-4:]}"


def get_client_ip(request: Request) -> str:
    """
    Extract client IP, accounting for proxies.

    Checks X-Forwarded-For header first (from reverse proxies),
    falls back to direct client IP.
    """
    # Check for proxy headers
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # Take the first IP (original client)
        return forwarded_for.split(",")[0].strip()

    # Check X-Real-IP (nginx)
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip

    # Direct connection
    if request.client:
        return request.client.host

    return "unknown"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs all HTTP requests with detailed information.

    Logs include:
    - Request ID (for tracing)
    - Method and path
    - Client IP and user agent
    - Response status code
    - Request duration in milliseconds
    - API key (masked)
    """

    # Paths to exclude from detailed logging (health checks, etc.)
    EXCLUDE_PATHS = {"/health", "/favicon.ico"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())[:8]

        # Store request ID for use in other parts of the app
        request.state.request_id = request_id

        # Capture start time
        start_time = time.perf_counter()

        # Extract request info
        method = request.method
        path = request.url.path
        query = str(request.url.query) if request.url.query else ""
        client_ip = get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")[:100]  # Truncate
        api_key = request.headers.get("x-api-key") or request.query_params.get("api_key")

        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            # Log exception and re-raise
            duration_ms = (time.perf_counter() - start_time) * 1000
            request_logger.error(
                f"[{request_id}] {method} {path} - EXCEPTION after {duration_ms:.1f}ms: {str(e)[:100]}"
            )
            raise

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        # Skip detailed logging for excluded paths
        if path in self.EXCLUDE_PATHS:
            return response

        # Build log message
        masked_key = mask_api_key(api_key)
        full_path = f"{path}?{query}" if query else path

        # Log based on status code
        if status_code >= 500:
            request_logger.error(
                f"[{request_id}] {method} {full_path} - {status_code} - "
                f"{duration_ms:.1f}ms - IP:{client_ip} - Key:{masked_key}"
            )
        elif status_code >= 400:
            request_logger.warning(
                f"[{request_id}] {method} {full_path} - {status_code} - "
                f"{duration_ms:.1f}ms - IP:{client_ip} - Key:{masked_key}"
            )
        else:
            request_logger.info(
                f"[{request_id}] {method} {full_path} - {status_code} - "
                f"{duration_ms:.1f}ms - IP:{client_ip} - Key:{masked_key}"
            )

        return response


def log_security_event(
    event_type: str,
    request: Request,
    details: str = "",
    severity: str = "warning"
):
    """
    Log a security-related event.

    Args:
        event_type: Type of event (auth_failure, rate_limit, suspicious_request, etc.)
        request: The FastAPI request object
        details: Additional details about the event
        severity: Log level (info, warning, error)
    """
    request_id = getattr(request.state, "request_id", "unknown")
    client_ip = get_client_ip(request)
    path = request.url.path
    method = request.method

    message = (
        f"[{request_id}] SECURITY:{event_type} - {method} {path} - "
        f"IP:{client_ip} - {details}"
    )

    if severity == "error":
        security_logger.error(message)
    elif severity == "warning":
        security_logger.warning(message)
    else:
        security_logger.info(message)


def log_auth_failure(request: Request, reason: str = "invalid_key"):
    """Log an authentication failure."""
    log_security_event(
        event_type="AUTH_FAILURE",
        request=request,
        details=f"Reason: {reason}",
        severity="warning"
    )


def log_rate_limit_hit(request: Request, limit: str = ""):
    """Log when a rate limit is exceeded."""
    log_security_event(
        event_type="RATE_LIMIT",
        request=request,
        details=f"Limit: {limit}",
        severity="warning"
    )


def setup_request_logging(app: FastAPI) -> None:
    """
    Add request logging middleware to the FastAPI app.

    Call this during app startup.
    """
    app.add_middleware(RequestLoggingMiddleware)
    request_logger.info("Request logging middleware enabled")


__all__ = [
    "RequestLoggingMiddleware",
    "setup_request_logging",
    "log_security_event",
    "log_auth_failure",
    "log_rate_limit_hit",
    "get_client_ip",
    "mask_api_key",
    "request_logger",
    "security_logger",
]
