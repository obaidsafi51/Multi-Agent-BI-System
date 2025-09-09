"""
MCP-based schema management for dynamic database operations.

This module provides dynamic schema discovery and management through
the TiDB MCP server, replacing static schema files and migrations.
"""

from .config import MCPSchemaConfig, SchemaValidationConfig
from .client import BackendMCPClient, EnhancedMCPClient
from .manager import MCPSchemaManager
from .enhanced_cache import EnhancedSchemaCache, CacheEntry, CacheEntryType, CacheMetrics
from .configuration_manager import ConfigurationManager, ConfigurationValidator, ConfigurationSnapshot
from .models import (
    DatabaseInfo,
    TableInfo,
    ColumnInfo,
    TableSchema,
    ValidationResult,
    ValidationError,
    ValidationWarning,
    SchemaDiscoveryResult,
    DetailedTableSchema,
    QueryValidationResult,
    ConstraintInfo,
    CompatibilityResult,
    IndexInfo,
    ForeignKeyInfo,
    CacheStats
)

__all__ = [
    # Configuration
    "MCPSchemaConfig",
    "SchemaValidationConfig",
    
    # Clients
    "BackendMCPClient", 
    "EnhancedMCPClient",
    
    # Manager
    "MCPSchemaManager",
    
    # Enhanced Components
    "EnhancedSchemaCache",
    "CacheEntry",
    "CacheEntryType", 
    "CacheMetrics",
    "ConfigurationManager",
    "ConfigurationValidator",
    "ConfigurationSnapshot",
    
    # Models
    "DatabaseInfo",
    "TableInfo", 
    "ColumnInfo",
    "TableSchema",
    "ValidationResult",
    "ValidationError",
    "ValidationWarning",
    "SchemaDiscoveryResult",
    "DetailedTableSchema", 
    "QueryValidationResult",
    "ConstraintInfo",
    "CompatibilityResult",
    "IndexInfo",
    "ForeignKeyInfo",
    "CacheStats"
]