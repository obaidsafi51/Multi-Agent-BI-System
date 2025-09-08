"""
Tests against real MCP server instance.

This module contains tests that run against an actual TiDB MCP server instance
to verify real-world functionality and integration.

These tests are marked as 'real_server' and can be run separately when a
real MCP server is available.
"""

import pytest
import asyncio
import os
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any, List, Optional

from backend.schema_management.manager import MCPSchemaManager
from backend.schema_management.client import EnhancedMCPClient, MCPConnectionError, MCPRequestError
from backend.schema_management.dynamic_validator import DynamicDataValidator, DynamicValidationConfig
from backend.schema_management.config import MCPSchemaConfig
from backend.schema_management.models import (
    ValidationResult, DatabaseInfo, TableInfo, TableSchema
)


def pytest_configure(config):
    """Configure pytest markers for real server tests."""
    config.addinivalue_line(
        "markers", "real_server: mark test as requiring a real MCP server instance"
    )


@pytest.mark.real_server
class TestRealMCPServerConnection:
    """Tests for real MCP server connection and basic operations."""
    
    @pytest.fixture
    def real_server_config(self):
        """Create configuration for real server testing."""
        server_url = os.getenv("TIDB_MCP_SERVER_URL", "http://localhost:8000")
        
        return MCPSchemaConfig(
            mcp_server_url=server_url,
            connection_timeout=30,
            request_timeout=60,
            max_retries=3,
            retry_delay=2.0,
            cache_ttl=300,
            enable_caching=True,
            fallback_enabled=True
        )
    
    @pytest.fixture
    async def real_manager(self, real_server_config):
        """Create manager connected to real server."""
        manager = MCPSchemaManager(real_server_config)
        
        # Attempt to connect
        try:
            connected = await manager.connect()
            if not connected:
                pytest.skip("Cannot connect to real MCP server")
            
            yield manager
            
        except Exception as e:
            pytest.skip(f"Real MCP server not available: {e}")
        finally:
            await manager.disconnect()
    
    @pytest.mark.asyncio
    async def test_real_server_health_check(self, real_manager):
        """Test health check against real server."""
        health = await real_manager.health_check()
        assert health is True, "Real MCP server should be healthy"
    
    @pytest.mark.asyncio
    async def test_real_database_discovery(self, real_manager):
        """Test database discovery against real server."""
        databases = await real_manager.discover_databases()
        
        assert isinstance(databases, list), "Should return list of databases"
        
        if len(databases) > 0:
            # Verify database structure
            db = databases[0]
            assert isinstance(db, DatabaseInfo)
            assert hasattr(db, 'name')
            assert hasattr(db, 'charset')
            assert hasattr(db, 'collation')
            assert hasattr(db, 'accessible')
            
            print(f"Found {len(databases)} databases:")
            for db in databases[:5]:  # Print first 5
                print(f"  - {db.name} ({db.charset}/{db.collation})")
    
    @pytest.mark.asyncio
    async def test_real_table_discovery(self, real_manager):
        """Test table discovery against real server."""
        # First get databases
        databases = await real_manager.discover_databases()
        
        if len(databases) == 0:
            pytest.skip("No databases found on real server")
        
        # Test table discovery for first accessible database
        test_db = None
        for db in databases:
            if db.accessible:
                test_db = db
                break
        
        if not test_db:
            pytest.skip("No accessible databases found")
        
        tables = await real_manager.get_tables(test_db.name)
        
        assert isinstance(tables, list), "Should return list of tables"
        
        print(f"Found {len(tables)} tables in database '{test_db.name}':")
        for table in tables[:10]:  # Print first 10
            print(f"  - {table.name} ({table.type}, {table.rows} rows, {table.size_mb:.2f} MB)")
    
    @pytest.mark.asyncio
    async def test_real_schema_retrieval(self, real_manager):
        """Test schema retrieval against real server."""
        # Get databases and tables
        databases = await real_manager.discover_databases()
        
        if len(databases) == 0:
            pytest.skip("No databases found on real server")
        
        test_db = next((db for db in databases if db.accessible), None)
        if not test_db:
            pytest.skip("No accessible databases found")
        
        tables = await real_manager.get_tables(test_db.name)
        
        if len(tables) == 0:
            pytest.skip(f"No tables found in database '{test_db.name}'")
        
        # Test schema retrieval for first table
        test_table = tables[0]
        schema = await real_manager.get_table_schema(test_db.name, test_table.name)
        
        if schema is None:
            pytest.skip(f"Could not retrieve schema for table '{test_table.name}'")
        
        assert isinstance(schema, TableSchema)
        assert schema.database == test_db.name
        assert schema.table == test_table.name
        assert len(schema.columns) > 0
        
        print(f"Schema for {test_db.name}.{test_table.name}:")
        print(f"  Columns: {len(schema.columns)}")
        print(f"  Primary keys: {schema.primary_keys}")
        print(f"  Foreign keys: {len(schema.foreign_keys)}")
        
        # Print first few columns
        for col in schema.columns[:5]:
            nullable = "NULL" if col.is_nullable else "NOT NULL"
            pk = " (PK)" if col.is_primary_key else ""
            print(f"    {col.name}: {col.data_type} {nullable}{pk}")
    
    @pytest.mark.asyncio
    async def test_real_server_performance(self, real_manager):
        """Test performance characteristics against real server."""
        # Test database discovery performance
        start_time = datetime.now()
        databases = await real_manager.discover_databases()
        db_discovery_time = (datetime.now() - start_time).total_seconds() * 1000
        
        print(f"Database discovery time: {db_discovery_time:.2f}ms")
        assert db_discovery_time < 10000, "Database discovery should complete within 10 seconds"
        
        if len(databases) > 0:
            test_db = next((db for db in databases if db.accessible), None)
            if test_db:
                # Test table discovery performance
                start_time = datetime.now()
                tables = await real_manager.get_tables(test_db.name)
                table_discovery_time = (datetime.now() - start_time).total_seconds() * 1000
                
                print(f"Table discovery time: {table_discovery_time:.2f}ms")
                assert table_discovery_time < 15000, "Table discovery should complete within 15 seconds"
                
                if len(tables) > 0:
                    # Test schema retrieval performance
                    start_time = datetime.now()
                    schema = await real_manager.get_table_schema(test_db.name, tables[0].name)
                    schema_retrieval_time = (datetime.now() - start_time).total_seconds() * 1000
                    
                    print(f"Schema retrieval time: {schema_retrieval_time:.2f}ms")
                    assert schema_retrieval_time < 20000, "Schema retrieval should complete within 20 seconds"
    
    @pytest.mark.asyncio
    async def test_real_server_caching(self, real_manager):
        """Test caching behavior against real server."""
        # Clear cache
        await real_manager.refresh_schema_cache("all")
        
        # First call - should hit server
        start_time = datetime.now()
        databases1 = await real_manager.discover_databases()
        first_call_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Second call - should use cache
        start_time = datetime.now()
        databases2 = await real_manager.discover_databases()
        second_call_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Results should be identical
        assert len(databases1) == len(databases2)
        if len(databases1) > 0:
            assert databases1[0].name == databases2[0].name
        
        # Second call should be faster (cached)
        print(f"First call: {first_call_time:.2f}ms, Second call: {second_call_time:.2f}ms")
        
        # Cache should provide some performance benefit
        # (Allow some margin as network conditions may vary)
        cache_benefit_ratio = second_call_time / first_call_time if first_call_time > 0 else 1
        assert cache_benefit_ratio <= 1.5, "Cache should provide performance benefit"
        
        # Verify cache statistics
        cache_stats = real_manager.get_cache_stats()
        assert cache_stats.total_entries > 0, "Cache should have entries"
        assert cache_stats.hit_rate > 0, "Should have cache hits"


