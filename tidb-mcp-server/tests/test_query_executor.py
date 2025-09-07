"""
Unit tests for QueryExecutor class.

Tests query validation, execution, security restrictions, and error handling.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import time
from typing import List, Dict, Any

from tidb_mcp_server.query_executor import QueryExecutor, QueryValidator
from tidb_mcp_server.exceptions import (
    QueryValidationError, 
    QueryExecutionError, 
    QueryTimeoutError
)
from tidb_mcp_server.models import QueryResult
from tidb_mcp_server.cache_manager import CacheManager


class TestQueryValidator:
    """Test cases for QueryValidator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = QueryValidator()
    
    def test_valid_select_queries(self):
        """Test validation of valid SELECT queries."""
        valid_queries = [
            "SELECT * FROM users",
            "SELECT id, name FROM users WHERE active = 1",
            "SELECT COUNT(*) FROM orders GROUP BY status",
            "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id",
            "SELECT * FROM products ORDER BY price DESC LIMIT 10",
            "SELECT DISTINCT category FROM products",
            "SELECT NOW(), CURDATE(), CURTIME()",
            "SELECT 1 + 1 AS result",
            "SELECT CASE WHEN price > 100 THEN 'expensive' ELSE 'cheap' END FROM products"
        ]
        
        for query in valid_queries:
            # Should not raise any exception
            self.validator.validate_query(query)
    
    def test_forbidden_keywords(self):
        """Test rejection of queries with forbidden keywords."""
        forbidden_queries = [
            "INSERT INTO users VALUES (1, 'test')",
            "UPDATE users SET name = 'test' WHERE id = 1",
            "DELETE FROM users WHERE id = 1",
            "DROP TABLE users",
            "CREATE TABLE test (id INT)",
            "ALTER TABLE users ADD COLUMN email VARCHAR(255)",
            "TRUNCATE TABLE users",
            "GRANT SELECT ON users TO test_user",
            "REVOKE SELECT ON users FROM test_user",
            "COMMIT",
            "ROLLBACK",
            "START TRANSACTION"
        ]
        
        for query in forbidden_queries:
            with pytest.raises(QueryValidationError, match="forbidden keywords"):
                self.validator.validate_query(query)
    
    def test_dangerous_patterns(self):
        """Test rejection of queries with dangerous patterns."""
        dangerous_queries = [
            "SELECT * FROM users; DROP TABLE users;",
            "SELECT * FROM users -- comment",
            "SELECT * FROM users /* comment */",
        ]
        
        for query in dangerous_queries:
            with pytest.raises(QueryValidationError, match="dangerous pattern"):
                self.validator.validate_query(query)
    
    def test_non_select_statements(self):
        """Test rejection of non-SELECT statements."""
        non_select_queries = [
            "SHOW TABLES",
            "DESCRIBE users",
            "EXPLAIN SELECT * FROM users",
            "CALL stored_procedure()",
            "EXECUTE sp_test"
        ]
        
        for query in non_select_queries:
            with pytest.raises(QueryValidationError):
                self.validator.validate_query(query)
    
    def test_empty_queries(self):
        """Test rejection of empty queries."""
        empty_queries = ["", "   ", "\n\t  "]
        
        for query in empty_queries:
            with pytest.raises(QueryValidationError, match="cannot be empty"):
                self.validator.validate_query(query)
    
    def test_unbalanced_parentheses(self):
        """Test rejection of queries with unbalanced parentheses."""
        unbalanced_queries = [
            "SELECT * FROM users WHERE id IN (1, 2, 3",
            "SELECT * FROM users WHERE id IN 1, 2, 3)",
            "SELECT COUNT(*) FROM (SELECT * FROM users WHERE active = 1"
        ]
        
        for query in unbalanced_queries:
            with pytest.raises(QueryValidationError, match="Unbalanced parentheses"):
                self.validator.validate_query(query)


