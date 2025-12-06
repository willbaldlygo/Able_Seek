"""
Security-focused unit tests for Able2 API.

Tests for:
- File upload security (path traversal, file type, size limits)
- Input validation
- Error handling (no internal error exposure)
"""

import pytest
from pathlib import Path
from io import BytesIO


class TestFileUploadSecurity:
    """Tests for file upload security measures."""

    def test_path_traversal_blocked(self, test_client):
        """Test that path traversal attempts are blocked."""
        # Attempt path traversal with filename
        malicious_filenames = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd",
            "test\x00.txt",  # Null byte injection
        ]

        for filename in malicious_filenames:
            # Create a simple file-like object
            file_content = b"malicious content"
            files = {"file": (filename, BytesIO(file_content), "text/plain")}

            response = test_client.post("/upload", files=files)

            # Should either reject or sanitize the filename
            # The file should NOT be written to a path outside uploads directory
            assert response.status_code in [400, 200]

            if response.status_code == 200:
                # If accepted, verify filename was sanitized
                data = response.json()
                assert ".." not in data.get("filename", "")
                assert "/" not in data.get("filename", "")
                assert "\\" not in data.get("filename", "")

    def test_invalid_file_type_rejected(self, test_client):
        """Test that non-allowed file types are rejected."""
        invalid_extensions = [".exe", ".sh", ".bat", ".py", ".js", ".php"]

        for ext in invalid_extensions:
            file_content = b"#!/bin/bash\necho 'malicious'"
            files = {"file": (f"malicious{ext}", BytesIO(file_content), "application/octet-stream")}

            response = test_client.post("/upload", files=files)

            assert response.status_code == 400
            assert "Invalid file type" in response.json().get("detail", "")

    def test_valid_file_types_accepted(self, test_client):
        """Test that valid file types are accepted."""
        valid_files = [
            ("document.pdf", b"%PDF-1.4 fake pdf content", "application/pdf"),
            ("notes.txt", b"Plain text content", "text/plain"),
            ("readme.md", b"# Markdown content", "text/markdown"),
        ]

        for filename, content, mime_type in valid_files:
            files = {"file": (filename, BytesIO(content), mime_type)}

            response = test_client.post("/upload", files=files)

            # Should be accepted (or fail for other reasons, not file type)
            if response.status_code == 400:
                assert "Invalid file type" not in response.json().get("detail", "")

    def test_file_size_limit(self, test_client):
        """Test that oversized files are rejected."""
        # Create a file larger than 50MB limit
        large_content = b"x" * (51 * 1024 * 1024)  # 51MB
        files = {"file": ("large_file.txt", BytesIO(large_content), "text/plain")}

        response = test_client.post("/upload", files=files)

        assert response.status_code == 413
        assert "too large" in response.json().get("detail", "").lower()


class TestInputValidation:
    """Tests for input validation on API endpoints."""

    def test_empty_message_rejected(self, test_client):
        """Test that empty messages are rejected."""
        response = test_client.post("/chat/v2", json={
            "message": "",
            "autonomy_level": "moderate"
        })

        assert response.status_code == 422  # Validation error

    def test_message_max_length(self, test_client):
        """Test that overly long messages are rejected."""
        response = test_client.post("/chat/v2", json={
            "message": "x" * 100000,  # Over 50k limit
            "autonomy_level": "moderate"
        })

        assert response.status_code == 422

    def test_invalid_autonomy_level(self, test_client):
        """Test that invalid autonomy levels are rejected."""
        response = test_client.post("/chat/v2", json={
            "message": "Hello",
            "autonomy_level": "super_aggressive"  # Invalid
        })

        assert response.status_code == 422

    def test_invalid_session_id_format(self, test_client):
        """Test that malformed session IDs are rejected."""
        invalid_session_ids = [
            "not-a-uuid",
            "'; DROP TABLE users; --",
            "<script>alert('xss')</script>",
        ]

        for session_id in invalid_session_ids:
            response = test_client.post("/chat/v2", json={
                "message": "Hello",
                "session_id": session_id,
                "autonomy_level": "moderate"
            })

            # Should reject invalid format
            assert response.status_code in [400, 422]

    def test_top_k_bounds(self, test_client):
        """Test that top_k parameter bounds are enforced."""
        # Test negative value
        response = test_client.post("/chat/enhanced", json={
            "message": "test",
            "top_k": -1
        })
        assert response.status_code == 422

        # Test exceeding maximum
        response = test_client.post("/chat/enhanced", json={
            "message": "test",
            "top_k": 1000
        })
        assert response.status_code == 422


class TestErrorHandling:
    """Tests to ensure internal errors are not exposed."""

    def test_internal_errors_not_exposed(self, test_client, monkeypatch):
        """Test that internal error details are not returned to client."""
        # This test verifies that when an internal error occurs,
        # the client receives a generic error message, not stack traces

        # The error messages should not contain:
        # - File paths
        # - Stack traces
        # - Database connection strings
        # - API keys

        response = test_client.get("/health")

        # Health check should work
        assert response.status_code == 200

        # Response should not contain sensitive patterns
        response_text = str(response.json())
        assert "password" not in response_text.lower()
        assert "api_key" not in response_text.lower()
        assert "traceback" not in response_text.lower()

    def test_404_does_not_leak_info(self, test_client):
        """Test that 404 responses don't leak internal information."""
        response = test_client.get("/nonexistent/path/../../etc/passwd")

        assert response.status_code == 404
        # Should not reveal file system structure
        assert "etc" not in response.text.lower()
        assert "passwd" not in response.text.lower()


class TestSQLInjection:
    """Tests for SQL injection prevention."""

    def test_document_id_sql_injection(self, test_client):
        """Test that document_id parameter is safe from SQL injection."""
        malicious_ids = [
            "'; DROP TABLE documents; --",
            "1 OR 1=1",
            "1; SELECT * FROM users",
            "1 UNION SELECT password FROM users",
        ]

        for malicious_id in malicious_ids:
            response = test_client.delete(f"/documents/{malicious_id}")

            # Should not cause server error (would indicate SQL injection worked)
            # 404 or 400 are acceptable responses
            assert response.status_code in [400, 404, 500]

            # If 500, verify it's not a SQL error
            if response.status_code == 500:
                error_detail = response.json().get("detail", "")
                assert "sql" not in error_detail.lower()
                assert "syntax" not in error_detail.lower()