@pytest.mark.real_server
class TestRealMCPServerValidation:
    """Tests for validation against real MCP server."""
    
    @pytest.fixture
    async def real_validator(self):
        """Create validator connected to real server."""
        server_url = os.getenv("TIDB_MCP_SERVER_URL", "http://localhost:8000")
        
        config = MCPSchemaConfig(
            mcp_server_url=server_url,
            connection_timeout=30,
            request_timeout=60,
            cache_ttl=300,
            enable_caching=True,
            fallback_enabled=True
        )
        
        manager = MCPSchemaManager(config)
        
        try:
            connected = await manager.connect()
            if not connected:
                pytest.skip("Cannot connect to real MCP server")
            
            validation_config = DynamicValidationConfig(
                strict_mode=False,  # Less strict for real server testing
                validate_types=True,
                validate_constraints=True,
                validate_relationships=True,
                fallback_to_static=True
            )
            
            validator = DynamicDataValidator(manager, validation_config)
            
            yield validator
            
        except Exception as e:
            pytest.skip(f"Real MCP server not available: {e}")
        finally:
            await manager.disconnect()
    
    @pytest.mark.asyncio
    async def test_real_validation_workflow(self, real_validator):
        """Test validation workflow against real server."""
        # Get available databases and tables
        databases = await real_validator.schema_manager.discover_databases()
        
        if len(databases) == 0:
            pytest.skip("No databases available for validation testing")
        
        test_db = next((db for db in databases if db.accessible), None)
        if not test_db:
            pytest.skip("No accessible databases for validation testing")
        
        tables = await real_validator.schema_manager.get_tables(test_db.name)
        
        if len(tables) == 0:
            pytest.skip(f"No tables available in database '{test_db.name}'")
        
        # Find a suitable table for testing
        test_table = None
        for table in tables:
            schema = await real_validator.schema_manager.get_table_schema(test_db.name, table.name)
            if schema and len(schema.columns) > 0:
                test_table = table
                break
        
        if not test_table:
            pytest.skip("No suitable tables found for validation testing")
        
        # Get the schema for validation testing
        schema = await real_validator.schema_manager.get_table_schema(test_db.name, test_table.name)
        
        # Create test data based on schema
        test_data = {}
        for col in schema.columns[:5]:  # Test first 5 columns
            if col.is_auto_increment:
                continue  # Skip auto-increment columns
            
            # Generate appropriate test data based on column type
            if col.data_type.lower() in ['int', 'integer', 'bigint']:
                test_data[col.name] = 123
            elif col.data_type.lower() in ['varchar', 'char', 'text']:
                max_len = min(col.max_length or 50, 50)
                test_data[col.name] = "test_value"[:max_len]
            elif col.data_type.lower() in ['decimal', 'numeric']:
                test_data[col.name] = Decimal("123.45")
            elif col.data_type.lower() == 'date':
                test_data[col.name] = date.today()
            elif col.data_type.lower() in ['timestamp', 'datetime']:
                test_data[col.name] = datetime.now()
            elif col.is_nullable:
                test_data[col.name] = None
        
        # Perform validation
        result = await real_validator.validate_against_schema(
            test_data, test_db.name, test_table.name
        )
        
        assert isinstance(result, ValidationResult)
        print(f"Validation result for {test_db.name}.{test_table.name}:")
        print(f"  Valid: {result.is_valid}")
        print(f"  Errors: {len(result.errors)}")
        print(f"  Warnings: {len(result.warnings)}")
        print(f"  Validated fields: {len(result.validated_fields)}")
        print(f"  Validation time: {result.validation_time_ms}ms")
        
        # Should have validated some fields
        assert len(result.validated_fields) > 0
        
        # Validation should complete reasonably quickly
        assert result.validation_time_ms < 5000  # Under 5 seconds
    
    @pytest.mark.asyncio
    async def test_real_validation_error_handling(self, real_validator):
        """Test validation error handling against real server."""
        # Test with non-existent database/table
        invalid_data = {"field": "value"}
        
        result = await real_validator.validate_against_schema(
            invalid_data, "nonexistent_db", "nonexistent_table"
        )
        
        # Should handle gracefully (fallback or error)
        assert isinstance(result, ValidationResult)
        
        # If fallback is enabled, should not crash
        print(f"Validation of non-existent table:")
        print(f"  Valid: {result.is_valid}")
        print(f"  Errors: {len(result.errors)}")
        print(f"  Used fallback: {len(result.warnings) > 0}")


