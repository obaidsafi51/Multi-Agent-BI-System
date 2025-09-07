"""
Cache management system for TiDB MCP Server.

This module provides in-memory caching with TTL-based expiration for database
schema information, query results, and other frequently accessed data.
"""

import time
import threading
from typing import Any, Dict, List, Optional, Pattern
from dataclasses import dataclass
from datetime import datetime, timedelta
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Represents a single cache entry with TTL support."""
    
    value: Any
    created_at: float
    ttl_seconds: int
    access_count: int = 0
    last_accessed: float = 0
    
    def __post_init__(self):
        """Initialize last_accessed to creation time."""
        if self.last_accessed == 0:
            self.last_accessed = self.created_at
    
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        if self.ttl_seconds <= 0:  # Never expires if TTL is 0 or negative
            return False
        return time.time() - self.created_at > self.ttl_seconds
    
    def get_remaining_ttl(self) -> float:
        """Get remaining TTL in seconds."""
        if self.ttl_seconds <= 0:
            return float('inf')
        elapsed = time.time() - self.created_at
        return max(0, self.ttl_seconds - elapsed)
    
    def touch(self) -> None:
        """Update access statistics."""
        self.access_count += 1
        self.last_accessed = time.time()


class CacheManager:
    """
    Thread-safe in-memory cache manager with TTL-based expiration.
    
    Provides caching for database schema information, query results, and other
    frequently accessed data to improve performance and reduce database load.
    """
    
    def __init__(self, default_ttl: int = 300, max_size: int = 1000):
        """
        Initialize the cache manager.
        
        Args:
            default_ttl: Default TTL in seconds (5 minutes)
            max_size: Maximum number of cache entries
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expired_removals': 0
        }
        
        logger.info(f"CacheManager initialized with TTL={default_ttl}s, max_size={max_size}")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value if found and not expired, None otherwise
        """
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._stats['misses'] += 1
                logger.debug(f"Cache miss for key: {key}")
                return None
            
            if entry.is_expired():
                del self._cache[key]
                self._stats['expired_removals'] += 1
                self._stats['misses'] += 1
                logger.debug(f"Cache expired for key: {key}")
                return None
            
            entry.touch()
            self._stats['hits'] += 1
            logger.debug(f"Cache hit for key: {key} (TTL remaining: {entry.get_remaining_ttl():.1f}s)")
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Store a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds (uses default if None)
        """
        if ttl is None:
            ttl = self._default_ttl
        
        with self._lock:
            # Remove expired entries before adding new ones
            self._cleanup_expired()
            
            # Evict entries if we're at capacity
            if len(self._cache) >= self._max_size and key not in self._cache:
                self._evict_lru()
            
            entry = CacheEntry(
                value=value,
                created_at=time.time(),
                ttl_seconds=ttl
            )
            
            self._cache[key] = entry
            logger.debug(f"Cached value for key: {key} (TTL: {ttl}s)")
    
    def cleanup_expired(self) -> int:
        """
        Manually trigger cleanup of expired entries.
        
        Returns:
            Number of entries removed
        """
        with self._lock:
            initial_size = len(self._cache)
            self._cleanup_expired()
            return initial_size - len(self._cache)
    
    def invalidate(self, pattern: str) -> int:
        """
        Invalidate cache entries matching a pattern.
        
        Args:
            pattern: Regex pattern to match keys
            
        Returns:
            Number of entries invalidated
        """
        try:
            regex = re.compile(pattern)
        except re.error as e:
            logger.error(f"Invalid regex pattern '{pattern}': {e}")
            return 0
        
        with self._lock:
            keys_to_remove = [
                key for key in self._cache.keys()
                if regex.search(key)
            ]
            
            for key in keys_to_remove:
                del self._cache[key]
            
            count = len(keys_to_remove)
            logger.info(f"Invalidated {count} cache entries matching pattern: {pattern}")
            return count
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._stats = {
                'hits': 0,
                'misses': 0,
                'evictions': 0,
                'expired_removals': 0
            }
            logger.info(f"Cleared {count} cache entries")
    
    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'size': len(self._cache),
                'max_size': self._max_size,
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'hit_rate_percent': round(hit_rate, 2),
                'evictions': self._stats['evictions'],
                'expired_removals': self._stats['expired_removals'],
                'total_requests': total_requests
            }
    
    def get_keys(self, pattern: Optional[str] = None) -> List[str]:
        """
        Get all cache keys, optionally filtered by pattern.
        
        Args:
            pattern: Optional regex pattern to filter keys
            
        Returns:
            List of cache keys
        """
        with self._lock:
            keys = list(self._cache.keys())
            
            if pattern:
                try:
                    regex = re.compile(pattern)
                    keys = [key for key in keys if regex.search(key)]
                except re.error as e:
                    logger.error(f"Invalid regex pattern '{pattern}': {e}")
                    return []
            
            return keys
    
    def _cleanup_expired(self) -> None:
        """Remove expired entries from cache (internal method)."""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            del self._cache[key]
            self._stats['expired_removals'] += 1
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def _evict_lru(self) -> None:
        """Evict least recently used entry (internal method)."""
        if not self._cache:
            return
        
        # Find the least recently used entry
        lru_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].last_accessed
        )
        
        del self._cache[lru_key]
        self._stats['evictions'] += 1
        logger.debug(f"Evicted LRU cache entry: {lru_key}")


