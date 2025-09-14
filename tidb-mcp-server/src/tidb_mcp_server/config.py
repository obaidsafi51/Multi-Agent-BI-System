"""Configuration management for Universal MCP Server."""

import os
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict
from pydantic_settings import BaseSettings


class LLMConfig(BaseModel):
    """LLM service configuration."""
    
    provider: str = Field(default="kimi", description="LLM provider name")
    api_key: str = Field(..., description="LLM API key")
    base_url: Optional[str] = Field(default=None, description="LLM API base URL")
    model: str = Field(default="moonshot-v1-8k", description="LLM model name")
    max_tokens: int = Field(default=4000, description="Maximum tokens per request")
    temperature: float = Field(default=0.7, description="Temperature for text generation")
    timeout: int = Field(default=180, description="Request timeout in seconds")
    
    @field_validator('temperature')
    @classmethod
    def validate_temperature(cls, v):
        """Validate temperature is in valid range."""
        if not 0.0 <= v <= 2.0:
            raise ValueError('Temperature must be between 0.0 and 2.0')
        return v
    
    @field_validator('max_tokens')
    @classmethod
    def validate_max_tokens(cls, v):
        """Validate max tokens is positive."""
        if v <= 0:
            raise ValueError('Max tokens must be positive')
        return v


class ToolsConfig(BaseModel):
    """Configuration for available tools."""
    
    enabled_tools: List[str] = Field(
        default_factory=lambda: ["database", "llm"],
        description="List of enabled tool categories"
    )
    database_tools_enabled: bool = Field(default=True, description="Enable database tools")
    llm_tools_enabled: bool = Field(default=True, description="Enable LLM tools") 
    analytics_tools_enabled: bool = Field(default=True, description="Enable analytics tools")
    
    @field_validator('enabled_tools', mode='before')
    @classmethod
    def validate_enabled_tools(cls, v):
        """Validate enabled tools list. Handle comma-separated strings."""
        if isinstance(v, str):
            # Handle comma-separated string from environment variable
            v = [tool.strip() for tool in v.split(',') if tool.strip()]
        
        valid_tools = ["database", "llm", "analytics", "visualization", "export"]
        invalid_tools = [tool for tool in v if tool not in valid_tools]
        if invalid_tools:
            raise ValueError(f'Invalid tools: {invalid_tools}. Valid tools: {valid_tools}')
        return v
        return v


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
    read_timeout: int = Field(default=180, description="Read timeout in seconds")
    write_timeout: int = Field(default=180, description="Write timeout in seconds")
    
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
    """Universal MCP server configuration."""
    
    name: str = Field(default="universal-mcp-server", description="Server name")
    version: str = Field(default="1.0.0", description="Server version")
    max_connections: int = Field(default=10, description="Maximum concurrent connections")
    request_timeout: int = Field(default=180, description="Request timeout in seconds")
    
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
    
    max_query_timeout: int = Field(default=180, description="Maximum query timeout in seconds")
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
    """Main Universal MCP server configuration loaded from environment variables."""
    
    # Database configuration
    tidb_host: str = Field(..., env="TIDB_HOST")
    tidb_port: int = Field(default=4000, env="TIDB_PORT")
    tidb_user: str = Field(..., env="TIDB_USER")
    tidb_password: str = Field(..., env="TIDB_PASSWORD")
    tidb_database: Optional[str] = Field(default=None, env="TIDB_DATABASE")
    tidb_ssl_ca: Optional[str] = Field(default=None, env="TIDB_SSL_CA")
    tidb_ssl_verify_cert: bool = Field(default=True, env="TIDB_SSL_VERIFY_CERT")
    tidb_ssl_verify_identity: bool = Field(default=True, env="TIDB_SSL_VERIFY_IDENTITY")
    
    # LLM configuration
    llm_provider: str = Field(default="kimi", env="LLM_PROVIDER")
    llm_api_key: str = Field(..., env="LLM_API_KEY")
    llm_base_url: Optional[str] = Field(default="https://api.moonshot.ai/v1", env="LLM_BASE_URL")
    llm_model: str = Field(default="moonshot-v1-8k", env="LLM_MODEL")
    llm_max_tokens: int = Field(default=4000, env="LLM_MAX_TOKENS")
    llm_temperature: float = Field(default=0.7, env="LLM_TEMPERATURE")
    llm_timeout: int = Field(default=180, env="LLM_TIMEOUT")
    
    # Tools configuration
    enabled_tools_str: str = Field(
        default="database,llm",
        env="ENABLED_TOOLS",
        description="Comma-separated list of enabled tools"
    )
    
    @property
    def enabled_tools(self) -> List[str]:
        """Get enabled tools as a list."""
        return [tool.strip() for tool in self.enabled_tools_str.split(',') if tool.strip()]
    database_tools_enabled: bool = Field(default=True, env="DATABASE_TOOLS_ENABLED")
    llm_tools_enabled: bool = Field(default=True, env="LLM_TOOLS_ENABLED")
    analytics_tools_enabled: bool = Field(default=True, env="ANALYTICS_TOOLS_ENABLED")
    
    # MCP server configuration
    mcp_server_name: str = Field(default="universal-mcp-server", env="MCP_SERVER_NAME")
    mcp_server_version: str = Field(default="1.0.0", env="MCP_SERVER_VERSION")
    mcp_max_connections: int = Field(default=10, env="MCP_MAX_CONNECTIONS")
    mcp_request_timeout: int = Field(default=180, env="MCP_REQUEST_TIMEOUT")
    
    # Cache configuration
    cache_enabled: bool = Field(default=True, env="CACHE_ENABLED")
    cache_ttl_seconds: int = Field(default=300, env="CACHE_TTL_SECONDS")
    cache_max_size: int = Field(default=1000, env="CACHE_MAX_SIZE")
    
    # Security configuration
    max_query_timeout: int = Field(default=180, env="MAX_QUERY_TIMEOUT")
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
    
    def get_llm_config(self) -> LLMConfig:
        """Get LLM configuration object."""
        return LLMConfig(
            provider=self.llm_provider,
            api_key=self.llm_api_key,
            base_url=self.llm_base_url,
            model=self.llm_model,
            max_tokens=self.llm_max_tokens,
            temperature=self.llm_temperature,
            timeout=self.llm_timeout,
        )
    
    def get_tools_config(self) -> ToolsConfig:
        """Get tools configuration object."""
        return ToolsConfig(
            enabled_tools=self.enabled_tools,
            database_tools_enabled=self.database_tools_enabled,
            llm_tools_enabled=self.llm_tools_enabled,
            analytics_tools_enabled=self.analytics_tools_enabled,
        )
    
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
        
        # Validate required database fields if database tools are enabled
        if self.database_tools_enabled:
            if not self.tidb_host:
                errors.append("TIDB_HOST is required when database tools are enabled")
            if not self.tidb_user:
                errors.append("TIDB_USER is required when database tools are enabled")
            if not self.tidb_password:
                errors.append("TIDB_PASSWORD is required when database tools are enabled")
        
        # Validate required LLM fields if LLM tools are enabled
        if self.llm_tools_enabled and not self.llm_api_key:
            errors.append("LLM_API_KEY is required when LLM tools are enabled")
        
        # Validate enabled tools
        if not self.enabled_tools:
            errors.append("At least one tool category must be enabled")
        
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


