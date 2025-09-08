"""
Performance benchmark tests for MCP Schema Management system.

This module contains performance benchmarks to ensure the MCP schema management
system meets performance requirements and to identify potential bottlenecks.
"""

import pytest
import asyncio
import time
import statistics
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any
import concurrent.futures

from backend.schema_management.manager import MCPSchemaManager
from backend.schema_management.client import EnhancedMCPClient
from backend.schema_management.dynamic_validator import DynamicDataValidator, DynamicValidationConfig
from backend.schema_management.config import MCPSchemaConfig
from backend.schema_management.models import (
    DatabaseInfo, TableInfo, TableSchema, ColumnInfo, ValidationResult
)


@pytest.mark.benchmark
class TestMCPPerformanceBenchmarks:
    """Performance benchmark tests for MCP operations."""
    
    @pytest.fixture
    def benchmark_config(self):
        """Create configuration optimized for benchmarking."""
        return MCPSchemaConfig(
            mcp_server_url="http://localhost:8000",
            connection_timeout=5,
            request_timeout=10,
            max_retries=1,  # Fewer retries for faster benchmarks
            retry_delay=0.1,
            cache_ttl=300,
            enable_caching=True,
            fallback_enabled=True
        )
    
    @pytest.fixture
    def benchmark_manager(self, benchmark_config):
        """Create schema manager for benchmarking."""
        with patch('backend.schema_management.manager.EnhancedMCPClient') as mock_client_class:
            mock_client = Mock(spec=EnhancedMCPClient)
            mock_client_class.return_value = mock_client
            
            # Mock fast responses for benchmarking
            mock_databases = [
                {"name": f"db_{i}", "charset": "utf8mb4", "collation": "utf8mb4_general_ci", "accessible": True}
                for i in range(10)
            ]
            mock_client._send_request = AsyncMock(return_value=mock_databases)
            
            manager = MCPSchemaManager(benchmark_config)
            manager.client = mock_client
            return manager
    
    @pytest.fixture
    def large_schema(self):
        """Create a large table schema for performance testing."""
        columns = []
        for i in range(100):  # 100 columns
            columns.append(ColumnInfo(
                name=f"column_{i}",
                data_type="varchar" if i % 2 == 0 else "decimal",
                is_nullable=i % 3 == 0,
                default_value=None,
                is_primary_key=i == 0,
                is_foreign_key=i % 10 == 0 and i > 0,
                max_length=255 if i % 2 == 0 else None,
                precision=10 if i % 2 == 1 else None,
                scale=2 if i % 2 == 1 else None
            ))
        
        return TableSchema(
            database="benchmark_db",
            table="large_table",
            columns=columns,
            indexes=[],
            primary_keys=["column_0"],
            foreign_keys=[],
            constraints=[]
        )
    
    @pytest.mark.asyncio
    async def test_database_discovery_performance(self, benchmark_manager):
        """Benchmark database discovery performance."""
        # Warm up
        await benchmark_manager.discover_databases()
        
        # Benchmark multiple calls
        times = []
        for _ in range(10):
            start_time = time.perf_counter()
            databases = await benchmark_manager.discover_databases()
            end_time = time.perf_counter()
            
            times.append((end_time - start_time) * 1000)  # Convert to milliseconds
            assert len(databases) > 0
        
        # Performance assertions
        avg_time = statistics.mean(times)
        max_time = max(times)
        min_time = min(times)
        
        print(f"Database discovery - Avg: {avg_time:.2f}ms, Min: {min_time:.2f}ms, Max: {max_time:.2f}ms")
        
        # Should complete quickly (cached calls should be very fast)
        assert avg_time < 50  # Average under 50ms
        assert max_time < 100  # No call over 100ms
    
    @pytest.mark.asyncio
    async def test_table_listing_performance(self, benchmark_manager):
        """Benchmark table listing performance."""
        # Mock table response
        mock_tables = [
            {"name": f"table_{i}", "type": "BASE TABLE", "engine": "InnoDB", "rows": 1000, "size_mb": 1.0}
            for i in range(50)  # 50 tables
        ]
        benchmark_manager.client._send_request = AsyncMock(return_value=mock_tables)
        
        # Benchmark multiple calls
        times = []
        for _ in range(10):
            start_time = time.perf_counter()
            tables = await benchmark_manager.get_tables("test_db")
            end_time = time.perf_counter()
            
            times.append((end_time - start_time) * 1000)
            assert len(tables) == 50
        
        # Performance assertions
        avg_time = statistics.mean(times)
        max_time = max(times)
        
        print(f"Table listing - Avg: {avg_time:.2f}ms, Max: {max_time:.2f}ms")
        
        assert avg_time < 100  # Average under 100ms
        assert max_time < 200  # No call over 200ms
    
    @pytest.mark.asyncio
    async def test_schema_retrieval_performance(self, benchmark_manager, large_schema):
        """Benchmark schema retrieval performance with large schemas."""
        from backend.schema_management.models import DetailedTableSchema
        
        # Mock large schema response
        detailed_schema = DetailedTableSchema(
            schema=large_schema,
            sample_data=[{f"column_{i}": f"value_{i}" for i in range(10)}],  # Sample with 10 columns
            discovery_time_ms=50
        )
        benchmark_manager.client.get_table_schema_detailed = AsyncMock(return_value=detailed_schema)
        
        # Benchmark multiple calls
        times = []
        for _ in range(10):
            start_time = time.perf_counter()
            schema = await benchmark_manager.get_table_schema("benchmark_db", "large_table")
            end_time = time.perf_counter()
            
            times.append((end_time - start_time) * 1000)
            assert schema is not None
            assert len(schema.columns) == 100
        
        # Performance assertions
        avg_time = statistics.mean(times)
        max_time = max(times)
        
        print(f"Large schema retrieval - Avg: {avg_time:.2f}ms, Max: {max_time:.2f}ms")
        
        assert avg_time < 150  # Average under 150ms for large schema
        assert max_time < 300  # No call over 300ms
    
    @pytest.mark.asyncio
    async def test_concurrent_operations_performance(self, benchmark_manager):
        """Benchmark concurrent operations performance."""
        async def operation_worker(worker_id: int) -> float:
            """Worker function that performs multiple operations."""
            start_time = time.perf_counter()
            
            # Perform multiple operations
            databases = await benchmark_manager.discover_databases()
            tables = await benchmark_manager.get_tables("test_db")
            
            end_time = time.perf_counter()
            return (end_time - start_time) * 1000
        
        # Run concurrent workers
        num_workers = 20
        start_time = time.perf_counter()
        
        tasks = [operation_worker(i) for i in range(num_workers)]
        worker_times = await asyncio.gather(*tasks)
        
        total_time = (time.perf_counter() - start_time) * 1000
        
        # Performance assertions
        avg_worker_time = statistics.mean(worker_times)
        max_worker_time = max(worker_times)
        
        print(f"Concurrent operations - Total: {total_time:.2f}ms, Avg worker: {avg_worker_time:.2f}ms, Max worker: {max_worker_time:.2f}ms")
        
        assert total_time < 2000  # Total time under 2 seconds
        assert avg_worker_time < 200  # Average worker time under 200ms
        assert max_worker_time < 500  # No worker over 500ms
    
    def test_cache_performance_scaling(self, benchmark_manager):
        """Benchmark cache performance with increasing load."""
        # Test cache performance with different numbers of entries
        entry_counts = [100, 500, 1000, 5000]
        results = {}
        
        for count in entry_counts:
            # Clear cache
            benchmark_manager._schema_cache.clear()
            benchmark_manager._cache_timestamps.clear()
            
            # Add entries
            start_time = time.perf_counter()
            for i in range(count):
                cache_key = f"test_key_{i}"
                test_data = {"id": i, "data": f"test_data_{i}"}
                benchmark_manager._set_cache(cache_key, test_data)
            set_time = (time.perf_counter() - start_time) * 1000
            
            # Retrieve entries
            start_time = time.perf_counter()
            hits = 0
            for i in range(count):
                cache_key = f"test_key_{i}"
                result = benchmark_manager._get_cache(cache_key)
                if result is not None:
                    hits += 1
            get_time = (time.perf_counter() - start_time) * 1000
            
            results[count] = {
                "set_time": set_time,
                "get_time": get_time,
                "hits": hits,
                "set_rate": count / (set_time / 1000),  # Operations per second
                "get_rate": count / (get_time / 1000)
            }
            
            print(f"Cache {count} entries - Set: {set_time:.2f}ms ({results[count]['set_rate']:.0f} ops/s), "
                  f"Get: {get_time:.2f}ms ({results[count]['get_rate']:.0f} ops/s), Hits: {hits}")
        
        # Performance assertions
        for count, result in results.items():
            assert result["set_rate"] > 1000  # At least 1000 set operations per second
            assert result["get_rate"] > 5000  # At least 5000 get operations per second
            assert result["hits"] == count    # All entries should be found
    
    def test_cache_eviction_performance(self, benchmark_manager):
        """Benchmark cache eviction performance."""
        # Simulate cache with eviction by patching
        original_set_cache = benchmark_manager._set_cache
        
        eviction_times = []
        
        def timed_set_cache_with_eviction(cache_key: str, data):
            max_cache_size = 1000  # Reasonable cache size
            
            start_time = time.perf_counter()
            
            if len(benchmark_manager._schema_cache) >= max_cache_size:
                # Find and remove oldest entry
                oldest_key = min(benchmark_manager._cache_timestamps.keys(),
                               key=lambda k: benchmark_manager._cache_timestamps[k])
                del benchmark_manager._schema_cache[oldest_key]
                del benchmark_manager._cache_timestamps[oldest_key]
                benchmark_manager._cache_stats["evictions"] += 1
            
            benchmark_manager._schema_cache[cache_key] = data
            benchmark_manager._cache_timestamps[cache_key] = datetime.now()
            
            eviction_time = (time.perf_counter() - start_time) * 1000
            eviction_times.append(eviction_time)
        
        benchmark_manager._set_cache = timed_set_cache_with_eviction
        
        # Fill cache beyond capacity to trigger evictions
        for i in range(1500):  # More than max_cache_size
            cache_key = f"eviction_test_{i}"
            test_data = {"id": i, "data": f"data_{i}"}
            benchmark_manager._set_cache(cache_key, test_data)
        
        # Analyze eviction performance
        eviction_times_with_eviction = [t for t in eviction_times if t > 0.01]  # Filter out very fast operations
        
        if eviction_times_with_eviction:
            avg_eviction_time = statistics.mean(eviction_times_with_eviction)
            max_eviction_time = max(eviction_times_with_eviction)
            
            print(f"Cache eviction - Avg: {avg_eviction_time:.3f}ms, Max: {max_eviction_time:.3f}ms")
            
            assert avg_eviction_time < 1.0  # Average eviction under 1ms
            assert max_eviction_time < 5.0  # No eviction over 5ms


