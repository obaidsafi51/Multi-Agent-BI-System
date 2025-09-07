"""Configuration management for TiDB MCP Server."""

import os
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from pydantic_settings import BaseSettings


class DatabaseConfig(BaseModel):
    """TiDB database connection configuration."""
    
    host: str = Field(..., description="TiDB host address")
    port: int = Field(default=4000, description="TiDB port number")
    user: str = Field(..., description="Database username")
    password: str = Field(..., description="Database password")
    database: Optional[str] = Field(default=None, description="Default database name")
    ssl_ca: Optional[str] = Field(default=None, description="SSL CA certificate path")
    ssl_verify_cert: bool = Field(default=True, description="Verify SSL certificate")
    ssl_verify_identity: bool = Field(default=True, description="Verify SSL identity")
    connect_timeout: int = Field(default=10, description="Connection timeout in seconds")
    read_timeout: int = Field(default=30, description="Read timeout in seconds")
    write_timeout: int = Field(default=30, description="Write timeout in seconds")
    
    @field_validator('port')
    @classmethod
    def validate_port(cls, v):
        """Validate port number is in valid range."""
        if not 1 <= v <= 65535:
            raise ValueError('Port must be between 1 and 65535')
        return v
    
    @field_validator('connect_timeout', 'read_timeout', 'write_timeout')
    @classmethod
    def validate_timeouts(cls, v):
        """Validate timeout values are positive."""
        if v <= 0:
            raise ValueError('Timeout values must be positive')
        return v


class MCPServerConfig(BaseModel):
    """MCP server configuration."""
    
    name: str = Field(default="tidb-mcp-server", description="Server name")
    version: str = Field(default="0.1.0", description="Server version")
    max_connections: int = Field(default=10, description="Maximum concurrent connections")
    request_timeout: int = Field(default=30, description="Request timeout in seconds")
    
    @field_validator('max_connections')
    @classmethod
    def validate_max_connections(cls, v):
        """Validate max connections is positive."""
        if v <= 0:
            raise ValueError('Max connections must be positive')
        return v
    
    @field_validator('request_timeout')
    @classmethod
    def validate_request_timeout(cls, v):
        """Validate request timeout is positive."""
        if v <= 0:
            raise ValueError('Request timeout must be positive')
        return v


class CacheConfig(BaseModel):
    """Cache configuration."""
    
    enabled: bool = Field(default=True, description="Enable caching")
    ttl_seconds: int = Field(default=300, description="Cache TTL in seconds (5 minutes)")
    max_size: int = Field(default=1000, description="Maximum cache entries")
    
    @field_validator('ttl_seconds')
    @classmethod
    def validate_ttl(cls, v):
        """Validate TTL is positive."""
        if v <= 0:
            raise ValueError('Cache TTL must be positive')
        return v
    
    @field_validator('max_size')
    @classmethod
    def validate_max_size(cls, v):
        """Validate max size is positive."""
        if v <= 0:
            raise ValueError('Cache max size must be positive')
        return v


class SecurityConfig(BaseModel):
    """Security configuration."""
    
    max_query_timeout: int = Field(default=30, description="Maximum query timeout in seconds")
    max_sample_rows: int = Field(default=100, description="Maximum sample rows to return")
    allowed_query_types: list[str] = Field(
        default=["SELECT"], 
        description="Allowed SQL query types"
    )
    rate_limit_requests_per_minute: int = Field(
        default=60, 
        description="Rate limit requests per minute"
    )
    
    @field_validator('max_query_timeout')
    @classmethod
    def validate_query_timeout(cls, v):
        """Validate query timeout is positive and reasonable."""
        if not 1 <= v <= 300:  # 1 second to 5 minutes
            raise ValueError('Query timeout must be between 1 and 300 seconds')
        return v
    
    @field_validator('max_sample_rows')
    @classmethod
    def validate_sample_rows(cls, v):
        """Validate sample rows limit."""
        if not 1 <= v <= 1000:
            raise ValueError('Max sample rows must be between 1 and 1000')
        return v
    
    @field_validator('rate_limit_requests_per_minute')
    @classmethod
    def validate_rate_limit(cls, v):
        """Validate rate limit is reasonable."""
        if not 1 <= v <= 1000:
            raise ValueError('Rate limit must be between 1 and 1000 requests per minute')
        return v


