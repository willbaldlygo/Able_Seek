"""
Logging configuration for Able2.
Provides structured logging for agents, API, and system events.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional
from datetime import datetime

from .config import settings


class AgentLogger:
    """
    Custom logger for agent actions.
    Logs to both file and console with structured format.
    """

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, settings.log_level))

        # Avoid duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers()

    def _setup_handlers(self):
        """Setup console and file handlers."""
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # File handler (if enabled)
        if settings.log_to_file:
            log_path = Path(settings.log_file_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=10485760,  # 10MB
                backupCount=5
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def info(self, message: str, **kwargs):
        """Log info message with optional context."""
        self.logger.info(message, extra=kwargs)

    def debug(self, message: str, **kwargs):
        """Log debug message with optional context."""
        self.logger.debug(message, extra=kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message with optional context."""
        self.logger.warning(message, extra=kwargs)

    def error(self, message: str, **kwargs):
        """Log error message with optional context."""
        self.logger.error(message, extra=kwargs)

    def agent_action(
        self,
        agent_type: str,
        action_type: str,
        success: bool,
        details: Optional[str] = None
    ):
        """
        Log an agent action in structured format.

        Args:
            agent_type: Type of agent
            action_type: Action performed
            success: Whether action succeeded
            details: Optional details
        """
        status = "SUCCESS" if success else "FAILED"
        message = f"[{agent_type}] {action_type} - {status}"
        if details:
            message += f" - {details}"

        if success:
            self.info(message)
        else:
            self.error(message)


def get_logger(name: str) -> AgentLogger:
    """
    Get a logger instance for a specific component.

    Args:
        name: Logger name (e.g., "orchestrator", "memory_agent", "api")

    Returns:
        AgentLogger instance
    """
    return AgentLogger(name)


# Pre-configured loggers for common components
orchestrator_logger = get_logger("orchestrator")
memory_logger = get_logger("memory_agent")
context_logger = get_logger("context_agent")
execution_logger = get_logger("execution_agent")
api_logger = get_logger("api")
database_logger = get_logger("database")
retrieval_logger = get_logger("retrieval")
request_logger = get_logger("request")
security_logger = get_logger("security")


__all__ = [
    "AgentLogger",
    "get_logger",
    "orchestrator_logger",
    "memory_logger",
    "context_logger",
    "execution_logger",
    "api_logger",
    "database_logger",
    "retrieval_logger",
    "request_logger",
    "security_logger",
]
