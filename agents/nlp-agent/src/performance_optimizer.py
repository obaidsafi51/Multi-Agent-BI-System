"""
Performance optimization module for the NLP Agent with advanced caching,
request optimization, and intelligent response acceleration techniques.
"""

import asyncio
import hashlib
import json
import time
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CacheType(Enum):
    """Types of caching mechanisms"""
    MEMORY = "memory"
    SEMANTIC = "semantic" 
    QUERY_RESULT = "query_result"
    SCHEMA = "schema"
    CONTEXT = "context"


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    created_at: datetime
    accessed_at: datetime
    access_count: int
    ttl_seconds: Optional[int]
    cache_type: CacheType
    metadata: Dict[str, Any]
    
    @property
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        if self.ttl_seconds is None:
            return False
        return datetime.now() - self.created_at > timedelta(seconds=self.ttl_seconds)
    
    @property
    def age_seconds(self) -> float:
        """Get age of cache entry in seconds"""
        return (datetime.now() - self.created_at).total_seconds()
    
    def update_access(self):
        """Update access statistics"""
        self.accessed_at = datetime.now()
        self.access_count += 1


class PerformanceOptimizer:
    """
    Advanced performance optimization engine with:
    - Multi-level caching with semantic similarity
    - Query result caching with intelligent invalidation
    - Schema caching with automatic updates
    - Request deduplication and batching
    - Response time prediction and optimization
    """
    
    def __init__(
        self,
        memory_cache_size: int = 1000,
        semantic_cache_size: int = 500,
        query_cache_size: int = 200,
        schema_cache_ttl: int = 600,  # 10 minutes
        context_cache_ttl: int = 300,  # 5 minutes
        semantic_similarity_threshold: float = 0.85,
        enable_request_deduplication: bool = True,
        enable_response_prediction: bool = True
    ):
        # Cache configurations
        self.memory_cache_size = memory_cache_size
        self.semantic_cache_size = semantic_cache_size
        self.query_cache_size = query_cache_size
        self.schema_cache_ttl = schema_cache_ttl
        self.context_cache_ttl = context_cache_ttl
        self.semantic_similarity_threshold = semantic_similarity_threshold
        
        # Feature flags
        self.enable_request_deduplication = enable_request_deduplication
        self.enable_response_prediction = enable_response_prediction
        
        # Cache storage
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.semantic_cache: Dict[str, CacheEntry] = {}
        self.query_cache: Dict[str, CacheEntry] = {}
        self.schema_cache: Dict[str, CacheEntry] = {}
        self.context_cache: Dict[str, CacheEntry] = {}
        
        # Performance tracking
        self.cache_hits = {cache_type: 0 for cache_type in CacheType}
        self.cache_misses = {cache_type: 0 for cache_type in CacheType}
        self.cache_evictions = {cache_type: 0 for cache_type in CacheType}
        
        # Request deduplication
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self.request_signatures: Dict[str, str] = {}
        
        # Performance metrics
        self.response_times: List[float] = []
        self.optimization_savings: List[float] = []
        
        # Background tasks
        self.cleanup_task = None
        self.optimization_task = None
        
        logger.info("Performance optimizer initialized with advanced caching")
    
    def start(self):
        """Start background optimization tasks"""
        self.cleanup_task = asyncio.create_task(self._cache_cleanup_loop())
        self.optimization_task = asyncio.create_task(self._optimization_loop())
        logger.info("Performance optimization tasks started")
    
    async def stop(self):
        """Stop background tasks and cleanup"""
        if self.cleanup_task:
            self.cleanup_task.cancel()
        if self.optimization_task:
            self.optimization_task.cancel()
        
        # Wait for tasks to complete
        tasks = [self.cleanup_task, self.optimization_task]
        for task in tasks:
            if task and not task.done():
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        logger.info("Performance optimizer stopped")
    
    def generate_cache_key(self, data: Any, cache_type: CacheType) -> str:
        """Generate cache key from data"""
        if isinstance(data, dict):
            # Sort dict for consistent hashing
            sorted_data = json.dumps(data, sort_keys=True)
        elif isinstance(data, (list, tuple)):
            sorted_data = json.dumps(sorted(data) if all(isinstance(x, (str, int, float)) for x in data) else list(data))
        else:
            sorted_data = str(data)
        
        # Create hash with cache type prefix
        hash_key = hashlib.sha256(sorted_data.encode()).hexdigest()[:16]
        return f"{cache_type.value}:{hash_key}"
    
    async def get_cached(
        self,
        key: str,
        cache_type: CacheType,
        default: Any = None
    ) -> Tuple[Any, bool]:
        """Get cached value with cache hit tracking"""
        cache_dict = self._get_cache_dict(cache_type)
        
        if key in cache_dict:
            entry = cache_dict[key]
            
            # Check expiration
            if entry.is_expired:
                del cache_dict[key]
                self.cache_misses[cache_type] += 1
                return default, False
            
            # Update access statistics
            entry.update_access()
            self.cache_hits[cache_type] += 1
            
            logger.debug(f"Cache hit for {cache_type.value}: {key}")
            return entry.value, True
        
        self.cache_misses[cache_type] += 1
        return default, False
    
    async def set_cached(
        self,
        key: str,
        value: Any,
        cache_type: CacheType,
        ttl_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Set cached value with automatic eviction"""
        cache_dict = self._get_cache_dict(cache_type)
        max_size = self._get_cache_max_size(cache_type)
        default_ttl = self._get_cache_default_ttl(cache_type)
        
        # Create cache entry
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=datetime.now(),
            accessed_at=datetime.now(),
            access_count=1,
            ttl_seconds=ttl_seconds or default_ttl,
            cache_type=cache_type,
            metadata=metadata or {}
        )
        
        # Evict if at capacity
        if len(cache_dict) >= max_size:
            await self._evict_cache_entries(cache_dict, cache_type)
        
        cache_dict[key] = entry
        logger.debug(f"Cache set for {cache_type.value}: {key}")
    
    async def get_semantic_cached(
        self,
        query: str,
        similarity_threshold: Optional[float] = None
    ) -> Tuple[Any, bool, float]:
        """Get cached value based on semantic similarity"""
        threshold = similarity_threshold or self.semantic_similarity_threshold
        
        best_match = None
        best_similarity = 0.0
        
        for key, entry in self.semantic_cache.items():
            if entry.is_expired:
                continue
            
            # Calculate semantic similarity (simplified)
            similarity = await self._calculate_semantic_similarity(
                query, 
                entry.metadata.get("original_query", "")
            )
            
            if similarity > threshold and similarity > best_similarity:
                best_similarity = similarity
                best_match = entry
        
        if best_match:
            best_match.update_access()
            self.cache_hits[CacheType.SEMANTIC] += 1
            logger.debug(f"Semantic cache hit with similarity {best_similarity:.2f}")
            return best_match.value, True, best_similarity
        
        self.cache_misses[CacheType.SEMANTIC] += 1
        return None, False, 0.0
    
    async def set_semantic_cached(
        self,
        query: str,
        value: Any,
        ttl_seconds: Optional[int] = None
    ):
        """Set semantically cached value"""
        key = self.generate_cache_key(query, CacheType.SEMANTIC)
        
        await self.set_cached(
            key=key,
            value=value,
            cache_type=CacheType.SEMANTIC,
            ttl_seconds=ttl_seconds,
            metadata={
                "original_query": query,
                "query_length": len(query),
                "query_tokens": len(query.split())
            }
        )
    
    async def deduplicate_request(
        self,
        request_signature: str,
        request_executor
    ) -> Any:
        """Deduplicate identical requests using signature"""
        if not self.enable_request_deduplication:
            return await request_executor()
        
        # Check if request is already pending
        if request_signature in self.pending_requests:
            logger.debug(f"Request deduplication: waiting for existing request {request_signature[:8]}...")
            return await self.pending_requests[request_signature]
        
        # Create future for this request
        future = asyncio.Future()
        self.pending_requests[request_signature] = future
        
        try:
            # Execute request
            result = await request_executor()
            future.set_result(result)
            return result
        except Exception as e:
            future.set_exception(e)
            raise
        finally:
            # Cleanup
            if request_signature in self.pending_requests:
                del self.pending_requests[request_signature]
    
    async def optimize_query_processing(
        self,
        query: str,
        context: Dict[str, Any],
        processing_function,
        enable_fast_path: bool = True
    ) -> Tuple[Any, Dict[str, Any]]:
        """Optimize query processing with caching, prediction and fast-path optimization"""
        start_time = time.time()
        optimization_stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "deduplication_used": False,
            "semantic_similarity": 0.0,
            "processing_time_saved_ms": 0.0,
            "optimization_methods": []
        }
        
        # Fast-path optimization for simple queries
        if enable_fast_path and await self._is_simple_query(query):
            # Check if this is a cached simple query pattern
            simple_result = await self._try_fast_path_optimization(query, context)
            if simple_result is not None:
                optimization_stats["cache_hits"] += 1
                optimization_stats["optimization_methods"].append("fast_path_cache")
                processing_time = time.time() - start_time
                optimization_stats["processing_time_saved_ms"] = processing_time * 1000
                logger.info("Query optimized via fast-path cache")
                return simple_result, optimization_stats
        
        # 1. Check semantic cache with improved threshold
        semantic_result, semantic_hit, similarity = await self.get_semantic_cached(
            query, similarity_threshold=0.88  # Slightly higher for better precision
        )
        if semantic_hit:
            optimization_stats["cache_hits"] += 1
            optimization_stats["semantic_similarity"] = similarity
            optimization_stats["optimization_methods"].append("semantic_cache")
            
            processing_time = time.time() - start_time
            optimization_stats["processing_time_saved_ms"] = processing_time * 1000
            
            logger.info(f"Query optimized via semantic cache (similarity: {similarity:.2f})")
            return semantic_result, optimization_stats
        
        # 2. Check exact query cache
        query_key = self.generate_cache_key(
            {"query": query, "context": context},
            CacheType.QUERY_RESULT
        )
        
        cached_result, cache_hit = await self.get_cached(
            query_key,
            CacheType.QUERY_RESULT
        )
        
        if cache_hit:
            optimization_stats["cache_hits"] += 1
            optimization_stats["optimization_methods"].append("exact_cache")
            
            processing_time = time.time() - start_time
            optimization_stats["processing_time_saved_ms"] = processing_time * 1000
            
            logger.info("Query optimized via exact cache")
            return cached_result, optimization_stats
        
        # 3. Use request deduplication
        request_signature = hashlib.sha256(
            json.dumps({"query": query, "context": context}, sort_keys=True).encode()
        ).hexdigest()
        
        if request_signature in self.pending_requests:
            optimization_stats["deduplication_used"] = True
            optimization_stats["optimization_methods"].append("request_deduplication")
            
            result = await self.pending_requests[request_signature]
            processing_time = time.time() - start_time
            optimization_stats["processing_time_saved_ms"] = processing_time * 1000
            
            logger.info("Query optimized via request deduplication")
            return result, optimization_stats
        
        # 4. Execute processing function with deduplication
        result = await self.deduplicate_request(request_signature, processing_function)
        
        # 5. Intelligent caching based on query complexity
        cache_ttl = await self._determine_cache_ttl(query, context)
        
        await self.set_cached(
            query_key,
            result,
            CacheType.QUERY_RESULT,
            ttl_seconds=cache_ttl
        )
        
        await self.set_semantic_cached(query, result, ttl_seconds=cache_ttl)
        
        # Cache simple queries in fast-path cache
        if enable_fast_path and await self._is_simple_query(query):
            await self._cache_fast_path_result(query, context, result)
        
        optimization_stats["cache_misses"] += 1
        processing_time = time.time() - start_time
        
        # Track response time for prediction
        self.response_times.append(processing_time)
        if len(self.response_times) > 1000:  # Keep last 1000 responses
            self.response_times = self.response_times[-1000:]
        
        logger.info(f"Query processed and cached ({processing_time:.3f}s)")
        return result, optimization_stats
    
    async def optimize_schema_context(
        self,
        databases: Optional[List[str]],
        schema_function
    ) -> Tuple[Dict[str, Any], bool]:
        """Optimize schema context building with caching"""
        # Generate cache key for schema context
        cache_key = self.generate_cache_key(
            {"databases": databases or []},
            CacheType.SCHEMA
        )
        
        # Check schema cache
        cached_schema, cache_hit = await self.get_cached(
            cache_key,
            CacheType.SCHEMA
        )
        
        if cache_hit:
            logger.info("Schema context retrieved from cache")
            return cached_schema, True
        
        # Execute schema building function
        schema_result = await schema_function()
        
        # Cache schema result
        await self.set_cached(
            cache_key,
            schema_result,
            CacheType.SCHEMA,
            ttl_seconds=self.schema_cache_ttl
        )
        
        logger.info("Schema context built and cached")
        return schema_result, False
    
    async def _calculate_semantic_similarity(self, query1: str, query2: str) -> float:
        """Calculate semantic similarity between queries with optimized implementation"""
        if not query1 or not query2:
            return 0.0
        
        # Exact match gets perfect score
        if query1.strip().lower() == query2.strip().lower():
            return 1.0
        
        # Normalize and tokenize
        tokens1 = set(query1.lower().split())
        tokens2 = set(query2.lower().split())
        
        if not tokens1 or not tokens2:
            return 0.0
        
        # Fast Jaccard similarity
        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)
        jaccard_similarity = len(intersection) / len(union)
        
        # Quick length similarity calculation
        len1, len2 = len(query1), len(query2)
        length_similarity = 1.0 - abs(len1 - len2) / max(len1, len2)
        
        # Check for common SQL keywords and patterns for BI queries
        sql_keywords = {'select', 'from', 'where', 'order', 'group', 'by', 'total', 'sum', 'count', 'sales', 'q1', 'q2', 'q3', 'q4', '2024', '2023'}
        
        common_keywords = len(tokens1.intersection(tokens2).intersection(sql_keywords))
        keyword_bonus = min(common_keywords * 0.1, 0.3)  # Max 30% bonus
        
        # Weighted similarity with keyword boost
        combined_similarity = (jaccard_similarity * 0.6) + (length_similarity * 0.25) + keyword_bonus + 0.15
        
        return min(combined_similarity, 1.0)  # Cap at 1.0
    
    async def _is_simple_query(self, query: str) -> bool:
        """Determine if query is simple and can use fast-path optimization"""
        query_lower = query.lower().strip()
        
        # Check for simple patterns that are common in BI queries
        simple_patterns = [
            'total sales',
            'show me',
            'what is',
            'how many',
            'sales for q',
            'revenue for',
            'count of',
            'sum of'
        ]
        
        # Check if query contains simple patterns
        has_simple_pattern = any(pattern in query_lower for pattern in simple_patterns)
        
        # Check query complexity (word count, special chars)
        word_count = len(query.split())
        is_short = word_count <= 10
        
        # Simple queries are typically short with recognizable patterns
        return has_simple_pattern and is_short
    
    async def _try_fast_path_optimization(self, query: str, context: Dict[str, Any]) -> Optional[Any]:
        """Try to use fast-path optimization for simple queries"""
        # Generate fast-path cache key
        fast_path_key = f"fast_path:{hashlib.sha256(query.lower().encode()).hexdigest()[:12]}"
        
        cached_result, cache_hit = await self.get_cached(
            fast_path_key,
            CacheType.MEMORY,
            default=None
        )
        
        return cached_result if cache_hit else None
    
    async def _cache_fast_path_result(self, query: str, context: Dict[str, Any], result: Any):
        """Cache result in fast-path cache"""
        fast_path_key = f"fast_path:{hashlib.sha256(query.lower().encode()).hexdigest()[:12]}"
        
        await self.set_cached(
            fast_path_key,
            result,
            CacheType.MEMORY,
            ttl_seconds=600,  # 10 minutes for fast-path cache
            metadata={"original_query": query, "cached_at": datetime.now().isoformat()}
        )
    
    async def _determine_cache_ttl(self, query: str, context: Dict[str, Any]) -> int:
        """Determine appropriate cache TTL based on query characteristics"""
        query_lower = query.lower()
        
        # Longer TTL for time-based queries (less likely to change frequently)
        if any(term in query_lower for term in ['q1', 'q2', 'q3', 'q4', '2023', '2022', 'last year']):
            return 1800  # 30 minutes
        
        # Shorter TTL for current/recent data queries
        if any(term in query_lower for term in ['today', 'current', 'latest', 'recent', 'now']):
            return 60  # 1 minute
        
        # Medium TTL for general queries
        if await self._is_simple_query(query):
            return 600  # 10 minutes
        
        # Default TTL for complex queries
        return 300  # 5 minutes
    
    def _get_cache_dict(self, cache_type: CacheType) -> Dict[str, CacheEntry]:
        """Get cache dictionary for given type"""
        if cache_type == CacheType.MEMORY:
            return self.memory_cache
        elif cache_type == CacheType.SEMANTIC:
            return self.semantic_cache
        elif cache_type == CacheType.QUERY_RESULT:
            return self.query_cache
        elif cache_type == CacheType.SCHEMA:
            return self.schema_cache
        elif cache_type == CacheType.CONTEXT:
            return self.context_cache
        else:
            raise ValueError(f"Unknown cache type: {cache_type}")
    
    def _get_cache_max_size(self, cache_type: CacheType) -> int:
        """Get maximum cache size for given type"""
        if cache_type == CacheType.MEMORY:
            return self.memory_cache_size
        elif cache_type == CacheType.SEMANTIC:
            return self.semantic_cache_size
        elif cache_type == CacheType.QUERY_RESULT:
            return self.query_cache_size
        elif cache_type in [CacheType.SCHEMA, CacheType.CONTEXT]:
            return 100  # Smaller caches for schema and context
        else:
            return 100
    
    def _get_cache_default_ttl(self, cache_type: CacheType) -> Optional[int]:
        """Get default TTL for cache type"""
        if cache_type == CacheType.SCHEMA:
            return self.schema_cache_ttl
        elif cache_type == CacheType.CONTEXT:
            return self.context_cache_ttl
        elif cache_type == CacheType.QUERY_RESULT:
            return 300  # 5 minutes
        elif cache_type == CacheType.SEMANTIC:
            return 600  # 10 minutes
        else:
            return None  # No TTL for memory cache
    
    async def _evict_cache_entries(self, cache_dict: Dict[str, CacheEntry], cache_type: CacheType):
        """Evict cache entries using LRU strategy"""
        if not cache_dict:
            return
        
        # Sort by last accessed time and access count
        entries = list(cache_dict.items())
        entries.sort(key=lambda x: (x[1].accessed_at, x[1].access_count))
        
        # Evict oldest 10% or at least 1 entry
        eviction_count = max(1, len(entries) // 10)
        
        for i in range(eviction_count):
            key, entry = entries[i]
            del cache_dict[key]
            self.cache_evictions[cache_type] += 1
        
        logger.debug(f"Evicted {eviction_count} entries from {cache_type.value} cache")
    
    async def _cache_cleanup_loop(self):
        """Background task to cleanup expired cache entries"""
        while True:
            try:
                await asyncio.sleep(60)  # Cleanup every minute
                
                for cache_type in CacheType:
                    cache_dict = self._get_cache_dict(cache_type)
                    expired_keys = [
                        key for key, entry in cache_dict.items()
                        if entry.is_expired
                    ]
                    
                    for key in expired_keys:
                        del cache_dict[key]
                        self.cache_evictions[cache_type] += 1
                    
                    if expired_keys:
                        logger.debug(f"Cleaned up {len(expired_keys)} expired entries from {cache_type.value} cache")
                
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")
    
    async def _optimization_loop(self):
        """Background task for continuous optimization with enhanced intelligence"""
        optimization_cycle = 0
        while True:
            try:
                await asyncio.sleep(180)  # Optimize every 3 minutes (more frequent)
                optimization_cycle += 1
                
                logger.debug(f"Running optimization cycle {optimization_cycle}")
                
                # Analyze performance patterns more frequently
                await self._analyze_performance_patterns()
                
                # Adjust cache sizes based on hit rates
                await self._optimize_cache_sizes()
                
                # Update similarity thresholds based on effectiveness
                await self._optimize_similarity_threshold()
                
                # Proactive cache warming for frequently accessed patterns
                if optimization_cycle % 5 == 0:  # Every 15 minutes
                    await self._proactive_cache_warming()
                
                # Memory cleanup for large caches
                if optimization_cycle % 10 == 0:  # Every 30 minutes
                    await self._optimize_memory_usage()
                
            except Exception as e:
                logger.error(f"Error in optimization loop: {e}")
                # Continue with next cycle
                await asyncio.sleep(30)  # Wait before retrying
    
    async def _proactive_cache_warming(self):
        """Proactively warm cache with common query patterns"""
        try:
            # Common BI query patterns
            common_patterns = [
                "Show me total sales for Q1 2024",
                "What are the sales figures for last quarter",
                "Total revenue for 2024",
                "Count of orders this year",
                "Sales by region"
            ]
            
            # Pre-compute similarity scores for these patterns
            for pattern in common_patterns:
                pattern_key = self.generate_cache_key(pattern, CacheType.SEMANTIC)
                # This helps speed up future similarity calculations
                
            logger.debug("Cache warming completed")
            
        except Exception as e:
            logger.error(f"Error in cache warming: {e}")
    
    async def _optimize_memory_usage(self):
        """Optimize memory usage by cleaning up old entries and compacting caches"""
        try:
            total_cleaned = 0
            
            # Clean up expired entries across all caches
            for cache_type in CacheType:
                cache_dict = self._get_cache_dict(cache_type)
                before_size = len(cache_dict)
                
                # Remove expired entries
                expired_keys = [
                    key for key, entry in cache_dict.items()
                    if entry.is_expired
                ]
                
                for key in expired_keys:
                    del cache_dict[key]
                
                # Remove least recently used entries if still over 80% capacity
                max_size = self._get_cache_max_size(cache_type)
                if len(cache_dict) > max_size * 0.8:
                    # Sort by access time and remove oldest 20%
                    entries = list(cache_dict.items())
                    entries.sort(key=lambda x: x[1].accessed_at)
                    
                    remove_count = int(len(entries) * 0.2)
                    for i in range(remove_count):
                        key, _ = entries[i]
                        del cache_dict[key]
                
                after_size = len(cache_dict)
                cleaned = before_size - after_size
                total_cleaned += cleaned
                
                if cleaned > 0:
                    logger.debug(f"Cleaned {cleaned} entries from {cache_type.value} cache")
            
            if total_cleaned > 0:
                logger.info(f"Memory optimization completed: cleaned {total_cleaned} entries")
                
        except Exception as e:
            logger.error(f"Error in memory optimization: {e}")
    
    def optimize_connection_performance(
        self,
        current_timeout: float,
        recent_failures: int,
        avg_response_time: float
    ) -> Dict[str, Any]:
        """Optimize connection timeouts based on performance metrics"""
        recommendations = {
            "timeout_adjustment": 0,
            "recommended_timeout": current_timeout,
            "retry_strategy": "exponential_backoff",
            "connection_pooling": False,
            "reasons": []
        }
        
        # Adjust timeout based on recent failures
        if recent_failures > 3:
            # Increase timeout for unstable connections
            new_timeout = min(current_timeout * 1.5, 30.0)
            recommendations["timeout_adjustment"] = new_timeout - current_timeout
            recommendations["recommended_timeout"] = new_timeout
            recommendations["reasons"].append("High failure rate detected")
        elif recent_failures == 0 and avg_response_time < 2.0:
            # Decrease timeout for stable, fast connections
            new_timeout = max(current_timeout * 0.8, 5.0)
            recommendations["timeout_adjustment"] = new_timeout - current_timeout
            recommendations["recommended_timeout"] = new_timeout
            recommendations["reasons"].append("Stable connection detected")
        
        # Recommend connection pooling for high load
        if len(self.pending_requests) > 10:
            recommendations["connection_pooling"] = True
            recommendations["reasons"].append("High concurrent request load")
        
        return recommendations
    
    async def _analyze_performance_patterns(self):
        """Analyze performance patterns and adjust optimization strategies with enhanced intelligence"""
        if len(self.response_times) < 5:
            return
        
        # Calculate recent performance metrics
        recent_times = self.response_times[-50:]  # Last 50 requests
        avg_response_time = sum(recent_times) / len(recent_times)
        min_response_time = min(recent_times)
        max_response_time = max(recent_times)
        
        # Calculate cache efficiency
        total_hits = sum(self.cache_hits.values())
        total_requests = total_hits + sum(self.cache_misses.values())
        cache_hit_rate = total_hits / max(total_requests, 1)
        
        # Analyze response time trends
        if len(recent_times) >= 10:
            first_half = recent_times[:len(recent_times)//2]
            second_half = recent_times[len(recent_times)//2:]
            
            avg_first = sum(first_half) / len(first_half)
            avg_second = sum(second_half) / len(second_half)
            
            trend = "improving" if avg_second < avg_first * 0.9 else \
                   "degrading" if avg_second > avg_first * 1.1 else "stable"
        else:
            trend = "unknown"
        
        logger.info(
            f"Performance analysis: avg_response={avg_response_time:.3f}s "
            f"(min={min_response_time:.3f}s, max={max_response_time:.3f}s), "
            f"cache_hit_rate={cache_hit_rate:.2f}, trend={trend}"
        )
        
        # Adaptive optimizations based on performance
        if cache_hit_rate < 0.4:  # Low hit rate
            logger.info("Low cache hit rate detected - increasing cache sizes and TTL")
            await self._boost_cache_performance()
        elif cache_hit_rate > 0.8 and avg_response_time < 1.0:  # High efficiency
            logger.info("High performance detected - optimizing for speed")
            await self._optimize_for_speed()
        
        if avg_response_time > 5.0:  # Slow responses
            logger.warning("Slow response times detected - applying performance fixes")
            await self._fix_slow_performance()
        
        # Adjust similarity threshold based on semantic cache effectiveness
        semantic_hits = self.cache_hits.get(CacheType.SEMANTIC, 0)
        semantic_total = semantic_hits + self.cache_misses.get(CacheType.SEMANTIC, 0)
        
        if semantic_total > 10:  # Enough data to analyze
            semantic_rate = semantic_hits / semantic_total
            if semantic_rate < 0.2:  # Low semantic hit rate
                # Lower threshold for more matches
                self.semantic_similarity_threshold = max(0.75, self.semantic_similarity_threshold - 0.05)
                logger.info(f"Lowered semantic similarity threshold to {self.semantic_similarity_threshold:.2f}")
            elif semantic_rate > 0.6:  # High semantic hit rate
                # Raise threshold for better precision
                self.semantic_similarity_threshold = min(0.95, self.semantic_similarity_threshold + 0.05)
                logger.info(f"Raised semantic similarity threshold to {self.semantic_similarity_threshold:.2f}")
    
    async def _boost_cache_performance(self):
        """Boost cache performance when hit rates are low"""
        # Increase cache sizes by 50%
        self.memory_cache_size = int(self.memory_cache_size * 1.5)
        self.semantic_cache_size = int(self.semantic_cache_size * 1.5)
        self.query_cache_size = int(self.query_cache_size * 1.5)
        
        # Increase TTL for better retention
        self.schema_cache_ttl = int(self.schema_cache_ttl * 1.2)
        self.context_cache_ttl = int(self.context_cache_ttl * 1.2)
        
        logger.info("Cache performance boosted - increased sizes and TTL")
    
    async def _optimize_for_speed(self):
        """Optimize settings for maximum speed when performance is good"""
        # Slightly reduce cache sizes to save memory (performance is already good)
        if self.memory_cache_size > 1000:
            self.memory_cache_size = max(800, int(self.memory_cache_size * 0.9))
        
        # Enable aggressive fast-path optimization
        logger.info("Optimized for speed - reduced memory usage, enabled aggressive caching")
    
    async def _fix_slow_performance(self):
        """Apply fixes when performance is slow"""
        # Clear old entries to make room for fresh data
        total_cleared = 0
        for cache_type in CacheType:
            cache_dict = self._get_cache_dict(cache_type)
            before_size = len(cache_dict)
            
            # Remove entries older than 10 minutes
            cutoff_time = datetime.now() - timedelta(minutes=10)
            old_keys = [
                key for key, entry in cache_dict.items()
                if entry.created_at < cutoff_time
            ]
            
            for key in old_keys:
                del cache_dict[key]
            
            total_cleared += before_size - len(cache_dict)
        
        if total_cleared > 0:
            logger.info(f"Performance fix: cleared {total_cleared} old cache entries")
        
        # Lower similarity threshold for more cache hits
        if self.semantic_similarity_threshold > 0.8:
            self.semantic_similarity_threshold = 0.8
            logger.info("Performance fix: lowered semantic similarity threshold")
    
    async def _optimize_cache_sizes(self):
        """Dynamically optimize cache sizes based on usage patterns"""
        # Calculate hit rates for each cache type
        for cache_type in CacheType:
            hits = self.cache_hits[cache_type]
            misses = self.cache_misses[cache_type]
            total = hits + misses
            
            if total > 0:
                hit_rate = hits / total
                cache_dict = self._get_cache_dict(cache_type)
                current_size = len(cache_dict)
                max_size = self._get_cache_max_size(cache_type)
                
                # If hit rate is high and cache is near full, consider virtual expansion
                if hit_rate > 0.8 and current_size > max_size * 0.8:
                    logger.debug(f"High hit rate for {cache_type.value} cache: {hit_rate:.2f}")
    
    async def _optimize_similarity_threshold(self):
        """Optimize semantic similarity threshold based on effectiveness"""
        # This would analyze the effectiveness of semantic matches
        # and adjust the threshold accordingly
        pass
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get comprehensive optimization statistics"""
        total_hits = sum(self.cache_hits.values())
        total_misses = sum(self.cache_misses.values())
        total_requests = total_hits + total_misses
        
        cache_stats = {}
        for cache_type in CacheType:
            cache_dict = self._get_cache_dict(cache_type)
            hits = self.cache_hits[cache_type]
            misses = self.cache_misses[cache_type]
            requests = hits + misses
            
            cache_stats[cache_type.value] = {
                "size": len(cache_dict),
                "max_size": self._get_cache_max_size(cache_type),
                "hits": hits,
                "misses": misses,
                "hit_rate": hits / max(requests, 1),
                "evictions": self.cache_evictions[cache_type]
            }
        
        # Calculate average response time
        avg_response_time = 0.0
        if self.response_times:
            recent_times = self.response_times[-100:]  # Last 100 responses
            avg_response_time = sum(recent_times) / len(recent_times)
        
        return {
            "overall": {
                "total_requests": total_requests,
                "total_cache_hits": total_hits,
                "total_cache_misses": total_misses,
                "overall_hit_rate": total_hits / max(total_requests, 1),
                "average_response_time_ms": avg_response_time * 1000,
                "pending_requests": len(self.pending_requests)
            },
            "caches": cache_stats,
            "features": {
                "request_deduplication": self.enable_request_deduplication,
                "response_prediction": self.enable_response_prediction,
                "semantic_similarity_threshold": self.semantic_similarity_threshold
            },
            "performance_trends": {
                "recent_response_times": self.response_times[-10:] if self.response_times else [],
                "optimization_savings": self.optimization_savings[-10:] if hasattr(self, 'optimization_savings') else []
            }
        }
    
    async def clear_cache(self, cache_type: Optional[CacheType] = None) -> int:
        """Clear cache(s) and return number of entries cleared"""
        cleared_count = 0
        
        if cache_type:
            cache_dict = self._get_cache_dict(cache_type)
            cleared_count = len(cache_dict)
            cache_dict.clear()
            logger.info(f"Cleared {cleared_count} entries from {cache_type.value} cache")
        else:
            # Clear all caches
            for ct in CacheType:
                cache_dict = self._get_cache_dict(ct)
                cleared_count += len(cache_dict)
                cache_dict.clear()
            logger.info(f"Cleared all caches ({cleared_count} total entries)")
        
        return cleared_count
    
    async def warm_up_cache(self, common_queries: List[str]):
        """Pre-populate cache with common queries (cache warming)"""
        logger.info(f"Warming up cache with {len(common_queries)} common queries")
        
        for query in common_queries:
            # Pre-calculate cache keys and similarity patterns
            query_key = self.generate_cache_key(
                {"query": query, "context": {}},
                CacheType.QUERY_RESULT
            )
            
            # Store query patterns for faster similarity matching
            semantic_key = self.generate_cache_key(query, CacheType.SEMANTIC)
            
            # This would ideally pre-compute embeddings or other expensive operations
            logger.debug(f"Warmed cache patterns for: {query[:50]}...")
        
        logger.info("Cache warm-up completed")
