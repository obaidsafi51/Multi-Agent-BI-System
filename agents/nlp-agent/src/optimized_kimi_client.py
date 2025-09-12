"""
Optimized KIMI client with parallel processing, connection pooling, and semantic caching.
This client reduces latency by making parallel API calls and implements intelligent caching.
"""

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import hashlib

import httpx
from pydantic import ValidationError

from .models import KimiRequest, KimiResponse
from .cache_manager import AdvancedCacheManager

logger = logging.getLogger(__name__)


class KimiAPIError(Exception):
    """Base exception for KIMI API errors"""
    pass


class KimiRateLimitError(KimiAPIError):
    """Rate limit exceeded error"""
    pass


class SemanticCache:
    """Semantic cache for KIMI responses using query similarity"""
    
    def __init__(self, cache_manager: AdvancedCacheManager, similarity_threshold: float = 0.85):
        self.cache_manager = cache_manager
        self.similarity_threshold = similarity_threshold
        self.query_embeddings = {}  # In production, use Redis with vector similarity
    
    def _get_cache_key(self, query: str, operation: str) -> str:
        """Generate cache key for query and operation"""
        query_hash = hashlib.md5(query.lower().encode()).hexdigest()
        return f"kimi_semantic:{operation}:{query_hash}"
    
    async def get_cached_result(self, query: str, operation: str) -> Optional[Dict[str, Any]]:
        """Get cached result for similar query"""
        cache_key = self._get_cache_key(query, operation)
        return await self.cache_manager.get("kimi", cache_key)
    
    async def cache_result(self, query: str, operation: str, result: Dict[str, Any], ttl: int = 3600):
        """Cache result for future similar queries"""
        cache_key = self._get_cache_key(query, operation)
        await self.cache_manager.set("kimi", cache_key, result, ttl)
    
    def _calculate_similarity(self, query1: str, query2: str) -> float:
        """Simple similarity calculation - in production use proper embeddings"""
        words1 = set(query1.lower().split())
        words2 = set(query2.lower().split())
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        return len(intersection) / len(union) if union else 0.0


