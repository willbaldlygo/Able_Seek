"""
Pytest configuration and fixtures for Able2 tests.
"""

import pytest
import asyncio
from pathlib import Path
from typing import Generator, AsyncGenerator
from unittest.mock import MagicMock, AsyncMock

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# Async Support
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic API client."""
    mock = MagicMock()
    mock.messages.create.return_value = MagicMock(
        content=[MagicMock(text="Mock LLM response")]
    )
    return mock


@pytest.fixture
def mock_ollama_response():
    """Mock Ollama API response."""
    return {"response": "Mock Ollama response"}


@pytest.fixture
def mock_vector_store():
    """Mock vector store for testing."""
    mock = MagicMock()
    mock.search.return_value = [
        {
            "id": "doc1",
            "content": "Test document content",
            "metadata": {"source": "test.pdf"},
            "score": 0.95
        }
    ]
    mock.add_documents.return_value = ["doc1"]
    return mock


# =============================================================================
# Test Data Fixtures
# =============================================================================

@pytest.fixture
def sample_document_content():
    """Sample document content for testing."""
    return """
    This is a test document for Able2.
    It contains multiple paragraphs of text.

    The document discusses various topics including:
    - Machine learning
    - Natural language processing
    - Knowledge graphs

    This content is used for testing retrieval and processing.
    """


@pytest.fixture
def sample_chat_request():
    """Sample chat request for testing."""
    return {
        "message": "What is machine learning?",
        "session_id": None,
        "autonomy_level": "moderate",
        "sources": ["documents"]
    }


@pytest.fixture
def sample_upload_file(tmp_path):
    """Create a sample file for upload testing."""
    file_path = tmp_path / "test_document.txt"
    file_path.write_text("This is test content for file upload testing.")
    return file_path


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    session.add = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    return session


# =============================================================================
# API Client Fixtures
# =============================================================================

@pytest.fixture
def test_client():
    """
    Create a test client for FastAPI application.

    Usage:
        def test_endpoint(test_client):
            response = test_client.get("/health")
            assert response.status_code == 200
    """
    from fastapi.testclient import TestClient
    from backend.api.main import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
async def async_test_client():
    """
    Create an async test client for FastAPI application.

    Usage:
        async def test_endpoint(async_test_client):
            response = await async_test_client.get("/health")
            assert response.status_code == 200
    """
    from httpx import AsyncClient
    from backend.api.main import app

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


# =============================================================================
# Environment Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    """
    Mock settings for testing.
    Prevents actual database/API connections during tests.
    """
    # Mock database URL to use SQLite in-memory
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    # Mock API keys (empty to prevent actual API calls)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")

    # Mock paths
    monkeypatch.setenv("PATH_UPLOADS", "/tmp/able2_test_uploads")
    monkeypatch.setenv("PATH_VECTOR_STORE", "/tmp/able2_test_vector")
    monkeypatch.setenv("PATH_GRAPH_STORE", "/tmp/able2_test_graph")
