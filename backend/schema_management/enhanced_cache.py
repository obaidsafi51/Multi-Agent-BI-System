"""
Enhanced schema cache system with advanced caching capabilities.
"""

import asyncio
import json
import time
import hashlib
from typing import Any, Dict, List, Optional, Set, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging

from .models import CacheStats, DatabaseInfo, TableSchema
from .config import MCPSchemaConfig

logger = logging.getLogger(__name__)


class CacheEntryType(str, Enum):
    """Types of cache entries."""
    SCHEMA = "schema"
    TABLE = "table"
    DATABASE = "database"
    SEMANTIC_MAPPING = "semantic_mapping"
    QUERY_RESULT = "query_result"


@dataclass
class CacheEntry:
    """Represents a cache entry with metadata."""
    key: str
    data: Any
    entry_type: CacheEntryType
    timestamp: datetime
    ttl_seconds: int
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if the cache entry is expired."""
        age = (datetime.now() - self.timestamp).total_seconds()
        return age > self.ttl_seconds
    
    def is_expiring_soon(self, threshold_ratio: float = 0.1) -> bool:
        """Check if the cache entry is expiring soon."""
        age = (datetime.now() - self.timestamp).total_seconds()
        remaining_ratio = (self.ttl_seconds - age) / self.ttl_seconds
        return remaining_ratio <= threshold_ratio
    
    def touch(self):
        """Update access information."""
        self.access_count += 1
        self.last_accessed = datetime.now()


@dataclass
class CacheMetrics:
    """Cache performance metrics."""
    total_entries: int
    entries_by_type: Dict[CacheEntryType, int]
    hit_rate: float
    miss_rate: float
    eviction_count: int
    memory_usage_bytes: int
    average_access_count: float
    hottest_entries: List[str]
    coldest_entries: List[str]


class EnhancedSchemaCache:
    """
    Enhanced cache system with TTL-based caching, semantic metadata support,
    and advanced cache management features.
    """
    
    def __init__(
        self,
        config: Optional[MCPSchemaConfig] = None,
        max_entries: int = 10000,
        default_ttl: int = 300,
        semantic_ttl: int = 3600
    ):
        """
        Initialize enhanced schema cache.
        
        Args:
            config: MCP schema configuration
            max_entries: Maximum number of cache entries
            default_ttl: Default TTL for cache entries in seconds
            semantic_ttl: TTL for semantic mappings in seconds
        """
        self.config = config or MCPSchemaConfig.from_env()
        self.max_entries = max_entries
        self.default_ttl = default_ttl
        self.semantic_ttl = semantic_ttl
        
        # Cache storage
        self._cache: Dict[str, CacheEntry] = {}
        self._type_indices: Dict[CacheEntryType, Set[str]] = {
            entry_type: set() for entry_type in CacheEntryType
        }
        
        # Statistics
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "prefetch_hits": 0
        }
        
        # Cache warming and prefetching
        self._warming_tasks: Set[asyncio.Task] = set()
        self._prefetch_patterns: List[Dict[str, Any]] = []
        
        # Eviction policy settings
        self._eviction_threshold = 0.9  # Start eviction at 90% capacity
        
        logger.info(f"Enhanced schema cache initialized with max_entries={max_entries}")
    
    def _generate_key(self, operation: str, **kwargs) -> str:
        """Generate cache key for operation."""
        key_parts = [operation]
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")
        return ":".join(key_parts)
    
    def _get_entry_type(self, key: str) -> CacheEntryType:
        """Determine cache entry type from key."""
        if key.startswith("schema:"):
            return CacheEntryType.SCHEMA
        elif key.startswith("table:"):
            return CacheEntryType.TABLE
        elif key.startswith("database:"):
            return CacheEntryType.DATABASE
        elif key.startswith("semantic:"):
            return CacheEntryType.SEMANTIC_MAPPING
        elif key.startswith("query:"):
            return CacheEntryType.QUERY_RESULT
        else:
            return CacheEntryType.SCHEMA  # Default
    
    def _should_evict(self) -> bool:
        """Check if cache eviction should be triggered."""
        return len(self._cache) >= (self.max_entries * self._eviction_threshold)
    
    def _evict_entries(self, target_count: int = None) -> int:
        """
        Evict cache entries using LRU + access frequency policy.
        
        Args:
            target_count: Number of entries to evict (default: 10% of max)
            
        Returns:
            Number of entries evicted
        """
        if not target_count:
            target_count = max(1, int(self.max_entries * 0.1))
        
        # Get entries sorted by eviction priority (LRU + low access count)
        entries = list(self._cache.values())
        
        # Sort by: expired first, then by access frequency and last access time
        def eviction_score(entry: CacheEntry) -> tuple:
            if entry.is_expired():
                return (0, 0, 0)  # Expired entries have highest priority for eviction
            
            # Calculate normalized access frequency
            now = datetime.now()
            age_hours = (now - entry.timestamp).total_seconds() / 3600
            access_frequency = entry.access_count / max(age_hours, 0.1)
            
            # Calculate recency score
            last_access = entry.last_accessed or entry.timestamp
            recency_hours = (now - last_access).total_seconds() / 3600
            
            return (1, -access_frequency, recency_hours)  # Lower is better for eviction
        
        entries.sort(key=eviction_score)
        
        evicted_count = 0
        for entry in entries[:target_count]:
            self._remove_entry(entry.key)
            evicted_count += 1
            
            if evicted_count >= target_count:
                break
        
        self._stats["evictions"] += evicted_count
        logger.info(f"Evicted {evicted_count} cache entries")
        
        return evicted_count
    
    def _remove_entry(self, key: str):
        """Remove entry from cache and indices."""
        if key in self._cache:
            entry = self._cache[key]
            del self._cache[key]
            
            # Remove from type index
            if entry.entry_type in self._type_indices:
                self._type_indices[entry.entry_type].discard(key)
    
    async def get(self, operation: str, **kwargs) -> Optional[Any]:
        """
        Get cached data for operation.
        
        Args:
            operation: Operation name
            **kwargs: Operation parameters
            
        Returns:
            Cached data or None if not found
        """
        key = self._generate_key(operation, **kwargs)
        
        if key not in self._cache:
            self._stats["misses"] += 1
            return None
        
        entry = self._cache[key]
        
        # Check if expired
        if entry.is_expired():
            self._remove_entry(key)
            self._stats["misses"] += 1
            return None
        
        # Update access information
        entry.touch()
        self._stats["hits"] += 1
        
        logger.debug(f"Cache hit for key: {key}")
        return entry.data
    
    async def set(
        self,
        operation: str,
        data: Any,
        ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> bool:
        """
        Set cached data for operation.
        
        Args:
            operation: Operation name
            data: Data to cache
            ttl: Time to live in seconds
            metadata: Additional metadata
            **kwargs: Operation parameters
            
        Returns:
            True if cached successfully
        """
        key = self._generate_key(operation, **kwargs)
        entry_type = self._get_entry_type(key)
        
        # Determine TTL
        if ttl is None:
            if entry_type == CacheEntryType.SEMANTIC_MAPPING:
                ttl = self.semantic_ttl
            else:
                ttl = self.default_ttl
        
        # Check if eviction is needed
        if self._should_evict():
            self._evict_entries()
        
        # Create cache entry
        entry = CacheEntry(
            key=key,
            data=data,
            entry_type=entry_type,
            timestamp=datetime.now(),
            ttl_seconds=ttl,
            metadata=metadata or {}
        )
        
        # Remove existing entry if present
        if key in self._cache:
            self._remove_entry(key)
        
        # Add new entry
        self._cache[key] = entry
        self._type_indices[entry_type].add(key)
        
        logger.debug(f"Cached data for key: {key} (TTL: {ttl}s)")
        return True
    
    async def get_schema(self, cache_key: str) -> Optional[Any]:
        """Get schema from cache (compatibility method)."""
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            if not entry.is_expired():
                entry.touch()
                self._stats["hits"] += 1
                return entry.data
            else:
                self._remove_entry(cache_key)
        
        self._stats["misses"] += 1
        return None
    
    async def set_schema(self, cache_key: str, data: Any, ttl: int) -> bool:
        """Set schema in cache (compatibility method)."""
        entry = CacheEntry(
            key=cache_key,
            data=data,
            entry_type=CacheEntryType.SCHEMA,
            timestamp=datetime.now(),
            ttl_seconds=ttl
        )
        
        if self._should_evict():
            self._evict_entries()
        
        if cache_key in self._cache:
            self._remove_entry(cache_key)
        
        self._cache[cache_key] = entry
        self._type_indices[CacheEntryType.SCHEMA].add(cache_key)
        
        return True
    
    async def invalidate(self, pattern: str = None, entry_type: CacheEntryType = None) -> int:
        """
        Invalidate cache entries.
        
        Args:
            pattern: Pattern to match keys (supports wildcards)
            entry_type: Specific entry type to invalidate
            
        Returns:
            Number of entries invalidated
        """
        import fnmatch
        
        keys_to_remove = []
        
        if entry_type:
            # Invalidate by type
            keys_to_remove = list(self._type_indices[entry_type])
        elif pattern:
            # Invalidate by pattern
            for key in self._cache.keys():
                if fnmatch.fnmatch(key, pattern):
                    keys_to_remove.append(key)
        else:
            # Invalidate all
            keys_to_remove = list(self._cache.keys())
        
        for key in keys_to_remove:
            self._remove_entry(key)
        
        logger.info(f"Invalidated {len(keys_to_remove)} cache entries")
        return len(keys_to_remove)
    
    async def clear(self) -> int:
        """Clear all cache entries."""
        count = len(self._cache)
        self._cache.clear()
        for type_index in self._type_indices.values():
            type_index.clear()
        
        logger.info(f"Cleared all cache entries ({count} entries)")
        return count
    
    async def warm_cache(self, operations: List[Dict[str, Any]]) -> int:
        """
        Warm cache with predefined operations.
        
        Args:
            operations: List of operations to warm cache with
            
        Returns:
            Number of operations warmed
        """
        warmed_count = 0
        
        for op_config in operations:
            try:
                operation = op_config["operation"]
                params = op_config.get("params", {})
                
                # Check if already cached
                key = self._generate_key(operation, **params)
                if key in self._cache and not self._cache[key].is_expired():
                    continue
                
                # This would typically call the actual operation to populate cache
                # For now, we'll mark it as a warming placeholder
                await self.set(
                    operation,
                    {"_warming": True, "_params": params},
                    ttl=op_config.get("ttl", self.default_ttl),
                    **params
                )
                
                warmed_count += 1
                
            except Exception as e:
                logger.warning(f"Failed to warm cache for operation {op_config}: {e}")
        
        logger.info(f"Warmed cache with {warmed_count} operations")
        return warmed_count
    
    async def prefetch(self, patterns: List[str]) -> int:
        """
        Setup prefetching patterns for automatic cache warming.
        
        Args:
            patterns: List of prefetch patterns
            
        Returns:
            Number of patterns configured
        """
        self._prefetch_patterns.extend([{"pattern": p} for p in patterns])
        logger.info(f"Configured {len(patterns)} prefetch patterns")
        return len(patterns)
    
    def get_cache_stats(self) -> CacheStats:
        """Get cache statistics."""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0.0
        miss_rate = 1.0 - hit_rate
        
        # Calculate ages
        now = datetime.now()
        ages = [(now - entry.timestamp).total_seconds() for entry in self._cache.values()]
        
        # Estimate memory usage
        memory_usage_mb = 0.0
        try:
            import sys
            total_size = sum(sys.getsizeof(str(entry.data)) for entry in self._cache.values())
            memory_usage_mb = total_size / (1024 * 1024)
        except Exception:
            memory_usage_mb = len(self._cache) * 0.001  # Rough estimate
        
        return CacheStats(
            total_entries=len(self._cache),
            hit_rate=hit_rate,
            miss_rate=miss_rate,
            eviction_count=self._stats["evictions"],
            memory_usage_mb=memory_usage_mb,
            oldest_entry_age_seconds=int(max(ages)) if ages else 0,
            newest_entry_age_seconds=int(min(ages)) if ages else 0
        )
    
    def get_detailed_metrics(self) -> CacheMetrics:
        """Get detailed cache metrics."""
        # Calculate entry counts by type
        entries_by_type = {}
        for entry_type in CacheEntryType:
            entries_by_type[entry_type] = len(self._type_indices[entry_type])
        
        # Calculate access statistics
        access_counts = [entry.access_count for entry in self._cache.values()]
        avg_access_count = sum(access_counts) / len(access_counts) if access_counts else 0
        
        # Find hottest and coldest entries
        entries_by_access = sorted(
            self._cache.items(),
            key=lambda x: x[1].access_count,
            reverse=True
        )
        
        hottest_entries = [key for key, _ in entries_by_access[:10]]
        coldest_entries = [key for key, _ in entries_by_access[-10:]]
        
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0.0
        
        return CacheMetrics(
            total_entries=len(self._cache),
            entries_by_type=entries_by_type,
            hit_rate=hit_rate,
            miss_rate=1.0 - hit_rate,
            eviction_count=self._stats["evictions"],
            memory_usage_bytes=self._estimate_memory_usage(),
            average_access_count=avg_access_count,
            hottest_entries=hottest_entries,
            coldest_entries=coldest_entries
        )
    
    def _estimate_memory_usage(self) -> int:
        """Estimate memory usage in bytes."""
        try:
            import sys
            total_size = 0
            
            for entry in self._cache.values():
                total_size += sys.getsizeof(entry.key)
                total_size += sys.getsizeof(entry.data)
                total_size += sys.getsizeof(entry.timestamp)
                total_size += sys.getsizeof(entry.metadata)
            
            return total_size
        except Exception:
            # Fallback estimation
            return len(self._cache) * 1024  # 1KB per entry estimate
    
    async def setup_distributed_sync(self, sync_callback: Callable) -> bool:
        """
        Setup distributed cache synchronization.
        
        Args:
            sync_callback: Callback function for cache synchronization
            
        Returns:
            True if setup successful
        """
        # This would implement distributed cache synchronization
        # For now, just store the callback
        self._sync_callback = sync_callback
        logger.info("Distributed cache synchronization configured")
        return True
    
    async def sync_with_agents(self, agent_ids: List[str]) -> Dict[str, bool]:
        """
        Synchronize cache with other agents.
        
        Args:
            agent_ids: List of agent IDs to sync with
            
        Returns:
            Dictionary of sync results per agent
        """
        sync_results = {}
        
        for agent_id in agent_ids:
            try:
                # This would implement actual agent synchronization
                # For now, simulate successful sync
                sync_results[agent_id] = True
                logger.debug(f"Cache synchronized with agent: {agent_id}")
            except Exception as e:
                sync_results[agent_id] = False
                logger.warning(f"Failed to sync cache with agent {agent_id}: {e}")
        
        return sync_results
    
    def get_entries_expiring_soon(self, threshold_minutes: int = 5) -> List[str]:
        """
        Get cache entries that will expire soon.
        
        Args:
            threshold_minutes: Threshold in minutes for "expiring soon"
            
        Returns:
            List of cache keys expiring soon
        """
        threshold_ratio = threshold_minutes * 60 / self.default_ttl
        expiring_keys = []
        
        for key, entry in self._cache.items():
            if entry.is_expiring_soon(threshold_ratio):
                expiring_keys.append(key)
        
        return expiring_keys
    
    async def refresh_expiring_entries(self, refresh_callback: Callable) -> int:
        """
        Refresh entries that are expiring soon.
        
        Args:
            refresh_callback: Callback to refresh entry data
            
        Returns:
            Number of entries refreshed
        """
        expiring_keys = self.get_entries_expiring_soon()
        refreshed_count = 0
        
        for key in expiring_keys:
            try:
                entry = self._cache[key]
                
                # Call refresh callback to get new data
                new_data = await refresh_callback(entry.key, entry.data)
                
                if new_data is not None:
                    # Update the entry with new data and reset timestamp
                    entry.data = new_data
                    entry.timestamp = datetime.now()
                    refreshed_count += 1
                    
            except Exception as e:
                logger.warning(f"Failed to refresh cache entry {key}: {e}")
        
        logger.info(f"Refreshed {refreshed_count} expiring cache entries")
        return refreshed_count
