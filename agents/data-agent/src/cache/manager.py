"""
Caching mechanism for frequently accessed financial data.
Implements Redis-based caching with intelligent cache invalidation and optimization.
"""

import hashlib
import json
import pickle
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict

import redis
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    data: Any
    created_at: datetime
    expires_at: Optional[datetime]
    access_count: int
    last_accessed: datetime
    size_bytes: int
    tags: List[str]


@dataclass
class CacheStats:
    """Cache performance statistics"""
    total_requests: int
    cache_hits: int
    cache_misses: int
    hit_rate: float
    total_size_bytes: int
    entry_count: int
    avg_access_time_ms: float


class CacheManager:
    """
    Redis-based cache manager for financial data with intelligent caching strategies.
    Implements cache warming, invalidation, and performance optimization.
    """
    
    # Cache TTL settings (in seconds)
    DEFAULT_TTL = {
        'financial_data': 3600,      # 1 hour for financial data
        'query_results': 1800,       # 30 minutes for query results
        'user_preferences': 86400,   # 24 hours for user preferences
        'metadata': 7200,            # 2 hours for metadata
        'aggregations': 14400,       # 4 hours for aggregated data
    }
    
    # Cache key prefixes
    KEY_PREFIXES = {
        'query': 'query:',
        'data': 'data:',
        'user': 'user:',
        'meta': 'meta:',
        'agg': 'agg:',
        'stats': 'stats:'
    }
    
    def __init__(self, redis_url: str, **kwargs):
        """
        Initialize cache manager with Redis connection.
        
        Args:
            redis_url: Redis connection URL
            **kwargs: Additional configuration options
        """
        self.redis_url = redis_url
        self.redis_client = None
        
        # Configuration
        self.config = {
            'max_memory_mb': kwargs.get('max_memory_mb', 512),
            'eviction_policy': kwargs.get('eviction_policy', 'allkeys-lru'),
            'compression_enabled': kwargs.get('compression_enabled', True),
            'compression_threshold': kwargs.get('compression_threshold', 1024),  # bytes
            'batch_size': kwargs.get('batch_size', 100),
            'stats_interval': kwargs.get('stats_interval', 300),  # 5 minutes
        }
        
        # Performance tracking
        self.stats = {
            'requests': 0,
            'hits': 0,
            'misses': 0,
            'total_access_time': 0.0,
            'last_stats_reset': time.time()
        }
        
        # Cache warming configuration
        self.warm_cache_queries = [
            "SELECT * FROM financial_overview WHERE period_date >= DATE_SUB(NOW(), INTERVAL 12 MONTH)",
            "SELECT * FROM cash_flow WHERE period_date >= DATE_SUB(NOW(), INTERVAL 6 MONTH)",
            "SELECT * FROM financial_ratios WHERE period_date >= DATE_SUB(NOW(), INTERVAL 3 MONTH)"
        ]
    
    async def initialize(self) -> None:
        """Initialize Redis connection and configure cache settings."""
        try:
            # Create Redis connection
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=False,  # We'll handle encoding ourselves
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            await self._test_connection()
            
            # Configure Redis settings
            await self._configure_redis()
            
            logger.info("Cache manager initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize cache manager", error=str(e))
            raise
    
    async def _test_connection(self) -> None:
        """Test Redis connection."""
        try:
            self.redis_client.ping()
            logger.info("Redis connection test successful")
        except Exception as e:
            logger.error("Redis connection test failed", error=str(e))
            raise
    
    async def _configure_redis(self) -> None:
        """Configure Redis settings for optimal performance."""
        try:
            # Set memory policy
            self.redis_client.config_set('maxmemory-policy', self.config['eviction_policy'])
            
            # Set max memory if specified
            if self.config['max_memory_mb'] > 0:
                max_memory_bytes = self.config['max_memory_mb'] * 1024 * 1024
                self.redis_client.config_set('maxmemory', max_memory_bytes)
            
            logger.info("Redis configuration applied successfully")
            
        except Exception as e:
            logger.warning("Failed to configure Redis settings", error=str(e))
    
    def _generate_cache_key(self, prefix: str, identifier: str, **kwargs) -> str:
        """
        Generate cache key with consistent hashing.
        
        Args:
            prefix: Key prefix from KEY_PREFIXES
            identifier: Base identifier
            **kwargs: Additional parameters for key generation
            
        Returns:
            Generated cache key
        """
        # Create deterministic key from parameters
        key_data = {
            'identifier': identifier,
            **kwargs
        }
        
        # Sort keys for consistent hashing
        key_string = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()[:12]
        
        return f"{self.KEY_PREFIXES[prefix]}{key_hash}"
    
    def _serialize_data(self, data: Any) -> bytes:
        """
        Serialize data for cache storage with optional compression.
        
        Args:
            data: Data to serialize
            
        Returns:
            Serialized data bytes
        """
        try:
            # Use pickle for Python objects
            serialized = pickle.dumps(data)
            
            # Apply compression if enabled and data is large enough
            if (self.config['compression_enabled'] and 
                len(serialized) > self.config['compression_threshold']):
                import gzip
                serialized = gzip.compress(serialized)
                # Add compression marker
                serialized = b'GZIP:' + serialized
            
            return serialized
            
        except Exception as e:
            logger.error("Failed to serialize data", error=str(e))
            raise
    
    def _deserialize_data(self, data: bytes) -> Any:
        """
        Deserialize data from cache storage.
        
        Args:
            data: Serialized data bytes
            
        Returns:
            Deserialized data
        """
        try:
            # Check for compression marker
            if data.startswith(b'GZIP:'):
                import gzip
                data = gzip.decompress(data[5:])  # Remove marker
            
            return pickle.loads(data)
            
        except Exception as e:
            logger.error("Failed to deserialize data", error=str(e))
            raise
    
    async def get(
        self, 
        cache_type: str, 
        identifier: str, 
        **kwargs
    ) -> Optional[Any]:
        """
        Get data from cache.
        
        Args:
            cache_type: Type of cache (query, data, user, etc.)
            identifier: Cache identifier
            **kwargs: Additional parameters for key generation
            
        Returns:
            Cached data or None if not found
        """
        start_time = time.time()
        self.stats['requests'] += 1
        
        try:
            cache_key = self._generate_cache_key(cache_type, identifier, **kwargs)
            
            # Get data from Redis
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data is not None:
                # Update access statistics
                self.redis_client.hincrby(f"{cache_key}:meta", "access_count", 1)
                self.redis_client.hset(f"{cache_key}:meta", "last_accessed", time.time())
                
                # Deserialize and return data
                data = self._deserialize_data(cached_data)
                
                self.stats['hits'] += 1
                access_time = (time.time() - start_time) * 1000
                self.stats['total_access_time'] += access_time
                
                logger.debug(
                    "Cache hit",
                    cache_key=cache_key,
                    access_time_ms=access_time
                )
                
                return data
            else:
                self.stats['misses'] += 1
                logger.debug("Cache miss", cache_key=cache_key)
                return None
                
        except Exception as e:
            self.stats['misses'] += 1
            logger.error("Cache get failed", error=str(e), cache_type=cache_type)
            return None
    
    async def set(
        self,
        cache_type: str,
        identifier: str,
        data: Any,
        ttl: Optional[int] = None,
        tags: Optional[List[str]] = None,
        **kwargs
    ) -> bool:
        """
        Set data in cache.
        
        Args:
            cache_type: Type of cache
            identifier: Cache identifier
            data: Data to cache
            ttl: Time to live in seconds
            tags: Cache tags for invalidation
            **kwargs: Additional parameters for key generation
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cache_key = self._generate_cache_key(cache_type, identifier, **kwargs)
            
            # Serialize data
            serialized_data = self._serialize_data(data)
            
            # Determine TTL
            if ttl is None:
                ttl = self.DEFAULT_TTL.get(cache_type, self.DEFAULT_TTL['query_results'])
            
            # Store data with TTL
            success = self.redis_client.setex(cache_key, ttl, serialized_data)
            
            if success:
                # Store metadata
                metadata = {
                    'created_at': time.time(),
                    'expires_at': time.time() + ttl,
                    'size_bytes': len(serialized_data),
                    'access_count': 0,
                    'last_accessed': time.time(),
                    'tags': json.dumps(tags or [])
                }
                
                self.redis_client.hmset(f"{cache_key}:meta", metadata)
                self.redis_client.expire(f"{cache_key}:meta", ttl)
                
                # Add to tag indexes for invalidation
                if tags:
                    for tag in tags:
                        self.redis_client.sadd(f"tag:{tag}", cache_key)
                        self.redis_client.expire(f"tag:{tag}", ttl)
                
                logger.debug(
                    "Cache set successful",
                    cache_key=cache_key,
                    size_bytes=len(serialized_data),
                    ttl=ttl
                )
                
                return True
            else:
                logger.warning("Cache set failed", cache_key=cache_key)
                return False
                
        except Exception as e:
            logger.error("Cache set failed", error=str(e), cache_type=cache_type)
            return False
    
    async def delete(self, cache_type: str, identifier: str, **kwargs) -> bool:
        """
        Delete data from cache.
        
        Args:
            cache_type: Type of cache
            identifier: Cache identifier
            **kwargs: Additional parameters for key generation
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cache_key = self._generate_cache_key(cache_type, identifier, **kwargs)
            
            # Delete data and metadata
            deleted_count = self.redis_client.delete(cache_key, f"{cache_key}:meta")
            
            logger.debug("Cache delete", cache_key=cache_key, deleted_count=deleted_count)
            
            return deleted_count > 0
            
        except Exception as e:
            logger.error("Cache delete failed", error=str(e), cache_type=cache_type)
            return False
    
    async def invalidate_by_tags(self, tags: List[str]) -> int:
        """
        Invalidate cache entries by tags.
        
        Args:
            tags: List of tags to invalidate
            
        Returns:
            Number of entries invalidated
        """
        try:
            invalidated_count = 0
            
            for tag in tags:
                tag_key = f"tag:{tag}"
                cache_keys = self.redis_client.smembers(tag_key)
                
                if cache_keys:
                    # Delete cache entries
                    for cache_key in cache_keys:
                        self.redis_client.delete(cache_key, f"{cache_key}:meta")
                        invalidated_count += 1
                    
                    # Delete tag index
                    self.redis_client.delete(tag_key)
            
            logger.info("Cache invalidation completed", tags=tags, invalidated_count=invalidated_count)
            
            return invalidated_count
            
        except Exception as e:
            logger.error("Cache invalidation failed", error=str(e), tags=tags)
            return 0
    
    async def clear_all(self) -> bool:
        """
        Clear all cache data.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get all cache keys
            all_keys = []
            for prefix in self.KEY_PREFIXES.values():
                keys = self.redis_client.keys(f"{prefix}*")
                all_keys.extend(keys)
            
            # Delete all keys
            if all_keys:
                deleted_count = self.redis_client.delete(*all_keys)
                logger.info("Cache cleared", deleted_count=deleted_count)
                return True
            else:
                logger.info("Cache already empty")
                return True
                
        except Exception as e:
            logger.error("Cache clear failed", error=str(e))
            return False
    
    async def get_stats(self) -> CacheStats:
        """
        Get cache performance statistics.
        
        Returns:
            CacheStats: Current cache statistics
        """
        try:
            # Calculate hit rate
            total_requests = self.stats['requests']
            hit_rate = (self.stats['hits'] / max(total_requests, 1)) * 100
            
            # Calculate average access time
            avg_access_time = (
                self.stats['total_access_time'] / max(self.stats['hits'], 1)
            )
            
            # Get Redis memory info
            redis_info = self.redis_client.info('memory')
            total_size_bytes = redis_info.get('used_memory', 0)
            
            # Count cache entries
            entry_count = 0
            for prefix in self.KEY_PREFIXES.values():
                keys = self.redis_client.keys(f"{prefix}*")
                entry_count += len([k for k in keys if not k.endswith(b':meta')])
            
            return CacheStats(
                total_requests=total_requests,
                cache_hits=self.stats['hits'],
                cache_misses=self.stats['misses'],
                hit_rate=hit_rate,
                total_size_bytes=total_size_bytes,
                entry_count=entry_count,
                avg_access_time_ms=avg_access_time
            )
            
        except Exception as e:
            logger.error("Failed to get cache stats", error=str(e))
            return CacheStats(0, 0, 0, 0.0, 0, 0, 0.0)
    
    async def warm_cache(self, queries: Optional[List[str]] = None) -> int:
        """
        Warm cache with frequently accessed data.
        
        Args:
            queries: List of queries to warm cache with
            
        Returns:
            Number of entries warmed
        """
        try:
            warm_queries = queries or self.warm_cache_queries
            warmed_count = 0
            
            logger.info("Starting cache warming", query_count=len(warm_queries))
            
            # This would typically execute queries and cache results
            # For now, we'll just log the warming process
            for query in warm_queries:
                cache_key = self._generate_cache_key('query', query)
                # In a real implementation, you would execute the query
                # and cache the results here
                warmed_count += 1
            
            logger.info("Cache warming completed", warmed_count=warmed_count)
            
            return warmed_count
            
        except Exception as e:
            logger.error("Cache warming failed", error=str(e))
            return 0
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform cache health check.
        
        Returns:
            Dictionary containing health status and metrics
        """
        health_status = {
            'status': 'healthy',
            'timestamp': time.time(),
            'redis_connected': False,
            'stats': {},
            'errors': []
        }
        
        try:
            # Test Redis connection
            self.redis_client.ping()
            health_status['redis_connected'] = True
            
            # Get cache statistics
            stats = await self.get_stats()
            health_status['stats'] = asdict(stats)
            
            # Check hit rate
            if stats.hit_rate < 50:  # Less than 50% hit rate
                health_status['errors'].append("Low cache hit rate")
            
            # Check memory usage
            redis_info = self.redis_client.info('memory')
            memory_usage_pct = (
                redis_info.get('used_memory', 0) / 
                max(redis_info.get('maxmemory', 1), 1) * 100
            )
            
            if memory_usage_pct > 90:
                health_status['errors'].append("High memory usage")
                health_status['status'] = 'warning'
            
        except Exception as e:
            health_status['status'] = 'unhealthy'
            health_status['errors'].append(str(e))
            logger.error("Cache health check failed", error=str(e))
        
        return health_status
    
    async def close(self) -> None:
        """Close Redis connection and cleanup resources."""
        try:
            if self.redis_client:
                self.redis_client.close()
            
            logger.info("Cache manager closed successfully")
            
        except Exception as e:
            logger.error("Error closing cache manager", error=str(e))


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


async def get_cache_manager() -> CacheManager:
    """
    Get or create global cache manager instance.
    
    Returns:
        CacheManager: Global cache manager instance
    """
    global _cache_manager
    
    if _cache_manager is None:
        import os
        redis_url = os.getenv('REDIS_URL')
        if not redis_url:
            raise ValueError("REDIS_URL environment variable not set")
        
        _cache_manager = CacheManager(redis_url)
        await _cache_manager.initialize()
    
    return _cache_manager


async def close_cache_manager() -> None:
    """Close global cache manager."""
    global _cache_manager
    
    if _cache_manager:
        await _cache_manager.close()
        _cache_manager = None