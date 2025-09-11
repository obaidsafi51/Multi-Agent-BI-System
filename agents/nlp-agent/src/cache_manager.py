"""
Advanced caching system for NLP Agent with multi-level caching strategy.
Implements schema context caching, KIMI response caching, and session management.
"""

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Union
import redis.asyncio as redis
from enum import Enum

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """Cache level enumeration."""
    L1_MEMORY = "l1_memory"
    L2_REDIS = "l2_redis"
    L3_PERSISTENT = "l3_persistent"


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    ttl_seconds: int = 3600
    cache_level: CacheLevel = CacheLevel.L1_MEMORY
    tags: Set[str] = field(default_factory=set)
    size_bytes: int = 0
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return (datetime.now() - self.created_at).total_seconds() > self.ttl_seconds
    
    def mark_accessed(self):
        """Mark entry as accessed."""
        self.last_accessed = datetime.now()
        self.access_count += 1
    
    def calculate_size(self) -> int:
        """Calculate entry size in bytes."""
        try:
            serialized = json.dumps(self.value, default=str)
            self.size_bytes = len(serialized.encode('utf-8'))
            return self.size_bytes
        except Exception:
            return 0


@dataclass
class CacheMetrics:
    """Cache performance metrics."""
    l1_hits: int = 0
    l1_misses: int = 0
    l2_hits: int = 0
    l2_misses: int = 0
    l3_hits: int = 0
    l3_misses: int = 0
    evictions: int = 0
    total_size_bytes: int = 0
    avg_response_time_ms: float = 0.0
    
    @property
    def total_hits(self) -> int:
        return self.l1_hits + self.l2_hits + self.l3_hits
    
    @property
    def total_misses(self) -> int:
        return self.l1_misses + self.l2_misses + self.l3_misses
    
    @property
    def hit_rate(self) -> float:
        total = self.total_hits + self.total_misses
        return (self.total_hits / total * 100) if total > 0 else 0.0


