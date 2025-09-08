"""
MCP Schema Adapter - Bridge between MCP dynamic schema and schema_knowledge business logic.

This adapter provides a unified interface for accessing database schema information
from the MCP server while maintaining compatibility with existing business logic components.
"""

import logging
import asyncio
import time
import threading
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime

from .types import DatabaseType

logger = logging.getLogger(__name__)


class SimpleCacheManager:
    """Simple in-memory cache manager for schema information."""
    
    def __init__(self, default_ttl: int = 600):
        self._cache: Dict[str, tuple[Any, float]] = {}
        self._lock = threading.RLock()
        self._default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if time.time() - timestamp < self._default_ttl:
                    return value
                else:
                    del self._cache[key]
            return None
    
    def set(self, key: str, value: Any) -> None:
        """Set value in cache with current timestamp."""
        with self._lock:
            self._cache[key] = (value, time.time())
    
    def delete(self, key: str) -> None:
        """Delete specific key from cache."""
        with self._lock:
            self._cache.pop(key, None)
    
    def invalidate(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern."""
        with self._lock:
            keys_to_remove = [k for k in self._cache.keys() if pattern in k or k.startswith(pattern.replace('*', ''))]
            for key in keys_to_remove:
                del self._cache[key]
            return len(keys_to_remove)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            return {"size": len(self._cache), "ttl": self._default_ttl}


@dataclass
class MCPSchemaInfo:
    """Schema information from MCP server"""
    database: str
    table: str
    columns: List[Dict[str, Any]]
    indexes: List[Dict[str, Any]]
    primary_keys: List[str]
    foreign_keys: List[Dict[str, Any]]
    row_count: Optional[int] = None
    table_type: Optional[str] = None
    engine: Optional[str] = None
    last_updated: Optional[datetime] = None


class MCPSchemaAdapter:
    """
    Adapter that bridges MCP dynamic schema discovery with schema_knowledge business logic.
    
    This class provides a unified interface for accessing database schema information
    from the MCP server while maintaining compatibility with existing components
    like TermMapper, QueryTemplateEngine, etc.
    """
    
    def __init__(self, mcp_client: Optional[Any] = None, cache_manager: Optional[SimpleCacheManager] = None):
        """
        Initialize the MCP Schema Adapter.
        
        Args:
            mcp_client: MCP client instance for communicating with MCP server
            cache_manager: Cache manager for caching schema information
        """
        self.mcp_client = mcp_client
        self.cache_manager = cache_manager or SimpleCacheManager(default_ttl=600)  # 10 minutes cache
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Schema mapping cache - maps business terms to actual database schema
        self._schema_mapping_cache: Dict[str, MCPSchemaInfo] = {}
        self._last_schema_refresh: Optional[datetime] = None
        
        self.logger.info("MCPSchemaAdapter initialized")
    
    async def get_available_databases(self) -> List[str]:
        """
        Get list of available databases from MCP server.
        
        Returns:
            List of database names
        """
        cache_key = "mcp_databases"
        
        # Check cache first
        cached_result = self.cache_manager.get(cache_key)
        if cached_result is not None:
            self.logger.debug("Retrieved databases from cache")
            return cached_result
        
        try:
            if not self.mcp_client:
                self.logger.warning("No MCP client available, returning empty database list")
                return []
            
            # Call MCP server to get databases
            databases = await self._call_mcp_tool("list_databases")
            
            # Extract database names
            db_names = []
            if isinstance(databases, dict) and "databases" in databases:
                db_names = [db.get("name", "") for db in databases["databases"] if db.get("accessible", True)]
            elif isinstance(databases, list):
                db_names = [db.get("name", "") for db in databases if db.get("accessible", True)]
            
            # Cache the results
            self.cache_manager.set(cache_key, db_names)
            
            self.logger.info(f"Retrieved {len(db_names)} databases from MCP server")
            return db_names
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve databases from MCP server: {e}")
            return []
    
    async def get_database_tables(self, database: str) -> List[Dict[str, Any]]:
        """
        Get tables for a specific database from MCP server.
        
        Args:
            database: Database name
            
        Returns:
            List of table information dictionaries
        """
        cache_key = f"mcp_tables_{database}"
        
        # Check cache first
        cached_result = self.cache_manager.get(cache_key)
        if cached_result is not None:
            self.logger.debug(f"Retrieved tables for database '{database}' from cache")
            return cached_result
        
        try:
            if not self.mcp_client:
                self.logger.warning("No MCP client available, returning empty table list")
                return []
            
            # Call MCP server to get tables
            tables = await self._call_mcp_tool("list_tables", {"database": database})
            
            # Extract table information
            table_list = []
            if isinstance(tables, dict) and "tables" in tables:
                table_list = tables["tables"]
            elif isinstance(tables, list):
                table_list = tables
            
            # Cache the results
            self.cache_manager.set(cache_key, table_list)
            
            self.logger.info(f"Retrieved {len(table_list)} tables for database '{database}' from MCP server")
            return table_list
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve tables for database '{database}' from MCP server: {e}")
            return []
    
    async def get_table_schema(self, database: str, table: str) -> Optional[MCPSchemaInfo]:
        """
        Get detailed schema information for a specific table from MCP server.
        
        Args:
            database: Database name
            table: Table name
            
        Returns:
            MCPSchemaInfo object with complete schema information
        """
        cache_key = f"mcp_schema_{database}_{table}"
        
        # Check cache first
        cached_result = self.cache_manager.get(cache_key)
        if cached_result is not None:
            self.logger.debug(f"Retrieved schema for table '{database}.{table}' from cache")
            return cached_result
        
        try:
            if not self.mcp_client:
                self.logger.warning("No MCP client available, returning None")
                return None
            
            # Call MCP server to get table schema
            schema_data = await self._call_mcp_tool("get_table_schema", {
                "database": database,
                "table": table
            })
            
            if not schema_data:
                return None
            
            # Parse schema data into MCPSchemaInfo
            schema_info = MCPSchemaInfo(
                database=database,
                table=table,
                columns=schema_data.get("columns", []),
                indexes=schema_data.get("indexes", []),
                primary_keys=schema_data.get("primary_keys", []),
                foreign_keys=schema_data.get("foreign_keys", []),
                row_count=schema_data.get("row_count"),
                table_type=schema_data.get("table_type"),
                engine=schema_data.get("engine"),
                last_updated=datetime.now()
            )
            
            # Cache the results
            self.cache_manager.set(cache_key, schema_info)
            
            self.logger.info(f"Retrieved schema for table '{database}.{table}' from MCP server")
            return schema_info
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve schema for table '{database}.{table}' from MCP server: {e}")
            return None
    
    async def resolve_business_term_to_schema(self, business_term: str, 
                                            term_mapping: str) -> Optional[MCPSchemaInfo]:
        """
        Resolve a business term mapping to actual database schema using MCP.
        
        Args:
            business_term: Business term (e.g., "revenue")
            term_mapping: Database mapping from business_terms.json (e.g., "financial_overview.revenue")
            
        Returns:
            MCPSchemaInfo object if mapping is valid, None otherwise
        """
        cache_key = f"mcp_resolve_{business_term}_{term_mapping}"
        
        # Check cache first
        cached_result = self.cache_manager.get(cache_key)
        if cached_result is not None:
            self.logger.debug(f"Retrieved resolved mapping for '{business_term}' from cache")
            return cached_result
        
        try:
            # Parse the term mapping to extract database and table
            if "." not in term_mapping:
                self.logger.warning(f"Invalid term mapping format: {term_mapping}")
                return None
            
            # Handle formats like "financial_overview.revenue" or "database.table.column"
            parts = term_mapping.split(".")
            if len(parts) == 2:
                # Assume current database context
                databases = await self.get_available_databases()
                if not databases:
                    return None
                database = databases[0]  # Use first available database
                table, column = parts
            elif len(parts) == 3:
                database, table, column = parts
            else:
                self.logger.warning(f"Unsupported term mapping format: {term_mapping}")
                return None
            
            # Get schema information for the table
            schema_info = await self.get_table_schema(database, table)
            if not schema_info:
                self.logger.warning(f"Table '{database}.{table}' not found for term '{business_term}'")
                return None
            
            # Verify the column exists
            column_exists = any(col.get("name") == column for col in schema_info.columns)
            if not column_exists:
                self.logger.warning(f"Column '{column}' not found in table '{database}.{table}' for term '{business_term}'")
                return None
            
            # Cache the results
            self.cache_manager.set(cache_key, schema_info)
            
            self.logger.info(f"Resolved business term '{business_term}' to table '{database}.{table}'")
            return schema_info
            
        except Exception as e:
            self.logger.error(f"Failed to resolve business term '{business_term}' to schema: {e}")
            return None
    
    async def validate_business_term_mappings(self, term_mappings: Dict[str, str]) -> Dict[str, bool]:
        """
        Validate multiple business term mappings against actual database schema.
        
        Args:
            term_mappings: Dictionary of business_term -> database_mapping
            
        Returns:
            Dictionary of business_term -> validation_result
        """
        validation_results = {}
        
        for business_term, term_mapping in term_mappings.items():
            try:
                schema_info = await self.resolve_business_term_to_schema(business_term, term_mapping)
                validation_results[business_term] = schema_info is not None
            except Exception as e:
                self.logger.error(f"Error validating term '{business_term}': {e}")
                validation_results[business_term] = False
        
        valid_count = sum(validation_results.values())
        total_count = len(validation_results)
        
        self.logger.info(f"Validated {valid_count}/{total_count} business term mappings")
        
        return validation_results
    
    async def get_sample_data(self, database: str, table: str, limit: int = 10) -> Optional[Dict[str, Any]]:
        """
        Get sample data from a table using MCP server.
        
        Args:
            database: Database name
            table: Table name
            limit: Number of sample rows
            
        Returns:
            Sample data dictionary or None if failed
        """
        try:
            if not self.mcp_client:
                self.logger.warning("No MCP client available, cannot get sample data")
                return None
            
            # Call MCP server to get sample data
            sample_data = await self._call_mcp_tool("get_sample_data", {
                "database": database,
                "table": table,
                "limit": limit
            })
            
            self.logger.info(f"Retrieved sample data for table '{database}.{table}'")
            return sample_data
            
        except Exception as e:
            self.logger.error(f"Failed to get sample data for table '{database}.{table}': {e}")
            return None
    
    async def execute_query(self, database: str, query: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """
        Execute a query using MCP server.
        
        Args:
            database: Database name
            query: SQL query to execute
            params: Optional query parameters
            
        Returns:
            Query result dictionary or None if failed
        """
        try:
            if not self.mcp_client:
                self.logger.warning("No MCP client available, cannot execute query")
                return None
            
            # Call MCP server to execute query
            result = await self._call_mcp_tool("execute_query", {
                "database": database,
                "query": query,
                "params": params or {}
            })
            
            self.logger.info(f"Executed query on database '{database}'")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to execute query on database '{database}': {e}")
            return None
    
    async def refresh_schema_cache(self, database: Optional[str] = None, table: Optional[str] = None) -> None:
        """
        Refresh cached schema information.
        
        Args:
            database: Optional database name to refresh (refreshes all if None)
            table: Optional table name to refresh (requires database)
        """
        try:
            if table and not database:
                raise ValueError("Database name is required when refreshing table cache")
            
            if database and table:
                # Refresh specific table schema
                cache_key = f"mcp_schema_{database}_{table}"
                self.cache_manager.delete(cache_key)
                await self.get_table_schema(database, table)  # Reload from MCP
                
            elif database:
                # Refresh all cache entries for a database
                patterns = [f"mcp_tables_{database}", f"mcp_schema_{database}_*"]
                for pattern in patterns:
                    self.cache_manager.invalidate(pattern)
                
                # Reload tables
                await self.get_database_tables(database)
                
            else:
                # Refresh all schema-related cache entries
                patterns = ["mcp_databases", "mcp_tables_*", "mcp_schema_*", "mcp_resolve_*"]
                for pattern in patterns:
                    self.cache_manager.invalidate(pattern)
                
                # Reload databases
                await self.get_available_databases()
            
            self._last_schema_refresh = datetime.now()
            self.logger.info(f"Refreshed schema cache for database='{database}', table='{table}'")
            
        except Exception as e:
            self.logger.error(f"Failed to refresh schema cache: {e}")
    
    async def _call_mcp_tool(self, tool_name: str, params: Optional[Dict] = None) -> Any:
        """
        Call an MCP tool with error handling and retry logic.
        
        Args:
            tool_name: Name of the MCP tool to call
            params: Optional parameters for the tool
            
        Returns:
            Tool result
        """
        if not self.mcp_client:
            raise RuntimeError("MCP client not available")
        
        try:
            # This is a placeholder for the actual MCP client call
            # The actual implementation will depend on how the MCP client is structured
            if hasattr(self.mcp_client, 'call_tool'):
                result = await self.mcp_client.call_tool(tool_name, params or {})
            elif hasattr(self.mcp_client, tool_name):
                tool_method = getattr(self.mcp_client, tool_name)
                if asyncio.iscoroutinefunction(tool_method):
                    result = await tool_method(**(params or {}))
                else:
                    result = tool_method(**(params or {}))
            else:
                raise NotImplementedError(f"MCP tool '{tool_name}' not available")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error calling MCP tool '{tool_name}': {e}")
            raise
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics for monitoring.
        
        Returns:
            Dictionary with cache statistics
        """
        stats = self.cache_manager.get_stats()
        stats.update({
            "last_schema_refresh": self._last_schema_refresh.isoformat() if self._last_schema_refresh else None,
            "schema_mappings_cached": len(self._schema_mapping_cache)
        })
        return stats
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on MCP connection and schema access.
        
        Returns:
            Health check results
        """
        health_status = {
            "mcp_client_available": self.mcp_client is not None,
            "cache_manager_available": self.cache_manager is not None,
            "databases_accessible": False,
            "last_check": datetime.now().isoformat(),
            "errors": []
        }
        
        try:
            if self.mcp_client:
                # Try to get databases as a basic connectivity test
                databases = await self.get_available_databases()
                health_status["databases_accessible"] = len(databases) > 0
                health_status["database_count"] = len(databases)
            else:
                health_status["errors"].append("MCP client not available")
                
        except Exception as e:
            health_status["errors"].append(f"MCP connectivity error: {str(e)}")
        
        return health_status
