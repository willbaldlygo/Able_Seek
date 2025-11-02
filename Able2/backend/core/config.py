"""
Configuration management for Able2.
Loads settings from config.yaml and environment variables.

This enhances the original Able1 config with:
- Agent configurations
- Database settings
- Integration settings
- Autonomy controls
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import BaseSettings, Field, validator
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings loaded from config.yaml and environment variables.
    Environment variables take precedence over config file.
    """

    # ========================================================================
    # LLM Settings (from Able1)
    # ========================================================================
    llm_provider: str = Field("anthropic", env="LLM_PROVIDER")
    llm_model: str = Field("claude-3-5-sonnet-20241022", env="LLM_MODEL")
    llm_temperature: float = Field(0.7, env="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(4000, env="LLM_MAX_TOKENS")

    # Anthropic
    anthropic_api_key: str = Field("", env="ANTHROPIC_API_KEY")

    # Ollama
    ollama_base_url: str = Field("http://localhost:11434", env="OLLAMA_BASE_URL")
    ollama_model: str = Field("llama3.2", env="OLLAMA_MODEL")
    ollama_embedding_model: str = Field("nomic-embed-text", env="OLLAMA_EMBEDDING_MODEL")

    # ========================================================================
    # Retrieval Settings (from Able1)
    # ========================================================================
    retrieval_top_k: int = Field(10, env="RETRIEVAL_TOP_K")
    retrieval_similarity_threshold: float = Field(0.7, env="RETRIEVAL_SIMILARITY_THRESHOLD")
    retrieval_chunk_size: int = Field(1000, env="RETRIEVAL_CHUNK_SIZE")
    retrieval_chunk_overlap: int = Field(200, env="RETRIEVAL_CHUNK_OVERLAP")
    retrieval_use_reranking: bool = Field(True, env="RETRIEVAL_USE_RERANKING")
    retrieval_bm25_weight: float = Field(0.3, env="RETRIEVAL_BM25_WEIGHT")
    retrieval_vector_weight: float = Field(0.7, env="RETRIEVAL_VECTOR_WEIGHT")

    # ========================================================================
    # GraphRAG Settings (from Able1)
    # ========================================================================
    graphrag_enabled: bool = Field(True, env="GRAPHRAG_ENABLED")
    graphrag_community_levels: int = Field(3, env="GRAPHRAG_COMMUNITY_LEVELS")
    graphrag_max_tokens: int = Field(8000, env="GRAPHRAG_MAX_TOKENS")

    # ========================================================================
    # Agent Settings (NEW in Able2)
    # ========================================================================
    agents_enabled: bool = Field(True, env="AGENTS_ENABLED")

    # Orchestrator
    orchestrator_model: str = Field("claude-3-5-sonnet-20241022", env="ORCHESTRATOR_MODEL")
    orchestrator_provider: str = Field("anthropic", env="ORCHESTRATOR_PROVIDER")
    orchestrator_temperature: float = Field(0.7, env="ORCHESTRATOR_TEMPERATURE")

    # Memory Agent
    memory_agent_model: str = Field("llama3.2", env="MEMORY_AGENT_MODEL")
    memory_agent_provider: str = Field("ollama", env="MEMORY_AGENT_PROVIDER")
    memory_agent_temperature: float = Field(0.3, env="MEMORY_AGENT_TEMPERATURE")

    # Context Agent
    context_agent_model: str = Field("llama3.2", env="CONTEXT_AGENT_MODEL")
    context_agent_provider: str = Field("ollama", env="CONTEXT_AGENT_PROVIDER")

    # Execution Agent
    execution_agent_model: str = Field("claude-3-5-sonnet-20241022", env="EXECUTION_AGENT_MODEL")
    execution_agent_provider: str = Field("anthropic", env="EXECUTION_AGENT_PROVIDER")

    # ========================================================================
    # Autonomy Settings (NEW in Able2)
    # ========================================================================
    autonomy_default_level: str = Field("moderate", env="AUTONOMY_DEFAULT_LEVEL")

    # ========================================================================
    # Database Settings (NEW in Able2)
    # ========================================================================
    database_url: str = Field(
        "postgresql://able2:able2password@localhost:5432/able2",
        env="DATABASE_URL"
    )
    database_pool_size: int = Field(10, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(20, env="DATABASE_MAX_OVERFLOW")

    redis_url: str = Field("redis://localhost:6379/0", env="REDIS_URL")
    redis_ttl: int = Field(3600, env="REDIS_TTL")

    # ========================================================================
    # Integration Settings (NEW in Able2)
    # ========================================================================
    gmail_enabled: bool = Field(False, env="GMAIL_ENABLED")
    gmail_credentials_path: str = Field("./config/gmail_credentials.json", env="GMAIL_CREDENTIALS_PATH")
    gmail_token_path: str = Field("./config/gmail_token.json", env="GMAIL_TOKEN_PATH")

    calendar_enabled: bool = Field(False, env="CALENDAR_ENABLED")
    calendar_credentials_path: str = Field("./config/calendar_credentials.json", env="CALENDAR_CREDENTIALS_PATH")
    calendar_token_path: str = Field("./config/calendar_token.json", env="CALENDAR_TOKEN_PATH")

    searxng_enabled: bool = Field(True, env="SEARXNG_ENABLED")
    searxng_url: str = Field("http://localhost:8080", env="SEARXNG_URL")

    # ========================================================================
    # File Paths (from Able1)
    # ========================================================================
    path_vector_store: str = Field("./Able2/data/vector_store", env="PATH_VECTOR_STORE")
    path_graph_store: str = Field("./Able2/data/graph_store", env="PATH_GRAPH_STORE")
    path_uploads: str = Field("./Able2/data/uploads", env="PATH_UPLOADS")
    path_logs: str = Field("./Able2/logs", env="PATH_LOGS")
    path_temp: str = Field("./Able2/temp", env="PATH_TEMP")

    # ========================================================================
    # API Settings
    # ========================================================================
    api_host: str = Field("0.0.0.0", env="API_HOST")
    api_port: int = Field(8000, env="API_PORT")
    api_reload: bool = Field(True, env="API_RELOAD")

    cors_origins: List[str] = Field(
        ["http://localhost:3001", "http://127.0.0.1:3001"],
        env="CORS_ORIGINS"
    )

    # ========================================================================
    # Logging Settings
    # ========================================================================
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_to_file: bool = Field(True, env="LOG_TO_FILE")
    log_file_path: str = Field("./Able2/logs/able2.log", env="LOG_FILE_PATH")

    # ========================================================================
    # Feature Flags
    # ========================================================================
    feature_multi_agent: bool = Field(True, env="FEATURE_MULTI_AGENT")
    feature_gmail: bool = Field(False, env="FEATURE_GMAIL")
    feature_calendar: bool = Field(False, env="FEATURE_CALENDAR")
    feature_web_browsing: bool = Field(False, env="FEATURE_WEB_BROWSING")
    feature_code_execution: bool = Field(False, env="FEATURE_CODE_EXECUTION")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @validator("autonomy_default_level")
    def validate_autonomy_level(cls, v):
        """Validate autonomy level."""
        valid_levels = ["conservative", "moderate", "aggressive"]
        if v not in valid_levels:
            raise ValueError(f"autonomy_default_level must be one of {valid_levels}")
        return v

    @validator("llm_provider", "orchestrator_provider", "memory_agent_provider")
    def validate_provider(cls, v):
        """Validate LLM provider."""
        valid_providers = ["anthropic", "ollama"]
        if v not in valid_providers:
            raise ValueError(f"provider must be one of {valid_providers}")
        return v

    def get_model_config(self, agent_type: str = "orchestrator") -> Dict[str, Any]:
        """
        Get model configuration for a specific agent.

        Args:
            agent_type: orchestrator, memory, context, execution, or default

        Returns:
            Dict with provider, model, temperature, api_key
        """
        if agent_type == "orchestrator":
            provider = self.orchestrator_provider
            model = self.orchestrator_model
            temperature = self.orchestrator_temperature
        elif agent_type == "memory":
            provider = self.memory_agent_provider
            model = self.memory_agent_model
            temperature = self.memory_agent_temperature
        elif agent_type == "context":
            provider = self.context_agent_provider
            model = self.context_agent_model
            temperature = 0.5
        elif agent_type == "execution":
            provider = self.execution_agent_provider
            model = self.execution_agent_model
            temperature = 0.5
        else:
            # Default to main LLM config
            provider = self.llm_provider
            model = self.llm_model
            temperature = self.llm_temperature

        config = {
            "provider": provider,
            "model": model,
            "temperature": temperature,
        }

        # Add API key or base URL based on provider
        if provider == "anthropic":
            config["api_key"] = self.anthropic_api_key
        elif provider == "ollama":
            config["base_url"] = self.ollama_base_url

        return config

    def ensure_directories(self):
        """Create necessary directories if they don't exist."""
        directories = [
            self.path_vector_store,
            self.path_graph_store,
            self.path_uploads,
            self.path_logs,
            self.path_temp,
        ]

        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)


class ConfigLoader:
    """Load configuration from YAML file and merge with environment variables."""

    def __init__(self, config_path: str = "./Able2/config/config.yaml"):
        self.config_path = config_path
        self.yaml_config = self._load_yaml()

    def _load_yaml(self) -> Dict[str, Any]:
        """Load YAML configuration file."""
        config_path = Path(self.config_path)

        if not config_path.exists():
            print(f"Warning: Config file not found at {config_path}, using defaults")
            return {}

        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        return config or {}

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get value from config using dot notation.

        Example:
            config.get("llm.provider") -> "anthropic"
            config.get("agents.orchestrator.model") -> "claude-3-5-sonnet-20241022"
        """
        keys = key_path.split(".")
        value = self.yaml_config

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default

            if value is None:
                return default

        return value

    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section."""
        return self.yaml_config.get(section, {})


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    This is called by FastAPI dependency injection.
    """
    settings = Settings()
    settings.ensure_directories()
    return settings


@lru_cache()
def get_config_loader() -> ConfigLoader:
    """Get cached config loader instance."""
    return ConfigLoader()


# Global instances (for convenience)
settings = get_settings()
config_loader = get_config_loader()


def get_agent_config(agent_type: str) -> Dict[str, Any]:
    """
    Get full configuration for an agent including YAML settings.

    Args:
        agent_type: orchestrator, memory, context, execution

    Returns:
        Dict with all agent configuration
    """
    yaml_config = config_loader.get_section("agents").get(agent_type, {})
    model_config = settings.get_model_config(agent_type)

    # Merge YAML and Settings
    return {**yaml_config, **model_config}


def get_integration_config(integration: str) -> Dict[str, Any]:
    """
    Get configuration for an integration.

    Args:
        integration: gmail, calendar, searxng, etc.

    Returns:
        Dict with integration configuration
    """
    return config_loader.get_section("integrations").get(integration, {})


def get_autonomy_config() -> Dict[str, Any]:
    """Get autonomy configuration."""
    return config_loader.get_section("autonomy")


# Export commonly used functions
__all__ = [
    "Settings",
    "ConfigLoader",
    "get_settings",
    "get_config_loader",
    "get_agent_config",
    "get_integration_config",
    "get_autonomy_config",
    "settings",
    "config_loader",
]
