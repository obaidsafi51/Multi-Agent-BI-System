"""
Unit tests for MCP tools.

Tests all MCP tool functions including parameter validation, error handling,
and proper integration with underlying components.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

from tidb_mcp_server import mcp_tools
from tidb_mcp_server.models import (
    DatabaseInfo, TableInfo, TableSchema, ColumnInfo, IndexInfo, 
    QueryResult, SampleDataResult
)
from tidb_mcp_server.exceptions import (
    QueryValidationError, QueryExecutionError, TiDBMCPServerError
)


class TestMCPToolsInitialization:
    """Test MCP tools initialization."""
    
    def test_initialize_tools(self):
        """Test tools initialization."""
        mock_schema_inspector = Mock()
        mock_query_executor = Mock()
        mock_cache_manager = Mock()
        mock_mcp_server = Mock()
        
        mcp_tools.initialize_tools(
            mock_schema_inspector,
            mock_query_executor,
            mock_cache_manager,
            mock_mcp_server
        )
        
        # Verify tools are initialized
        assert mcp_tools._schema_inspector is mock_schema_inspector
        assert mcp_tools._query_executor is mock_query_executor
        assert mcp_tools._cache_manager is mock_cache_manager
        assert mcp_tools._mcp_server is mock_mcp_server
    
    def test_ensure_initialized_error(self):
        """Test error when tools are not initialized."""
        # Reset tools
        mcp_tools._schema_inspector = None
        mcp_tools._query_executor = None
        mcp_tools._cache_manager = None
        mcp_tools._mcp_server = None
        
        with pytest.raises(RuntimeError, match="not initialized"):
            mcp_tools.discover_databases()


class TestDiscoverDatabases:
    """Test discover_databases MCP tool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_schema_inspector = Mock()
        self.mock_query_executor = Mock()
        self.mock_cache_manager = Mock()
        self.mock_mcp_server = Mock()
        
        mcp_tools.initialize_tools(
            self.mock_schema_inspector,
            self.mock_query_executor,
            self.mock_cache_manager,
            self.mock_mcp_server
        )
    
    def test_successful_database_discovery(self):
        """Test successful database discovery."""
        # Mock database info
        mock_databases = [
            DatabaseInfo(name="test_db", charset="utf8mb4", collation="utf8mb4_unicode_ci", accessible=True),
            DatabaseInfo(name="analytics", charset="utf8mb4", collation="utf8mb4_unicode_ci", accessible=True),
            DatabaseInfo(name="restricted", charset="utf8mb4", collation="utf8mb4_unicode_ci", accessible=False)
        ]
        
        self.mock_schema_inspector.get_databases.return_value = mock_databases
        
        result = mcp_tools.discover_databases()
        
        assert len(result) == 3
        assert result[0]["name"] == "test_db"
        assert result[0]["accessible"] is True
        assert result[2]["accessible"] is False
        
        self.mock_schema_inspector.get_databases.assert_called_once()
    
    def test_database_discovery_error(self):
        """Test database discovery error handling."""
        self.mock_schema_inspector.get_databases.side_effect = Exception("Connection failed")
        
        with pytest.raises(TiDBMCPServerError, match="Failed to discover databases"):
            mcp_tools.discover_databases()


