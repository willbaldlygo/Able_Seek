"""
Execution Agent for Able2.

Handles actions with side effects:
- Web browsing (SearxNG) - Phase 1
- Task breakdown - Phase 1
- Code execution (sandboxed) - Phase 3
- Email sending - Phase 2
- Calendar event creation - Phase 2
"""

from typing import Dict, Any, List
from backend.schemas import AgentType, AgentMessage, AgentResponse, ActionType
from backend.core import execution_logger, settings
from backend.integrations.searxng import SearxNGClient
from .base_agent import BaseAgent


class ExecutionAgent(BaseAgent):
    """
    Execution Agent - handles actions with side effects.

    Phase 1 capabilities:
    - Web search via SearxNG
    - Task breakdown using LLM

    Phase 2 additions:
    - Email sending
    - Calendar events

    Phase 3 additions:
    - Code execution (sandboxed)
    """

    def __init__(self):
        """Initialize Execution Agent."""
        super().__init__(
            agent_type=AgentType.EXECUTION,
            model_provider="anthropic"  # Use Claude for execution planning
        )

        # Initialize SearxNG client
        self.searxng = SearxNGClient()

        self.logger.info(f"Execution Agent initialized (SearxNG: {self.searxng.enabled})")

    async def process(self, message: AgentMessage) -> AgentResponse:
        """
        Process execution-related message.

        Args:
            message: Agent message

        Returns:
            Agent response
        """
        action_type = message.metadata.get("action_type", ActionType.BROWSE_WEB)

        self.logger.info(f"Execution Agent processing: {action_type}")

        if action_type == ActionType.BROWSE_WEB:
            return await self.browse_web(message)
        elif action_type == ActionType.EXECUTE_CODE:
            return await self.execute_code(message)
        elif action_type == ActionType.SEND_EMAIL:
            return await self.send_email(message)
        elif action_type == ActionType.CREATE_CALENDAR_EVENT:
            return await self.create_calendar_event(message)
        elif action_type == ActionType.BREAK_DOWN_TASK:
            return await self.break_down_task(message)
        else:
            return self.create_response(
                success=False,
                data={},
                error=f"Unsupported action type: {action_type}"
            )

    async def browse_web(self, message: AgentMessage) -> AgentResponse:
        """
        Browse web using SearxNG.

        Args:
            message: Web browsing request

        Returns:
            Web search results
        """
        query = message.content
        max_results = message.metadata.get("max_results", 10)

        self.logger.info(f"Web search: {query}")

        # Check if SearxNG is available
        if not self.searxng.enabled:
            return self.create_response(
                success=False,
                data={"query": query, "results": []},
                error="Web search is disabled. Enable SearxNG in settings."
            )

        # Check availability
        if not self.searxng.is_available():
            return self.create_response(
                success=False,
                data={"query": query, "results": []},
                error="SearxNG is not responding. Check if the service is running."
            )

        try:
            # Perform search
            results = await self.searxng.search(query, max_results=max_results)

            if not results:
                return self.create_response(
                    success=True,
                    data={
                        "query": query,
                        "results": [],
                        "num_results": 0
                    },
                    reasoning="Search completed but no results found."
                )

            # Optionally summarize results using LLM
            summarize = message.metadata.get("summarize", False)
            summary = None

            if summarize and results:
                summary = await self._summarize_search_results(query, results)

            self.log_action("browse_web", success=True, details=f"Found {len(results)} results")

            return self.create_response(
                success=True,
                data={
                    "query": query,
                    "results": results,
                    "num_results": len(results),
                    "summary": summary
                },
                reasoning=f"Found {len(results)} web results for '{query}'"
            )

        except Exception as e:
            self.logger.error(f"Web search failed: {str(e)}")
            return self.create_response(
                success=False,
                data={"query": query, "results": []},
                error=f"Web search failed: {str(e)}"
            )

    async def _summarize_search_results(self, query: str, results: List[Dict[str, Any]]) -> str:
        """Summarize search results using LLM."""
        # Build context from results
        results_text = ""
        for i, result in enumerate(results[:5], 1):
            results_text += f"{i}. {result.get('title', 'No title')}\n"
            results_text += f"   {result.get('content', 'No content')[:200]}\n\n"

        system_prompt = """Summarize these search results in 2-3 sentences.
Focus on answering the user's query based on the search results.
Be concise and factual."""

        try:
            summary = self.call_llm(
                prompt=f"Query: {query}\n\nSearch Results:\n{results_text}\n\nSummary:",
                system_prompt=system_prompt,
                max_tokens=200
            )
            return summary.strip()
        except Exception as e:
            self.logger.warning(f"Failed to summarize results: {e}")
            return None

    async def execute_code(self, message: AgentMessage) -> AgentResponse:
        """
        Execute code in sandboxed environment.

        Phase 3 implementation with security measures.

        Args:
            message: Code execution request

        Returns:
            Execution results
        """
        code = message.content
        self.logger.info("Code execution (stub)")

        return self.create_response(
            success=True,
            data={
                "output": "",
                "error": None,
                "execution_time_ms": 0
            },
            reasoning="[Phase 1 Stub] Code execution coming in Phase 3 with proper sandboxing.",
            requires_confirmation=True  # Always require confirmation for code execution
        )

    async def send_email(self, message: AgentMessage) -> AgentResponse:
        """
        Send email via Gmail API.

        Phase 2 implementation.

        Args:
            message: Email send request

        Returns:
            Send confirmation
        """
        self.logger.info("Send email (stub)")

        return self.create_response(
            success=True,
            data={
                "sent": False,
                "message_id": None
            },
            reasoning="[Phase 1 Stub] Email sending coming in Phase 2 with Gmail integration.",
            requires_confirmation=True  # Always require confirmation for emails
        )

    async def create_calendar_event(self, message: AgentMessage) -> AgentResponse:
        """
        Create Google Calendar event.

        Phase 2 implementation.

        Args:
            message: Calendar event creation request

        Returns:
            Event creation confirmation
        """
        self.logger.info("Create calendar event (stub)")

        return self.create_response(
            success=True,
            data={
                "created": False,
                "event_id": None
            },
            reasoning="[Phase 1 Stub] Calendar event creation coming in Phase 2.",
            requires_confirmation=True  # Always require confirmation
        )

    async def break_down_task(self, message: AgentMessage) -> AgentResponse:
        """
        Break down a large task into smaller subtasks.

        This can work in Phase 1 using LLM.

        Args:
            message: Task breakdown request

        Returns:
            List of subtasks
        """
        task_description = message.content
        self.logger.info(f"Breaking down task: {task_description}")

        try:
            system_prompt = """You are a task breakdown specialist. Break down the given task into 3-7 smaller, actionable subtasks.

Rules:
- Each subtask should be clear and specific
- Subtasks should be ordered logically
- Each subtask should be completable in 30-60 minutes
- Format: One subtask per line, numbered

Example:
1. Research existing solutions
2. Draft initial implementation
3. Write unit tests
4. Review and refactor"""

            subtasks_text = self.call_llm(
                prompt=f"Task: {task_description}\n\nBreak this down into subtasks:",
                system_prompt=system_prompt,
                max_tokens=500
            )

            # Parse subtasks
            subtasks = []
            for line in subtasks_text.strip().split("\n"):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith("-")):
                    # Remove numbering
                    task = line.split(".", 1)[-1].strip()
                    if task:
                        subtasks.append(task)

            self.log_action("break_down_task", success=True, details=f"Created {len(subtasks)} subtasks")

            return self.create_response(
                success=True,
                data={
                    "original_task": task_description,
                    "subtasks": subtasks,
                    "num_subtasks": len(subtasks)
                },
                reasoning=f"Broke down task into {len(subtasks)} manageable subtasks."
            )

        except Exception as e:
            self.logger.error(f"Task breakdown failed: {str(e)}")

            return self.create_response(
                success=False,
                data={},
                error=f"Task breakdown failed: {str(e)}"
            )


# Stub classes for future implementation

class WebBrowser:
    """Web browsing with SearxNG (Phase 3)."""

    def __init__(self):
        self.logger = execution_logger
        self.logger.info("Web browser (Phase 3)")

    async def search(self, query: str):
        """Search web."""
        pass

    async def fetch_page(self, url: str):
        """Fetch and parse webpage."""
        pass


class CodeExecutor:
    """Sandboxed code execution (Phase 3)."""

    def __init__(self):
        self.logger = execution_logger
        self.logger.info("Code executor (Phase 3)")

    async def execute(self, code: str, language: str = "python"):
        """Execute code in sandbox."""
        pass
