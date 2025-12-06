"""
API request/response schemas for Able2.
Pydantic models for FastAPI endpoints.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================================================
# Chat Schemas
# ============================================================================

class ChatRequestV2(BaseModel):
    """Request schema for /chat/v2 (orchestrator-based chat)."""
    message: str = Field(
        ...,
        description="User's message/query",
        min_length=1,
        max_length=50000  # Reasonable limit to prevent abuse
    )
    session_id: Optional[str] = Field(
        None,
        description="Chat session ID (UUID format)",
        max_length=36,
        pattern=r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$|^$'
    )
    autonomy_level: str = Field("moderate", description="conservative, moderate, or aggressive")
    sources: Optional[List[str]] = Field(
        default=["documents"],
        description="Sources to search: documents, emails, calendar",
        max_items=10
    )
    context: Optional[Dict[str, Any]] = Field(
        default={},
        description="Additional context from UI"
    )

    @validator("autonomy_level")
    def validate_autonomy(cls, v):
        """Validate autonomy level."""
        valid_levels = ["conservative", "moderate", "aggressive"]
        if v not in valid_levels:
            raise ValueError(f"autonomy_level must be one of {valid_levels}")
        return v

    @validator("sources")
    def validate_sources(cls, v):
        """Validate source list."""
        if v is None:
            return ["documents"]
        valid_sources = {"documents", "emails", "calendar"}
        for source in v:
            if source not in valid_sources:
                raise ValueError(f"Invalid source: {source}. Valid sources: {valid_sources}")
        return v


class ChatResponseV2(BaseModel):
    """Response schema for /chat/v2."""
    success: bool
    message: str
    reasoning: Optional[str] = None
    sources: Optional[List[Dict[str, Any]]] = None
    requires_confirmation: bool = False
    suggested_actions: Optional[List[str]] = None
    session_id: str
    agent_actions: Optional[List[Dict[str, Any]]] = None


class ChatRequestEnhanced(BaseModel):
    """Request schema for /chat/enhanced (legacy Able1 endpoint)."""
    message: str = Field(..., min_length=1, max_length=50000)
    session_id: Optional[str] = Field(None, max_length=36)
    use_graph: bool = True
    top_k: int = Field(10, ge=1, le=100, description="Number of results (1-100)")


class ChatResponseEnhanced(BaseModel):
    """Response schema for /chat/enhanced."""
    response: str
    sources: List[Dict[str, Any]]
    session_id: str


# ============================================================================
# Document Schemas
# ============================================================================

class DocumentUploadResponse(BaseModel):
    """Response after document upload."""
    success: bool
    document_id: str
    filename: str
    num_chunks: int
    message: str


class DocumentListResponse(BaseModel):
    """Response for listing documents."""
    documents: List[Dict[str, Any]]
    total_count: int


class DocumentDetailResponse(BaseModel):
    """Response for document details."""
    document_id: str
    filename: str
    upload_date: datetime
    file_size: int
    num_chunks: int
    metadata: Dict[str, Any]


# ============================================================================
# Model Management Schemas
# ============================================================================

class ModelInfo(BaseModel):
    """Information about an available model."""
    model_id: str
    provider: str  # anthropic, ollama
    display_name: str
    description: Optional[str] = None
    context_window: int
    is_active: bool


class ModelListResponse(BaseModel):
    """Response for listing available models."""
    models: List[ModelInfo]
    active_model: str


class ModelSwitchRequest(BaseModel):
    """Request to switch active model."""
    provider: str = Field(..., description="anthropic or ollama")
    model_id: str = Field(..., description="Model identifier")

    @validator("provider")
    def validate_provider(cls, v):
        """Validate provider."""
        valid_providers = ["anthropic", "ollama"]
        if v not in valid_providers:
            raise ValueError(f"provider must be one of {valid_providers}")
        return v


class ModelSwitchResponse(BaseModel):
    """Response after switching model."""
    success: bool
    message: str
    active_model: str


# ============================================================================
# Graph RAG Schemas
# ============================================================================

class GraphBuildRequest(BaseModel):
    """Request to build knowledge graph."""
    document_ids: Optional[List[str]] = Field(
        None,
        description="Specific documents to build graph from. None = all documents"
    )
    community_levels: int = Field(3, description="Number of community hierarchy levels")
    force_rebuild: bool = Field(False, description="Rebuild even if graph exists")


class GraphBuildResponse(BaseModel):
    """Response after building graph."""
    success: bool
    message: str
    num_entities: int
    num_relationships: int
    num_communities: int
    build_time_seconds: float


class GraphQueryRequest(BaseModel):
    """Request to query knowledge graph."""
    query: str = Field(..., description="Natural language query", min_length=1, max_length=10000)
    community_level: Optional[int] = Field(
        None,
        description="Specific community level to query. None = use best level",
        ge=0,
        le=10
    )
    max_tokens: int = Field(1000, description="Max tokens for graph summary", ge=1, le=8000)


class GraphQueryResponse(BaseModel):
    """Response from graph query."""
    answer: str
    community_summaries: List[Dict[str, Any]]
    entities_found: List[str]
    relationships_found: List[Dict[str, Any]]


# ============================================================================
# Agent-specific Schemas
# ============================================================================

class MemorySearchRequest(BaseModel):
    """Direct request to Memory Agent."""
    query: str = Field(..., min_length=1, max_length=10000)
    sources: List[str] = Field(default=["documents"], max_items=10)
    top_k: int = Field(10, ge=1, le=100)
    use_reranking: bool = True
    include_graph: bool = True
    filters: Optional[Dict[str, Any]] = Field(None, description="Search filters")


class MemorySearchResponse(BaseModel):
    """Response from Memory Agent search."""
    success: bool
    results: List[Dict[str, Any]]
    total_found: int
    sources_searched: List[str]
    reasoning: Optional[str] = None


class ContextRequest(BaseModel):
    """Request current context from Context Agent."""
    include_calendar: bool = True
    include_emails: bool = True
    time_horizon_hours: int = Field(24, description="Look ahead this many hours")


class ContextResponse(BaseModel):
    """Response from Context Agent."""
    success: bool
    current_time: datetime
    upcoming_events: List[Dict[str, Any]]
    pending_emails: List[Dict[str, Any]]
    workload_score: float
    available_time_blocks: List[Dict[str, Any]]
    energy_level: str


class ExecutionRequest(BaseModel):
    """Request to Execution Agent."""
    action_type: str  # browse_web, execute_code, etc.
    parameters: Dict[str, Any]
    requires_confirmation: bool = True


class ExecutionResponse(BaseModel):
    """Response from Execution Agent."""
    success: bool
    action_type: str
    result: Any
    reasoning: str
    error: Optional[str] = None


# ============================================================================
# Session Management Schemas
# ============================================================================

class SessionCreateRequest(BaseModel):
    """Request to create new chat session."""
    user_id: Optional[int] = None
    title: Optional[str] = None
    autonomy_level: str = "moderate"


class SessionCreateResponse(BaseModel):
    """Response after creating session."""
    session_id: str
    created_at: datetime


class SessionListResponse(BaseModel):
    """Response for listing sessions."""
    sessions: List[Dict[str, Any]]
    total_count: int


# ============================================================================
# Task Management Schemas (ADHD Support)
# ============================================================================

class TaskCreateRequest(BaseModel):
    """Request to create a task."""
    title: str
    description: Optional[str] = None
    priority: int = Field(3, ge=1, le=5, description="1=lowest, 5=highest")
    estimated_duration: Optional[int] = Field(None, description="Estimated minutes")
    energy_level: str = Field("medium", description="low, medium, high")
    deadline: Optional[datetime] = None


class TaskCreateResponse(BaseModel):
    """Response after creating task."""
    success: bool
    task_id: int
    suggested_time_blocks: Optional[List[Dict[str, Any]]] = None


class TaskListRequest(BaseModel):
    """Request to list tasks."""
    completed: Optional[bool] = None
    priority_min: Optional[int] = None
    due_before: Optional[datetime] = None


class TaskListResponse(BaseModel):
    """Response for listing tasks."""
    tasks: List[Dict[str, Any]]
    total_count: int


# ============================================================================
# Integration Schemas (Gmail, Calendar)
# ============================================================================

class IntegrationStatus(BaseModel):
    """Status of an integration."""
    name: str  # gmail, calendar
    enabled: bool
    authenticated: bool
    last_sync: Optional[datetime] = None
    error: Optional[str] = None


class IntegrationStatusResponse(BaseModel):
    """Response for integration status."""
    integrations: List[IntegrationStatus]


class OAuthCallbackRequest(BaseModel):
    """OAuth callback data."""
    code: str
    state: str
    integration: str  # gmail or calendar


# ============================================================================
# Error Response
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response."""
    success: bool = False
    error: str
    error_type: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


# ============================================================================
# Health Check
# ============================================================================

class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str  # ok, degraded, error
    version: str
    services: Dict[str, str]  # service_name -> status
    timestamp: datetime
