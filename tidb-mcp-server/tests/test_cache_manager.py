"""
Unit tests for the cache management system.

Tests cache operations, TTL expiration, key management, and thread safety.
"""

import pytest
import time
import threading
from unittest.mock import patch
from typing import Any, Dict

from tidb_mcp_server.cache_manager import CacheManager, CacheEntry, CacheKeyGenerator


class TestCacheEntry:
    """Test cases for CacheEntry class."""
    
    def test_cache_entry_creation(self):
        """Test cache entry creation and initialization."""
        value = {"test": "data"}
        created_at = time.time()
        ttl = 300
        
        entry = CacheEntry(value=value, created_at=created_at, ttl_seconds=ttl)
        
        assert entry.value == value
        assert entry.created_at == created_at
        assert entry.ttl_seconds == ttl
        assert entry.access_count == 0
        assert entry.last_accessed == created_at
    
    def test_cache_entry_expiration(self):
        """Test cache entry expiration logic."""
        # Non-expired entry
        entry = CacheEntry(
            value="test",
            created_at=time.time(),
            ttl_seconds=300
        )
        assert not entry.is_expired()
        
        # Expired entry
        expired_entry = CacheEntry(
            value="test",
            created_at=time.time() - 400,  # 400 seconds ago
            ttl_seconds=300  # 5 minutes TTL
        )
        assert expired_entry.is_expired()
        
        # Never expires (TTL <= 0)
        never_expires = CacheEntry(
            value="test",
            created_at=time.time() - 1000,
            ttl_seconds=0
        )
        assert not never_expires.is_expired()
    
    def test_remaining_ttl(self):
        """Test remaining TTL calculation."""
        current_time = time.time()
        
        # Fresh entry
        entry = CacheEntry(
            value="test",
            created_at=current_time,
            ttl_seconds=300
        )
        remaining = entry.get_remaining_ttl()
        assert 299 <= remaining <= 300  # Allow for small time differences
        
        # Partially expired entry
        partial_entry = CacheEntry(
            value="test",
            created_at=current_time - 100,
            ttl_seconds=300
        )
        remaining = partial_entry.get_remaining_ttl()
        assert 199 <= remaining <= 201
        
        # Fully expired entry
        expired_entry = CacheEntry(
            value="test",
            created_at=current_time - 400,
            ttl_seconds=300
        )
        assert expired_entry.get_remaining_ttl() == 0
        
        # Never expires
        never_expires = CacheEntry(
            value="test",
            created_at=current_time,
            ttl_seconds=0
        )
        assert never_expires.get_remaining_ttl() == float('inf')
    
    def test_touch_updates_access_stats(self):
        """Test that touch() updates access statistics."""
        entry = CacheEntry(
            value="test",
            created_at=time.time(),
            ttl_seconds=300
        )
        
        initial_access_count = entry.access_count
        initial_last_accessed = entry.last_accessed
        
        time.sleep(0.01)  # Small delay to ensure time difference
        entry.touch()
        
        assert entry.access_count == initial_access_count + 1
        assert entry.last_accessed > initial_last_accessed


