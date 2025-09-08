"""
MCP client implementations for schema management.
"""

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional
import aiohttp
from datetime import datetime

from .config import MCPSchemaConfig
from .models import (
    SchemaDiscoveryResult, DetailedTableSchema, QueryValidationResult,
    ConstraintInfo, CompatibilityResult, DatabaseInfo, TableSchema,
    TableInfo, ColumnInfo, IndexInfo, ForeignKeyInfo
)

logger = logging.getLogger(__name__)


class MCPConnectionError(Exception):
    """Raised when MCP server connection fails."""
    pass


class MCPRequestError(Exception):
    """Raised when MCP request fails."""
    pass


class BackendMCPClient:
    """
    Base MCP client for backend database operations.
    
    Provides core functionality for communicating with the TiDB MCP server
    including connection management, request handling, and error recovery.
    """
    
    def __init__(self, config: Optional[MCPSchemaConfig] = None, url: Optional[str] = None):
        """
        Initialize MCP client.
        
        Args:
            config: MCP configuration, defaults to environment-based config
            url: Override URL for testing purposes
        """
        self.config = config or MCPSchemaConfig.from_env()
        if url:
            # Override the server URL for testing
            self.config.server_url = url
        self.session: Optional[aiohttp.ClientSession] = None
        self.is_connected = False
        
        logger.info(f"Initialized Backend MCP Client for server: {self.config.mcp_server_url}")
    
    async def connect(self) -> bool:
        """
        Connect to the TiDB MCP Server.
        
        Returns:
            True if connection successful, False otherwise
            
        Raises:
            MCPConnectionError: If connection fails after retries
        """
        for attempt in range(self.config.max_retries + 1):
            try:
                if not self.session:
                    timeout = aiohttp.ClientTimeout(
                        total=self.config.connection_timeout,
                        connect=self.config.connection_timeout
                    )
                    self.session = aiohttp.ClientSession(timeout=timeout)
                
                # Test connection with server health check
                result = await self._send_request("get_server_stats_tool", {})
                if result and not result.get('error'):
                    self.is_connected = True
                    logger.info("Successfully connected to TiDB MCP Server")
                    return True
                
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < self.config.max_retries:
                    await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
                else:
                    logger.error(f"Failed to connect after {self.config.max_retries} attempts")
                    raise MCPConnectionError(f"Cannot connect to MCP server: {e}")
        
        self.is_connected = False
        return False
    
    async def disconnect(self):
        """Disconnect from the TiDB MCP Server."""
        if self.session:
            await self.session.close()
            self.session = None
        
        self.is_connected = False
        logger.info("Disconnected from TiDB MCP Server")
    
    async def _send_request(self, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Send MCP request to the server with retry logic.
        
        Args:
            method: MCP method name
            params: Request parameters
            
        Returns:
            Response data or None if failed
            
        Raises:
            MCPRequestError: If request fails after retries
        """
        if not self.session:
            await self.connect()
        
        for attempt in range(self.config.max_retries + 1):
            try:
                url = f"{self.config.mcp_server_url}/tools/{method}"
                
                logger.debug(f"Sending MCP request to {url}: {method}")
                
                timeout = aiohttp.ClientTimeout(total=self.config.request_timeout)
                async with self.session.post(
                    url,
                    json=params,
                    headers={"Content-Type": "application/json"},
                    timeout=timeout
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.debug(f"MCP request successful: {method}")
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"MCP request failed ({response.status}): {error_text}")
                        if attempt < self.config.max_retries:
                            await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
                            continue
                        return {"error": f"HTTP {response.status}: {error_text}"}
            
            except asyncio.TimeoutError:
                logger.warning(f"MCP request timeout for {method} (attempt {attempt + 1})")
                if attempt < self.config.max_retries:
                    await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
                    continue
                raise MCPRequestError(f"Request timeout for {method}")
            
            except Exception as e:
                logger.warning(f"MCP request error for {method} (attempt {attempt + 1}): {e}")
                if attempt < self.config.max_retries:
                    await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
                    continue
                raise MCPRequestError(f"Request failed for {method}: {e}")
        
        return None
    
    async def health_check(self) -> bool:
        """
        Check if the MCP server is healthy.
        
        Returns:
            True if server is healthy, False otherwise
        """
        try:
            result = await self._send_request("get_server_stats_tool", {})
            return result is not None and not result.get('error')
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def health_check_sync(self) -> bool:
        """Synchronous version of health_check for testing."""
        # Simple mock implementation for testing
        try:
            import requests
            # Use server_url or mcp_server_url depending on which is set
            base_url = getattr(self.config, 'server_url', None) or self.config.mcp_server_url
            response = requests.get(f"{base_url}/health", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def discover_schema(self) -> Dict[str, Any]:
        """Synchronous version of discover_schema for testing."""
        # Simple mock implementation for testing
        try:
            import requests
            # Use server_url or mcp_server_url depending on which is set
            base_url = getattr(self.config, 'server_url', None) or self.config.mcp_server_url
            response = requests.get(f"{base_url}/schema", timeout=5)
            if response.status_code == 200:
                return response.json()
            return {"tables": [], "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"tables": [], "error": str(e)}
    
    async def get_server_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get server statistics.
        
        Returns:
            Server statistics or None if failed
        """
        try:
            return await self._send_request("get_server_stats_tool", {})
        except Exception as e:
            logger.error(f"Failed to get server stats: {e}")
            return None


class EnhancedMCPClient(BackendMCPClient):
    """
    Enhanced MCP client with schema-specific operations.
    
    Extends the base client with specialized methods for schema discovery,
    validation, and management operations.
    """
    
    async def discover_schema(self, database: str = "") -> SchemaDiscoveryResult:
        """
        Discover schema for a specific database or all databases.
        
        Args:
            database: Database name (empty string for all databases)
            
        Returns:
            Schema discovery result
        """
        start_time = datetime.now()
        
        try:
            # Get database info
            db_result = await self._send_request("discover_databases_tool", {})
            if not db_result or db_result.get('error'):
                return SchemaDiscoveryResult(
                    databases=[],
                    discovery_time_ms=0,
                    error=f"Failed to discover databases: {db_result.get('error') if db_result else 'Unknown error'}"
                )
            
            # Process database results
            databases = []
            for db_data in db_result:
                # If specific database requested, filter for it
                if database and db_data.get('name') != database:
                    continue
                    
                databases.append(DatabaseInfo(
                    name=db_data['name'],
                    charset=db_data.get('charset', 'utf8mb4'),
                    collation=db_data.get('collation', 'utf8mb4_general_ci'),
                    accessible=db_data.get('accessible', True),
                    table_count=db_data.get('table_count')
                ))
            
            discovery_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return SchemaDiscoveryResult(
                databases=databases,
                discovery_time_ms=discovery_time,
                cached=False
            )
            
        except Exception as e:
            logger.error(f"Schema discovery failed for database '{database}': {e}")
            return SchemaDiscoveryResult(
                databases=[],
                discovery_time_ms=0,
                error=str(e)
            )
    
    def discover_schema_sync(self) -> Dict[str, Any]:
        """Synchronous version of discover_schema for testing."""
        # Inherit the sync method from parent class
        return super().discover_schema()
    
    async def discover_all_databases(self) -> SchemaDiscoveryResult:
        """
        Discover all accessible databases.
        
        Returns:
            Schema discovery result with all databases
        """
        return await self.discover_schema("")
    
    async def get_table_schema_detailed(self, database: str, table: str) -> DetailedTableSchema:
        """
        Get detailed table schema information.
        
        Args:
            database: Database name
            table: Table name
            
        Returns:
            Detailed table schema
        """
        start_time = datetime.now()
        
        try:
            # Get basic table schema
            schema_result = await self._send_request("get_table_schema_tool", {
                "database": database,
                "table": table
            })
            
            if not schema_result or schema_result.get('error'):
                raise MCPRequestError(f"Failed to get table schema: {schema_result.get('error') if schema_result else 'Unknown error'}")
            
            # Parse schema information
            columns = []
            for col_data in schema_result.get('columns', []):
                columns.append(ColumnInfo(
                    name=col_data['name'],
                    data_type=col_data['data_type'],
                    is_nullable=col_data.get('is_nullable', True),
                    default_value=col_data.get('default_value'),
                    is_primary_key=col_data.get('is_primary_key', False),
                    is_foreign_key=col_data.get('is_foreign_key', False),
                    comment=col_data.get('comment'),
                    max_length=col_data.get('max_length'),
                    precision=col_data.get('precision'),
                    scale=col_data.get('scale'),
                    is_auto_increment=col_data.get('is_auto_increment', False),
                    character_set=col_data.get('character_set'),
                    collation=col_data.get('collation')
                ))
            
            # Parse indexes
            indexes = []
            for idx_data in schema_result.get('indexes', []):
                indexes.append(IndexInfo(
                    name=idx_data['name'],
                    columns=idx_data['columns'],
                    is_unique=idx_data.get('is_unique', False),
                    is_primary=idx_data.get('is_primary', False),
                    index_type=idx_data.get('index_type', 'BTREE'),
                    comment=idx_data.get('comment')
                ))
            
            # Parse foreign keys
            foreign_keys = []
            for fk_data in schema_result.get('foreign_keys', []):
                foreign_keys.append(ForeignKeyInfo(
                    name=fk_data['name'],
                    column=fk_data['column'],
                    referenced_table=fk_data['referenced_table'],
                    referenced_column=fk_data['referenced_column'],
                    on_delete=fk_data.get('on_delete', 'RESTRICT'),
                    on_update=fk_data.get('on_update', 'RESTRICT')
                ))
            
            # Create table schema
            table_schema = TableSchema(
                database=database,
                table=table,
                columns=columns,
                indexes=indexes,
                primary_keys=schema_result.get('primary_keys', []),
                foreign_keys=foreign_keys,
                constraints=[]  # Will be populated if constraint info is available
            )
            
            # Get sample data if available
            sample_data = None
            try:
                sample_result = await self._send_request("get_sample_data_tool", {
                    "database": database,
                    "table": table,
                    "limit": 5
                })
                if sample_result and not sample_result.get('error'):
                    sample_data = sample_result.get('data', [])
            except Exception as e:
                logger.warning(f"Failed to get sample data for {database}.{table}: {e}")
            
            discovery_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return DetailedTableSchema(
                schema=table_schema,
                sample_data=sample_data,
                statistics=schema_result.get('statistics'),
                relationships=schema_result.get('relationships'),
                discovery_time_ms=discovery_time
            )
            
        except Exception as e:
            logger.error(f"Failed to get detailed table schema for {database}.{table}: {e}")
            raise
    
    async def validate_query_against_schema(self, query: str) -> QueryValidationResult:
        """
        Validate a SQL query against the current schema.
        
        Args:
            query: SQL query to validate
            
        Returns:
            Query validation result
        """
        try:
            result = await self._send_request("validate_query_tool", {"query": query})
            
            if not result:
                return QueryValidationResult(
                    is_valid=False,
                    errors=["Failed to validate query - no response from server"],
                    warnings=[],
                    affected_tables=[]
                )
            
            if result.get('error'):
                return QueryValidationResult(
                    is_valid=False,
                    errors=[result['error']],
                    warnings=[],
                    affected_tables=[]
                )
            
            return QueryValidationResult(
                is_valid=result.get('is_valid', False),
                errors=result.get('errors', []),
                warnings=result.get('warnings', []),
                affected_tables=result.get('affected_tables', []),
                estimated_rows=result.get('estimated_rows'),
                execution_plan=result.get('execution_plan')
            )
            
        except Exception as e:
            logger.error(f"Query validation failed: {e}")
            return QueryValidationResult(
                is_valid=False,
                errors=[f"Validation error: {str(e)}"],
                warnings=[],
                affected_tables=[]
            )
    
    async def get_constraint_info(self, database: str, table: str) -> ConstraintInfo:
        """
        Get constraint information for a table.
        
        Args:
            database: Database name
            table: Table name
            
        Returns:
            Constraint information
        """
        try:
            # This would be implemented when the MCP server supports constraint discovery
            # For now, return empty constraint info
            return ConstraintInfo(
                name="",
                constraint_type="",
                columns=[],
                definition="",
                is_deferrable=False
            )
        except Exception as e:
            logger.error(f"Failed to get constraint info for {database}.{table}: {e}")
            raise
    
    async def check_schema_compatibility(self, expected_schema: Dict[str, Any]) -> CompatibilityResult:
        """
        Check schema compatibility against expected schema.
        
        Args:
            expected_schema: Expected schema definition
            
        Returns:
            Compatibility check result
        """
        try:
            # This would be implemented based on specific compatibility requirements
            # For now, return a basic compatibility result
            return CompatibilityResult(
                is_compatible=True,
                missing_tables=[],
                missing_columns=[],
                type_mismatches=[],
                constraint_differences=[],
                recommendations=[]
            )
        except Exception as e:
            logger.error(f"Schema compatibility check failed: {e}")
            raise