class TestDiscoverTables:
    """Test discover_tables MCP tool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_schema_inspector = Mock()
        self.mock_query_executor = Mock()
        self.mock_cache_manager = Mock()
        self.mock_mcp_server = Mock()
        
        mcp_tools.initialize_tools(
            self.mock_schema_inspector,
            self.mock_query_executor,
            self.mock_cache_manager,
            self.mock_mcp_server
        )
    
    def test_successful_table_discovery(self):
        """Test successful table discovery."""
        # Mock table info
        mock_tables = [
            TableInfo(name="users", type="BASE TABLE", engine="InnoDB", rows=1000, size_mb=5.2, comment="User data"),
            TableInfo(name="orders", type="BASE TABLE", engine="InnoDB", rows=5000, size_mb=12.8, comment="Order data")
        ]
        
        self.mock_schema_inspector.get_tables.return_value = mock_tables
        
        result = mcp_tools.discover_tables("test_db")
        
        assert len(result) == 2
        assert result[0]["name"] == "users"
        assert result[0]["rows"] == 1000
        assert result[1]["name"] == "orders"
        
        self.mock_schema_inspector.get_tables.assert_called_once_with("test_db")
    
    def test_empty_database_name(self):
        """Test error with empty database name."""
        with pytest.raises(ValueError, match="Database name is required"):
            mcp_tools.discover_tables("")
        
        with pytest.raises(ValueError, match="Database name is required"):
            mcp_tools.discover_tables("   ")
    
    def test_table_discovery_error(self):
        """Test table discovery error handling."""
        self.mock_schema_inspector.get_tables.side_effect = Exception("Database not found")
        
        with pytest.raises(TiDBMCPServerError, match="Failed to discover tables"):
            mcp_tools.discover_tables("nonexistent_db")


class TestGetTableSchema:
    """Test get_table_schema MCP tool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_schema_inspector = Mock()
        self.mock_query_executor = Mock()
        self.mock_cache_manager = Mock()
        self.mock_mcp_server = Mock()
        
        mcp_tools.initialize_tools(
            self.mock_schema_inspector,
            self.mock_query_executor,
            self.mock_cache_manager,
            self.mock_mcp_server
        )
    
    def test_successful_schema_retrieval(self):
        """Test successful table schema retrieval."""
        # Mock schema info
        mock_columns = [
            ColumnInfo(name="id", data_type="int", is_nullable=False, is_primary_key=True),
            ColumnInfo(name="name", data_type="varchar", is_nullable=False),
            ColumnInfo(name="email", data_type="varchar", is_nullable=True)
        ]
        
        mock_indexes = [
            IndexInfo(name="PRIMARY", columns=["id"], is_unique=True, index_type="BTREE"),
            IndexInfo(name="idx_email", columns=["email"], is_unique=True, index_type="BTREE")
        ]
        
        mock_schema = TableSchema(
            database="test_db",
            table="users",
            columns=mock_columns,
            indexes=mock_indexes,
            primary_keys=["id"],
            foreign_keys=[]
        )
        
        self.mock_schema_inspector.get_table_schema.return_value = mock_schema
        
        result = mcp_tools.get_table_schema("test_db", "users")
        
        assert result["database"] == "test_db"
        assert result["table"] == "users"
        assert len(result["columns"]) == 3
        assert len(result["indexes"]) == 2
        assert result["primary_keys"] == ["id"]
        
        # Check column details
        assert result["columns"][0]["name"] == "id"
        assert result["columns"][0]["is_primary_key"] is True
        
        self.mock_schema_inspector.get_table_schema.assert_called_once_with("test_db", "users")
    
    def test_empty_parameters(self):
        """Test error with empty parameters."""
        with pytest.raises(ValueError, match="Database name is required"):
            mcp_tools.get_table_schema("", "users")
        
        with pytest.raises(ValueError, match="Table name is required"):
            mcp_tools.get_table_schema("test_db", "")
    
    def test_schema_retrieval_error(self):
        """Test schema retrieval error handling."""
        self.mock_schema_inspector.get_table_schema.side_effect = Exception("Table not found")
        
        with pytest.raises(TiDBMCPServerError, match="Failed to get schema"):
            mcp_tools.get_table_schema("test_db", "nonexistent_table")