class TestQueryExecutor:
    """Test cases for QueryExecutor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db_manager = Mock()
        self.mock_cache_manager = Mock(spec=CacheManager)
        self.executor = QueryExecutor(
            db_manager=self.mock_db_manager,
            cache_manager=self.mock_cache_manager,
            max_timeout=30,
            max_result_rows=1000
        )
    
    def test_successful_query_execution(self):
        """Test successful query execution."""
        # Mock database response
        mock_results = [
            {"id": 1, "name": "Alice", "email": "alice@example.com"},
            {"id": 2, "name": "Bob", "email": "bob@example.com"}
        ]
        self.mock_db_manager.execute_query.return_value = mock_results
        self.mock_cache_manager.get.return_value = None  # No cache hit
        
        query = "SELECT id, name, email FROM users LIMIT 2"
        result = self.executor.execute_query(query)
        
        assert isinstance(result, QueryResult)
        assert result.is_successful()
        assert result.row_count == 2
        assert result.columns == ["id", "name", "email"]
        assert result.rows == mock_results
        assert not result.truncated
        assert result.execution_time_ms > 0
        
        # Verify database was called
        self.mock_db_manager.execute_query.assert_called_once_with(query, fetch_all=True)
        
        # Verify cache was used
        self.mock_cache_manager.get.assert_called_once()
        self.mock_cache_manager.set.assert_called_once()
    
    def test_cached_query_result(self):
        """Test retrieval of cached query results."""
        # Mock cached result
        cached_result = QueryResult(
            columns=["id", "name"],
            rows=[{"id": 1, "name": "Alice"}],
            row_count=1,
            execution_time_ms=50.0
        )
        self.mock_cache_manager.get.return_value = cached_result
        
        query = "SELECT id, name FROM users"
        result = self.executor.execute_query(query)
        
        assert result == cached_result
        
        # Verify database was not called
        self.mock_db_manager.execute_query.assert_not_called()
        
        # Verify cache was checked
        self.mock_cache_manager.get.assert_called_once()
    
    def test_query_validation_error(self):
        """Test query validation error handling."""
        invalid_query = "DROP TABLE users"
        
        with pytest.raises(QueryValidationError, match="forbidden keywords"):
            self.executor.execute_query(invalid_query)
        
        # Verify database was not called
        self.mock_db_manager.execute_query.assert_not_called()
    
    def test_query_execution_error(self):
        """Test database execution error handling."""
        self.mock_db_manager.execute_query.side_effect = Exception("Table 'users' doesn't exist")
        self.mock_cache_manager.get.return_value = None
        
        query = "SELECT * FROM users"
        
        with pytest.raises(QueryExecutionError, match="Table 'users' doesn't exist"):
            self.executor.execute_query(query)
    
    def test_query_timeout_error(self):
        """Test query timeout error handling."""
        self.mock_db_manager.execute_query.side_effect = Exception("Query timeout")
        self.mock_cache_manager.get.return_value = None
        
        query = "SELECT * FROM large_table"
        
        with pytest.raises(QueryTimeoutError, match="timed out"):
            self.executor.execute_query(query)
    
    def test_result_truncation(self):
        """Test result truncation when exceeding max rows."""
        # Create more results than max_result_rows
        mock_results = [{"id": i, "name": f"User{i}"} for i in range(1500)]
        self.mock_db_manager.execute_query.return_value = mock_results
        self.mock_cache_manager.get.return_value = None
        
        query = "SELECT id, name FROM users"
        result = self.executor.execute_query(query)
        
        assert result.truncated
        assert result.row_count == 1000  # max_result_rows
        assert len(result.rows) == 1000
    
    def test_timeout_validation(self):
        """Test timeout parameter validation."""
        query = "SELECT * FROM users"
        
        # Test timeout exceeding maximum
        with pytest.raises(QueryValidationError, match="cannot exceed"):
            self.executor.execute_query(query, timeout=60)  # max is 30
    
    def test_empty_results(self):
        """Test handling of empty query results."""
        self.mock_db_manager.execute_query.return_value = []
        self.mock_cache_manager.get.return_value = None
        
        query = "SELECT * FROM users WHERE id = 999999"
        result = self.executor.execute_query(query)
        
        assert result.is_successful()
        assert result.row_count == 0
        assert result.rows == []
        assert result.columns == []
        assert not result.truncated
    
    def test_data_type_processing(self):
        """Test processing of different data types in results."""
        from datetime import datetime
        
        mock_results = [
            {
                "id": 1,
                "name": "Alice",
                "balance": 123.45,
                "active": True,
                "created_at": datetime(2023, 1, 1, 12, 0, 0),
                "notes": None
            }
        ]
        self.mock_db_manager.execute_query.return_value = mock_results
        self.mock_cache_manager.get.return_value = None
        
        query = "SELECT * FROM users"
        result = self.executor.execute_query(query)
        
        processed_row = result.rows[0]
        assert processed_row["id"] == 1
        assert processed_row["name"] == "Alice"
        assert processed_row["balance"] == 123.45
        assert processed_row["active"] is True
        assert processed_row["created_at"] == "2023-01-01T12:00:00"
        assert processed_row["notes"] is None
    
    def test_query_hash_generation(self):
        """Test query hash generation for caching."""
        query1 = "SELECT * FROM users"
        query2 = "select * from users"  # Different case
        query3 = "SELECT  *  FROM  users"  # Different whitespace
        query4 = "SELECT * FROM products"  # Different query
        
        hash1 = self.executor._generate_query_hash(query1)
        hash2 = self.executor._generate_query_hash(query2)
        hash3 = self.executor._generate_query_hash(query3)
        hash4 = self.executor._generate_query_hash(query4)
        
        # Same queries should have same hash
        assert hash1 == hash2 == hash3
        
        # Different queries should have different hash
        assert hash1 != hash4
        
        # Hash should be reasonable length
        assert len(hash1) == 16
    
    def test_validate_query_syntax(self):
        """Test query syntax validation method."""
        valid_query = "SELECT * FROM users"
        invalid_query = "DROP TABLE users"
        
        # Valid query
        result = self.executor.validate_query_syntax(valid_query)
        assert result["valid"] is True
        assert result["query_type"] == "SELECT"
        assert "validation passed" in result["message"].lower()
        
        # Invalid query
        result = self.executor.validate_query_syntax(invalid_query)
        assert result["valid"] is False
        assert result["query_type"] is None
        assert "forbidden" in result["message"].lower()
    
    def test_get_query_stats(self):
        """Test query statistics retrieval."""
        self.mock_cache_manager.get_stats.return_value = {
            "hits": 10,
            "misses": 5,
            "hit_rate_percent": 66.67
        }
        
        stats = self.executor.get_query_stats()
        
        assert "max_timeout" in stats
        assert "max_result_rows" in stats
        assert "cache_stats" in stats
        assert stats["max_timeout"] == 30
        assert stats["max_result_rows"] == 1000
    
    def test_clear_query_cache(self):
        """Test query cache clearing."""
        self.mock_cache_manager.invalidate.return_value = 5
        
        cleared_count = self.executor.clear_query_cache()
        
        assert cleared_count == 5
        self.mock_cache_manager.invalidate.assert_called_once()
    
    def test_cache_disabled_execution(self):
        """Test query execution with caching disabled."""
        mock_results = [{"id": 1, "name": "Alice"}]
        self.mock_db_manager.execute_query.return_value = mock_results
        
        query = "SELECT id, name FROM users"
        result = self.executor.execute_query(query, use_cache=False)
        
        assert result.is_successful()
        assert result.row_count == 1
        
        # Verify cache was not used
        self.mock_cache_manager.get.assert_not_called()
        self.mock_cache_manager.set.assert_not_called()


class TestQueryExecutorIntegration:
    """Integration tests for QueryExecutor with real components."""
    
    def test_with_real_cache_manager(self):
        """Test QueryExecutor with real CacheManager."""
        mock_db_manager = Mock()
        cache_manager = CacheManager(default_ttl=60, max_size=100)
        
        executor = QueryExecutor(
            db_manager=mock_db_manager,
            cache_manager=cache_manager,
            max_timeout=30,
            max_result_rows=1000
        )
        
        # Mock database response
        mock_results = [{"id": 1, "name": "Alice"}]
        mock_db_manager.execute_query.return_value = mock_results
        
        query = "SELECT id, name FROM users"
        
        # First execution - should hit database
        result1 = executor.execute_query(query)
        assert result1.is_successful()
        assert mock_db_manager.execute_query.call_count == 1
        
        # Second execution - should hit cache
        result2 = executor.execute_query(query)
        assert result2.is_successful()
        assert mock_db_manager.execute_query.call_count == 1  # No additional call
        
        # Results should be equivalent
        assert result1.rows == result2.rows
        assert result1.columns == result2.columns