def _is_containerized_environment() -> bool:
    """Detect if running in a containerized environment."""
    import os
    
    # Check for common container indicators
    container_indicators = [
        os.path.exists('/.dockerenv'),  # Docker creates this file
        os.environ.get('DOCKER_ENV') == 'true',  # Custom Docker env flag
        os.environ.get('CONTAINER') == 'docker',  # Some orchestrators set this
        os.environ.get('KUBERNETES_SERVICE_HOST'),  # Kubernetes environment
        os.path.exists('/proc/1/cgroup') and 'docker' in open('/proc/1/cgroup').read(),  # Docker cgroup
    ]
    
    return any(container_indicators)


def load_config() -> ServerConfig:
    """Load and validate server configuration with environment-aware loading."""
    import os
    import logging
    
    # Set up logging for configuration
    logger = logging.getLogger(__name__)
    
    try:
        # Detect environment type
        is_containerized = _is_containerized_environment()
        
        if is_containerized:
            # Container environment: rely on environment variables passed by orchestrator
            logger.info("Detected containerized environment - using environment variables directly")
            
            # Verify critical environment variables are present
            required_env_vars = ['TIDB_HOST', 'TIDB_USER', 'TIDB_PASSWORD']
            missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
            
            if missing_vars:
                logger.warning(f"Missing required environment variables: {missing_vars}")
                logger.info("This is normal if variables are set at runtime by Docker Compose")
            
        else:
            # Local development environment: try to load .env files
            logger.info("Detected local development environment - attempting to load .env files")
            
            from dotenv import load_dotenv
            
            # Try to load .env from different locations
            env_paths = [
                ".env",  # Current directory
                os.path.join(os.path.dirname(__file__), "..", "..", ".env"),  # Project root
                os.path.join(os.getcwd(), ".env"),  # Working directory
                os.path.expanduser("~/.config/tidb-mcp-server/.env"),  # User config directory
            ]
            
            env_loaded = False
            for env_path in env_paths:
                if os.path.exists(env_path):
                    load_dotenv(env_path, override=True)
                    env_loaded = True
                    logger.info(f"✅ Loaded environment from: {env_path}")
                    break
            
            if not env_loaded:
                logger.warning("⚠️  No .env file found - ensure environment variables are set")
                logger.info("Expected .env file locations:")
                for path in env_paths:
                    logger.info(f"  - {path}")
        
        # Create and validate configuration
        # Pydantic automatically reads from environment variables
        config = ServerConfig()
        
        # Validate the configuration
        config.validate_configuration()
        
        # Log configuration summary (without sensitive data)
        logger.info("✅ Configuration loaded successfully")
        logger.info(f"  - Environment: {'Container' if is_containerized else 'Local Development'}")
        logger.info(f"  - TiDB Host: {config.tidb_host}")
        logger.info(f"  - LLM Provider: {config.llm_provider}")
        logger.info(f"  - Enabled Tools: {', '.join(config.enabled_tools)}")
        logger.info(f"  - MCP Server: {config.mcp_server_name} v{config.mcp_server_version}")
        
        return config
        
    except Exception as e:
        logger.error(f"❌ Failed to load configuration: {e}")
        if not is_containerized:
            logger.error("💡 For local development, ensure you have a .env file with required variables")
            logger.error("💡 For Docker deployment, ensure environment variables are passed via docker-compose")
        raise ValueError(f"Failed to load configuration: {e}") from e