class ServerConfig(BaseSettings):
    """Main server configuration loaded from environment variables."""
    
    # Database configuration
    tidb_host: str = Field(..., env="TIDB_HOST")
    tidb_port: int = Field(default=4000, env="TIDB_PORT")
    tidb_user: str = Field(..., env="TIDB_USER")
    tidb_password: str = Field(..., env="TIDB_PASSWORD")
    tidb_database: Optional[str] = Field(default=None, env="TIDB_DATABASE")
    tidb_ssl_ca: Optional[str] = Field(default=None, env="TIDB_SSL_CA")
    tidb_ssl_verify_cert: bool = Field(default=True, env="TIDB_SSL_VERIFY_CERT")
    tidb_ssl_verify_identity: bool = Field(default=True, env="TIDB_SSL_VERIFY_IDENTITY")
    
    # MCP server configuration
    mcp_server_name: str = Field(default="tidb-mcp-server", env="MCP_SERVER_NAME")
    mcp_server_version: str = Field(default="0.1.0", env="MCP_SERVER_VERSION")
    mcp_max_connections: int = Field(default=10, env="MCP_MAX_CONNECTIONS")
    mcp_request_timeout: int = Field(default=30, env="MCP_REQUEST_TIMEOUT")
    
    # Cache configuration
    cache_enabled: bool = Field(default=True, env="CACHE_ENABLED")
    cache_ttl_seconds: int = Field(default=300, env="CACHE_TTL_SECONDS")
    cache_max_size: int = Field(default=1000, env="CACHE_MAX_SIZE")
    
    # Security configuration
    max_query_timeout: int = Field(default=30, env="MAX_QUERY_TIMEOUT")
    max_sample_rows: int = Field(default=100, env="MAX_SAMPLE_ROWS")
    rate_limit_requests_per_minute: int = Field(default=60, env="RATE_LIMIT_RPM")
    
    # Logging configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Allow extra environment variables to be ignored
    )
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of: {valid_levels}')
        return v.upper()
    
    @field_validator('log_format')
    @classmethod
    def validate_log_format(cls, v):
        """Validate log format."""
        valid_formats = ["json", "text"]
        if v.lower() not in valid_formats:
            raise ValueError(f'Log format must be one of: {valid_formats}')
        return v.lower()
    
    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration object."""
        return DatabaseConfig(
            host=self.tidb_host,
            port=self.tidb_port,
            user=self.tidb_user,
            password=self.tidb_password,
            database=self.tidb_database,
            ssl_ca=self.tidb_ssl_ca,
            ssl_verify_cert=self.tidb_ssl_verify_cert,
            ssl_verify_identity=self.tidb_ssl_verify_identity,
        )
    
    def get_mcp_server_config(self) -> MCPServerConfig:
        """Get MCP server configuration object."""
        return MCPServerConfig(
            name=self.mcp_server_name,
            version=self.mcp_server_version,
            max_connections=self.mcp_max_connections,
            request_timeout=self.mcp_request_timeout,
        )
    
    def get_cache_config(self) -> CacheConfig:
        """Get cache configuration object."""
        return CacheConfig(
            enabled=self.cache_enabled,
            ttl_seconds=self.cache_ttl_seconds,
            max_size=self.cache_max_size,
        )
    
    def get_security_config(self) -> SecurityConfig:
        """Get security configuration object."""
        return SecurityConfig(
            max_query_timeout=self.max_query_timeout,
            max_sample_rows=self.max_sample_rows,
            rate_limit_requests_per_minute=self.rate_limit_requests_per_minute,
        )
    
    def validate_configuration(self) -> None:
        """Validate the complete configuration and raise errors if invalid."""
        errors = []
        
        # Validate required database fields
        if not self.tidb_host:
            errors.append("TIDB_HOST is required")
        if not self.tidb_user:
            errors.append("TIDB_USER is required")
        if not self.tidb_password:
            errors.append("TIDB_PASSWORD is required")
        
        # Validate SSL configuration consistency
        if self.tidb_ssl_ca and not os.path.exists(self.tidb_ssl_ca):
            errors.append(f"SSL CA file not found: {self.tidb_ssl_ca}")
        
        # Validate timeout relationships
        if self.mcp_request_timeout < self.max_query_timeout:
            errors.append(
                "MCP request timeout must be >= max query timeout to prevent premature timeouts"
            )
        
        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")


def load_config() -> ServerConfig:
    """Load and validate server configuration from environment variables."""
    try:
        config = ServerConfig()
        config.validate_configuration()
        return config
    except Exception as e:
        raise ValueError(f"Failed to load configuration: {e}") from e