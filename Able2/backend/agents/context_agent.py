"""
Context Agent for Able2.

Provides context awareness for conversations:
- Conversation history management
- Session summarization for long contexts
- Time-of-day awareness
- Topic tracking

Phase 1: Local context (no external integrations)
Phase 2: Gmail and Calendar integration
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session as DBSession

from backend.schemas import AgentType, AgentMessage, AgentResponse, ActionType, ContextSnapshot
from backend.core import context_logger, get_db_context
from backend.models import Session, AgentAction
from .base_agent import BaseAgent


class ContextAgent(BaseAgent):
    """
    Context Agent - provides environmental and conversational context.

    Phase 1 capabilities:
    - Conversation history retrieval
    - Context summarization
    - Time-of-day awareness
    - Topic extraction

    Phase 2 additions:
    - Gmail integration
    - Calendar integration
    """

    # Time periods for energy estimation
    TIME_PERIODS = {
        "early_morning": (5, 8),    # 5am - 8am
        "morning": (8, 12),          # 8am - 12pm
        "afternoon": (12, 17),       # 12pm - 5pm
        "evening": (17, 21),         # 5pm - 9pm
        "night": (21, 24),           # 9pm - midnight
        "late_night": (0, 5),        # midnight - 5am
    }

    # Typical energy levels by time
    ENERGY_BY_TIME = {
        "early_morning": "low",
        "morning": "high",
        "afternoon": "medium",
        "evening": "medium",
        "night": "low",
        "late_night": "low",
    }

    def __init__(self):
        """Initialize Context Agent."""
        super().__init__(
            agent_type=AgentType.CONTEXT,
            model_provider="ollama"  # Fast local model for summarization
        )

        self.logger.info("Context Agent initialized")

    async def process(self, message: AgentMessage) -> AgentResponse:
        """
        Process context-related message.

        Args:
            message: Agent message

        Returns:
            Agent response
        """
        action_type = message.metadata.get("action_type", ActionType.GET_CONTEXT)

        self.logger.info(f"Context Agent processing: {action_type}")

        if action_type == ActionType.GET_CONTEXT:
            return await self.get_context(message)
        elif action_type == ActionType.ANALYZE_CALENDAR:
            return await self.analyze_calendar(message)
        elif action_type == ActionType.ANALYZE_EMAILS:
            return await self.analyze_emails(message)
        elif action_type == ActionType.ASSESS_WORKLOAD:
            return await self.assess_workload(message)
        elif action_type == "get_conversation_history":
            return await self.get_conversation_history(message)
        elif action_type == "summarize_conversation":
            return await self.summarize_conversation(message)
        elif action_type == "extract_topics":
            return await self.extract_topics(message)
        else:
            return self.create_response(
                success=False,
                data={},
                error=f"Unsupported action type: {action_type}"
            )

    async def get_context(self, message: AgentMessage) -> AgentResponse:
        """
        Get current context snapshot.

        Includes:
        - Current time and time period
        - Estimated energy level
        - Recent conversation summary (if session provided)

        Args:
            message: Context request message

        Returns:
            Context snapshot
        """
        self.logger.info("Getting context snapshot")

        now = datetime.now()
        time_period = self._get_time_period(now)
        energy_level = self.ENERGY_BY_TIME.get(time_period, "medium")

        # Get session context if available
        session_id = message.metadata.get("session_id")
        conversation_summary = None
        recent_topics = []

        if session_id:
            history = await self._get_session_history(session_id)
            if history:
                # Extract topics from recent messages
                recent_topics = self._extract_simple_topics(history)

                # Summarize if conversation is long
                if len(history) > 5:
                    conversation_summary = await self._summarize_history(history)

        context = ContextSnapshot(
            current_time=now,
            upcoming_events=[],  # Phase 2: Calendar integration
            pending_emails=[],    # Phase 2: Gmail integration
            workload_score=self._estimate_workload(time_period),
            available_time_blocks=[],
            energy_level=energy_level
        )

        # Add local context data
        context_data = context.to_dict()
        context_data.update({
            "time_period": time_period,
            "conversation_summary": conversation_summary,
            "recent_topics": recent_topics,
            "greeting": self._get_time_greeting(time_period),
        })

        return self.create_response(
            success=True,
            data=context_data,
            reasoning=f"Context snapshot at {time_period}. Energy typically {energy_level} at this time."
        )

    async def get_conversation_history(self, message: AgentMessage) -> AgentResponse:
        """
        Get conversation history for a session.

        Args:
            message: Request with session_id in metadata

        Returns:
            Conversation history
        """
        session_id = message.metadata.get("session_id")

        if not session_id:
            return self.create_response(
                success=False,
                data={},
                error="session_id required in metadata"
            )

        history = await self._get_session_history(session_id)

        return self.create_response(
            success=True,
            data={
                "session_id": session_id,
                "message_count": len(history),
                "history": history
            },
            reasoning=f"Retrieved {len(history)} messages from session history"
        )

    async def summarize_conversation(self, message: AgentMessage) -> AgentResponse:
        """
        Summarize a conversation to condense context.

        Useful for long conversations that exceed context window.

        Args:
            message: Request with session_id or history in metadata

        Returns:
            Conversation summary
        """
        session_id = message.metadata.get("session_id")
        provided_history = message.metadata.get("history", [])

        if session_id:
            history = await self._get_session_history(session_id)
        elif provided_history:
            history = provided_history
        else:
            return self.create_response(
                success=False,
                data={},
                error="session_id or history required"
            )

        if not history:
            return self.create_response(
                success=True,
                data={"summary": "No conversation history to summarize."},
                reasoning="Empty history"
            )

        summary = await self._summarize_history(history)
        topics = self._extract_simple_topics(history)

        return self.create_response(
            success=True,
            data={
                "summary": summary,
                "topics": topics,
                "message_count": len(history)
            },
            reasoning=f"Summarized {len(history)} messages into key points"
        )

    async def extract_topics(self, message: AgentMessage) -> AgentResponse:
        """
        Extract key topics from conversation.

        Args:
            message: Request with session_id or text in metadata

        Returns:
            List of topics
        """
        session_id = message.metadata.get("session_id")
        text = message.metadata.get("text", message.content)

        if session_id:
            history = await self._get_session_history(session_id)
            if history:
                text = " ".join([h.get("content", "") for h in history])

        if not text:
            return self.create_response(
                success=True,
                data={"topics": []},
                reasoning="No text to extract topics from"
            )

        # Use LLM for topic extraction
        topics = await self._extract_topics_llm(text)

        return self.create_response(
            success=True,
            data={"topics": topics},
            reasoning=f"Extracted {len(topics)} topics from conversation"
        )

    async def analyze_calendar(self, message: AgentMessage) -> AgentResponse:
        """
        Analyze calendar for upcoming events and conflicts.

        Phase 2 implementation - requires Google Calendar integration.
        """
        self.logger.info("Calendar analysis requested (Phase 2 feature)")

        return self.create_response(
            success=True,
            data={
                "upcoming_events": [],
                "conflicts": [],
                "free_time_blocks": [],
                "note": "Calendar integration available in Phase 2"
            },
            reasoning="Calendar integration requires Google Calendar setup (Phase 2)"
        )

    async def analyze_emails(self, message: AgentMessage) -> AgentResponse:
        """
        Analyze emails for priority and action items.

        Phase 2 implementation - requires Gmail integration.
        """
        self.logger.info("Email analysis requested (Phase 2 feature)")

        return self.create_response(
            success=True,
            data={
                "high_priority_emails": [],
                "action_required": [],
                "total_unread": 0,
                "note": "Gmail integration available in Phase 2"
            },
            reasoning="Gmail integration requires Google API setup (Phase 2)"
        )

    async def assess_workload(self, message: AgentMessage) -> AgentResponse:
        """
        Assess current workload based on context.

        Phase 1: Time-based estimation
        Phase 2: Calendar and task integration
        """
        self.logger.info("Assessing workload")

        now = datetime.now()
        time_period = self._get_time_period(now)
        workload = self._estimate_workload(time_period)

        # Determine suggested action based on workload
        if workload > 70:
            suggested_action = "take_break"
        elif workload < 30:
            suggested_action = "good_time_for_deep_work"
        else:
            suggested_action = "maintain_pace"

        return self.create_response(
            success=True,
            data={
                "workload_score": workload,
                "suggested_action": suggested_action,
                "time_period": time_period,
                "busy_periods": [],  # Phase 2: from calendar
                "note": "Workload based on time of day. More accurate with calendar integration."
            },
            reasoning=f"Workload estimate: {workload}% based on {time_period} time period"
        )

    # =========================================================================
    # Private Helper Methods
    # =========================================================================

    def _get_time_period(self, dt: datetime) -> str:
        """Determine time period from datetime."""
        hour = dt.hour

        for period, (start, end) in self.TIME_PERIODS.items():
            if start <= hour < end:
                return period

        return "afternoon"  # Fallback

    def _get_time_greeting(self, time_period: str) -> str:
        """Get appropriate greeting for time period."""
        greetings = {
            "early_morning": "Good early morning",
            "morning": "Good morning",
            "afternoon": "Good afternoon",
            "evening": "Good evening",
            "night": "Good night",
            "late_night": "Working late?",
        }
        return greetings.get(time_period, "Hello")

    def _estimate_workload(self, time_period: str) -> float:
        """Estimate workload score based on time period."""
        # Simple heuristic - can be enhanced with calendar data
        workload_by_time = {
            "early_morning": 30.0,
            "morning": 60.0,
            "afternoon": 50.0,
            "evening": 40.0,
            "night": 20.0,
            "late_night": 10.0,
        }
        return workload_by_time.get(time_period, 50.0)

    async def _get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get conversation history from database."""
        history = []

        try:
            with get_db_context() as db:
                # Get session
                session = db.query(Session).filter(
                    Session.session_id == session_id
                ).first()

                if not session:
                    return []

                # Get agent actions (which contain the conversation)
                actions = db.query(AgentAction).filter(
                    AgentAction.session_id == session.id
                ).order_by(AgentAction.timestamp.desc()).limit(20).all()

                for action in reversed(actions):
                    history.append({
                        "agent": action.agent_type,
                        "action": action.action_type,
                        "content": action.input_data.get("message", "") if action.input_data else "",
                        "response": action.output_data.get("message", "") if action.output_data else "",
                        "timestamp": action.timestamp.isoformat() if action.timestamp else None,
                        "success": action.success
                    })

        except Exception as e:
            self.logger.error(f"Failed to get session history: {e}")

        return history

    def _extract_simple_topics(self, history: List[Dict[str, Any]]) -> List[str]:
        """Extract topics using simple keyword extraction."""
        # Combine all text
        all_text = ""
        for item in history:
            all_text += " " + item.get("content", "")
            all_text += " " + item.get("response", "")

        # Simple word frequency for topics
        words = all_text.lower().split()

        # Filter out common words
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "can", "this",
            "that", "these", "those", "i", "you", "he", "she", "it",
            "we", "they", "what", "which", "who", "when", "where", "why",
            "how", "all", "each", "every", "both", "few", "more", "most",
            "other", "some", "such", "no", "not", "only", "same", "so",
            "than", "too", "very", "just", "but", "and", "or", "if",
            "because", "as", "until", "while", "of", "at", "by", "for",
            "with", "about", "against", "between", "into", "through",
            "during", "before", "after", "above", "below", "to", "from",
            "up", "down", "in", "out", "on", "off", "over", "under",
            "again", "further", "then", "once", "here", "there", "when",
            "where", "why", "how", "any", "both", "each", "few", "more",
            "most", "other", "some", "such", "your", "my", "me", "him",
        }

        # Count word frequencies
        word_counts = {}
        for word in words:
            # Clean word
            word = ''.join(c for c in word if c.isalnum())
            if len(word) > 3 and word not in stop_words:
                word_counts[word] = word_counts.get(word, 0) + 1

        # Get top topics
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        topics = [word for word, count in sorted_words[:5] if count > 1]

        return topics

    async def _summarize_history(self, history: List[Dict[str, Any]]) -> str:
        """Use LLM to summarize conversation history."""
        if not history:
            return "No conversation history."

        # Build conversation text
        conversation_parts = []
        for item in history[-10:]:  # Last 10 messages
            content = item.get("content", "")
            response = item.get("response", "")
            if content:
                conversation_parts.append(f"User: {content}")
            if response:
                conversation_parts.append(f"Assistant: {response[:200]}...")

        conversation_text = "\n".join(conversation_parts)

        if not conversation_text.strip():
            return "Conversation started but no messages exchanged yet."

        # Use LLM to summarize
        system_prompt = """Summarize this conversation in 2-3 sentences.
Focus on:
- Main topics discussed
- Key questions asked
- Any actions taken or pending

Be concise."""

        try:
            summary = self.call_llm(
                prompt=f"Conversation:\n{conversation_text}\n\nSummary:",
                system_prompt=system_prompt,
                max_tokens=150
            )
            return summary.strip()
        except Exception as e:
            self.logger.warning(f"LLM summarization failed: {e}")
            # Fallback to simple summary
            return f"Conversation with {len(history)} exchanges."

    async def _extract_topics_llm(self, text: str) -> List[str]:
        """Use LLM to extract topics from text."""
        if not text or len(text.strip()) < 20:
            return []

        # Truncate if too long
        text = text[:2000]

        system_prompt = """Extract 3-5 key topics from this text.
Return ONLY a comma-separated list of topics, nothing else.
Example: machine learning, data analysis, python programming"""

        try:
            response = self.call_llm(
                prompt=f"Text:\n{text}\n\nTopics:",
                system_prompt=system_prompt,
                max_tokens=100
            )

            # Parse topics
            topics = [t.strip() for t in response.split(",")]
            return [t for t in topics if t and len(t) < 50][:5]

        except Exception as e:
            self.logger.warning(f"LLM topic extraction failed: {e}")
            # Fallback to simple extraction
            return self._extract_simple_topics([{"content": text, "response": ""}])
