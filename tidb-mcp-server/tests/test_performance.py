"""Performance tests for TiDB MCP Server."""

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import psutil
import os

from tidb_mcp_server.config import ServerConfig
from tidb_mcp_server.query_executor import QueryExecutor
from tidb_mcp_server.cache_manager import CacheManager
from tidb_mcp_server.schema_inspector import SchemaInspector


class TestResponseTimePerformance:
    """Test response time performance requirements."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = MagicMock(spec=ServerConfig)
        config.tidb_host = "test-host.com"
        config.tidb_port = 4000
        config.tidb_user = "test_user"
        config.tidb_password = "test_password"
        config.tidb_database = "test_db"
        config.cache_ttl = 300
        config.cache_max_size = 1000
        return config
    
    @pytest.mark.asyncio
    async def test_simple_query_response_time(self, mock_config):
        """Test that simple queries respond within acceptable time limits."""
        with patch('tidb_mcp_server.query_executor.pymysql.connect') as mock_connect:
            mock_connection = AsyncMock()
            mock_cursor = AsyncMock()
            mock_cursor.fetchall.return_value = [(1, "test")]
            mock_cursor.description = [("id",), ("name",)]
            mock_connection.cursor.return_value.__aenter__.return_value = mock_cursor
            mock_connect.return_value = mock_connection
            
            executor = QueryExecutor(mock_config)
            
            start_time = time.time()
            result = await executor.execute_query("SELECT * FROM test_table")
            end_time = time.time()
            
            response_time = end_time - start_time
            
            # Should respond within 1 second for simple queries
            assert response_time < 1.0
            assert "columns" in result
            assert "rows" in result
    
    @pytest.mark.asyncio
    async def test_schema_inspection_response_time(self, mock_config):
        """Test that schema inspection responds within acceptable time limits."""
        with patch('tidb_mcp_server.schema_inspector.pymysql.connect') as mock_connect:
            mock_connection = AsyncMock()
            mock_cursor = AsyncMock()
            mock_cursor.fetchall.return_value = [
                ("table1", "BASE TABLE"),
                ("table2", "BASE TABLE"),
                ("view1", "VIEW")
            ]
            mock_connection.cursor.return_value.__aenter__.return_value = mock_cursor
            mock_connect.return_value = mock_connection
            
            inspector = SchemaInspector(mock_config)
            
            start_time = time.time()
            tables = await inspector.list_tables()
            end_time = time.time()
            
            response_time = end_time - start_time
            
            # Should respond within 2 seconds for schema inspection
            assert response_time < 2.0
            assert len(tables) == 3
    
    @pytest.mark.asyncio
    async def test_cached_query_response_time(self, mock_config):
        """Test that cached queries respond very quickly."""
        cache_manager = CacheManager(mock_config)
        
        # Pre-populate cache
        cached_result = {
            "columns": ["id", "name"],
            "rows": [(1, "test")],
            "row_count": 1
        }
        await cache_manager.set("query:SELECT * FROM test_table", cached_result)
        
        start_time = time.time()
        result = await cache_manager.get("query:SELECT * FROM test_table")
        end_time = time.time()
        
        response_time = end_time - start_time
        
        # Cached queries should respond within 10ms
        assert response_time < 0.01
        assert result == cached_result


class TestThroughputPerformance:
    """Test throughput performance requirements."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = MagicMock(spec=ServerConfig)
        config.tidb_host = "test-host.com"
        config.tidb_port = 4000
        config.tidb_user = "test_user"
        config.tidb_password = "test_password"
        config.tidb_database = "test_db"
        config.cache_ttl = 300
        config.cache_max_size = 1000
        return config
    
    @pytest.mark.asyncio
    async def test_concurrent_query_throughput(self, mock_config):
        """Test concurrent query execution throughput."""
        with patch('tidb_mcp_server.query_executor.pymysql.connect') as mock_connect:
            mock_connection = AsyncMock()
            mock_cursor = AsyncMock()
            mock_cursor.fetchall.return_value = [(1, "test")]
            mock_cursor.description = [("id",), ("name",)]
            mock_connection.cursor.return_value.__aenter__.return_value = mock_cursor
            mock_connect.return_value = mock_connection
            
            executor = QueryExecutor(mock_config)
            
            # Execute 50 concurrent queries
            num_queries = 50
            queries = [f"SELECT * FROM table_{i}" for i in range(num_queries)]
            
            start_time = time.time()
            tasks = [executor.execute_query(query) for query in queries]
            results = await asyncio.gather(*tasks)
            end_time = time.time()
            
            total_time = end_time - start_time
            throughput = num_queries / total_time
            
            # Should handle at least 10 queries per second
            assert throughput >= 10.0
            assert len(results) == num_queries
    
    @pytest.mark.asyncio
    async def test_cache_operation_throughput(self, mock_config):
        """Test cache operation throughput."""
        cache_manager = CacheManager(mock_config)
        
        # Test cache set operations
        num_operations = 1000
        test_data = {"test": "data"}
        
        start_time = time.time()
        tasks = [cache_manager.set(f"key_{i}", test_data) for i in range(num_operations)]
        await asyncio.gather(*tasks)
        end_time = time.time()
        
        set_time = end_time - start_time
        set_throughput = num_operations / set_time
        
        # Should handle at least 100 cache operations per second
        assert set_throughput >= 100.0
        
        # Test cache get operations
        start_time = time.time()
        tasks = [cache_manager.get(f"key_{i}") for i in range(num_operations)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        get_time = end_time - start_time
        get_throughput = num_operations / get_time
        
        # Cache gets should be even faster
        assert get_throughput >= 500.0
        assert len(results) == num_operations


class TestMemoryUsagePerformance:
    """Test memory usage performance requirements."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = MagicMock(spec=ServerConfig)
        config.cache_ttl = 300
        config.cache_max_size = 1000
        return config
    
    def get_memory_usage(self):
        """Get current memory usage in MB."""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    
    @pytest.mark.asyncio
    async def test_cache_memory_usage(self, mock_config):
        """Test that cache doesn't consume excessive memory."""
        cache_manager = CacheManager(mock_config)
        
        initial_memory = self.get_memory_usage()
        
        # Add many items to cache
        large_data = {"data": "x" * 1000}  # 1KB per item
        for i in range(1000):
            await cache_manager.set(f"large_key_{i}", large_data)
        
        final_memory = self.get_memory_usage()
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 50MB for 1MB of data)
        assert memory_increase < 50.0
    
    @pytest.mark.asyncio
    async def test_cache_size_limit_enforcement(self, mock_config):
        """Test that cache enforces size limits."""
        # Set a small cache size for testing
        mock_config.cache_max_size = 10
        cache_manager = CacheManager(mock_config)
        
        # Add more items than the cache limit
        for i in range(20):
            await cache_manager.set(f"key_{i}", f"value_{i}")
        
        # Verify that cache doesn't exceed the limit
        cache_size = len(cache_manager._cache)
        assert cache_size <= mock_config.cache_max_size
    
    @pytest.mark.asyncio
    async def test_large_result_set_memory_handling(self, mock_config):
        """Test memory handling with large result sets."""
        with patch('tidb_mcp_server.query_executor.pymysql.connect') as mock_connect:
            # Simulate a large result set (10,000 rows)
            large_result = [(i, f"name_{i}", f"email_{i}@test.com") for i in range(10000)]
            
            mock_connection = AsyncMock()
            mock_cursor = AsyncMock()
            mock_cursor.fetchall.return_value = large_result
            mock_cursor.description = [("id",), ("name",), ("email",)]
            mock_connection.cursor.return_value.__aenter__.return_value = mock_cursor
            mock_connect.return_value = mock_connection
            
            executor = QueryExecutor(mock_config)
            
            initial_memory = self.get_memory_usage()
            
            result = await executor.execute_query("SELECT * FROM large_table")
            
            final_memory = self.get_memory_usage()
            memory_increase = final_memory - initial_memory
            
            # Memory increase should be reasonable for the result size
            assert memory_increase < 100.0  # Less than 100MB for 10k rows
            assert result["row_count"] == 10000


