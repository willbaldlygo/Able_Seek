"""
Base agent class for Able2.
All agents inherit from this base class.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import asyncio
from datetime import datetime

from backend.schemas import AgentType, AgentMessage, AgentResponse
from backend.core import get_logger, get_agent_config


class BaseAgent(ABC):
    """
    Abstract base class for all agents.

    Provides:
    - Common logging infrastructure
    - Retry logic for failed operations
    - Response creation helpers
    - Model configuration
    """

    def __init__(
        self,
        agent_type: AgentType,
        model_provider: Optional[str] = None
    ):
        """
        Initialize base agent.

        Args:
            agent_type: Type of this agent
            model_provider: LLM provider (anthropic or ollama)
        """
        self.agent_type = agent_type
        self.logger = get_logger(agent_type.value)

        # Load agent configuration
        self.config = get_agent_config(agent_type.value)

        # Set model provider
        self.model_provider = model_provider or self.config.get("provider", "ollama")
        self.model_name = self.config.get("model", "llama3.2")
        self.temperature = self.config.get("temperature", 0.7)
        self.max_retries = self.config.get("max_retries", 3)
        self.timeout = self.config.get("timeout_seconds", 30)

        self.logger.info(
            f"Initialized {agent_type.value} agent "
            f"(provider={self.model_provider}, model={self.model_name})"
        )

    @abstractmethod
    async def process(self, message: AgentMessage) -> AgentResponse:
        """
        Process a message and return a response.

        This is the main method that each agent must implement.

        Args:
            message: Message to process

        Returns:
            Agent response
        """
        pass

    def create_response(
        self,
        success: bool,
        data: Dict[str, Any],
        reasoning: str = "",
        next_action: Optional[str] = None,
        requires_confirmation: bool = False,
        error: Optional[str] = None
    ) -> AgentResponse:
        """
        Create a standardized agent response.

        Args:
            success: Whether operation succeeded
            data: Response data
            reasoning: Explanation of what was done
            next_action: Suggested next step
            requires_confirmation: Whether user confirmation needed
            error: Error message if success=False

        Returns:
            AgentResponse object
        """
        return AgentResponse(
            agent_type=self.agent_type,
            success=success,
            data=data,
            reasoning=reasoning,
            next_action=next_action,
            requires_confirmation=requires_confirmation,
            error=error,
            timestamp=datetime.now()
        )

    async def process_with_retry(
        self,
        message: AgentMessage,
        max_retries: Optional[int] = None
    ) -> AgentResponse:
        """
        Process message with automatic retry on failure.

        Args:
            message: Message to process
            max_retries: Max retry attempts (default: from config)

        Returns:
            Agent response
        """
        if max_retries is None:
            max_retries = self.max_retries

        last_error = None

        for attempt in range(max_retries):
            try:
                self.logger.debug(f"Processing message (attempt {attempt + 1}/{max_retries})")

                start_time = time.time()
                response = await self.process(message)
                duration_ms = int((time.time() - start_time) * 1000)

                self.logger.info(
                    f"Processed message successfully in {duration_ms}ms "
                    f"(attempt {attempt + 1})"
                )

                return response

            except Exception as e:
                last_error = str(e)
                self.logger.warning(
                    f"Processing failed (attempt {attempt + 1}/{max_retries}): {last_error}"
                )

                # Wait before retrying (exponential backoff)
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 1s, 2s, 4s, ...
                    self.logger.debug(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)

        # All retries failed
        self.logger.error(f"All retry attempts failed: {last_error}")

        return self.create_response(
            success=False,
            data={},
            error=f"Failed after {max_retries} attempts: {last_error}"
        )

    def call_llm(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Call LLM for text generation.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Max tokens to generate

        Returns:
            Generated text
        """
        self.logger.debug(f"Calling LLM: {self.model_provider}/{self.model_name}")

        try:
            if self.model_provider == "anthropic":
                return self._call_anthropic(prompt, system_prompt, max_tokens)
            elif self.model_provider == "ollama":
                return self._call_ollama(prompt, system_prompt, max_tokens)
            else:
                raise ValueError(f"Unsupported provider: {self.model_provider}")

        except Exception as e:
            self.logger.error(f"LLM call failed: {str(e)}")
            raise

    def _call_anthropic(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Call Anthropic API."""
        from anthropic import Anthropic
        from backend.core import settings

        client = Anthropic(api_key=settings.anthropic_api_key)

        messages = [{"role": "user", "content": prompt}]

        response = client.messages.create(
            model=self.model_name,
            max_tokens=max_tokens or 4000,
            temperature=self.temperature,
            system=system_prompt or "",
            messages=messages
        )

        return response.content[0].text

    def _call_ollama(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Call Ollama API."""
        import requests
        from backend.core import settings

        url = f"{settings.ollama_base_url}/api/generate"

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
            }
        }

        if system_prompt:
            payload["system"] = system_prompt

        response = requests.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()

        return response.json()["response"]

    def log_action(
        self,
        action_type: str,
        success: bool,
        details: Optional[str] = None
    ):
        """
        Log an agent action.

        Args:
            action_type: Type of action performed
            success: Whether action succeeded
            details: Optional details
        """
        self.logger.agent_action(
            agent_type=self.agent_type.value,
            action_type=action_type,
            success=success,
            details=details
        )

    def __repr__(self):
        return f"<{self.__class__.__name__}(type={self.agent_type.value})>"
