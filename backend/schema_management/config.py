"""
Configuration models for MCP schema management.
"""

import os
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


@dataclass
class MCPSchemaConfig:
    """Configuration for MCP schema operations."""
    
    mcp_server_url: str
    connection_timeout: int = 30
    request_timeout: int = 60
    max_retries: int = 3
    retry_delay: float = 1.0
    cache_ttl: int = 300  # 5 minutes
    enable_caching: bool = True
    fallback_enabled: bool = True
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """Validate configuration parameters."""
        # Validate MCP server URL
        if not self.mcp_server_url:
            raise ValueError("MCP server URL is required")
        
        try:
            parsed_url = urlparse(self.mcp_server_url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ValueError(f"Invalid MCP server URL format: {self.mcp_server_url}")
        except Exception as e:
            raise ValueError(f"Invalid MCP server URL: {e}")
        
        # Validate timeout values
        if self.connection_timeout <= 0:
            raise ValueError("Connection timeout must be positive")
        if self.request_timeout <= 0:
            raise ValueError("Request timeout must be positive")
        if self.connection_timeout >= self.request_timeout:
            logger.warning("Connection timeout should be less than request timeout")
        
        # Validate retry configuration
        if self.max_retries < 0:
            raise ValueError("Max retries cannot be negative")
        if self.retry_delay < 0:
            raise ValueError("Retry delay cannot be negative")
        
        # Validate cache configuration
        if self.cache_ttl <= 0:
            raise ValueError("Cache TTL must be positive")
        
        logger.info(f"MCP schema configuration validated: {self.mcp_server_url}")
    
    @classmethod
    def from_env(cls) -> "MCPSchemaConfig":
        """Create configuration from environment variables."""
        try:
            config = cls(
                mcp_server_url=os.getenv(
                    "TIDB_MCP_SERVER_URL", 
                    "http://tidb-mcp-server:8000"
                ),
                connection_timeout=int(os.getenv("MCP_CONNECTION_TIMEOUT", "30")),
                request_timeout=int(os.getenv("MCP_REQUEST_TIMEOUT", "60")),
                max_retries=int(os.getenv("MCP_MAX_RETRIES", "3")),
                retry_delay=float(os.getenv("MCP_RETRY_DELAY", "1.0")),
                cache_ttl=int(os.getenv("MCP_CACHE_TTL", "300")),
                enable_caching=os.getenv("MCP_ENABLE_CACHING", "true").lower() == "true",
                fallback_enabled=os.getenv("MCP_FALLBACK_ENABLED", "true").lower() == "true"
            )
            return config
        except (ValueError, TypeError) as e:
            logger.error(f"Failed to create MCP schema configuration from environment: {e}")
            raise ValueError(f"Invalid MCP schema configuration: {e}")
    
    def get_health_check_url(self) -> str:
        """Get the health check URL for the MCP server."""
        base_url = self.mcp_server_url.rstrip('/')
        return f"{base_url}/health"


@dataclass
class SchemaValidationConfig:
    """Configuration for schema validation behavior."""
    
    strict_mode: bool = False
    validate_types: bool = True
    validate_constraints: bool = True
    validate_relationships: bool = True
    allow_unknown_columns: bool = False
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """Validate schema validation configuration."""
        # Log configuration for debugging
        logger.info(f"Schema validation config - strict_mode: {self.strict_mode}, "
                   f"validate_types: {self.validate_types}, "
                   f"validate_constraints: {self.validate_constraints}, "
                   f"validate_relationships: {self.validate_relationships}, "
                   f"allow_unknown_columns: {self.allow_unknown_columns}")
        
        # Warn about potentially problematic configurations
        if self.strict_mode and self.allow_unknown_columns:
            logger.warning("Strict mode enabled with allow_unknown_columns=True may cause conflicts")
        
        if not any([self.validate_types, self.validate_constraints, self.validate_relationships]):
            logger.warning("All validation types are disabled - validation will be minimal")
    
    @classmethod
    def from_env(cls) -> "SchemaValidationConfig":
        """Create validation configuration from environment variables."""
        try:
            config = cls(
                strict_mode=os.getenv("SCHEMA_STRICT_MODE", "false").lower() == "true",
                validate_types=os.getenv("SCHEMA_VALIDATE_TYPES", "true").lower() == "true",
                validate_constraints=os.getenv("SCHEMA_VALIDATE_CONSTRAINTS", "true").lower() == "true",
                validate_relationships=os.getenv("SCHEMA_VALIDATE_RELATIONSHIPS", "true").lower() == "true",
                allow_unknown_columns=os.getenv("SCHEMA_ALLOW_UNKNOWN_COLUMNS", "false").lower() == "true"
            )
            return config
        except Exception as e:
            logger.error(f"Failed to create schema validation configuration from environment: {e}")
            raise ValueError(f"Invalid schema validation configuration: {e}")


def load_mcp_config() -> MCPSchemaConfig:
    """Load and validate MCP schema configuration."""
    return MCPSchemaConfig.from_env()


def load_validation_config() -> SchemaValidationConfig:
    """Load and validate schema validation configuration."""
    return SchemaValidationConfig.from_env()