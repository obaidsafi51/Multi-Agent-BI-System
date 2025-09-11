"""
MCP Client for NLP Agent to communicate with TiDB MCP Server.
Provides tools for schema discovery and SQL generation via HTTP API.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)


class MCPClientError(Exception):
    """Base exception for MCP client errors."""
    pass


class MCPServerUnavailableError(MCPClientError):
    """MCP server is unavailable."""
    pass


class MCPClient:
    """
    Client for communicating with TiDB MCP Server via HTTP API.
    Provides tools for schema discovery, SQL generation, and data analysis.
    """
    
    def __init__(self, base_url: str = "http://tidb-mcp-server:8000"):
        """
        Initialize MCP client.
        
        Args:
            base_url: Base URL of the MCP server HTTP API
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = httpx.Timeout(30.0)
        self.is_connected = False
        
        logger.info(f"MCPClient initialized with base URL: {base_url}")
    
    async def connect(self) -> bool:
        """
        Test connection to MCP server.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/health")
                
                if response.status_code == 200:
                    health_data = response.json()
                    self.is_connected = health_data.get("status") == "healthy"
                    
                    if self.is_connected:
                        logger.info("Successfully connected to MCP server")
                        
                        # Initialize MCP tools if needed
                        await self.initialize_mcp_tools()
                    else:
                        logger.warning("MCP server is not healthy")
                        
                    return self.is_connected
                else:
                    logger.error(f"MCP server health check failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            self.is_connected = False
            return False
    
    async def initialize_mcp_tools(self) -> bool:
        """
        Initialize MCP tools on the server.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/admin/initialize")
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("status") in ["success", "already_initialized"]:
                        logger.info(f"MCP tools initialization: {result.get('message')}")
                        return True
                    else:
                        logger.error(f"MCP tools initialization failed: {result}")
                        return False
                else:
                    logger.error(f"MCP tools initialization request failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to initialize MCP tools: {e}")
            return False
    
    async def discover_databases(self) -> List[Dict[str, Any]]:
        """
        Discover all accessible databases.
        
        Returns:
            List of database information dictionaries
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/tools/discover_databases_tool")
                
                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, list):
                        logger.debug(f"Discovered {len(result)} databases")
                        return result
                    elif isinstance(result, dict) and "error" in result:
                        logger.error(f"Database discovery error: {result['error']}")
                        return []
                    else:
                        logger.warning(f"Unexpected database discovery response: {result}")
                        return []
                else:
                    logger.error(f"Database discovery failed: {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Database discovery error: {e}")
            return []
    
    async def discover_tables(self, database: str) -> List[Dict[str, Any]]:
        """
        Discover tables in a specific database.
        
        Args:
            database: Database name
            
        Returns:
            List of table information dictionaries
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/tools/discover_tables_tool",
                    json={"database": database}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, list):
                        logger.debug(f"Discovered {len(result)} tables in database '{database}'")
                        return result
                    elif isinstance(result, dict) and "error" in result:
                        logger.error(f"Table discovery error: {result['error']}")
                        return []
                    else:
                        logger.warning(f"Unexpected table discovery response: {result}")
                        return []
                else:
                    logger.error(f"Table discovery failed: {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Table discovery error: {e}")
            return []
    
    async def get_table_schema(self, database: str, table: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed schema information for a table.
        
        Args:
            database: Database name
            table: Table name
            
        Returns:
            Table schema dictionary or None if failed
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/tools/get_table_schema_tool",
                    json={"database": database, "table": table}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, dict) and "columns" in result:
                        logger.debug(f"Retrieved schema for table '{database}.{table}'")
                        return result
                    elif isinstance(result, dict) and "error" in result:
                        logger.error(f"Table schema error: {result['error']}")
                        return None
                    else:
                        logger.warning(f"Unexpected table schema response: {result}")
                        return None
                else:
                    logger.error(f"Table schema request failed: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Table schema error: {e}")
            return None
    
    async def get_sample_data(
        self,
        database: str,
        table: str,
        limit: int = 10,
        masked_columns: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get sample data from a table.
        
        Args:
            database: Database name
            table: Table name
            limit: Number of sample rows
            masked_columns: Columns to mask for security
            
        Returns:
            Sample data dictionary or None if failed
        """
        try:
            request_data = {
                "database": database,
                "table": table,
                "limit": limit
            }
            
            if masked_columns:
                request_data["masked_columns"] = masked_columns
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/tools/get_sample_data_tool",
                    json=request_data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, dict) and "rows" in result:
                        logger.debug(f"Retrieved {result.get('row_count', 0)} sample rows from '{database}.{table}'")
                        return result
                    elif isinstance(result, dict) and "error" in result:
                        logger.error(f"Sample data error: {result['error']}")
                        return None
                    else:
                        logger.warning(f"Unexpected sample data response: {result}")
                        return None
                else:
                    logger.error(f"Sample data request failed: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Sample data error: {e}")
            return None
    
    async def generate_sql(
        self,
        natural_language_query: str,
        schema_info: Optional[str] = None,
        examples: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Generate SQL query from natural language using LLM.
        
        Args:
            natural_language_query: User's question in natural language
            schema_info: Database schema information as string
            examples: Optional example queries
            
        Returns:
            Generated SQL and metadata or None if failed
        """
        try:
            request_data = {
                "natural_language_query": natural_language_query
            }
            
            if schema_info:
                request_data["schema_info"] = schema_info
            
            if examples:
                request_data["examples"] = examples
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/tools/llm_generate_sql_tool",
                    json=request_data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, dict) and result.get("success", False):
                        logger.debug(f"Generated SQL for query: {natural_language_query[:50]}...")
                        return result
                    elif isinstance(result, dict) and "error" in result:
                        logger.error(f"SQL generation error: {result['error']}")
                        return None
                    else:
                        logger.warning(f"Unexpected SQL generation response: {result}")
                        return None
                else:
                    logger.error(f"SQL generation request failed: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"SQL generation error: {e}")
            return None
    
    async def validate_query(self, query: str) -> bool:
        """
        Validate a SQL query without executing it.
        
        Args:
            query: SQL query to validate
            
        Returns:
            True if query is valid, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/tools/validate_query_tool",
                    json={"query": query}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    is_valid = result.get("valid", False)
                    logger.debug(f"Query validation result: {is_valid}")
                    return is_valid
                else:
                    logger.error(f"Query validation request failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Query validation error: {e}")
            return False
    
    async def execute_query(
        self,
        query: str,
        timeout: Optional[int] = None,
        use_cache: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Execute a SQL query.
        
        Args:
            query: SQL query to execute
            timeout: Query timeout in seconds
            use_cache: Whether to use caching
            
        Returns:
            Query results or None if failed
        """
        try:
            request_data = {
                "query": query,
                "use_cache": use_cache
            }
            
            if timeout:
                request_data["timeout"] = timeout
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/tools/execute_query_tool",
                    json=request_data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, dict) and result.get("success", False):
                        logger.debug(f"Query executed successfully: {result.get('row_count', 0)} rows")
                        return result
                    elif isinstance(result, dict) and "error" in result:
                        logger.error(f"Query execution error: {result['error']}")
                        return None
                    else:
                        logger.warning(f"Unexpected query execution response: {result}")
                        return None
                else:
                    logger.error(f"Query execution request failed: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            return None
    
    async def analyze_data(
        self,
        data: str,
        analysis_type: str = "financial",
        context: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze data using LLM.
        
        Args:
            data: Data to analyze (JSON, CSV, or text format)
            analysis_type: Type of analysis (general, financial, trend, summary)
            context: Optional context about the data
            
        Returns:
            Analysis results or None if failed
        """
        try:
            request_data = {
                "data": data,
                "analysis_type": analysis_type
            }
            
            if context:
                request_data["context"] = context
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/tools/llm_analyze_data_tool",
                    json=request_data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, dict) and result.get("success", False):
                        logger.debug(f"Data analysis completed: {analysis_type}")
                        return result
                    elif isinstance(result, dict) and "error" in result:
                        logger.error(f"Data analysis error: {result['error']}")
                        return None
                    else:
                        logger.warning(f"Unexpected data analysis response: {result}")
                        return None
                else:
                    logger.error(f"Data analysis request failed: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Data analysis error: {e}")
            return None
    
    async def health_check(self) -> bool:
        """
        Check MCP server health.
        
        Returns:
            True if server is healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                response = await client.get(f"{self.base_url}/health")
                
                if response.status_code == 200:
                    health_data = response.json()
                    return health_data.get("status") == "healthy"
                else:
                    return False
                    
        except Exception as e:
            logger.debug(f"MCP server health check failed: {e}")
            return False
    
    async def get_server_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get server statistics.
        
        Returns:
            Server statistics or None if failed
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/tools/get_server_stats_tool")
                
                if response.status_code == 200:
                    result = response.json()
                    logger.debug("Retrieved server statistics")
                    return result
                else:
                    logger.error(f"Server stats request failed: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Server stats error: {e}")
            return None
    
    async def build_schema_context(self, databases: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Build comprehensive schema context for SQL generation.
        
        Args:
            databases: List of databases to include (discovers all if None)
            
        Returns:
            Schema context dictionary
        """
        schema_context = {
            "databases": {},
            "tables": [],
            "metrics": set(),
            "timestamp": datetime.now().isoformat(),
            "source": "mcp_server"
        }
        
        try:
            # Discover databases if not specified
            if databases is None:
                discovered_dbs = await self.discover_databases()
                databases = [db["name"] for db in discovered_dbs if db.get("accessible", True)]
            
            # Build schema for each database
            for db_name in databases:
                tables = await self.discover_tables(db_name)
                
                schema_context["databases"][db_name] = {
                    "tables": {},
                    "table_count": len(tables)
                }
                
                # Process each table
                for table_info in tables[:10]:  # Limit to 10 tables per database
                    table_name = table_info["name"]
                    schema_context["tables"].append(f"{db_name}.{table_name}")
                    
                    # Get table schema
                    table_schema = await self.get_table_schema(db_name, table_name)
                    if table_schema:
                        schema_context["databases"][db_name]["tables"][table_name] = {
                            "columns": table_schema.get("columns", []),
                            "column_count": len(table_schema.get("columns", [])),
                            "row_count": table_info.get("rows", 0),
                            "size_mb": table_info.get("size_mb", 0)
                        }
                        
                        # Extract potential metrics from column names
                        for column in table_schema.get("columns", []):
                            column_name = column.get("name", "").lower()
                            if any(metric in column_name for metric in [
                                'revenue', 'profit', 'income', 'expense', 'cost', 'cash', 'flow',
                                'margin', 'sales', 'amount', 'value', 'total', 'balance', 'roi'
                            ]):
                                schema_context["metrics"].add(column_name)
            
            # Convert metrics set to list
            schema_context["metrics"] = sorted(list(schema_context["metrics"]))
            
            logger.info(f"Built schema context for {len(databases)} databases, "
                       f"{len(schema_context['tables'])} tables, "
                       f"{len(schema_context['metrics'])} metrics")
            
            return schema_context
            
        except Exception as e:
            logger.error(f"Error building schema context: {e}")
            return {
                "databases": {},
                "tables": [],
                "metrics": [],
                "timestamp": datetime.now().isoformat(),
                "source": "mcp_server",
                "error": str(e)
            }


# Global MCP client instance
_mcp_client: Optional[MCPClient] = None


def get_mcp_client(base_url: str = "http://tidb-mcp-server:8000") -> MCPClient:
    """Get the global MCP client instance."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient(base_url)
    return _mcp_client


async def close_mcp_client():
    """Close the global MCP client instance."""
    global _mcp_client
    if _mcp_client:
        # No explicit close needed for httpx client
        _mcp_client = None
