"""
Main FastAPI application for Able2.

Combines Able mk I endpoints with new agent-based endpoints.
"""

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import uuid
import os
import re
from pathlib import Path
from datetime import datetime

# Security constants
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'.pdf', '.txt', '.md', '.markdown', '.docx', '.doc'}

from backend.core import (
    settings, api_logger, init_database,
    check_database_connection, get_db, verify_api_key,
    setup_rate_limiting, limiter, limit_chat, limit_upload, limit_default
)
from backend.schemas import (
    ChatRequestV2, ChatResponseV2,
    ChatRequestEnhanced, ChatResponseEnhanced,
    DocumentUploadResponse, DocumentListResponse,
    ModelInfo, ModelListResponse, ModelSwitchRequest, ModelSwitchResponse,
    GraphBuildRequest, GraphBuildResponse,
    GraphQueryRequest, GraphQueryResponse,
    ErrorResponse, HealthCheckResponse,
    AgentType, AgentMessage, AutonomyLevel
)
from backend.agents import OrchestratorAgent, MemoryAgent
from backend.knowledge import get_hybrid_retriever
from backend.models import get_or_create_default_user, Session as ChatSession, AgentAction

# Create FastAPI app
app = FastAPI(
    title="Able2 API",
    description="Multi-agent AI assistant with advanced retrieval",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup rate limiting
setup_rate_limiting(app)

# Initialize components on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database and check connections."""
    api_logger.info("Starting Able2 API...")

    # Initialize database
    try:
        init_database()
        api_logger.info("Database initialized")
    except Exception as e:
        api_logger.error(f"Database initialization failed: {str(e)}")

    # Check database connection
    if check_database_connection():
        api_logger.info("Database connection OK")
    else:
        api_logger.warning("Database connection failed")

    # Log authentication status
    if settings.api_key_enabled:
        if settings.api_key:
            api_logger.info("API key authentication ENABLED")
        else:
            api_logger.warning(
                "API key authentication enabled but NO KEY SET! "
                "Set ABLE2_API_KEY environment variable."
            )
    else:
        api_logger.warning("API key authentication DISABLED - endpoints are unprotected!")

    api_logger.info("Able2 API started successfully")


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint."""
    db_ok = check_database_connection()

    status = "ok" if db_ok else "degraded"

    return HealthCheckResponse(
        status=status,
        version="2.0.0",
        services={
            "database": "ok" if db_ok else "error",
            "vector_store": "ok",
            "agents": "ok"
        },
        timestamp=datetime.now()
    )


# ============================================================================
# NEW: Agent-based Chat (v2)
# ============================================================================

@app.post("/chat/v2", response_model=ChatResponseV2)
@limiter.limit(f"{settings.rate_limit_chat_per_minute}/minute")
async def chat_v2(
    request: Request,
    chat_request: ChatRequestV2,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    NEW orchestrator-based chat endpoint.

    This is the recommended endpoint for Able2.
    Routes through the agent system for intelligent orchestration.
    """
    api_logger.info(f"Chat v2: '{chat_request.message[:50]}...'")

    try:
        # Get or create user
        user = get_or_create_default_user(db)

        # Get or create session
        if chat_request.session_id:
            session = db.query(ChatSession).filter(
                ChatSession.session_id == chat_request.session_id
            ).first()

            if not session:
                session = ChatSession(
                    session_id=chat_request.session_id,
                    user_id=user.id,
                    autonomy_level=chat_request.autonomy_level
                )
                db.add(session)
                db.commit()
        else:
            # Create new session
            session_id = str(uuid.uuid4())
            session = ChatSession(
                session_id=session_id,
                user_id=user.id,
                autonomy_level=chat_request.autonomy_level,
                title=chat_request.message[:50]
            )
            db.add(session)
            db.commit()

        # Create orchestrator
        autonomy = AutonomyLevel(chat_request.autonomy_level)
        orchestrator = OrchestratorAgent(autonomy_level=autonomy)

        # Create agent message
        message = AgentMessage(
            from_agent=AgentType.USER,
            to_agent=AgentType.ORCHESTRATOR,
            content=chat_request.message,
            metadata={
                "sources": chat_request.sources,
                "context": chat_request.context
            }
        )

        # Process through orchestrator
        response = await orchestrator.process(message)

        # Log agent action
        action = AgentAction(
            session_id=session.id,
            agent_type=AgentType.ORCHESTRATOR.value,
            action_type="orchestrate",
            input_data={"message": chat_request.message},
            output_data=response.data,
            reasoning=response.reasoning,
            success=response.success
        )
        db.add(action)
        db.commit()

        # Update session
        session.message_count += 1
        session.updated_at = datetime.now()
        db.commit()

        # Format response
        return ChatResponseV2(
            success=response.success,
            message=response.data.get("message", ""),
            reasoning=response.reasoning,
            sources=response.data.get("sources"),
            requires_confirmation=response.requires_confirmation,
            suggested_actions=[response.next_action] if response.next_action else None,
            session_id=session.session_id,
            agent_actions=[{
                "agent": response.agent_type.value,
                "success": response.success,
                "reasoning": response.reasoning
            }]
        )

    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        api_logger.error(f"Chat v2 failed: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred processing your request")


# ============================================================================
# Legacy: Able1 Chat Endpoints (Preserved for compatibility)
# ============================================================================

@app.post("/chat/enhanced", response_model=ChatResponseEnhanced)
@limiter.limit(f"{settings.rate_limit_chat_per_minute}/minute")
async def chat_enhanced(
    request: Request,
    chat_request: ChatRequestEnhanced,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Legacy Able1 enhanced chat endpoint.
    Uses hybrid retrieval directly without agent orchestration.

    Preserved for backward compatibility.
    """
    api_logger.info(f"Chat enhanced (legacy): '{chat_request.message[:50]}...'")

    try:
        # Get hybrid retriever
        retriever = get_hybrid_retriever()

        # Search
        results = await retriever.search(
            query=chat_request.message,
            top_k=chat_request.top_k,
            use_reranking=True,
            include_graph=chat_request.use_graph
        )

        # Create simple response (no LLM synthesis in legacy mode)
        if results:
            response_text = f"Found {len(results)} relevant sources."
        else:
            response_text = "No relevant sources found."

        # Get or create session
        session_id = chat_request.session_id or str(uuid.uuid4())

        return ChatResponseEnhanced(
            response=response_text,
            sources=results,
            session_id=session_id
        )

    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        api_logger.error(f"Chat enhanced failed: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred processing your request")


# ============================================================================
# Document Management
# ============================================================================

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal and other attacks."""
    # Get just the basename (removes any directory components)
    filename = os.path.basename(filename)
    # Remove any null bytes
    filename = filename.replace('\x00', '')
    # Remove or replace dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255 - len(ext)] + ext
    return filename


def validate_file_extension(filename: str) -> bool:
    """Check if file extension is allowed."""
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_EXTENSIONS


@app.post("/upload", response_model=DocumentUploadResponse)
@limiter.limit(f"{settings.rate_limit_upload_per_minute}/minute")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    api_key: str = Depends(verify_api_key)
):
    """
    Upload a document for processing.

    Supports PDF and text files.
    """
    # Sanitize filename for logging (don't log raw user input)
    safe_display_name = sanitize_filename(file.filename or "unknown")
    api_logger.info(f"Upload request: {safe_display_name}")

    try:
        # Validate file extension
        if not validate_file_extension(file.filename or ""):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        # Read content and check size
        content = await file.read()
        if len(content) > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {MAX_UPLOAD_SIZE // (1024*1024)}MB"
            )

        # Generate secure filename with UUID to prevent collisions and path traversal
        original_ext = Path(file.filename or ".txt").suffix.lower()
        secure_filename = f"{uuid.uuid4()}{original_ext}"

        # Save uploaded file
        upload_dir = Path(settings.path_uploads)
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_path = upload_dir / secure_filename

        # Verify the resolved path is still within upload_dir (defense in depth)
        if not file_path.resolve().is_relative_to(upload_dir.resolve()):
            raise HTTPException(status_code=400, detail="Invalid file path")

        with open(file_path, "wb") as f:
            f.write(content)

        # Process document through Memory Agent
        memory_agent = MemoryAgent()
        response = await memory_agent.add_document(str(file_path))

        if response.success:
            return DocumentUploadResponse(
                success=True,
                document_id=response.data["document_id"],
                filename=safe_display_name,  # Return sanitized original name
                num_chunks=response.data["num_chunks"],
                message="Document uploaded and processed successfully"
            )
        else:
            # Don't expose internal error details
            api_logger.error(f"Document processing failed: {response.error}")
            raise HTTPException(status_code=500, detail="Document processing failed")

    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        api_logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred during upload")


@app.get("/documents", response_model=DocumentListResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def list_documents(request: Request, api_key: str = Depends(verify_api_key)):
    """List all uploaded documents."""
    try:
        retriever = get_hybrid_retriever()
        stats = retriever.get_statistics()

        # For Phase 1, return statistics
        # Full document listing in later phase
        return DocumentListResponse(
            documents=[],
            total_count=stats.get("vector_store", {}).get("document_count", 0)
        )

    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        api_logger.error(f"List documents failed: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred listing documents")


@app.delete("/documents/{document_id}")
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def delete_document(request: Request, document_id: str, api_key: str = Depends(verify_api_key)):
    """Delete a document."""
    try:
        memory_agent = MemoryAgent()
        response = await memory_agent.delete_document(document_id)

        if response.success:
            return {"success": True, "message": "Document deleted"}
        else:
            api_logger.error(f"Delete document failed: {response.error}")
            raise HTTPException(status_code=500, detail="Failed to delete document")

    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        api_logger.error(f"Delete document failed: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred deleting the document")


# ============================================================================
# Model Management
# ============================================================================

@app.get("/models", response_model=ModelListResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def list_models(request: Request, api_key: str = Depends(verify_api_key)):
    """List available LLM models."""
    models = [
        ModelInfo(
            model_id="claude-3-5-sonnet-20241022",
            provider="anthropic",
            display_name="Claude 3.5 Sonnet",
            description="Most capable model",
            context_window=200000,
            is_active=settings.llm_provider == "anthropic"
        ),
        ModelInfo(
            model_id="llama3.2",
            provider="ollama",
            display_name="Llama 3.2",
            description="Fast local model",
            context_window=8192,
            is_active=settings.llm_provider == "ollama"
        )
    ]

    active_model = f"{settings.llm_provider}/{settings.llm_model}"

    return ModelListResponse(
        models=models,
        active_model=active_model
    )


@app.post("/models/switch", response_model=ModelSwitchResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def switch_model(request: Request, switch_request: ModelSwitchRequest, api_key: str = Depends(verify_api_key)):
    """Switch active LLM model."""
    # In Phase 1, this is informational only
    # Full switching requires runtime config updates

    return ModelSwitchResponse(
        success=True,
        message=f"Model switch noted (restart required for Phase 1)",
        active_model=f"{switch_request.provider}/{switch_request.model_id}"
    )


# ============================================================================
# GraphRAG
# ============================================================================

@app.post("/graph/build", response_model=GraphBuildResponse)
@limiter.limit(f"{settings.rate_limit_upload_per_minute}/minute")  # Resource intensive
async def build_graph(request: Request, build_request: GraphBuildRequest, api_key: str = Depends(verify_api_key)):
    """Build or rebuild knowledge graph."""
    try:
        memory_agent = MemoryAgent()

        message = AgentMessage(
            from_agent=AgentType.USER,
            to_agent=AgentType.MEMORY,
            content="build_graph",
            metadata={
                "action_type": "build_graph",
                "force_rebuild": build_request.force_rebuild
            }
        )

        response = await memory_agent.process(message)

        if response.success:
            stats = response.data

            return GraphBuildResponse(
                success=True,
                message="Graph built successfully",
                num_entities=stats.get("num_entities", 0),
                num_relationships=stats.get("num_relationships", 0),
                num_communities=stats.get("num_communities", 0),
                build_time_seconds=0.0  # Not tracked in Phase 1
            )
        else:
            api_logger.error(f"Graph build failed: {response.error}")
            raise HTTPException(status_code=500, detail="Failed to build knowledge graph")

    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        api_logger.error(f"Graph build failed: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred building the graph")


@app.post("/graph/query", response_model=GraphQueryResponse)
@limiter.limit(f"{settings.rate_limit_chat_per_minute}/minute")  # Similar to chat
async def query_graph(request: Request, query_request: GraphQueryRequest, api_key: str = Depends(verify_api_key)):
    """Query knowledge graph."""
    try:
        memory_agent = MemoryAgent()

        message = AgentMessage(
            from_agent=AgentType.USER,
            to_agent=AgentType.MEMORY,
            content=query_request.query,
            metadata={
                "action_type": "query_graph",
                "max_tokens": query_request.max_tokens
            }
        )

        response = await memory_agent.process(message)

        if response.success:
            return GraphQueryResponse(**response.data)
        else:
            api_logger.error(f"Graph query failed: {response.error}")
            raise HTTPException(status_code=500, detail="Failed to query knowledge graph")

    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        api_logger.error(f"Graph query failed: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred querying the graph")


# ============================================================================
# Info Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Able2 API",
        "version": "2.0.0",
        "description": "Multi-agent AI assistant",
        "authentication": {
            "enabled": settings.api_key_enabled,
            "method": "API Key (X-API-Key header or api_key query param)",
            "public_endpoints": ["/", "/health"]
        },
        "rate_limiting": {
            "enabled": settings.rate_limit_enabled,
            "default": f"{settings.rate_limit_per_minute}/minute",
            "chat": f"{settings.rate_limit_chat_per_minute}/minute",
            "upload": f"{settings.rate_limit_upload_per_minute}/minute"
        },
        "endpoints": {
            "chat": "/chat/v2 (recommended), /chat/enhanced (legacy)",
            "documents": "/upload, /documents, /documents/{id}",
            "models": "/models, /models/switch",
            "graph": "/graph/build, /graph/query",
            "health": "/health"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload
    )
