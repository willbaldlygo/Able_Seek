"""
Core package for Able2.
Contains configuration, database, and logging utilities.
"""

from .config import (
    settings,
    get_settings,
    get_config_loader,
    get_agent_config,
    get_integration_config,
    get_autonomy_config,
)

from .database import (
    engine,
    SessionLocal,
    Base,
    get_db,
    get_db_context,
    init_database,
    check_database_connection,
)

from .logger import (
    get_logger,
    orchestrator_logger,
    memory_logger,
    context_logger,
    execution_logger,
    api_logger,
    database_logger,
    retrieval_logger,
)

from .auth import (
    verify_api_key,
    optional_api_key,
    generate_api_key,
)

from .rate_limit import (
    limiter,
    setup_rate_limiting,
    limit_default,
    limit_chat,
    limit_upload,
    limit_custom,
)

from .request_logging import (
    setup_request_logging,
    log_security_event,
    log_auth_failure,
    log_rate_limit_hit,
    request_logger,
    security_logger,
)

__all__ = [
    # Config
    "settings",
    "get_settings",
    "get_config_loader",
    "get_agent_config",
    "get_integration_config",
    "get_autonomy_config",
    # Database
    "engine",
    "SessionLocal",
    "Base",
    "get_db",
    "get_db_context",
    "init_database",
    "check_database_connection",
    # Logging
    "get_logger",
    "orchestrator_logger",
    "memory_logger",
    "context_logger",
    "execution_logger",
    "api_logger",
    "database_logger",
    "retrieval_logger",
    # Auth
    "verify_api_key",
    "optional_api_key",
    "generate_api_key",
    # Rate Limiting
    "limiter",
    "setup_rate_limiting",
    "limit_default",
    "limit_chat",
    "limit_upload",
    "limit_custom",
    # Request Logging
    "setup_request_logging",
    "log_security_event",
    "log_auth_failure",
    "log_rate_limit_hit",
    "request_logger",
    "security_logger",
]