@pytest.mark.benchmark
class TestValidationPerformanceBenchmarks:
    """Performance benchmarks for validation operations."""
    
    @pytest.fixture
    def benchmark_validator(self):
        """Create validator for benchmarking."""
        config = MCPSchemaConfig(
            mcp_server_url="http://localhost:8000",
            cache_ttl=300,
            enable_caching=True
        )
        
        with patch('backend.schema_management.manager.EnhancedMCPClient'):
            manager = MCPSchemaManager(config)
            
            # Mock financial schema
            financial_columns = [
                ColumnInfo("id", "int", False, None, True, False),
                ColumnInfo("period_date", "date", False, None, False, False),
                ColumnInfo("period_type", "varchar", False, None, False, False, max_length=20),
                ColumnInfo("revenue", "decimal", False, "0.00", False, False, precision=15, scale=2),
                ColumnInfo("expenses", "decimal", True, None, False, False, precision=15, scale=2),
                ColumnInfo("net_profit", "decimal", True, None, False, False, precision=15, scale=2)
            ]
            
            financial_schema = TableSchema(
                database="financial_db",
                table="financial_overview",
                columns=financial_columns,
                indexes=[],
                primary_keys=["id"],
                foreign_keys=[],
                constraints=[]
            )
            
            manager.get_table_schema = AsyncMock(return_value=financial_schema)
            
            validation_config = DynamicValidationConfig(
                strict_mode=True,
                validate_types=True,
                validate_constraints=True,
                validate_relationships=True
            )
            
            return DynamicDataValidator(manager, validation_config)
    
    @pytest.fixture
    def sample_financial_data(self):
        """Create sample financial data for validation benchmarks."""
        return {
            "id": 1,
            "period_date": datetime.now().date(),
            "period_type": "monthly",
            "revenue": Decimal("100000.00"),
            "expenses": Decimal("60000.00"),
            "net_profit": Decimal("40000.00")
        }
    
    @pytest.mark.asyncio
    async def test_single_validation_performance(self, benchmark_validator, sample_financial_data):
        """Benchmark single validation operation performance."""
        # Warm up
        await benchmark_validator.validate_against_schema(
            sample_financial_data, "financial_db", "financial_overview"
        )
        
        # Benchmark multiple validations
        times = []
        for _ in range(100):
            start_time = time.perf_counter()
            result = await benchmark_validator.validate_against_schema(
                sample_financial_data, "financial_db", "financial_overview"
            )
            end_time = time.perf_counter()
            
            times.append((end_time - start_time) * 1000)
            assert result.is_valid is True
        
        # Performance assertions
        avg_time = statistics.mean(times)
        max_time = max(times)
        min_time = min(times)
        
        print(f"Single validation - Avg: {avg_time:.2f}ms, Min: {min_time:.2f}ms, Max: {max_time:.2f}ms")
        
        assert avg_time < 10  # Average under 10ms
        assert max_time < 50  # No validation over 50ms
    
    @pytest.mark.asyncio
    async def test_batch_validation_performance(self, benchmark_validator):
        """Benchmark batch validation performance."""
        # Create batch of data
        batch_size = 1000
        batch_data = []
        
        for i in range(batch_size):
            data = {
                "id": i,
                "period_date": datetime.now().date(),
                "period_type": "monthly",
                "revenue": Decimal(f"{10000 + i}.00"),
                "expenses": Decimal(f"{6000 + i}.00"),
                "net_profit": Decimal(f"{4000 + i}.00")
            }
            batch_data.append(data)
        
        # Benchmark batch validation
        start_time = time.perf_counter()
        
        validation_tasks = [
            benchmark_validator.validate_against_schema(data, "financial_db", "financial_overview")
            for data in batch_data
        ]
        results = await asyncio.gather(*validation_tasks)
        
        end_time = time.perf_counter()
        total_time = (end_time - start_time) * 1000
        
        # Performance assertions
        avg_time_per_validation = total_time / batch_size
        validations_per_second = batch_size / (total_time / 1000)
        
        print(f"Batch validation - Total: {total_time:.2f}ms, Avg per item: {avg_time_per_validation:.2f}ms, "
              f"Rate: {validations_per_second:.0f} validations/sec")
        
        assert all(result.is_valid for result in results)
        assert avg_time_per_validation < 5  # Average under 5ms per validation
        assert validations_per_second > 200  # At least 200 validations per second
    
    @pytest.mark.asyncio
    async def test_validation_with_errors_performance(self, benchmark_validator):
        """Benchmark validation performance with error cases."""
        # Create data with various error types
        error_data_sets = [
            {
                "id": "not_an_int",  # Type error
                "period_date": datetime.now().date(),
                "period_type": "monthly",
                "revenue": Decimal("100000.00"),
                "expenses": Decimal("60000.00"),
                "net_profit": Decimal("40000.00")
            },
            {
                "id": 1,
                "period_date": datetime.now().date(),
                "period_type": "A" * 50,  # Length error
                "revenue": Decimal("100000.00"),
                "expenses": Decimal("60000.00"),
                "net_profit": Decimal("40000.00")
            },
            {
                "id": 1,
                "period_date": datetime.now().date(),
                "period_type": "monthly",
                "revenue": "not_a_decimal",  # Type error
                "expenses": Decimal("60000.00"),
                "net_profit": Decimal("40000.00")
            }
        ]
        
        # Benchmark error validation
        times = []
        for error_data in error_data_sets:
            for _ in range(10):  # Multiple runs per error type
                start_time = time.perf_counter()
                result = await benchmark_validator.validate_against_schema(
                    error_data, "financial_db", "financial_overview"
                )
                end_time = time.perf_counter()
                
                times.append((end_time - start_time) * 1000)
                assert result.is_valid is False
                assert len(result.errors) > 0
        
        # Performance assertions
        avg_time = statistics.mean(times)
        max_time = max(times)
        
        print(f"Error validation - Avg: {avg_time:.2f}ms, Max: {max_time:.2f}ms")
        
        assert avg_time < 15  # Error validation should still be fast
        assert max_time < 100  # No error validation over 100ms
    
    @pytest.mark.asyncio
    async def test_large_data_validation_performance(self, benchmark_validator):
        """Benchmark validation performance with large data objects."""
        # Create large data object
        large_data = {
            "id": 1,
            "period_date": datetime.now().date(),
            "period_type": "monthly",
            "revenue": Decimal("100000.00"),
            "expenses": Decimal("60000.00"),
            "net_profit": Decimal("40000.00")
        }
        
        # Add many additional fields (simulating large objects)
        for i in range(100):
            large_data[f"extra_field_{i}"] = f"value_{i}" * 10  # Longer values
        
        # Benchmark large data validation
        times = []
        for _ in range(10):
            start_time = time.perf_counter()
            result = await benchmark_validator.validate_against_schema(
                large_data, "financial_db", "financial_overview"
            )
            end_time = time.perf_counter()
            
            times.append((end_time - start_time) * 1000)
            # Should be valid for known fields, may have warnings for unknown fields
            assert isinstance(result, ValidationResult)
        
        # Performance assertions
        avg_time = statistics.mean(times)
        max_time = max(times)
        
        print(f"Large data validation - Avg: {avg_time:.2f}ms, Max: {max_time:.2f}ms")
        
        assert avg_time < 50  # Large data validation under 50ms average
        assert max_time < 200  # No large data validation over 200ms


