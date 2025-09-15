"""
Cache Manager for Data Agent

This module provides caching functionality for the data agent to improve performance
and reduce redundant database queries.
"""

import asyncio
import json
import time
from typing import Any, Dict, Optional, Union
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    """
    Simple in-memory cache manager with TTL (Time To Live) support.
    """
    
    def __init__(self, default_ttl: int = 300):  # 5 minutes default TTL
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._default_ttl = default_ttl
        self._cleanup_task: Optional[asyncio.Task] = None
        logger.info(f"Cache manager initialized with default TTL: {default_ttl}s")
    
    async def start(self):
        """Start the cache manager and cleanup task."""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._cleanup_expired())
            logger.info("Cache manager cleanup task started")
    
    async def stop(self):
        """Stop the cache manager and cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
        self._cache.clear()
        logger.info("Cache manager stopped and cache cleared")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value if exists and not expired, None otherwise
        """
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        if time.time() > entry['expires_at']:
            del self._cache[key]
            return None
        
        entry['last_accessed'] = time.time()
        return entry['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set a value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (uses default if None)
        """
        ttl = ttl or self._default_ttl
        now = time.time()
        
        self._cache[key] = {
            'value': value,
            'expires_at': now + ttl,
            'created_at': now,
            'last_accessed': now,
            'ttl': ttl
        }
        
        logger.debug(f"Cached key '{key}' with TTL {ttl}s")
    
    def delete(self, key: str) -> bool:
        """
        Delete a key from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key existed, False otherwise
        """
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Deleted cache key '{key}'")
            return True
        return False
    
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache and is not expired.
        
        Args:
            key: Cache key to check
            
        Returns:
            True if key exists and is valid, False otherwise
        """
        return self.get(key) is not None
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        now = time.time()
        total_entries = len(self._cache)
        expired_entries = sum(1 for entry in self._cache.values() if now > entry['expires_at'])
        
        return {
            'total_entries': total_entries,
            'active_entries': total_entries - expired_entries,
            'expired_entries': expired_entries,
            'memory_usage_mb': self._estimate_memory_usage() / (1024 * 1024),
            'default_ttl': self._default_ttl
        }
    
    def _estimate_memory_usage(self) -> int:
        """Estimate memory usage of cache in bytes."""
        try:
            return len(json.dumps(self._cache, default=str).encode('utf-8'))
        except Exception:
            # Fallback estimation
            return len(self._cache) * 1024  # Rough estimate: 1KB per entry
    
    async def _cleanup_expired(self):
        """Cleanup expired cache entries periodically."""
        while True:
            try:
                await asyncio.sleep(60)  # Run cleanup every minute
                await self._perform_cleanup()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error during cache cleanup: {e}")
    
    async def _perform_cleanup(self):
        """Perform the actual cleanup of expired entries."""
        now = time.time()
        expired_keys = [
            key for key, entry in self._cache.items()
            if now > entry['expires_at']
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


async def get_cache_manager() -> CacheManager:
    """
    Get the global cache manager instance.
    
    Returns:
        CacheManager instance
    """
    global _cache_manager
    
    if _cache_manager is None:
        _cache_manager = CacheManager()
        await _cache_manager.start()
        logger.info("Global cache manager created and started")
    
    return _cache_manager


async def close_cache_manager():
    """Close the global cache manager instance."""
    global _cache_manager
    
    if _cache_manager is not None:
        await _cache_manager.stop()
        _cache_manager = None
        logger.info("Global cache manager closed")


# Query-specific cache helpers
class QueryCache:
    """Helper class for caching query results."""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
    
    def get_query_result(self, query: str, params: Optional[Dict] = None) -> Optional[Any]:
        """Get cached query result."""
        cache_key = self._make_query_key(query, params)
        return self.cache_manager.get(cache_key)
    
    def set_query_result(self, query: str, result: Any, params: Optional[Dict] = None, ttl: Optional[int] = None):
        """Cache query result."""
        cache_key = self._make_query_key(query, params)
        self.cache_manager.set(cache_key, result, ttl)
    
    def _make_query_key(self, query: str, params: Optional[Dict] = None) -> str:
        """Create a cache key from query and parameters."""
        import hashlib
        
        query_normalized = query.strip().lower()
        params_str = json.dumps(params or {}, sort_keys=True)
        combined = f"{query_normalized}:{params_str}"
        
        return f"query:{hashlib.md5(combined.encode('utf-8')).hexdigest()}"


# Schema cache helpers
class SchemaCache:
    """Helper class for caching schema information."""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
    
    def get_schema(self, database: str) -> Optional[Dict]:
        """Get cached schema for database."""
        cache_key = f"schema:{database}"
        return self.cache_manager.get(cache_key)
    
    def set_schema(self, database: str, schema: Dict, ttl: int = 1800):  # 30 minutes default
        """Cache schema for database."""
        cache_key = f"schema:{database}"
        self.cache_manager.set(cache_key, schema, ttl)
    
    def get_table_info(self, database: str, table: str) -> Optional[Dict]:
        """Get cached table information."""
        cache_key = f"table:{database}:{table}"
        return self.cache_manager.get(cache_key)
    
    def set_table_info(self, database: str, table: str, info: Dict, ttl: int = 1800):
        """Cache table information."""
        cache_key = f"table:{database}:{table}"
        self.cache_manager.set(cache_key, info, ttl)
