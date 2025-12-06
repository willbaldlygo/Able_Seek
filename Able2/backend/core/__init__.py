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
]
