"""Custom exceptions for TiDB MCP Server."""


class TiDBMCPServerError(Exception):
    """Base exception for TiDB MCP Server errors."""
    
    def __init__(self, message: str, error_code: str = "UNKNOWN_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class ConfigurationError(TiDBMCPServerError):
    """Raised when configuration is invalid or missing."""
    
    def __init__(self, message: str):
        super().__init__(message, "CONFIGURATION_ERROR")


class DatabaseConnectionError(TiDBMCPServerError):
    """Raised when database connection fails."""
    
    def __init__(self, message: str):
        super().__init__(message, "DATABASE_CONNECTION_ERROR")


class AuthenticationError(TiDBMCPServerError):
    """Raised when database authentication fails."""
    
    def __init__(self, message: str):
        super().__init__(message, "AUTHENTICATION_ERROR")


class QueryValidationError(TiDBMCPServerError):
    """Raised when query validation fails."""
    
    def __init__(self, message: str):
        super().__init__(message, "QUERY_VALIDATION_ERROR")


class QueryExecutionError(TiDBMCPServerError):
    """Raised when query execution fails."""
    
    def __init__(self, message: str):
        super().__init__(message, "QUERY_EXECUTION_ERROR")


class QueryTimeoutError(TiDBMCPServerError):
    """Raised when query execution times out."""
    
    def __init__(self, message: str):
        super().__init__(message, "QUERY_TIMEOUT_ERROR")


class CacheError(TiDBMCPServerError):
    """Raised when cache operations fail."""
    
    def __init__(self, message: str):
        super().__init__(message, "CACHE_ERROR")


class RateLimitError(TiDBMCPServerError):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, message: str):
        super().__init__(message, "RATE_LIMIT_ERROR")


class MCPProtocolError(TiDBMCPServerError):
    """Raised when MCP protocol errors occur."""
    
    def __init__(self, message: str):
        super().__init__(message, "MCP_PROTOCOL_ERROR")