class TestGetSampleData:
    """Test get_sample_data MCP tool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_schema_inspector = Mock()
        self.mock_query_executor = Mock()
        self.mock_cache_manager = Mock()
        self.mock_mcp_server = Mock()
        
        mcp_tools.initialize_tools(
            self.mock_schema_inspector,
            self.mock_query_executor,
            self.mock_cache_manager,
            self.mock_mcp_server
        )
    
    def test_successful_sample_data_retrieval(self):
        """Test successful sample data retrieval."""
        # Mock sample data result
        mock_sample_result = SampleDataResult(
            database="test_db",
            table="users",
            columns=["id", "name", "email"],
            rows=[
                {"id": 1, "name": "Alice", "email": "alice@example.com"},
                {"id": 2, "name": "Bob", "email": "bob@example.com"}
            ],
            row_count=2,
            total_table_rows=1000,
            execution_time_ms=45.2,
            sampling_method="LIMIT_ORDER_BY",
            masked_columns=[]
        )
        
        self.mock_schema_inspector.get_sample_data.return_value = mock_sample_result
        
        result = mcp_tools.get_sample_data("test_db", "users", limit=10)
        
        assert result["database"] == "test_db"
        assert result["table"] == "users"
        assert result["row_count"] == 2
        assert result["total_table_rows"] == 1000
        assert result["success"] is True
        assert len(result["rows"]) == 2
        
        self.mock_schema_inspector.get_sample_data.assert_called_once_with(
            database="test_db",
            table="users",
            limit=10,
            masked_columns=[]
        )
    
    def test_sample_data_with_masking(self):
        """Test sample data retrieval with column masking."""
        mock_sample_result = SampleDataResult(
            database="test_db",
            table="users",
            columns=["id", "name", "email"],
            rows=[
                {"id": 1, "name": "Alice", "email": "***MASKED***"},
                {"id": 2, "name": "Bob", "email": "***MASKED***"}
            ],
            row_count=2,
            total_table_rows=1000,
            execution_time_ms=45.2,
            sampling_method="LIMIT_ORDER_BY",
            masked_columns=["email"]
        )
        
        self.mock_schema_inspector.get_sample_data.return_value = mock_sample_result
        
        result = mcp_tools.get_sample_data("test_db", "users", limit=5, masked_columns=["email"])
        
        assert result["masked_columns"] == ["email"]
        assert result["rows"][0]["email"] == "***MASKED***"
        
        self.mock_schema_inspector.get_sample_data.assert_called_once_with(
            database="test_db",
            table="users",
            limit=5,
            masked_columns=["email"]
        )
    
    def test_invalid_parameters(self):
        """Test error with invalid parameters."""
        # Empty database name
        with pytest.raises(ValueError, match="Database name is required"):
            mcp_tools.get_sample_data("", "users")
        
        # Empty table name
        with pytest.raises(ValueError, match="Table name is required"):
            mcp_tools.get_sample_data("test_db", "")
        
        # Invalid limit
        with pytest.raises(ValueError, match="Limit must be an integer between 1 and 100"):
            mcp_tools.get_sample_data("test_db", "users", limit=0)
        
        with pytest.raises(ValueError, match="Limit must be an integer between 1 and 100"):
            mcp_tools.get_sample_data("test_db", "users", limit=101)
        
        # Invalid masked_columns type
        with pytest.raises(ValueError, match="Masked columns must be a list"):
            mcp_tools.get_sample_data("test_db", "users", masked_columns="email")
    
    def test_sample_data_error(self):
        """Test sample data retrieval error handling."""
        self.mock_schema_inspector.get_sample_data.side_effect = Exception("Table access denied")
        
        with pytest.raises(TiDBMCPServerError, match="Failed to get sample data"):
            mcp_tools.get_sample_data("test_db", "restricted_table")


class TestExecuteQuery:
    """Test execute_query MCP tool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_schema_inspector = Mock()
        self.mock_query_executor = Mock()
        self.mock_cache_manager = Mock()
        self.mock_mcp_server = Mock()
        
        mcp_tools.initialize_tools(
            self.mock_schema_inspector,
            self.mock_query_executor,
            self.mock_cache_manager,
            self.mock_mcp_server
        )
    
    def test_successful_query_execution(self):
        """Test successful query execution."""
        # Mock query result
        mock_query_result = QueryResult(
            columns=["id", "name", "email"],
            rows=[
                {"id": 1, "name": "Alice", "email": "alice@example.com"},
                {"id": 2, "name": "Bob", "email": "bob@example.com"}
            ],
            row_count=2,
            execution_time_ms=123.45,
            truncated=False
        )
        
        self.mock_query_executor.execute_query.return_value = mock_query_result
        
        result = mcp_tools.execute_query("SELECT id, name, email FROM users LIMIT 2")
        
        assert result["row_count"] == 2
        assert result["execution_time_ms"] == 123.45
        assert result["success"] is True
        assert not result["truncated"]
        assert len(result["rows"]) == 2
        
        self.mock_query_executor.execute_query.assert_called_once_with(
            query="SELECT id, name, email FROM users LIMIT 2",
            timeout=None,
            use_cache=True
        )
    
    def test_query_execution_with_options(self):
        """Test query execution with timeout and cache options."""
        mock_query_result = QueryResult(
            columns=["count"],
            rows=[{"count": 1000}],
            row_count=1,
            execution_time_ms=50.0,
            truncated=False
        )
        
        self.mock_query_executor.execute_query.return_value = mock_query_result
        
        result = mcp_tools.execute_query(
            "SELECT COUNT(*) as count FROM users",
            timeout=15,
            use_cache=False
        )
        
        assert result["success"] is True
        
        self.mock_query_executor.execute_query.assert_called_once_with(
            query="SELECT COUNT(*) as count FROM users",
            timeout=15,
            use_cache=False
        )
    
    def test_query_validation_error(self):
        """Test query validation error handling."""
        self.mock_query_executor.execute_query.side_effect = QueryValidationError("Forbidden keyword: DROP")
        
        result = mcp_tools.execute_query("DROP TABLE users")
        
        assert result["success"] is False
        assert result["error"] == "Forbidden keyword: DROP"
        assert result["error_type"] == "QueryValidationError"
        assert result["row_count"] == 0
    
    def test_query_execution_error(self):
        """Test query execution error handling."""
        self.mock_query_executor.execute_query.side_effect = QueryExecutionError("Table 'users' doesn't exist")
        
        result = mcp_tools.execute_query("SELECT * FROM users")
        
        assert result["success"] is False
        assert result["error"] == "Table 'users' doesn't exist"
        assert result["error_type"] == "QueryExecutionError"
    
    def test_invalid_parameters(self):
        """Test error with invalid parameters."""
        # Empty query
        with pytest.raises(ValueError, match="Query is required"):
            mcp_tools.execute_query("")
        
        # Invalid timeout
        with pytest.raises(ValueError, match="Timeout must be a positive integer"):
            mcp_tools.execute_query("SELECT 1", timeout=-1)
        
        # Invalid use_cache type
        with pytest.raises(ValueError, match="use_cache must be a boolean"):
            mcp_tools.execute_query("SELECT 1", use_cache="true")