class RateLimiter:
    """Async rate limiter for KIMI API calls"""
    
    def __init__(self, max_calls: int = 100, time_window: int = 60):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire rate limit token"""
        async with self.lock:
            now = time.time()
            # Remove old calls outside time window
            self.calls = [call_time for call_time in self.calls if now - call_time < self.time_window]
            
            if len(self.calls) >= self.max_calls:
                sleep_time = self.time_window - (now - self.calls[0]) + 0.1
                logger.warning(f"Rate limit reached, sleeping for {sleep_time:.2f}s")
                await asyncio.sleep(sleep_time)
                return await self.acquire()
            
            self.calls.append(now)


class OptimizedKimiClient:
    """Optimized KIMI client with parallel processing and intelligent caching"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.moonshot.ai/v1",
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        cache_manager: Optional[AdvancedCacheManager] = None,
        max_connections: int = 10
    ):
        self.api_key = api_key or os.getenv("KIMI_API_KEY")
        
        if not self.api_key or self.api_key in ["your_actual_kimi_api_key_here", "your_moonshot_api_key_here"]:
            raise ValueError("MOONSHOT API key is required")
        
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Connection pooling for better performance
        limits = httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_connections // 2
        )
        
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=limits,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
        
        # Initialize caching and rate limiting
        self.semantic_cache = SemanticCache(cache_manager) if cache_manager else None
        self.rate_limiter = RateLimiter(max_calls=90, time_window=60)  # Conservative rate limit
        
        # Performance metrics
        self.metrics = {
            "total_requests": 0,
            "cache_hits": 0,
            "parallel_requests": 0,
            "total_latency": 0.0
        }
        
        logger.info(f"Optimized KIMI client initialized with connection pooling (max_connections={max_connections})")
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def extract_all_financial_data_parallel(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Extract intent, entities, and ambiguities in parallel for maximum performance.
        This is the main optimization - reduces 3 sequential calls to 3 parallel calls.
        """
        start_time = time.time()
        
        try:
            # Check semantic cache for all operations
            cache_tasks = []
            if self.semantic_cache:
                cache_tasks = [
                    self.semantic_cache.get_cached_result(query, "intent"),
                    self.semantic_cache.get_cached_result(query, "entities"),
                    self.semantic_cache.get_cached_result(query, "ambiguities")
                ]
                cached_results = await asyncio.gather(*cache_tasks, return_exceptions=True)
                
                # Check if all results are cached
                if all(result and not isinstance(result, Exception) for result in cached_results):
                    self.metrics["cache_hits"] += 3
                    logger.info("All financial data served from semantic cache")
                    return cached_results[0], cached_results[1], cached_results[2]
            
            # Prepare parallel tasks for KIMI API calls
            tasks = [
                self._extract_financial_intent_internal(query, context),
                self._extract_financial_entities_internal(query, context),
                self._detect_ambiguities_internal(query, context)
            ]
            
            # Execute all tasks in parallel
            logger.info(f"Executing 3 KIMI API calls in parallel for query: {query[:50]}...")
            intent_data, entities_data, ambiguities_data = await asyncio.gather(*tasks)
            
            # Cache results if caching is enabled
            if self.semantic_cache:
                cache_tasks = [
                    self.semantic_cache.cache_result(query, "intent", intent_data),
                    self.semantic_cache.cache_result(query, "entities", entities_data),
                    self.semantic_cache.cache_result(query, "ambiguities", ambiguities_data)
                ]
                await asyncio.gather(*cache_tasks, return_exceptions=True)
            
            # Update metrics
            execution_time = time.time() - start_time
            self.metrics["parallel_requests"] += 1
            self.metrics["total_latency"] += execution_time
            
            logger.info(f"Parallel financial data extraction completed in {execution_time:.2f}s")
            return intent_data, entities_data, ambiguities_data
            
        except Exception as e:
            logger.error(f"Parallel financial data extraction failed: {e}")
            raise KimiAPIError(f"Parallel extraction failed: {e}")
    
    async def _make_request_with_rate_limit(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request with rate limiting and retry logic"""
        
        # Acquire rate limit token
        await self.rate_limiter.acquire()
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(f"Making {method} request to {url} (attempt {attempt + 1})")
                
                response = await self.client.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params
                )
                
                self.metrics["total_requests"] += 1
                
                # Handle different HTTP status codes
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    raise KimiAPIError("Invalid API key or authentication failed")
                elif response.status_code == 429:
                    # Rate limit hit, wait longer
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Rate limit exceeded, waiting {wait_time}s")
                    await asyncio.sleep(wait_time)
                    continue
                elif response.status_code >= 500:
                    if attempt < self.max_retries:
                        wait_time = self.retry_delay * (2 ** attempt)
                        logger.warning(f"Server error {response.status_code}, retrying in {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        raise KimiAPIError(f"Server error: {response.status_code}")
                else:
                    error_detail = response.text
                    raise KimiAPIError(f"API error {response.status_code}: {error_detail}")
                    
            except httpx.TimeoutException:
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Request timeout, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise KimiAPIError("Request timed out after all retries")
            except httpx.RequestError as e:
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Request error: {e}, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise KimiAPIError(f"Request failed: {e}")
        
        raise KimiAPIError("Max retries exceeded")
    
    async def _extract_financial_intent_internal(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Internal method for extracting financial intent"""
        system_prompt = """You are a financial data analysis expert. Your task is to analyze natural language queries from CFOs and extract structured financial intent.

Extract the following information from the query:
1. metric_type: The type of financial metric (revenue, profit, cash_flow, budget, investment, ratio, etc.)
2. time_period: The time period requested (specific dates, quarters, years, relative periods)
3. aggregation_level: How data should be aggregated (daily, monthly, quarterly, yearly)
4. filters: Any additional filters or conditions as a JSON object (e.g., {"department": "sales", "region": "north"})
5. comparison_periods: Any comparison periods mentioned as a JSON array (e.g., ["previous_quarter", "same_period_last_year"])
6. visualization_hint: Suggested chart type if mentioned or implied

IMPORTANT: Return ONLY a valid JSON object with these exact fields:
{
    "metric_type": "string value",
    "time_period": "string value", 
    "aggregation_level": "string value",
    "filters": {},
    "comparison_periods": [],
    "visualization_hint": "string value or null",
    "confidence_score": 0.8
}

If any information is unclear or missing, use empty objects/arrays or "unknown" for string fields. Do NOT include explanatory text."""

        user_message = f"Query: {query}"
        if context:
            user_message += f"\nContext: {json.dumps(context)}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        try:
            response_data = await self._make_request_with_rate_limit(
                method="POST",
                endpoint="/chat/completions",
                data={
                    "model": "moonshot-v1-8k",
                    "messages": messages,
                    "temperature": 0.1,
                    "max_tokens": 1000
                }
            )
            
            assistant_message = response_data["choices"][0]["message"]["content"]
            
            # Parse JSON response
            try:
                intent_data = json.loads(assistant_message)
                return intent_data
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\{.*\}', assistant_message, re.DOTALL)
                if json_match:
                    intent_data = json.loads(json_match.group())
                    return intent_data
                else:
                    raise KimiAPIError("Could not extract JSON from KIMI response")
                    
        except Exception as e:
            logger.error(f"Financial intent extraction failed: {e}")
            raise KimiAPIError(f"Intent extraction failed: {e}")
    
    async def _extract_financial_entities_internal(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Internal method for extracting financial entities"""
        system_prompt = """You are a financial entity recognition expert. Extract all financial entities from the given query.

For each entity found, provide:
1. entity_type: Type of entity (metric, time_period, department, currency, percentage, etc.)
2. entity_value: Normalized value of the entity
3. confidence_score: Confidence in recognition (0.0 to 1.0)
4. synonyms: Alternative terms for this entity
5. original_text: Original text from the query

Return a JSON array of entities. If no entities are found, return an empty array."""

        user_message = f"Query: {query}"
        if context:
            user_message += f"\nContext: {json.dumps(context)}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        try:
            response_data = await self._make_request_with_rate_limit(
                method="POST",
                endpoint="/chat/completions",
                data={
                    "model": "moonshot-v1-8k",
                    "messages": messages,
                    "temperature": 0.1,
                    "max_tokens": 1500
                }
            )
            
            assistant_message = response_data["choices"][0]["message"]["content"]
            
            try:
                entities_data = json.loads(assistant_message)
                return entities_data if isinstance(entities_data, list) else []
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\[.*\]', assistant_message, re.DOTALL)
                if json_match:
                    entities_data = json.loads(json_match.group())
                    return entities_data if isinstance(entities_data, list) else []
                else:
                    logger.warning("Could not extract JSON array from KIMI response")
                    return []
                    
        except Exception as e:
            logger.error(f"Financial entity extraction failed: {e}")
            return []
    
    async def _detect_ambiguities_internal(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Internal method for detecting ambiguities"""
        system_prompt = """You are an expert at detecting ambiguities in financial queries. Analyze the query and identify any unclear or ambiguous parts that might need clarification.

For each ambiguity found, provide:
1. ambiguity_type: Type of ambiguity (time_period, metric_type, comparison_basis, aggregation_level, entity_reference)
2. description: Description of what is ambiguous
3. possible_interpretations: List of possible interpretations
4. confidence_score: Confidence in ambiguity detection (0.0 to 1.0)
5. suggested_clarification: A clarifying question to ask the user

Return a JSON array of ambiguities. If no ambiguities are found, return an empty array."""

        user_message = f"Query: {query}"
        if context:
            user_message += f"\nContext: {json.dumps(context)}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        try:
            response_data = await self._make_request_with_rate_limit(
                method="POST",
                endpoint="/chat/completions",
                data={
                    "model": "moonshot-v1-8k",
                    "messages": messages,
                    "temperature": 0.2,
                    "max_tokens": 1500
                }
            )
            
            assistant_message = response_data["choices"][0]["message"]["content"]
            
            try:
                ambiguities_data = json.loads(assistant_message)
                return ambiguities_data if isinstance(ambiguities_data, list) else []
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\[.*\]', assistant_message, re.DOTALL)
                if json_match:
                    ambiguities_data = json.loads(json_match.group())
                    return ambiguities_data if isinstance(ambiguities_data, list) else []
                else:
                    logger.warning("Could not extract JSON array from KIMI response")
                    return []
                    
        except Exception as e:
            logger.error(f"Ambiguity detection failed: {e}")
            return []
    
    async def health_check(self) -> bool:
        """Check if KIMI API is accessible"""
        try:
            messages = [{"role": "user", "content": "Hello"}]
            
            response_data = await self._make_request_with_rate_limit(
                method="POST",
                endpoint="/chat/completions",
                data={
                    "model": "moonshot-v1-8k",
                    "messages": messages,
                    "max_tokens": 10
                }
            )
            
            return response_data.get("choices", [{}])[0].get("message", {}).get("content") is not None
            
        except Exception as e:
            logger.error(f"KIMI API health check failed: {e}")
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        avg_latency = (
            self.metrics["total_latency"] / self.metrics["parallel_requests"]
            if self.metrics["parallel_requests"] > 0 else 0
        )
        
        cache_hit_rate = (
            self.metrics["cache_hits"] / self.metrics["total_requests"]
            if self.metrics["total_requests"] > 0 else 0
        )
        
        return {
            **self.metrics,
            "average_latency": avg_latency,
            "cache_hit_rate": cache_hit_rate
        }