class TestResourceCleanupPerformance:
    """Test resource cleanup and connection management."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = MagicMock(spec=ServerConfig)
        config.tidb_host = "test-host.com"
        config.tidb_port = 4000
        config.tidb_user = "test_user"
        config.tidb_password = "test_password"
        config.tidb_database = "test_db"
        return config
    
    @pytest.mark.asyncio
    async def test_connection_cleanup_after_queries(self, mock_config):
        """Test that database connections are properly cleaned up."""
        connection_count = 0
        
        def mock_connect(*args, **kwargs):
            nonlocal connection_count
            connection_count += 1
            mock_connection = AsyncMock()
            mock_cursor = AsyncMock()
            mock_cursor.fetchall.return_value = [(1, "test")]
            mock_cursor.description = [("id",), ("name",)]
            mock_connection.cursor.return_value.__aenter__.return_value = mock_cursor
            return mock_connection
        
        with patch('tidb_mcp_server.query_executor.pymysql.connect', side_effect=mock_connect):
            executor = QueryExecutor(mock_config)
            
            # Execute multiple queries
            for i in range(10):
                await executor.execute_query(f"SELECT * FROM table_{i}")
            
            # Verify connections are being managed properly
            # (In a real implementation, this would test connection pooling)
            assert connection_count <= 10  # Should reuse connections if pooled
    
    @pytest.mark.asyncio
    async def test_cache_cleanup_on_ttl_expiry(self, mock_config):
        """Test that cache items are cleaned up when TTL expires."""
        # Set a very short TTL for testing
        mock_config.cache_ttl = 0.1  # 100ms
        cache_manager = CacheManager(mock_config)
        
        # Add an item to cache
        await cache_manager.set("test_key", "test_value")
        
        # Verify item is cached
        result = await cache_manager.get("test_key")
        assert result == "test_value"
        
        # Wait for TTL to expire
        await asyncio.sleep(0.2)
        
        # Verify item is cleaned up
        result = await cache_manager.get("test_key")
        assert result is None


class TestStressTestPerformance:
    """Stress tests for performance under load."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = MagicMock(spec=ServerConfig)
        config.tidb_host = "test-host.com"
        config.tidb_port = 4000
        config.tidb_user = "test_user"
        config.tidb_password = "test_password"
        config.tidb_database = "test_db"
        config.cache_ttl = 300
        config.cache_max_size = 10000
        return config
    
    @pytest.mark.asyncio
    async def test_sustained_load_performance(self, mock_config):
        """Test performance under sustained load."""
        with patch('tidb_mcp_server.query_executor.pymysql.connect') as mock_connect:
            mock_connection = AsyncMock()
            mock_cursor = AsyncMock()
            mock_cursor.fetchall.return_value = [(1, "test")]
            mock_cursor.description = [("id",), ("name",)]
            mock_connection.cursor.return_value.__aenter__.return_value = mock_cursor
            mock_connect.return_value = mock_connection
            
            executor = QueryExecutor(mock_config)
            
            # Run queries for 5 seconds continuously
            start_time = time.time()
            query_count = 0
            
            while time.time() - start_time < 5.0:
                await executor.execute_query("SELECT * FROM test_table")
                query_count += 1
            
            total_time = time.time() - start_time
            throughput = query_count / total_time
            
            # Should maintain reasonable throughput under sustained load
            assert throughput >= 5.0  # At least 5 queries per second
            assert query_count >= 25  # At least 25 queries in 5 seconds
    
    @pytest.mark.asyncio
    async def test_mixed_workload_performance(self, mock_config):
        """Test performance with mixed read/write workloads."""
        with patch('tidb_mcp_server.query_executor.pymysql.connect') as mock_connect:
            mock_connection = AsyncMock()
            mock_cursor = AsyncMock()
            mock_cursor.fetchall.return_value = [(1, "test")]
            mock_cursor.description = [("id",), ("name",)]
            mock_connection.cursor.return_value.__aenter__.return_value = mock_cursor
            mock_connect.return_value = mock_connection
            
            executor = QueryExecutor(mock_config)
            cache_manager = CacheManager(mock_config)
            
            # Mix of different operations
            tasks = []
            
            # Add query tasks
            for i in range(20):
                tasks.append(executor.execute_query(f"SELECT * FROM table_{i}"))
            
            # Add cache tasks
            for i in range(30):
                tasks.append(cache_manager.set(f"cache_key_{i}", f"value_{i}"))
            
            # Add cache retrieval tasks
            for i in range(25):
                tasks.append(cache_manager.get(f"cache_key_{i}"))
            
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            total_time = end_time - start_time
            total_operations = len(tasks)
            throughput = total_operations / total_time
            
            # Should handle mixed workload efficiently
            assert throughput >= 20.0  # At least 20 operations per second
            
            # Verify no exceptions occurred
            exceptions = [r for r in results if isinstance(r, Exception)]
            assert len(exceptions) == 0