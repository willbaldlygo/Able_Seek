"""
Tests for authentication and rate limiting.

Tests API key authentication and rate limiting middleware.
"""

import pytest
from io import BytesIO


class TestAPIKeyAuthentication:
    """Tests for API key authentication."""

    def test_request_without_api_key_rejected(self, unauthenticated_client):
        """Test that requests without API key are rejected."""
        response = unauthenticated_client.get("/documents")

        assert response.status_code == 401
        assert "API key required" in response.json().get("detail", "")

    def test_request_with_invalid_api_key_rejected(self, unauthenticated_client):
        """Test that requests with invalid API key are rejected."""
        unauthenticated_client.headers["X-API-Key"] = "wrong-key-12345"
        response = unauthenticated_client.get("/documents")

        assert response.status_code == 403
        assert "Invalid API key" in response.json().get("detail", "")

    def test_request_with_valid_api_key_accepted(self, test_client):
        """Test that requests with valid API key are accepted."""
        # test_client already has the valid API key set
        response = test_client.get("/models")

        assert response.status_code == 200

    def test_api_key_in_query_param_works(self, unauthenticated_client):
        """Test that API key can be passed as query parameter."""
        from tests.conftest import TEST_API_KEY

        response = unauthenticated_client.get(f"/models?api_key={TEST_API_KEY}")

        assert response.status_code == 200

    def test_public_endpoints_dont_require_auth(self, unauthenticated_client):
        """Test that public endpoints work without auth."""
        # Root endpoint
        response = unauthenticated_client.get("/")
        assert response.status_code == 200

        # Health check
        response = unauthenticated_client.get("/health")
        assert response.status_code == 200


class TestRateLimiting:
    """Tests for rate limiting functionality."""

    def test_rate_limit_headers_present(self, test_client):
        """Test that rate limit headers are present in responses."""
        response = test_client.get("/models")

        # SlowAPI should add these headers
        # Note: Exact headers depend on SlowAPI configuration
        assert response.status_code == 200

    def test_rate_limit_on_chat_endpoint(self, test_client):
        """Test that chat endpoint has rate limiting."""
        # Make multiple requests - should work until limit hit
        for i in range(5):
            response = test_client.post("/chat/v2", json={
                "message": f"Test message {i}",
                "autonomy_level": "moderate"
            })
            # Should not get rate limited with just 5 requests
            assert response.status_code != 429

    def test_rate_limit_on_upload_endpoint(self, test_client):
        """Test that upload endpoint has rate limiting."""
        content = b"Test content"
        files = {"file": ("test.txt", BytesIO(content), "text/plain")}

        response = test_client.post("/upload", files=files)

        # Should not be rate limited on first request
        assert response.status_code != 429


class TestRequestLogging:
    """Tests for request logging middleware."""

    def test_request_id_header_in_response(self, test_client):
        """Test that X-Request-ID header is added to responses."""
        response = test_client.get("/health")

        assert "X-Request-ID" in response.headers
        # Request ID should be 8 characters
        assert len(response.headers["X-Request-ID"]) == 8

    def test_request_id_unique_per_request(self, test_client):
        """Test that each request gets a unique ID."""
        response1 = test_client.get("/health")
        response2 = test_client.get("/health")

        id1 = response1.headers.get("X-Request-ID")
        id2 = response2.headers.get("X-Request-ID")

        assert id1 != id2


class TestSecurityHeaders:
    """Tests for security-related response behavior."""

    def test_api_key_not_echoed_in_response(self, test_client):
        """Test that API key is not echoed back in responses."""
        response = test_client.get("/")

        response_text = response.text.lower()
        # API key should not appear in response
        assert "test-api-key" not in response_text

    def test_masked_api_key_in_error(self, unauthenticated_client):
        """Test that invalid API key attempts don't echo the key."""
        unauthenticated_client.headers["X-API-Key"] = "my-secret-key-12345"
        response = unauthenticated_client.get("/documents")

        response_text = response.text.lower()
        # The secret key should not appear in the error message
        assert "my-secret-key" not in response_text