class CacheKeyGenerator:
    """
    Utility class for generating consistent cache keys for different data types.
    
    Provides standardized key generation for databases, tables, schemas, and queries
    to ensure consistent caching behavior across the application.
    """
    
    # Key prefixes for different data types
    PREFIX_DATABASES = "db_list"
    PREFIX_TABLES = "tables"
    PREFIX_SCHEMA = "schema"
    PREFIX_SAMPLE_DATA = "sample"
    PREFIX_QUERY = "query"
    
    @staticmethod
    def databases_key() -> str:
        """Generate cache key for database list."""
        return CacheKeyGenerator.PREFIX_DATABASES
    
    @staticmethod
    def tables_key(database: str) -> str:
        """
        Generate cache key for table list in a database.
        
        Args:
            database: Database name
            
        Returns:
            Cache key for table list
        """
        return f"{CacheKeyGenerator.PREFIX_TABLES}:{database}"
    
    @staticmethod
    def schema_key(database: str, table: str) -> str:
        """
        Generate cache key for table schema.
        
        Args:
            database: Database name
            table: Table name
            
        Returns:
            Cache key for table schema
        """
        return f"{CacheKeyGenerator.PREFIX_SCHEMA}:{database}:{table}"
    
    @staticmethod
    def sample_data_key(database: str, table: str, limit: int) -> str:
        """
        Generate cache key for sample data.
        
        Args:
            database: Database name
            table: Table name
            limit: Number of sample rows
            
        Returns:
            Cache key for sample data
        """
        return f"{CacheKeyGenerator.PREFIX_SAMPLE_DATA}:{database}:{table}:{limit}"
    
    @staticmethod
    def query_key(query_hash: str) -> str:
        """
        Generate cache key for query results.
        
        Args:
            query_hash: Hash of the SQL query
            
        Returns:
            Cache key for query results
        """
        return f"{CacheKeyGenerator.PREFIX_QUERY}:{query_hash}"
    
    @staticmethod
    def database_pattern() -> str:
        """Get regex pattern for all database-related cache keys."""
        return f"^{CacheKeyGenerator.PREFIX_DATABASES}.*"
    
    @staticmethod
    def tables_pattern(database: Optional[str] = None) -> str:
        """
        Get regex pattern for table cache keys.
        
        Args:
            database: Optional database name to filter by
            
        Returns:
            Regex pattern for table cache keys
        """
        if database:
            return f"^{CacheKeyGenerator.PREFIX_TABLES}:{re.escape(database)}$"
        return f"^{CacheKeyGenerator.PREFIX_TABLES}:.*"
    
    @staticmethod
    def schema_pattern(database: Optional[str] = None, table: Optional[str] = None) -> str:
        """
        Get regex pattern for schema cache keys.
        
        Args:
            database: Optional database name to filter by
            table: Optional table name to filter by
            
        Returns:
            Regex pattern for schema cache keys
        """
        if database and table:
            return f"^{CacheKeyGenerator.PREFIX_SCHEMA}:{re.escape(database)}:{re.escape(table)}$"
        elif database:
            return f"^{CacheKeyGenerator.PREFIX_SCHEMA}:{re.escape(database)}:.*"
        return f"^{CacheKeyGenerator.PREFIX_SCHEMA}:.*"
    
    @staticmethod
    def sample_data_pattern(database: Optional[str] = None, table: Optional[str] = None) -> str:
        """
        Get regex pattern for sample data cache keys.
        
        Args:
            database: Optional database name to filter by
            table: Optional table name to filter by
            
        Returns:
            Regex pattern for sample data cache keys
        """
        if database and table:
            return f"^{CacheKeyGenerator.PREFIX_SAMPLE_DATA}:{re.escape(database)}:{re.escape(table)}:.*"
        elif database:
            return f"^{CacheKeyGenerator.PREFIX_SAMPLE_DATA}:{re.escape(database)}:.*"
        return f"^{CacheKeyGenerator.PREFIX_SAMPLE_DATA}:.*"