@pytest.mark.real_server
class TestRealMCPServerStress:
    """Stress tests against real MCP server."""
    
    @pytest.fixture
    async def stress_manager(self):
        """Create manager for stress testing."""
        server_url = os.getenv("TIDB_MCP_SERVER_URL", "http://localhost:8000")
        
        config = MCPSchemaConfig(
            mcp_server_url=server_url,
            connection_timeout=60,
            request_timeout=120,
            max_retries=5,
            retry_delay=1.0,
            cache_ttl=600,  # Longer cache for stress testing
            enable_caching=True,
            fallback_enabled=True
        )
        
        manager = MCPSchemaManager(config)
        
        try:
            connected = await manager.connect()
            if not connected:
                pytest.skip("Cannot connect to real MCP server for stress testing")
            
            yield manager
            
        except Exception as e:
            pytest.skip(f"Real MCP server not available for stress testing: {e}")
        finally:
            await manager.disconnect()
    
    @pytest.mark.asyncio
    async def test_concurrent_operations_stress(self, stress_manager):
        """Test concurrent operations under stress."""
        async def operation_worker(worker_id: int):
            """Worker function for stress testing."""
            try:
                # Perform multiple operations
                databases = await stress_manager.discover_databases()
                
                if len(databases) > 0:
                    db = databases[0]
                    tables = await stress_manager.get_tables(db.name)
                    
                    if len(tables) > 0:
                        table = tables[0]
                        schema = await stress_manager.get_table_schema(db.name, table.name)
                        return {"worker_id": worker_id, "success": True, "schema_columns": len(schema.columns) if schema else 0}
                
                return {"worker_id": worker_id, "success": True, "schema_columns": 0}
                
            except Exception as e:
                return {"worker_id": worker_id, "success": False, "error": str(e)}
        
        # Run many concurrent workers
        num_workers = 50
        start_time = datetime.now()
        
        tasks = [operation_worker(i) for i in range(num_workers)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        # Analyze results
        successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed_results = [r for r in results if isinstance(r, dict) and not r.get("success")]
        exception_results = [r for r in results if isinstance(r, Exception)]
        
        print(f"Stress test results ({num_workers} workers, {total_time:.2f}s):")
        print(f"  Successful: {len(successful_results)}")
        print(f"  Failed: {len(failed_results)}")
        print(f"  Exceptions: {len(exception_results)}")
        
        # Should handle most operations successfully
        success_rate = len(successful_results) / num_workers
        assert success_rate >= 0.8, f"Success rate should be at least 80%, got {success_rate:.2%}"
        
        # Should complete within reasonable time
        assert total_time < 120, f"Stress test should complete within 2 minutes, took {total_time:.2f}s"
        
        # Check cache effectiveness under stress
        cache_stats = stress_manager.get_cache_stats()
        print(f"Cache stats after stress test:")
        print(f"  Entries: {cache_stats.total_entries}")
        print(f"  Hit rate: {cache_stats.hit_rate:.2%}")
        print(f"  Evictions: {cache_stats.eviction_count}")
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, stress_manager):
        """Test memory usage under sustained load."""
        # Perform many operations to test memory usage
        for cycle in range(10):
            # Perform operations that should populate cache
            databases = await stress_manager.discover_databases()
            
            for db in databases[:3]:  # Limit to first 3 databases
                if db.accessible:
                    tables = await stress_manager.get_tables(db.name)
                    
                    for table in tables[:5]:  # Limit to first 5 tables
                        schema = await stress_manager.get_table_schema(db.name, table.name)
            
            # Check memory usage periodically
            if cycle % 3 == 0:
                cache_stats = stress_manager.get_cache_stats()
                print(f"Cycle {cycle}: Cache entries: {cache_stats.total_entries}, Memory: {cache_stats.memory_usage_mb:.2f} MB")
                
                # Memory usage should not grow unbounded
                assert cache_stats.memory_usage_mb < 100, "Memory usage should stay reasonable"
        
        # Final cache statistics
        final_stats = stress_manager.get_cache_stats()
        print(f"Final cache stats:")
        print(f"  Entries: {final_stats.total_entries}")
        print(f"  Memory usage: {final_stats.memory_usage_mb:.2f} MB")
        print(f"  Hit rate: {final_stats.hit_rate:.2%}")


if __name__ == "__main__":
    # Run only real server tests
    pytest.main([__file__, "-v", "-m", "real_server"])