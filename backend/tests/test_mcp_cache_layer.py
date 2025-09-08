"""
Comprehensive tests for MCP Cache Layer functionality.

This module tests the caching mechanisms used in MCP schema management,
including cache performance, eviction policies, and statistics.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import time

from backend.schema_management.manager import MCPSchemaManager
from backend.schema_management.config import MCPSchemaConfig
from backend.schema_management.models import CacheStats, DatabaseInfo, TableInfo


class TestMCPCacheLayer:
    """Test cases for MCP cache layer functionality."""
    
    @pytest.fixture
    def cache_config(self):
        """Create cache configuration for testing."""
        return MCPSchemaConfig(
            mcp_server_url="http://test-server:8000",
            cache_ttl=300,  # 5 minutes
            enable_caching=True,
            fallback_enabled=True
        )
    
    @pytest.fixture
    def no_cache_config(self):
        """Create configuration with caching disabled."""
        return MCPSchemaConfig(
            mcp_server_url="http://test-server:8000",
            cache_ttl=300,
            enable_caching=False,
            fallback_enabled=True
        )
    
    @pytest.fixture
    def schema_manager(self, cache_config):
        """Create schema manager with caching enabled."""
        with patch('backend.schema_management.manager.EnhancedMCPClient'):
            return MCPSchemaManager(cache_config)
    
    @pytest.fixture
    def no_cache_manager(self, no_cache_config):
        """Create schema manager with caching disabled."""
        with patch('backend.schema_management.manager.EnhancedMCPClient'):
            return MCPSchemaManager(no_cache_config)
    
    def test_cache_key_generation_consistency(self, schema_manager):
        """Test that cache keys are generated consistently."""
        # Same parameters in different order should produce same key
        key1 = schema_manager._get_cache_key("operation", param1="value1", param2="value2")
        key2 = schema_manager._get_cache_key("operation", param2="value2", param1="value1")
        
        assert key1 == key2
        
        # Different operations should produce different keys
        key3 = schema_manager._get_cache_key("other_operation", param1="value1", param2="value2")
        assert key1 != key3
        
        # Different parameter values should produce different keys
        key4 = schema_manager._get_cache_key("operation", param1="different", param2="value2")
        assert key1 != key4
    
    def test_cache_key_format(self, schema_manager):
        """Test cache key format and structure."""
        key = schema_manager._get_cache_key("test_op", db="test_db", table="test_table")
        
        assert "test_op" in key
        assert "db:test_db" in key
        assert "table:test_table" in key
        assert key.count(":") >= 3  # operation + 2 parameters
    
    def test_cache_validity_fresh_entry(self, schema_manager):
        """Test cache validity for fresh entries."""
        cache_key = "test_key"
        schema_manager._cache_timestamps[cache_key] = datetime.now()
        
        assert schema_manager._is_cache_valid(cache_key) is True
    
    def test_cache_validity_expired_entry(self, schema_manager):
        """Test cache validity for expired entries."""
        cache_key = "test_key"
        # Set timestamp to 10 minutes ago (TTL is 5 minutes)
        schema_manager._cache_timestamps[cache_key] = datetime.now() - timedelta(minutes=10)
        
        assert schema_manager._is_cache_valid(cache_key) is False
    
    def test_cache_validity_missing_entry(self, schema_manager):
        """Test cache validity for missing entries."""
        cache_key = "nonexistent_key"
        
        assert schema_manager._is_cache_valid(cache_key) is False
    
    def test_cache_validity_disabled_caching(self, no_cache_manager):
        """Test cache validity when caching is disabled."""
        cache_key = "test_key"
        no_cache_manager._cache_timestamps[cache_key] = datetime.now()
        
        assert no_cache_manager._is_cache_valid(cache_key) is False
    
    def test_set_cache_enabled(self, schema_manager):
        """Test setting cache when caching is enabled."""
        cache_key = "test_key"
        test_data = {"test": "data"}
        
        schema_manager._set_cache(cache_key, test_data)
        
        assert cache_key in schema_manager._schema_cache
        assert schema_manager._schema_cache[cache_key] == test_data
        assert cache_key in schema_manager._cache_timestamps
        assert isinstance(schema_manager._cache_timestamps[cache_key], datetime)
    
    def test_set_cache_disabled(self, no_cache_manager):
        """Test setting cache when caching is disabled."""
        cache_key = "test_key"
        test_data = {"test": "data"}
        
        no_cache_manager._set_cache(cache_key, test_data)
        
        # Should not store anything when caching is disabled
        assert cache_key not in no_cache_manager._schema_cache
        assert cache_key not in no_cache_manager._cache_timestamps
    
    def test_get_cache_hit(self, schema_manager):
        """Test cache hit scenario."""
        cache_key = "test_key"
        test_data = {"test": "data"}
        
        # Set up cache entry
        schema_manager._schema_cache[cache_key] = test_data
        schema_manager._cache_timestamps[cache_key] = datetime.now()
        
        result = schema_manager._get_cache(cache_key)
        
        assert result == test_data
        assert schema_manager._cache_stats["hits"] == 1
        assert schema_manager._cache_stats["misses"] == 0
    
    def test_get_cache_miss_expired(self, schema_manager):
        """Test cache miss due to expiration."""
        cache_key = "test_key"
        test_data = {"test": "data"}
        
        # Set up expired cache entry
        schema_manager._schema_cache[cache_key] = test_data
        schema_manager._cache_timestamps[cache_key] = datetime.now() - timedelta(minutes=10)
        
        result = schema_manager._get_cache(cache_key)
        
        assert result is None
        assert schema_manager._cache_stats["hits"] == 0
        assert schema_manager._cache_stats["misses"] == 1
    
    def test_get_cache_miss_not_found(self, schema_manager):
        """Test cache miss for non-existent key."""
        result = schema_manager._get_cache("nonexistent_key")
        
        assert result is None
        assert schema_manager._cache_stats["hits"] == 0
        assert schema_manager._cache_stats["misses"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])