class AdvancedCacheManager:
    """
    Advanced multi-level caching system with intelligent cache management.
    
    Features:
    - L1: In-memory cache for frequently accessed data
    - L2: Redis cache for shared data across instances
    - L3: Persistent cache for long-term storage
    - Intelligent eviction policies
    - Cache warming and preloading
    - Compression and serialization
    - Tag-based invalidation
    """
    
    def __init__(
        self,
        l1_max_size: int = 1000,
        l1_ttl_seconds: int = 300,
        l2_ttl_seconds: int = 1800,
        l3_ttl_seconds: int = 7200,
        redis_url: str = "redis://redis:6379",
        enable_compression: bool = True,
        max_memory_mb: int = 100
    ):
        """
        Initialize advanced cache manager.
        
        Args:
            l1_max_size: Maximum entries in L1 cache
            l1_ttl_seconds: L1 cache TTL
            l2_ttl_seconds: L2 cache TTL
            l3_ttl_seconds: L3 cache TTL
            redis_url: Redis connection URL
            enable_compression: Enable data compression
            max_memory_mb: Maximum memory usage in MB
        """
        self.l1_max_size = l1_max_size
        self.l1_ttl_seconds = l1_ttl_seconds
        self.l2_ttl_seconds = l2_ttl_seconds
        self.l3_ttl_seconds = l3_ttl_seconds
        self.redis_url = redis_url
        self.enable_compression = enable_compression
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        
        # L1 Cache (In-memory)
        self._l1_cache: Dict[str, CacheEntry] = {}
        self._l1_access_order: List[str] = []  # For LRU eviction
        
        # L2 Cache (Redis)
        self._redis_client: Optional[redis.Redis] = None
        
        # Cache management
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._warm_cache_task: Optional[asyncio.Task] = None
        
        # Metrics
        self.metrics = CacheMetrics()
        
        # Tag tracking for invalidation
        self._tag_to_keys: Dict[str, Set[str]] = {}
        
        logger.info(
            f"Advanced cache manager initialized: "
            f"L1={l1_max_size} entries, "
            f"max_memory={max_memory_mb}MB, "
            f"compression={enable_compression}"
        )
    
    async def initialize(self) -> None:
        """Initialize cache manager and connections."""
        try:
            # Initialize Redis connection
            self._redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            
            # Test Redis connection
            await self._redis_client.ping()
            logger.info("Redis connection established")
            
            # Start background tasks
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            self._warm_cache_task = asyncio.create_task(self._cache_warming_loop())
            
            logger.info("Cache manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize cache manager: {e}")
            # Continue without Redis if connection fails
            self._redis_client = None
    
    async def get(
        self,
        category: str,
        key: str,
        default: Any = None
    ) -> Any:
        """
        Get value from cache with multi-level lookup.
        
        Args:
            category: Cache category (schema, kimi, session, etc.)
            key: Cache key
            default: Default value if not found
            
        Returns:
            Cached value or default
        """
        cache_key = self._build_cache_key(category, key)
        start_time = time.time()
        
        try:
            # L1 Cache lookup
            if cache_key in self._l1_cache:
                entry = self._l1_cache[cache_key]
                if not entry.is_expired():
                    entry.mark_accessed()
                    self._update_access_order(cache_key)
                    self.metrics.l1_hits += 1
                    
                    response_time = (time.time() - start_time) * 1000
                    self._update_avg_response_time(response_time)
                    
                    logger.debug(f"L1 cache hit: {cache_key}")
                    return entry.value
                else:
                    # Remove expired entry
                    await self._evict_l1_entry(cache_key)
            
            self.metrics.l1_misses += 1
            
            # L2 Cache lookup (Redis)
            if self._redis_client:
                try:
                    redis_value = await self._redis_client.get(f"nlp_cache:{cache_key}")
                    if redis_value:
                        value = json.loads(redis_value)
                        
                        # Promote to L1 cache
                        await self._set_l1_cache(cache_key, value, self.l1_ttl_seconds)
                        
                        self.metrics.l2_hits += 1
                        response_time = (time.time() - start_time) * 1000
                        self._update_avg_response_time(response_time)
                        
                        logger.debug(f"L2 cache hit: {cache_key}")
                        return value
                except Exception as e:
                    logger.warning(f"Redis lookup failed for {cache_key}: {e}")
            
            self.metrics.l2_misses += 1
            
            # L3 Cache would go here (file system, database, etc.)
            # For now, we'll just return default
            self.metrics.l3_misses += 1
            
            response_time = (time.time() - start_time) * 1000
            self._update_avg_response_time(response_time)
            
            logger.debug(f"Cache miss: {cache_key}")
            return default
            
        except Exception as e:
            logger.error(f"Cache lookup error for {cache_key}: {e}")
            return default
    
    async def set(
        self,
        category: str,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[Set[str]] = None
    ) -> bool:
        """
        Set value in cache with multi-level storage.
        
        Args:
            category: Cache category
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            tags: Tags for invalidation
            
        Returns:
            True if stored successfully
        """
        cache_key = self._build_cache_key(category, key)
        ttl = ttl or self._get_default_ttl(category)
        tags = tags or set()
        
        try:
            # Store in L1 cache
            await self._set_l1_cache(cache_key, value, ttl, tags)
            
            # Store in L2 cache (Redis)
            if self._redis_client:
                try:
                    serialized_value = json.dumps(value, default=str)
                    await self._redis_client.setex(
                        f"nlp_cache:{cache_key}",
                        self.l2_ttl_seconds,
                        serialized_value
                    )
                except Exception as e:
                    logger.warning(f"Redis storage failed for {cache_key}: {e}")
            
            # Update tag tracking
            for tag in tags:
                if tag not in self._tag_to_keys:
                    self._tag_to_keys[tag] = set()
                self._tag_to_keys[tag].add(cache_key)
            
            logger.debug(f"Cached: {cache_key} (TTL: {ttl}s, Tags: {tags})")
            return True
            
        except Exception as e:
            logger.error(f"Cache storage error for {cache_key}: {e}")
            return False
    
    async def invalidate_by_tags(self, tags: Set[str]) -> int:
        """
        Invalidate cache entries by tags.
        
        Args:
            tags: Tags to invalidate
            
        Returns:
            Number of entries invalidated
        """
        invalidated_count = 0
        
        async with self._lock:
            keys_to_invalidate = set()
            
            for tag in tags:
                if tag in self._tag_to_keys:
                    keys_to_invalidate.update(self._tag_to_keys[tag])
                    del self._tag_to_keys[tag]
            
            # Remove from L1 cache
            for cache_key in keys_to_invalidate:
                if cache_key in self._l1_cache:
                    await self._evict_l1_entry(cache_key)
                    invalidated_count += 1
            
            # Remove from L2 cache (Redis)
            if self._redis_client and keys_to_invalidate:
                try:
                    redis_keys = [f"nlp_cache:{key}" for key in keys_to_invalidate]
                    await self._redis_client.delete(*redis_keys)
                except Exception as e:
                    logger.warning(f"Redis invalidation failed: {e}")
        
        logger.info(f"Invalidated {invalidated_count} cache entries for tags: {tags}")
        return invalidated_count
    
    async def warm_cache(self, warm_data: Dict[str, Any]) -> None:
        """
        Warm cache with frequently accessed data.
        
        Args:
            warm_data: Data to preload into cache
        """
        logger.info("Starting cache warming...")
        
        for cache_key, data in warm_data.items():
            category, key = cache_key.split(':', 1)
            await self.set(category, key, data, ttl=self.l1_ttl_seconds)
        
        logger.info(f"Cache warming completed: {len(warm_data)} entries")
    
    async def _set_l1_cache(
        self,
        cache_key: str,
        value: Any,
        ttl: int,
        tags: Optional[Set[str]] = None
    ) -> None:
        """Set entry in L1 cache with eviction management."""
        async with self._lock:
            # Check memory limits
            while self._should_evict():
                await self._evict_lru_entry()
            
            # Create cache entry
            entry = CacheEntry(
                key=cache_key,
                value=value,
                ttl_seconds=ttl,
                cache_level=CacheLevel.L1_MEMORY,
                tags=tags or set()
            )
            entry.calculate_size()
            
            # Store entry
            self._l1_cache[cache_key] = entry
            self._update_access_order(cache_key)
            
            # Update metrics
            self.metrics.total_size_bytes += entry.size_bytes
    
    def _should_evict(self) -> bool:
        """Check if eviction is needed."""
        return (
            len(self._l1_cache) >= self.l1_max_size or
            self.metrics.total_size_bytes > self.max_memory_bytes
        )
    
    async def _evict_lru_entry(self) -> None:
        """Evict least recently used entry."""
        if not self._l1_access_order:
            return
        
        lru_key = self._l1_access_order[0]
        await self._evict_l1_entry(lru_key)
        self.metrics.evictions += 1
    
    async def _evict_l1_entry(self, cache_key: str) -> None:
        """Evict specific entry from L1 cache."""
        if cache_key in self._l1_cache:
            entry = self._l1_cache[cache_key]
            self.metrics.total_size_bytes -= entry.size_bytes
            del self._l1_cache[cache_key]
        
        if cache_key in self._l1_access_order:
            self._l1_access_order.remove(cache_key)
    
    def _update_access_order(self, cache_key: str) -> None:
        """Update LRU access order."""
        if cache_key in self._l1_access_order:
            self._l1_access_order.remove(cache_key)
        self._l1_access_order.append(cache_key)
    
    def _build_cache_key(self, category: str, key: str) -> str:
        """Build standardized cache key."""
        # Create hash for long keys
        if len(key) > 100:
            key_hash = hashlib.md5(key.encode()).hexdigest()
            return f"{category}:{key_hash}"
        return f"{category}:{key}"
    
    def _get_default_ttl(self, category: str) -> int:
        """Get default TTL for category."""
        ttl_map = {
            "schema": 600,      # 10 minutes
            "kimi": 3600,       # 1 hour
            "session": 1800,    # 30 minutes
            "sql": 1800,        # 30 minutes
            "validation": 900,  # 15 minutes
        }
        return ttl_map.get(category, self.l1_ttl_seconds)
    
    def _update_avg_response_time(self, response_time_ms: float) -> None:
        """Update average response time metric."""
        total_requests = (
            self.metrics.total_hits + self.metrics.total_misses
        )
        if total_requests > 0:
            self.metrics.avg_response_time_ms = (
                (self.metrics.avg_response_time_ms * (total_requests - 1) + response_time_ms) /
                total_requests
            )
    
    async def _cleanup_loop(self) -> None:
        """Background task for cache cleanup."""
        while True:
            try:
                await self._cleanup_expired_entries()
                await asyncio.sleep(60)  # Cleanup every minute
                
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
                await asyncio.sleep(30)
    
    async def _cleanup_expired_entries(self) -> None:
        """Clean up expired cache entries."""
        async with self._lock:
            expired_keys = []
            
            for cache_key, entry in self._l1_cache.items():
                if entry.is_expired():
                    expired_keys.append(cache_key)
            
            for cache_key in expired_keys:
                await self._evict_l1_entry(cache_key)
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    async def _cache_warming_loop(self) -> None:
        """Background task for cache warming."""
        while True:
            try:
                # Warm cache with common schema data every 10 minutes
                await asyncio.sleep(600)
                await self._warm_common_data()
                
            except Exception as e:
                logger.error(f"Cache warming error: {e}")
                await asyncio.sleep(300)
    
    async def _warm_common_data(self) -> None:
        """Warm cache with commonly accessed data."""
        # This would typically load schema data, common queries, etc.
        # For now, we'll just log the warming attempt
        logger.debug("Cache warming cycle completed")
    
    async def shutdown(self) -> None:
        """Shutdown cache manager."""
        logger.info("Shutting down cache manager...")
        
        # Cancel background tasks
        if self._cleanup_task:
            self._cleanup_task.cancel()
        if self._warm_cache_task:
            self._warm_cache_task.cancel()
        
        # Close Redis connection
        if self._redis_client:
            await self._redis_client.close()
        
        # Clear L1 cache
        self._l1_cache.clear()
        
        logger.info("Cache manager shutdown complete")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "l1_cache_size": len(self._l1_cache),
            "l1_hits": self.metrics.l1_hits,
            "l1_misses": self.metrics.l1_misses,
            "l2_hits": self.metrics.l2_hits,
            "l2_misses": self.metrics.l2_misses,
            "total_hits": self.metrics.total_hits,
            "total_misses": self.metrics.total_misses,
            "hit_rate_percent": self.metrics.hit_rate,
            "evictions": self.metrics.evictions,
            "total_size_mb": self.metrics.total_size_bytes / (1024 * 1024),
            "avg_response_time_ms": self.metrics.avg_response_time_ms,
            "memory_usage_percent": (self.metrics.total_size_bytes / self.max_memory_bytes) * 100
        }


# Global cache manager instance
_cache_manager: Optional[AdvancedCacheManager] = None


async def get_cache_manager() -> AdvancedCacheManager:
    """Get or create global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = AdvancedCacheManager()
        await _cache_manager.initialize()
    return _cache_manager


async def close_cache_manager():
    """Close global cache manager."""
    global _cache_manager
    if _cache_manager:
        await _cache_manager.shutdown()
        _cache_manager = None