@pytest.mark.benchmark
class TestMemoryPerformanceBenchmarks:
    """Memory usage and performance benchmarks."""
    
    @pytest.fixture
    def memory_manager(self):
        """Create manager for memory benchmarking."""
        config = MCPSchemaConfig(
            mcp_server_url="http://localhost:8000",
            cache_ttl=3600,  # Long TTL for memory testing
            enable_caching=True
        )
        
        with patch('backend.schema_management.manager.EnhancedMCPClient'):
            return MCPSchemaManager(config)
    
    def test_memory_usage_scaling(self, memory_manager):
        """Test memory usage scaling with cache size."""
        import sys
        
        # Measure memory usage at different cache sizes
        cache_sizes = [100, 500, 1000, 2000]
        memory_usage = {}
        
        for size in cache_sizes:
            # Clear cache
            memory_manager._schema_cache.clear()
            memory_manager._cache_timestamps.clear()
            
            # Add entries of known size
            test_data = {"data": "A" * 1000}  # ~1KB per entry
            
            for i in range(size):
                cache_key = f"memory_test_{i}"
                memory_manager._set_cache(cache_key, test_data)
            
            # Estimate memory usage
            cache_stats = memory_manager.get_cache_stats()
            memory_usage[size] = cache_stats.memory_usage_mb
            
            print(f"Cache size {size}: {cache_stats.memory_usage_mb:.2f} MB")
        
        # Memory usage should scale reasonably
        for size in cache_sizes:
            expected_min_mb = (size * 1000) / (1024 * 1024)  # Minimum expected
            expected_max_mb = expected_min_mb * 5  # Allow for overhead
            
            assert memory_usage[size] >= expected_min_mb
            assert memory_usage[size] <= expected_max_mb
    
    def test_memory_leak_detection(self, memory_manager):
        """Test for memory leaks in cache operations."""
        import gc
        
        # Baseline memory usage
        gc.collect()
        initial_cache_size = len(memory_manager._schema_cache)
        
        # Perform many cache operations
        for cycle in range(10):
            # Add many entries
            for i in range(1000):
                cache_key = f"leak_test_{cycle}_{i}"
                test_data = {"cycle": cycle, "item": i, "data": "test" * 100}
                memory_manager._set_cache(cache_key, test_data)
            
            # Clear cache
            memory_manager._schema_cache.clear()
            memory_manager._cache_timestamps.clear()
            
            # Force garbage collection
            gc.collect()
        
        # Final memory usage should be similar to initial
        final_cache_size = len(memory_manager._schema_cache)
        
        assert final_cache_size == initial_cache_size
        print(f"Memory leak test - Initial: {initial_cache_size}, Final: {final_cache_size}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "benchmark"])