class TestCacheManager:
    """Test cases for CacheManager class."""
    
    def test_cache_manager_initialization(self):
        """Test cache manager initialization."""
        cache = CacheManager(default_ttl=600, max_size=500)
        
        assert cache._default_ttl == 600
        assert cache._max_size == 500
        assert cache.size() == 0
        
        stats = cache.get_stats()
        assert stats['size'] == 0
        assert stats['max_size'] == 500
        assert stats['hits'] == 0
        assert stats['misses'] == 0
    
    def test_basic_get_set_operations(self):
        """Test basic cache get and set operations."""
        cache = CacheManager(default_ttl=300, max_size=100)
        
        # Test cache miss
        result = cache.get("nonexistent")
        assert result is None
        
        # Test cache set and hit
        test_data = {"key": "value", "number": 42}
        cache.set("test_key", test_data)
        
        retrieved = cache.get("test_key")
        assert retrieved == test_data
        
        # Verify stats
        stats = cache.get_stats()
        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['size'] == 1
    
    def test_ttl_expiration(self):
        """Test TTL-based cache expiration."""
        cache = CacheManager(default_ttl=1, max_size=100)  # 1 second TTL
        
        # Set a value with short TTL
        cache.set("short_ttl", "test_value", ttl=1)
        
        # Should be available immediately
        assert cache.get("short_ttl") == "test_value"
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired and return None
        assert cache.get("short_ttl") is None
        
        # Verify expired entry was removed
        assert cache.size() == 0
    
    def test_custom_ttl(self):
        """Test setting custom TTL values."""
        cache = CacheManager(default_ttl=300, max_size=100)
        
        # Set with custom TTL
        cache.set("custom_ttl", "value", ttl=600)
        
        # Verify the entry exists
        assert cache.get("custom_ttl") == "value"
        
        # Set with default TTL (should use 300)
        cache.set("default_ttl", "value")
        
        # Both should exist
        assert cache.size() == 2
    
    def test_cache_invalidation_by_pattern(self):
        """Test cache invalidation using regex patterns."""
        cache = CacheManager(default_ttl=300, max_size=100)
        
        # Set multiple entries
        cache.set("user:123", "user_data_123")
        cache.set("user:456", "user_data_456")
        cache.set("product:789", "product_data_789")
        cache.set("session:abc", "session_data_abc")
        
        assert cache.size() == 4
        
        # Invalidate all user entries
        invalidated = cache.invalidate("^user:.*")
        assert invalidated == 2
        assert cache.size() == 2
        
        # Verify correct entries remain
        assert cache.get("user:123") is None
        assert cache.get("user:456") is None
        assert cache.get("product:789") == "product_data_789"
        assert cache.get("session:abc") == "session_data_abc"
    
    def test_cache_clear(self):
        """Test clearing all cache entries."""
        cache = CacheManager(default_ttl=300, max_size=100)
        
        # Add multiple entries
        for i in range(10):
            cache.set(f"key_{i}", f"value_{i}")
        
        assert cache.size() == 10
        
        # Clear cache
        cache.clear()
        
        assert cache.size() == 0
        
        # Verify stats are reset
        stats = cache.get_stats()
        assert stats['hits'] == 0
        assert stats['misses'] == 0
    
    def test_lru_eviction(self):
        """Test LRU eviction when cache reaches max size."""
        cache = CacheManager(default_ttl=300, max_size=3)
        
        # Fill cache to capacity
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        assert cache.size() == 3
        
        # Access key1 to make it more recently used
        cache.get("key1")
        
        # Add another entry, should evict key2 (least recently used)
        cache.set("key4", "value4")
        
        assert cache.size() == 3
        assert cache.get("key1") == "value1"  # Should still exist
        assert cache.get("key2") is None      # Should be evicted
        assert cache.get("key3") == "value3"  # Should still exist
        assert cache.get("key4") == "value4"  # Should exist
        
        # Verify eviction stats
        stats = cache.get_stats()
        assert stats['evictions'] == 1
    
    def test_expired_cleanup(self):
        """Test automatic cleanup of expired entries."""
        cache = CacheManager(default_ttl=1, max_size=100)
        
        # Add entries with short TTL
        cache.set("temp1", "value1", ttl=1)
        cache.set("temp2", "value2", ttl=1)
        cache.set("permanent", "value3", ttl=0)  # Never expires
        
        assert cache.size() == 3
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Trigger explicit cleanup
        removed_count = cache.cleanup_expired()
        
        # Expired entries should be cleaned up
        assert removed_count == 2
        assert cache.size() == 1
        assert cache.get("permanent") == "value3"
        
        # Verify cleanup stats
        stats = cache.get_stats()
        assert stats['expired_removals'] >= 2
    
    def test_get_keys_functionality(self):
        """Test getting cache keys with optional pattern filtering."""
        cache = CacheManager(default_ttl=300, max_size=100)
        
        # Add various keys
        cache.set("user:123", "data1")
        cache.set("user:456", "data2")
        cache.set("product:789", "data3")
        cache.set("session:abc", "data4")
        
        # Get all keys
        all_keys = cache.get_keys()
        assert len(all_keys) == 4
        assert set(all_keys) == {"user:123", "user:456", "product:789", "session:abc"}
        
        # Get keys matching pattern
        user_keys = cache.get_keys("^user:.*")
        assert len(user_keys) == 2
        assert set(user_keys) == {"user:123", "user:456"}
        
        # Test invalid pattern
        invalid_keys = cache.get_keys("[invalid")
        assert invalid_keys == []
    
    def test_thread_safety(self):
        """Test thread safety of cache operations."""
        cache = CacheManager(default_ttl=300, max_size=1000)
        results = []
        errors = []
        
        def worker(thread_id: int):
            """Worker function for threading test."""
            try:
                for i in range(100):
                    key = f"thread_{thread_id}_key_{i}"
                    value = f"thread_{thread_id}_value_{i}"
                    
                    # Set value
                    cache.set(key, value)
                    
                    # Get value
                    retrieved = cache.get(key)
                    if retrieved != value:
                        errors.append(f"Thread {thread_id}: Expected {value}, got {retrieved}")
                    
                    results.append((thread_id, i, retrieved == value))
            except Exception as e:
                errors.append(f"Thread {thread_id} error: {e}")
        
        # Create and start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        
        # Verify all operations succeeded
        successful_ops = sum(1 for _, _, success in results if success)
        assert successful_ops == 500  # 5 threads * 100 operations each
    
    def test_cache_statistics(self):
        """Test cache statistics tracking."""
        cache = CacheManager(default_ttl=300, max_size=100)
        
        # Initial stats
        stats = cache.get_stats()
        assert stats['hits'] == 0
        assert stats['misses'] == 0
        assert stats['hit_rate_percent'] == 0
        
        # Generate some cache activity
        cache.set("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss
        cache.get("key1")  # Hit
        
        stats = cache.get_stats()
        assert stats['hits'] == 2
        assert stats['misses'] == 1
        assert stats['hit_rate_percent'] == 66.67
        assert stats['total_requests'] == 3


class TestCacheKeyGenerator:
    """Test cases for CacheKeyGenerator utility class."""
    
    def test_databases_key(self):
        """Test database list key generation."""
        key = CacheKeyGenerator.databases_key()
        assert key == "db_list"
    
    def test_tables_key(self):
        """Test table list key generation."""
        key = CacheKeyGenerator.tables_key("test_db")
        assert key == "tables:test_db"
    
    def test_schema_key(self):
        """Test schema key generation."""
        key = CacheKeyGenerator.schema_key("test_db", "test_table")
        assert key == "schema:test_db:test_table"
    
    def test_sample_data_key(self):
        """Test sample data key generation."""
        key = CacheKeyGenerator.sample_data_key("test_db", "test_table", 10)
        assert key == "sample:test_db:test_table:10"
    
    def test_query_key(self):
        """Test query result key generation."""
        query_hash = "abc123def456"
        key = CacheKeyGenerator.query_key(query_hash)
        assert key == "query:abc123def456"
    
    def test_pattern_generation(self):
        """Test regex pattern generation for different key types."""
        # Database pattern
        db_pattern = CacheKeyGenerator.database_pattern()
        assert db_pattern == "^db_list.*"
        
        # Tables patterns
        all_tables_pattern = CacheKeyGenerator.tables_pattern()
        assert all_tables_pattern == "^tables:.*"
        
        specific_db_pattern = CacheKeyGenerator.tables_pattern("test_db")
        assert specific_db_pattern == "^tables:test_db$"
        
        # Schema patterns
        all_schema_pattern = CacheKeyGenerator.schema_pattern()
        assert all_schema_pattern == "^schema:.*"
        
        db_schema_pattern = CacheKeyGenerator.schema_pattern("test_db")
        assert db_schema_pattern == "^schema:test_db:.*"
        
        specific_schema_pattern = CacheKeyGenerator.schema_pattern("test_db", "test_table")
        assert specific_schema_pattern == "^schema:test_db:test_table$"
        
        # Sample data patterns
        all_sample_pattern = CacheKeyGenerator.sample_data_pattern()
        assert all_sample_pattern == "^sample:.*"
        
        db_sample_pattern = CacheKeyGenerator.sample_data_pattern("test_db")
        assert db_sample_pattern == "^sample:test_db:.*"
        
        table_sample_pattern = CacheKeyGenerator.sample_data_pattern("test_db", "test_table")
        assert table_sample_pattern == "^sample:test_db:test_table:.*"
    
    def test_key_escaping(self):
        """Test that special regex characters are properly escaped in keys."""
        # Test with database name containing special characters
        db_name = "test.db-name_with[special]chars"
        pattern = CacheKeyGenerator.tables_pattern(db_name)
        
        # Should not raise regex error
        import re
        compiled_pattern = re.compile(pattern)
        
        # Should match exact key
        test_key = f"tables:{db_name}"
        assert compiled_pattern.match(test_key)
        
        # Should not match different key
        different_key = "tables:other_db"
        assert not compiled_pattern.match(different_key)


class TestCacheIntegration:
    """Integration tests for cache manager with realistic usage patterns."""
    
    def test_database_schema_caching_workflow(self):
        """Test a realistic database schema caching workflow."""
        cache = CacheManager(default_ttl=300, max_size=1000)
        
        # Simulate caching database list
        databases = ["db1", "db2", "db3"]
        cache.set(CacheKeyGenerator.databases_key(), databases)
        
        # Simulate caching table lists for each database
        for db in databases:
            tables = [f"{db}_table_{i}" for i in range(3)]
            cache.set(CacheKeyGenerator.tables_key(db), tables)
        
        # Simulate caching schema for some tables
        schema_data = {
            "columns": ["id", "name", "created_at"],
            "types": ["int", "varchar", "timestamp"]
        }
        cache.set(CacheKeyGenerator.schema_key("db1", "db1_table_0"), schema_data)
        
        # Verify all data can be retrieved
        cached_dbs = cache.get(CacheKeyGenerator.databases_key())
        assert cached_dbs == databases
        
        cached_tables = cache.get(CacheKeyGenerator.tables_key("db1"))
        assert len(cached_tables) == 3
        
        cached_schema = cache.get(CacheKeyGenerator.schema_key("db1", "db1_table_0"))
        assert cached_schema == schema_data
        
        # Test invalidation of specific database
        invalidated = cache.invalidate(CacheKeyGenerator.tables_pattern("db1"))
        assert invalidated == 1
        
        # Verify db1 tables are gone but others remain
        assert cache.get(CacheKeyGenerator.tables_key("db1")) is None
        assert cache.get(CacheKeyGenerator.tables_key("db2")) is not None
    
    def test_performance_with_large_dataset(self):
        """Test cache performance with a large number of entries."""
        cache = CacheManager(default_ttl=300, max_size=10000)
        
        # Add a large number of entries
        start_time = time.time()
        for i in range(1000):
            cache.set(f"key_{i}", f"value_{i}")
        set_time = time.time() - start_time
        
        # Retrieve all entries
        start_time = time.time()
        for i in range(1000):
            value = cache.get(f"key_{i}")
            assert value == f"value_{i}"
        get_time = time.time() - start_time
        
        # Performance should be reasonable (adjust thresholds as needed)
        assert set_time < 1.0  # Should set 1000 entries in under 1 second
        assert get_time < 1.0  # Should get 1000 entries in under 1 second
        
        # Verify stats
        stats = cache.get_stats()
        assert stats['hits'] == 1000
        assert stats['size'] == 1000
        assert stats['hit_rate_percent'] == 100.0