class TestValidateQuery:
    """Test validate_query MCP tool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_schema_inspector = Mock()
        self.mock_query_executor = Mock()
        self.mock_cache_manager = Mock()
        self.mock_mcp_server = Mock()
        
        mcp_tools.initialize_tools(
            self.mock_schema_inspector,
            self.mock_query_executor,
            self.mock_cache_manager,
            self.mock_mcp_server
        )
    
    def test_valid_query_validation(self):
        """Test validation of valid query."""
        self.mock_query_executor.validate_query_syntax.return_value = {
            "valid": True,
            "message": "Query validation passed",
            "query_type": "SELECT"
        }
        
        result = mcp_tools.validate_query("SELECT * FROM users")
        
        assert result["valid"] is True
        assert result["query_type"] == "SELECT"
        
        self.mock_query_executor.validate_query_syntax.assert_called_once_with("SELECT * FROM users")
    
    def test_invalid_query_validation(self):
        """Test validation of invalid query."""
        self.mock_query_executor.validate_query_syntax.return_value = {
            "valid": False,
            "message": "Query contains forbidden keywords: DROP",
            "query_type": None
        }
        
        result = mcp_tools.validate_query("DROP TABLE users")
        
        assert result["valid"] is False
        assert result["query_type"] is None
        assert "forbidden" in result["message"]
    
    def test_empty_query_validation(self):
        """Test validation error with empty query."""
        with pytest.raises(ValueError, match="Query is required"):
            mcp_tools.validate_query("")


class TestGetServerStats:
    """Test get_server_stats MCP tool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_schema_inspector = Mock()
        self.mock_query_executor = Mock()
        self.mock_cache_manager = Mock()
        self.mock_mcp_server = Mock()
        
        mcp_tools.initialize_tools(
            self.mock_schema_inspector,
            self.mock_query_executor,
            self.mock_cache_manager,
            self.mock_mcp_server
        )
    
    def test_server_stats_retrieval(self):
        """Test server statistics retrieval."""
        # Mock statistics
        self.mock_cache_manager.get_stats.return_value = {
            "hits": 50,
            "misses": 10,
            "hit_rate_percent": 83.33
        }
        
        self.mock_query_executor.get_query_stats.return_value = {
            "max_timeout": 30,
            "max_result_rows": 1000
        }
        
        self.mock_schema_inspector.get_cache_stats.return_value = {
            "schema_cache_hits": 25,
            "schema_cache_misses": 5
        }
        
        result = mcp_tools.get_server_stats()
        
        assert "cache" in result
        assert "query_executor" in result
        assert "schema_cache" in result
        assert result["server_status"] == "healthy"
        assert result["cache"]["hit_rate_percent"] == 83.33


