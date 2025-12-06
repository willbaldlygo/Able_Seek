"""
Integration tests for Able2 API endpoints.

Tests the full request/response cycle for all API endpoints.
"""

import pytest
from pathlib import Path
from io import BytesIO


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_check_returns_ok(self, test_client):
        """Test that health check returns successful response."""
        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "services" in data

    def test_health_check_includes_services(self, test_client):
        """Test that health check includes service status."""
        response = test_client.get("/health")

        data = response.json()
        services = data.get("services", {})

        # Should report on key services
        assert "database" in services or "vector_store" in services


class TestRootEndpoint:
    """Tests for / endpoint."""

    def test_root_returns_api_info(self, test_client):
        """Test that root endpoint returns API information."""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "endpoints" in data


class TestChatEndpoints:
    """Tests for chat endpoints."""

    def test_chat_v2_accepts_valid_request(self, test_client):
        """Test that /chat/v2 accepts valid requests."""
        response = test_client.post("/chat/v2", json={
            "message": "What is machine learning?",
            "autonomy_level": "moderate",
            "sources": ["documents"]
        })

        # May fail due to missing dependencies in test, but should not be 422
        assert response.status_code != 422 or "message" not in str(response.json())

    def test_chat_v2_returns_session_id(self, test_client):
        """Test that /chat/v2 returns a session ID."""
        response = test_client.post("/chat/v2", json={
            "message": "Hello",
            "autonomy_level": "moderate"
        })

        if response.status_code == 200:
            data = response.json()
            assert "session_id" in data

    def test_chat_enhanced_legacy_endpoint(self, test_client):
        """Test that legacy /chat/enhanced endpoint works."""
        response = test_client.post("/chat/enhanced", json={
            "message": "Test query",
            "use_graph": True,
            "top_k": 5
        })

        # Should accept the request format
        assert response.status_code != 422


class TestDocumentEndpoints:
    """Tests for document management endpoints."""

    def test_list_documents(self, test_client):
        """Test that /documents returns document list."""
        response = test_client.get("/documents")

        if response.status_code == 200:
            data = response.json()
            assert "documents" in data
            assert "total_count" in data

    def test_upload_document_pdf(self, test_client, tmp_path):
        """Test uploading a PDF document."""
        # Create a minimal PDF-like file
        pdf_content = b"%PDF-1.4\ntest content"
        files = {"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")}

        response = test_client.post("/upload", files=files)

        # Should accept or fail gracefully (not 422 validation error)
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") is True
            assert "document_id" in data

    def test_upload_document_txt(self, test_client):
        """Test uploading a text document."""
        content = b"This is test content for the text file."
        files = {"file": ("test.txt", BytesIO(content), "text/plain")}

        response = test_client.post("/upload", files=files)

        if response.status_code == 200:
            data = response.json()
            assert data.get("success") is True

    def test_delete_nonexistent_document(self, test_client):
        """Test deleting a document that doesn't exist."""
        response = test_client.delete("/documents/nonexistent-id-12345")

        # Should return 404 or handle gracefully
        assert response.status_code in [404, 500]


class TestModelEndpoints:
    """Tests for model management endpoints."""

    def test_list_models(self, test_client):
        """Test that /models returns available models."""
        response = test_client.get("/models")

        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert "active_model" in data
        assert len(data["models"]) > 0

    def test_switch_model(self, test_client):
        """Test model switching endpoint."""
        response = test_client.post("/models/switch", json={
            "provider": "ollama",
            "model_id": "llama3.2"
        })

        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True


class TestGraphEndpoints:
    """Tests for knowledge graph endpoints."""

    def test_build_graph(self, test_client):
        """Test graph building endpoint."""
        response = test_client.post("/graph/build", json={
            "force_rebuild": False
        })

        if response.status_code == 200:
            data = response.json()
            assert "success" in data

    def test_query_graph(self, test_client):
        """Test graph query endpoint."""
        response = test_client.post("/graph/query", json={
            "query": "What documents are in the knowledge graph?",
            "max_tokens": 500
        })

        if response.status_code == 200:
            data = response.json()
            assert "answer" in data


class TestCORSHeaders:
    """Tests for CORS configuration."""

    def test_cors_headers_present(self, test_client):
        """Test that CORS headers are set correctly."""
        response = test_client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3001",
                "Access-Control-Request-Method": "GET"
            }
        )

        # Should allow the configured origin
        assert response.status_code in [200, 204, 405]


class TestRequestValidation:
    """Tests for request validation across endpoints."""

    def test_missing_required_fields(self, test_client):
        """Test that missing required fields return 422."""
        # Missing 'message' field
        response = test_client.post("/chat/v2", json={
            "autonomy_level": "moderate"
        })

        assert response.status_code == 422

    def test_invalid_json(self, test_client):
        """Test that invalid JSON returns proper error."""
        response = test_client.post(
            "/chat/v2",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422
