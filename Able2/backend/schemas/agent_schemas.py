"""
Agent communication schemas and enums.
Defines the protocol for inter-agent communication in Able2.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid


class AgentType(str, Enum):
    """Types of agents in the system."""
    USER = "user"
    ORCHESTRATOR = "orchestrator"
    MEMORY = "memory"
    CONTEXT = "context"
    EXECUTION = "execution"


class ActionType(str, Enum):
    """Types of actions agents can perform."""
    # Memory Agent Actions
    SEARCH_DOCUMENTS = "search_documents"
    SEARCH_EMAILS = "search_emails"
    SEARCH_CALENDAR = "search_calendar"
    SEARCH_MULTI_SOURCE = "search_multi_source"
    BUILD_GRAPH = "build_graph"
    QUERY_GRAPH = "query_graph"

    # Context Agent Actions
    ANALYZE_CALENDAR = "analyze_calendar"
    ANALYZE_EMAILS = "analyze_emails"
    ASSESS_WORKLOAD = "assess_workload"
    GET_CONTEXT = "get_context"

    # Execution Agent Actions
    BROWSE_WEB = "browse_web"
    EXECUTE_CODE = "execute_code"
    SEND_EMAIL = "send_email"
    CREATE_CALENDAR_EVENT = "create_calendar_event"
    BREAK_DOWN_TASK = "break_down_task"

    # Orchestrator Actions
    ANALYZE_INTENT = "analyze_intent"
    PLAN_ACTIONS = "plan_actions"
    DELEGATE = "delegate"
    SYNTHESIZE = "synthesize"


class AutonomyLevel(str, Enum):
    """
    User-selected autonomy levels.

    Conservative: Ask before every action, show all reasoning
    Moderate: Auto-execute searches, ask before actions with side effects
    Aggressive: Auto-execute most actions, only ask for destructive operations
    """
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class MessagePriority(str, Enum):
    """Priority levels for agent messages."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class AgentMessage:
    """
    Message passed between agents.

    Attributes:
        from_agent: Agent sending the message
        to_agent: Agent receiving the message
        content: The actual message content (query, instruction, etc.)
        metadata: Additional context (sources, filters, etc.)
        timestamp: When message was created
        message_id: Unique identifier
        priority: Message priority
        requires_response: Whether sender expects a response
        parent_message_id: For threading conversations
    """
    from_agent: AgentType
    to_agent: AgentType
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    priority: MessagePriority = MessagePriority.MEDIUM
    requires_response: bool = True
    parent_message_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "from_agent": self.from_agent.value,
            "to_agent": self.to_agent.value,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "message_id": self.message_id,
            "priority": self.priority.value,
            "requires_response": self.requires_response,
            "parent_message_id": self.parent_message_id
        }


@dataclass
class AgentResponse:
    """
    Response from an agent after processing a message.

    Attributes:
        agent_type: Agent that generated this response
        success: Whether the action succeeded
        data: Response data (search results, analysis, etc.)
        reasoning: Explanation of what the agent did and why
        next_action: Suggested next step (for orchestrator)
        requires_confirmation: Whether user confirmation is needed
        error: Error message if success=False
        metadata: Additional context
        timestamp: When response was created
        response_id: Unique identifier
    """
    agent_type: AgentType
    success: bool
    data: Dict[str, Any]
    reasoning: str = ""
    next_action: Optional[str] = None
    requires_confirmation: bool = False
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    response_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "agent_type": self.agent_type.value,
            "success": self.success,
            "data": self.data,
            "reasoning": self.reasoning,
            "next_action": self.next_action,
            "requires_confirmation": self.requires_confirmation,
            "error": self.error,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "response_id": self.response_id
        }