class TestClearCache:
    """Test clear_cache MCP tool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_schema_inspector = Mock()
        self.mock_query_executor = Mock()
        self.mock_cache_manager = Mock()
        self.mock_mcp_server = Mock()
        
        mcp_tools.initialize_tools(
            self.mock_schema_inspector,
            self.mock_query_executor,
            self.mock_cache_manager,
            self.mock_mcp_server
        )
    
    def test_clear_all_cache(self):
        """Test clearing all cache."""
        result = mcp_tools.clear_cache("all")
        
        assert result["cache_type"] == "all"
        assert result["cleared_entries"] == "all"
        assert result["success"] is True
        
        self.mock_cache_manager.clear.assert_called_once()
    
    def test_clear_query_cache(self):
        """Test clearing query cache."""
        self.mock_query_executor.clear_query_cache.return_value = 15
        
        result = mcp_tools.clear_cache("queries")
        
        assert result["cache_type"] == "queries"
        assert result["cleared_entries"] == 15
        assert result["success"] is True
        
        self.mock_query_executor.clear_query_cache.assert_called_once()
    
    def test_clear_schema_cache(self):
        """Test clearing schema cache."""
        self.mock_schema_inspector.invalidate_cache.return_value = 8
        
        result = mcp_tools.clear_cache("schema")
        
        assert result["cache_type"] == "schema"
        assert result["cleared_entries"] == 8
        assert result["success"] is True
        
        self.mock_schema_inspector.invalidate_cache.assert_called_once()
    
    def test_invalid_cache_type(self):
        """Test error with invalid cache type."""
        with pytest.raises(ValueError, match="Invalid cache_type"):
            mcp_tools.clear_cache("invalid_type")


class TestMCPToolsList:
    """Test MCP tools list for registration."""
    
    def test_mcp_tools_list(self):
        """Test that all tools are included in MCP_TOOLS list."""
        expected_tools = [
            mcp_tools.discover_databases,
            mcp_tools.discover_tables,
            mcp_tools.get_table_schema,
            mcp_tools.get_sample_data,
            mcp_tools.execute_query,
            mcp_tools.validate_query,
            mcp_tools.get_server_stats,
            mcp_tools.clear_cache
        ]
        
        assert len(mcp_tools.MCP_TOOLS) == len(expected_tools)
        
        for tool in expected_tools:
            assert tool in mcp_tools.MCP_TOOLS