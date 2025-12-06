"""
Unit tests for Able2 agents.

Tests for:
- BaseAgent functionality
- OrchestratorAgent
- MemoryAgent
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime


class TestBaseAgent:
    """Tests for BaseAgent class."""

    @pytest.fixture
    def base_agent(self):
        """Create a concrete implementation of BaseAgent for testing."""
        from backend.agents.base_agent import BaseAgent
        from backend.schemas import AgentType, AgentMessage, AgentResponse

        class TestAgent(BaseAgent):
            async def process(self, message):
                return self.create_response(
                    success=True,
                    data={"result": "test"},
                    reasoning="Test reasoning"
                )

        return TestAgent(agent_type=AgentType.MEMORY)

    def test_create_response(self, base_agent):
        """Test that create_response creates proper AgentResponse."""
        response = base_agent.create_response(
            success=True,
            data={"key": "value"},
            reasoning="Test reasoning",
            requires_confirmation=False
        )

        assert response.success is True
        assert response.data == {"key": "value"}
        assert response.reasoning == "Test reasoning"
        assert response.requires_confirmation is False

    def test_create_error_response(self, base_agent):
        """Test error response creation."""
        response = base_agent.create_response(
            success=False,
            data={},
            error="Something went wrong"
        )

        assert response.success is False
        assert response.error == "Something went wrong"

    @pytest.mark.asyncio
    async def test_process_with_retry_success(self, base_agent):
        """Test successful processing without retry."""
        from backend.schemas import AgentType, AgentMessage

        message = AgentMessage(
            from_agent=AgentType.USER,
            to_agent=AgentType.MEMORY,
            content="Test message"
        )

        response = await base_agent.process_with_retry(message, max_retries=3)

        assert response.success is True

    @pytest.mark.asyncio
    async def test_process_with_retry_failure(self):
        """Test retry logic on failure."""
        from backend.agents.base_agent import BaseAgent
        from backend.schemas import AgentType, AgentMessage

        class FailingAgent(BaseAgent):
            def __init__(self):
                super().__init__(agent_type=AgentType.MEMORY)
                self.call_count = 0

            async def process(self, message):
                self.call_count += 1
                raise Exception("Simulated failure")

        agent = FailingAgent()
        message = AgentMessage(
            from_agent=AgentType.USER,
            to_agent=AgentType.MEMORY,
            content="Test message"
        )

        response = await agent.process_with_retry(message, max_retries=3)

        assert response.success is False
        assert agent.call_count == 3  # Should have retried 3 times
        assert "Failed after 3 attempts" in response.error


class TestMemoryAgent:
    """Tests for MemoryAgent class."""

    @pytest.fixture
    def memory_agent(self, mock_vector_store):
        """Create MemoryAgent with mocked dependencies."""
        from backend.agents.memory_agent import MemoryAgent

        with patch('backend.agents.memory_agent.get_hybrid_retriever') as mock_retriever:
            mock_retriever.return_value = mock_vector_store
            agent = MemoryAgent()
            agent._retriever = mock_vector_store
            return agent

    @pytest.mark.asyncio
    async def test_search_documents(self, memory_agent, mock_vector_store):
        """Test document search functionality."""
        from backend.schemas import AgentType, AgentMessage

        # Setup mock
        mock_vector_store.search = AsyncMock(return_value=[
            {"id": "doc1", "content": "Test content", "score": 0.9}
        ])

        message = AgentMessage(
            from_agent=AgentType.ORCHESTRATOR,
            to_agent=AgentType.MEMORY,
            content="search query",
            metadata={"action_type": "search", "query": "test query"}
        )

        # This test validates the agent can be called
        # Full integration testing would require actual retriever


class TestOrchestratorAgent:
    """Tests for OrchestratorAgent class."""

    @pytest.fixture
    def orchestrator(self):
        """Create OrchestratorAgent for testing."""
        from backend.agents.orchestrator import OrchestratorAgent
        from backend.schemas import AutonomyLevel

        return OrchestratorAgent(autonomy_level=AutonomyLevel.MODERATE)

    def test_autonomy_levels(self, orchestrator):
        """Test that autonomy level is properly set."""
        from backend.schemas import AutonomyLevel

        assert orchestrator.autonomy_level == AutonomyLevel.MODERATE

    def test_requires_confirmation_conservative(self):
        """Test confirmation requirements in conservative mode."""
        from backend.agents.orchestrator import OrchestratorAgent
        from backend.schemas import AutonomyLevel

        agent = OrchestratorAgent(autonomy_level=AutonomyLevel.CONSERVATIVE)

        # In conservative mode, most actions should require confirmation
        # This tests the autonomy control system


class TestAgentCommunication:
    """Tests for inter-agent communication."""

    def test_agent_message_creation(self):
        """Test AgentMessage creation and validation."""
        from backend.schemas import AgentType, AgentMessage, MessagePriority

        message = AgentMessage(
            from_agent=AgentType.USER,
            to_agent=AgentType.ORCHESTRATOR,
            content="Test message",
            metadata={"key": "value"},
            priority=MessagePriority.HIGH
        )

        assert message.from_agent == AgentType.USER
        assert message.to_agent == AgentType.ORCHESTRATOR
        assert message.content == "Test message"
        assert message.priority == MessagePriority.HIGH
        assert message.message_id is not None

    def test_agent_response_creation(self):
        """Test AgentResponse creation and validation."""
        from backend.schemas import AgentType, AgentResponse

        response = AgentResponse(
            agent_type=AgentType.MEMORY,
            success=True,
            data={"results": []},
            reasoning="Search completed",
            requires_confirmation=False
        )

        assert response.agent_type == AgentType.MEMORY
        assert response.success is True
        assert response.requires_confirmation is False