@dataclass
class SearchQuery:
    """
    Structured search query for Memory Agent.

    Attributes:
        query: The search query string
        sources: Which sources to search (documents, emails, calendar)
        top_k: Number of results to return
        filters: Additional filters (date range, authors, etc.)
        use_reranking: Whether to use cross-encoder reranking
        include_graph: Whether to include GraphRAG results
    """
    query: str
    sources: List[str] = field(default_factory=lambda: ["documents"])
    top_k: int = 10
    filters: Dict[str, Any] = field(default_factory=dict)
    use_reranking: bool = True
    include_graph: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query": self.query,
            "sources": self.sources,
            "top_k": self.top_k,
            "filters": self.filters,
            "use_reranking": self.use_reranking,
            "include_graph": self.include_graph
        }


@dataclass
class ActionPlan:
    """
    Plan of actions created by Orchestrator.

    Attributes:
        intent: User's inferred intent
        actions: List of actions to perform
        action_sequence: Order of execution
        requires_confirmation: Whether plan needs user approval
        estimated_duration: Estimated time to complete (seconds)
        autonomy_level: Autonomy level for this plan
    """
    intent: str
    actions: List[ActionType]
    action_sequence: List[Dict[str, Any]]
    requires_confirmation: bool = False
    estimated_duration: Optional[int] = None
    autonomy_level: AutonomyLevel = AutonomyLevel.MODERATE

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "intent": self.intent,
            "actions": [action.value for action in self.actions],
            "action_sequence": self.action_sequence,
            "requires_confirmation": self.requires_confirmation,
            "estimated_duration": self.estimated_duration,
            "autonomy_level": self.autonomy_level.value
        }


@dataclass
class AgentCapability:
    """
    Describes what an agent can do.

    Used by agents to advertise their capabilities to the orchestrator.
    """
    agent_type: AgentType
    actions: List[ActionType]
    description: str
    requires_auth: bool = False
    estimated_latency_ms: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_type": self.agent_type.value,
            "actions": [action.value for action in self.actions],
            "description": self.description,
            "requires_auth": self.requires_auth,
            "estimated_latency_ms": self.estimated_latency_ms
        }


@dataclass
class ContextSnapshot:
    """
    Current context from Context Agent.

    Attributes:
        current_time: Current datetime
        upcoming_events: Calendar events in next 24h
        pending_emails: Emails requiring action
        workload_score: 0-100, how busy the user is
        available_time_blocks: Free time slots
        energy_level: User's estimated energy (from patterns)
    """
    current_time: datetime
    upcoming_events: List[Dict[str, Any]] = field(default_factory=list)
    pending_emails: List[Dict[str, Any]] = field(default_factory=list)
    workload_score: float = 50.0
    available_time_blocks: List[Dict[str, Any]] = field(default_factory=list)
    energy_level: str = "medium"  # low, medium, high

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "current_time": self.current_time.isoformat(),
            "upcoming_events": self.upcoming_events,
            "pending_emails": self.pending_emails,
            "workload_score": self.workload_score,
            "available_time_blocks": self.available_time_blocks,
            "energy_level": self.energy_level
        }


# Confirmation required for these actions at different autonomy levels
CONFIRMATION_RULES = {
    AutonomyLevel.CONSERVATIVE: [
        ActionType.SEARCH_DOCUMENTS,
        ActionType.SEARCH_EMAILS,
        ActionType.SEARCH_CALENDAR,
        ActionType.BROWSE_WEB,
        ActionType.EXECUTE_CODE,
        ActionType.SEND_EMAIL,
        ActionType.CREATE_CALENDAR_EVENT,
    ],
    AutonomyLevel.MODERATE: [
        ActionType.EXECUTE_CODE,
        ActionType.SEND_EMAIL,
        ActionType.CREATE_CALENDAR_EVENT,
    ],
    AutonomyLevel.AGGRESSIVE: [
        ActionType.EXECUTE_CODE,
        ActionType.SEND_EMAIL,  # Always confirm email sends
    ]
}


def requires_confirmation(action: ActionType, autonomy: AutonomyLevel) -> bool:
    """Check if an action requires user confirmation at given autonomy level."""
    return action in CONFIRMATION_RULES.get(autonomy, [])
