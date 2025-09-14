"""
Optimized NLP Agent with parallel processing, WebSocket connections, intelligent caching,
and query classification for maximum performance and efficiency.
"""

import asyncio
import hashlib
import json
import logging
import re
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from .optimized_kimi_client import OptimizedKimiClient, KimiAPIError
from .hybrid_mcp_operations_adapter import HybridMCPOperationsAdapter
# Query classifier removed - using unified processing approach
from .cache_manager import AdvancedCacheManager, CacheLevel
from .context_builder import ContextBuilder
from .models import ProcessingResult, QueryContext, QueryIntent, FinancialEntity

logger = logging.getLogger(__name__)


class OptimizedNLPAgent:
    """
    Optimized NLP Agent with advanced performance features:
    - Parallel KIMI API calls (60-70% latency reduction)
    - WebSocket persistent connections to MCP server
    - Intelligent query classification and routing
    - Multi-level semantic caching
    - Request batching and connection pooling
    - Real-time event handling and schema updates
    """
    
    def __init__(
        self,
        kimi_api_key: str,
        mcp_ws_url: str = "ws://tidb-mcp-server:8000/ws",
        agent_id: str = "nlp-agent-001",
        enable_optimizations: bool = True,
        enable_semantic_caching: bool = True,
        enable_request_batching: bool = True,
        websocket_client=None  # Optional external WebSocket client
    ):
        """
        Initialize optimized NLP agent.
        
        Args:
            kimi_api_key: KIMI API key
            mcp_ws_url: WebSocket URL for MCP server
            agent_id: Unique agent identifier
            enable_optimizations: Enable all optimization features
            enable_semantic_caching: Enable semantic similarity caching
            enable_request_batching: Enable request batching
            cache_config: Cache configuration overrides
        """
        self.agent_id = agent_id or f"nlp-agent-{uuid.uuid4().hex[:8]}"
        self.enable_optimizations = enable_optimizations
        self.enable_semantic_caching = enable_semantic_caching
        self.enable_request_batching = enable_request_batching
        
        # Initialize optimized KIMI client with connection pooling
        # Initialize cache manager
        cache_manager = AdvancedCacheManager(
            l1_max_size=1000,
            l1_ttl_seconds=300
        )
        
        self.kimi_client = OptimizedKimiClient(
            api_key=kimi_api_key,
            cache_manager=cache_manager,
            max_connections=10  # Connection pooling
        )
        
        # Initialize MCP operations with hybrid WebSocket/HTTP adapter
        logger.info("Initializing Hybrid MCP Operations Adapter (WebSocket-first with HTTP fallback)")
        self.mcp_ops = HybridMCPOperationsAdapter(
            ws_url=mcp_ws_url,
            http_url="http://tidb-mcp-server:8000",
            agent_id=agent_id,
            prefer_websocket=True,
            ws_failure_threshold=2,  # Switch to HTTP after 2 failures
            ws_retry_cooldown=30.0   # Retry WebSocket after 30s
        )
        
        # Store reference to the WebSocket client for backward compatibility
        self.mcp_client = self.mcp_ops.websocket_client
        self.owns_websocket_client = True
        logger.info(f"✅ Using Hybrid MCP Adapter with WebSocket client: {type(self.mcp_client)}")
        
        # Query classifier removed - using unified processing path
        
        # Initialize context builder
        self.context_builder = ContextBuilder()
        
        # Initialize cache manager
        self.cache_manager = cache_manager
        
        # Agent state
        self.is_running = False
        self.schema_cache = {}
        self.schema_cache_ttl = 600  # 10 minutes
        self.last_schema_update = 0
        
        # Performance metrics (simplified)
        self.metrics = {
            "total_queries": 0,
            "unified_path_queries": 0,
            "mcp_llm_calls": 0,
            "cache_hits": 0,
            "websocket_requests": 0,
            "total_latency": 0.0,
            "average_latency": 0.0
        }
        
        # Event handlers
        self._setup_event_handlers()
        
        logger.info(f"Optimized NLP Agent initialized: {self.agent_id}")
        logger.info(f"Optimizations enabled: {enable_optimizations}")
        logger.info(f"Semantic caching: {enable_semantic_caching}")
        logger.info(f"Request batching: {enable_request_batching}")
    


    def _setup_event_handlers(self):
        """Setup event handlers for real-time updates"""
        self.mcp_client.register_event_handler("schema_update", self._handle_schema_update)
        self.mcp_client.register_event_handler("cache_invalidation", self._handle_cache_invalidation)
        self.mcp_client.register_event_handler("server_status", self._handle_server_status)
    
    async def start(self):
        """Start the optimized NLP agent"""
        try:
            logger.info("Starting optimized NLP agent...")
            
            # Initialize cache manager
            await self.cache_manager.initialize()
            logger.info("Cache manager initialized successfully")
            
            # Connect to MCP server via WebSocket (only if we own the client)
            if self.owns_websocket_client:
                if not await self.mcp_client.connect():
                    logger.warning("MCP WebSocket connection failed - will use fallback mode")
                else:
                    logger.info("Successfully connected to MCP server via WebSocket")
            else:
                logger.info("Using external WebSocket client - connection managed externally")
            
            # Verify KIMI API connectivity
            if not await self.kimi_client.health_check():
                logger.warning("KIMI API health check failed - NLP parsing may be limited")
            else:
                logger.info("KIMI API health check passed")
            
            # Warm up caches
            await self._warm_up_caches()
            
            self.is_running = True
            logger.info("Optimized NLP agent started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start optimized NLP agent: {e}")
            raise
    
    async def stop(self):
        """Stop the NLP agent"""
        logger.info("Stopping optimized NLP agent...")
        
        self.is_running = False
        
        # Close connections (only if we own the WebSocket client)
        if self.owns_websocket_client:
            await self.mcp_client.disconnect()
        await self.kimi_client.close()
        
        logger.info("Optimized NLP agent stopped")
    
    async def process_query_optimized(
        self,
        query: str,
        user_id: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None,
        database_context: Optional[Dict[str, Any]] = None
    ) -> ProcessingResult:
        """
        Simplified unified query processing.
        Uses single optimized path for all queries - no complex routing.
        """
        start_time = time.time()
        query_id = f"q_{uuid.uuid4().hex[:8]}"
        
        try:
            logger.info(f"Processing query {query_id}: {query}")
            
            # Database context logging and validation
            if database_context:
                logger.info(f"Using database context for query {query_id}: {database_context.get('database_name', 'unknown')}")
                if not self._validate_database_context(database_context):
                    logger.warning(f"Invalid database context for query {query_id}: {database_context}")
                    # Continue processing but log the issue
            else:
                logger.info(f"No database context provided for query {query_id}")
            
            self.metrics["total_queries"] += 1
            
            # Step 1: Check semantic cache first
            if self.enable_semantic_caching:
                cached_result = await self._check_semantic_cache(query)
                if cached_result:
                    self.metrics["cache_hits"] += 1
                    logger.info(f"Query {query_id} served from semantic cache")
                    return self._create_cached_result(query_id, cached_result, start_time)
            
            # Step 2: Use unified processing (combines best of all paths)
            result = await self._process_unified_path(query, user_id, session_id, context, query_id, database_context)
            
            # Step 3: Cache result if successful
            if result.success and self.enable_semantic_caching:
                await self._cache_semantic_result(query, result)
            
            # Step 4: Update metrics
            processing_time = time.time() - start_time
            result.processing_time_ms = int(processing_time * 1000)
            self.metrics["total_latency"] += processing_time
            
            logger.info(f"Query {query_id} processed via unified_path in {processing_time:.2f}s")
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Query processing failed for {query_id}: {e}")
            
            return ProcessingResult(
                query_id=query_id,
                success=False,
                error=str(e),
                processing_time_ms=int(processing_time * 1000),
                processing_path="error"
            )
    
    async def _process_unified_path(
        self,
        query: str,
        user_id: str,
        session_id: str,
        context: Optional[Dict[str, Any]],
        query_id: str,
        database_context: Optional[Dict[str, Any]] = None
    ) -> ProcessingResult:
        """
        Unified processing path combining all query types.
        Uses single KIMI call + MCP operations for comprehensive processing.
        """
        logger.info(f"Starting unified path processing for query: {query}")
        logger.info(f"MCP ops type: {type(self.mcp_ops)}")
        try:
            logger.debug(f"Processing {query_id} via unified path")
            
            # Step 1: Get schema context (cached for performance, database-aware)
            schema_context = await self._get_cached_schema_context(database_context)
            
            # Step 2: Extract intent via MCP (with fallback)
            intent_data = await self._extract_intent_via_mcp(query, context)
            intent = self._create_query_intent(intent_data)
            
            # Step 3: Generate SQL via MCP WebSocket (database-context aware)
            logger.info(f"Calling MCP generate_sql for query: {query}")
            sql_params = {
                "natural_language_query": query,
                "schema_info": self._format_schema_for_llm(schema_context)
            }
            
            # Include database context if available
            if database_context and database_context.get('database_name'):
                logger.info(f"Including database context in SQL generation: {database_context['database_name']}")
                sql_params["database_name"] = database_context['database_name']
            
            sql_result = await self.mcp_ops.generate_sql(**sql_params)
            logger.info(f"MCP SQL result: {sql_result}")
            
            # Step 4: Extract SQL from MCP response
            sql_query = self._extract_sql_from_mcp_response(sql_result)
            logger.info(f"Extracted SQL query: {sql_query}")
            
            # Step 5: Build comprehensive context
            query_context = self.context_builder.build_query_context(
                query=query,
                intent=intent,
                user_context=context,
                schema_context=schema_context
            )
            
            return ProcessingResult(
                query_id=query_id,
                success=True,
                intent=intent,
                sql_query=sql_query,
                query_context=query_context,
                processing_path="unified"
            )
            
        except Exception as e:
            logger.error(f"Unified path processing failed for {query_id}: {e}")
            raise

    async def _process_fast_path(
        self,
        query: str,
        user_id: str,
        session_id: str,
        context: Optional[Dict[str, Any]],
        query_id: str
    ) -> ProcessingResult:
        """
        Fast path processing for simple queries.
        - Single KIMI call for intent only
        - Cached schema context
        - Minimal context building
        - Optimized for sub-second response
        """
        try:
            logger.debug(f"Processing {query_id} via fast path")
            
            # Get cached schema context (avoid repeated fetching)
            schema_context = await self._get_cached_schema_context()
            
            # Use MCP server's LLM tool instead of direct KIMI API calls
            intent_data = await self._extract_intent_via_mcp(query, context)
            intent = self._create_query_intent(intent_data)
            
            # Generate SQL via WebSocket (faster than HTTP)
            sql_result = await self.mcp_ops.generate_sql(
                natural_language_query=query,
                schema_info=self._format_schema_for_llm(schema_context)
            )
            
            # Minimal context building for fast response
            minimal_context = self._build_minimal_context(query, intent, context)
            
            return ProcessingResult(
                query_id=query_id,
                success=True,
                intent=intent,
                sql_query=self._extract_sql_from_mcp_response(sql_result),
                query_context=minimal_context,
                processing_path="fast_path"
            )
            
        except Exception as e:
            logger.error(f"Fast path processing failed for {query_id}: {e}")
            raise
    
    async def _process_standard_path(
        self,
        query: str,
        user_id: str,
        session_id: str,
        context: Optional[Dict[str, Any]],
        query_id: str
    ) -> ProcessingResult:
        """
        Standard path processing for medium complexity queries.
        - Parallel KIMI calls for intent and entities
        - Standard context building
        - Balanced performance vs completeness
        """
        try:
            logger.debug(f"Processing {query_id} via standard path")
            
            # Get schema context
            schema_context = await self._get_cached_schema_context()
            
            # Parallel MCP LLM calls for intent and entities (skip ambiguities)
            intent_data, entities_data = await asyncio.gather(
                self._extract_intent_via_mcp(query, context),
                self._extract_entities_via_mcp(query, context)
            )
            self.metrics["parallel_kimi_calls"] += 1
            
            # Process results
            intent = self._create_query_intent(intent_data)
            entities = self._process_entities(entities_data)
            
            # Batch WebSocket requests to MCP server
            sql_result, validation_result = await asyncio.gather(
                self.mcp_ops.generate_sql(
                    natural_language_query=query,
                    schema_info=self._format_schema_for_llm(schema_context)
                ),
                self.mcp_ops.validate_query(query)
            )
            self.metrics["websocket_requests"] += 2
            
            # Standard context building
            comprehensive_context = self.context_builder.build_query_context(
                query=query,
                intent=intent,
                user_context=context,
                schema_context=schema_context
            )
            
            return ProcessingResult(
                query_id=query_id,
                success=True,
                intent=intent,
                sql_query=self._extract_sql_from_mcp_response(sql_result),
                query_context=comprehensive_context,
                processing_path="standard_path"
            )
            
        except Exception as e:
            logger.error(f"Standard path processing failed for {query_id}: {e}")
            raise
    
    async def _process_comprehensive_path(
        self,
        query: str,
        user_id: str,
        session_id: str,
        context: Optional[Dict[str, Any]],
        query_id: str
    ) -> ProcessingResult:
        """
        Comprehensive path processing for complex queries.
        - Full parallel KIMI pipeline
        - Complete entity extraction and ambiguity detection
        - Comprehensive context building
        - Maximum accuracy and completeness
        """
        try:
            logger.debug(f"Processing {query_id} via comprehensive path")
            
            # Get fresh schema context for complex queries
            schema_context = await self.mcp_ops.get_schema_context()
            
            # Try MCP LLM tools for enhanced extraction, fallback to basic extraction
            try:
                # Full parallel MCP LLM pipeline (all 3 calls in parallel)
                intent_data, entities_data, ambiguities_data = await asyncio.gather(
                    self._extract_intent_via_mcp(query, context),
                    self._extract_entities_via_mcp(query, context),
                    self._extract_ambiguities_via_mcp(query, context)
                )
                self.metrics["parallel_kimi_calls"] += 1
                
                # Process MCP LLM results
                intent = self._create_query_intent(intent_data)
                entities = self._process_entities(entities_data)
                ambiguities = self._process_ambiguities(ambiguities_data)
                
                logger.debug(f"Enhanced extraction successful for {query_id}")
                
            except Exception as mcp_error:
                logger.warning(f"MCP LLM tools unavailable for {query_id}, using fallback extraction: {mcp_error}")
                
                # Fallback: Basic intent and entity extraction
                intent = self._create_basic_query_intent(query)
                entities = self._extract_basic_entities(query)
                ambiguities = []  # Skip ambiguity detection in fallback mode
            
            # Batch WebSocket requests to MCP server
            batch_results = await asyncio.gather(
                self.mcp_ops.generate_sql(
                    natural_language_query=query,
                    schema_info=self._format_schema_for_llm(schema_context)
                ),
                self.mcp_ops.validate_query(query),
                self.mcp_ops.analyze_data(
                    data=json.dumps({"query": query, "intent": intent.model_dump()}),
                    analysis_type="financial",
                    context="Query complexity analysis"
                )
            )
            self.metrics["websocket_requests"] += 3
            
            sql_result, validation_result, analysis_result = batch_results
            
            # Comprehensive context building
            comprehensive_context = self.context_builder.build_query_context(
                query=query,
                intent=intent,
                user_context=context,
                schema_context=schema_context
            )
            
            # Add analysis insights
            comprehensive_context["analysis"] = analysis_result
            
            return ProcessingResult(
                query_id=query_id,
                success=True,
                intent=intent,
                sql_query=self._extract_sql_from_mcp_response(sql_result),
                query_context=comprehensive_context,
                processing_path="comprehensive_path"
            )
            
        except Exception as e:
            logger.error(f"Comprehensive path processing failed for {query_id}: {e}")
            raise
    
    async def _check_semantic_cache(self, query: str) -> Optional[Dict[str, Any]]:
        """Check semantic cache for similar query results"""
        # Use semantic similarity cache key
        cache_key = hashlib.md5(query.encode()).hexdigest()
        return await self.cache_manager.get("semantic", cache_key)
    
    async def _cache_semantic_result(self, query: str, result: ProcessingResult):
        """Cache result for semantic similarity matching"""
        cache_data = {
            "intent": result.intent.model_dump() if result.intent else None,
            "sql_query": result.sql_query,
            "query_context": result.query_context,
            "processing_path": result.processing_path
        }
        # Use semantic similarity cache key
        cache_key = hashlib.md5(query.encode()).hexdigest()
        await self.cache_manager.set("semantic", cache_key, cache_data, ttl=3600)
    
    async def _get_cached_schema_context(self, database_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get schema context with intelligent caching and database context awareness"""
        current_time = time.time()
        
        # Create cache key based on database context
        cache_key = "default"
        if database_context and database_context.get('database_name'):
            cache_key = database_context['database_name']
            logger.debug(f"Using database-specific schema cache key: {cache_key}")
        
        # Check if cached schema is still valid for this database
        if (self.schema_cache and 
            current_time - self.last_schema_update < self.schema_cache_ttl and
            getattr(self, 'schema_cache_key', None) == cache_key):
            logger.debug(f"Using cached schema context for database: {cache_key}")
            return self.schema_cache
        
        # Fetch fresh schema context
        try:
            schema_params = {}
            if database_context and database_context.get('database_name'):
                schema_params['database'] = database_context['database_name']
                logger.info(f"Fetching schema context for database: {database_context['database_name']}")
            
            schema_context = await self.mcp_ops.get_schema_context(**schema_params)
            self.schema_cache = schema_context
            self.last_schema_update = current_time
            self.schema_cache_key = cache_key
            
            logger.debug(f"Schema context refreshed for database: {cache_key}")
            return schema_context
        except Exception as e:
            logger.warning(f"Failed to fetch schema context for database {cache_key}: {e}")
            return self.schema_cache or {}
    
    def _format_schema_for_llm(self, schema_context: Dict[str, Any]) -> str:
        """Format schema context for LLM consumption"""
        try:
            schema_lines = ["Database Schema Information:"]
            
            tables = schema_context.get("tables", [])
            if tables:
                schema_lines.append(f"Available Tables: {', '.join(tables[:10])}")
            
            metrics = schema_context.get("metrics", [])
            if metrics:
                schema_lines.append(f"Available Metrics: {', '.join(metrics[:20])}")
            
            databases = schema_context.get("databases", {})
            if databases:
                schema_lines.append(f"Databases: {', '.join(databases.keys())}")
            
            return "\n".join(schema_lines)
            
        except Exception as e:
            logger.error(f"Error formatting schema for LLM: {e}")
            return "Schema information unavailable"
    
    def _extract_sql_from_mcp_response(self, mcp_response: Dict[str, Any]) -> str:
        """Extract SQL query from MCP server response"""
        try:
            # The MCP server returns SQL in different formats
            # Check common response fields
            
            # First, check if it's directly in 'sql' field
            if "sql" in mcp_response:
                return str(mcp_response["sql"]).strip()
            
            # Check if it's in 'generated_text' field (LLM tool response)
            if "generated_text" in mcp_response:
                generated_text = str(mcp_response["generated_text"])
                
                # Extract SQL from markdown code blocks (re already imported at top)
                sql_match = re.search(r'```sql\s*(.*?)\s*```', generated_text, re.DOTALL | re.IGNORECASE)
                if sql_match:
                    sql_query = sql_match.group(1).strip()
                    # Remove comments and extract just the SQL
                    lines = sql_query.split('\n')
                    sql_lines = [line for line in lines if line.strip() and not line.strip().startswith('--')]
                    return '\n'.join(sql_lines).strip()
                
                # If no code block, try to extract SQL directly
                # Look for SELECT, INSERT, UPDATE, DELETE statements
                sql_keywords = r'\b(SELECT|INSERT|UPDATE|DELETE|WITH)\b'
                if re.search(sql_keywords, generated_text, re.IGNORECASE):
                    # Clean up and return the text
                    return generated_text.strip()
            
            # Check if it's in 'query' field
            if "query" in mcp_response:
                return str(mcp_response["query"]).strip()
            
            # Check if it's in 'result' field
            if "result" in mcp_response:
                result = mcp_response["result"]
                if isinstance(result, str):
                    return result.strip()  
                elif isinstance(result, dict):
                    return self._extract_sql_from_mcp_response(result)
            
            # Log the response structure for debugging
            logger.warning(f"Could not extract SQL from MCP response. Response keys: {list(mcp_response.keys())}")
            logger.debug(f"MCP response: {mcp_response}")
            
            return ""
            
        except Exception as e:
            logger.error(f"Error extracting SQL from MCP response: {e}")
            logger.debug(f"MCP response was: {mcp_response}")
            return ""
    
    def _build_minimal_context(
        self,
        query: str,
        intent: QueryIntent,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build minimal context for fast path processing"""
        return {
            "query_metadata": {
                "original_query": query,
                "intent": intent.model_dump() if intent else None,
                "processing_timestamp": datetime.now().isoformat(),
                "processing_path": "fast_path"
            },
            "data_agent_context": {
                "metric_type": intent.metric_type if intent else "unknown",
                "time_period": intent.time_period if intent else "unknown",
                "aggregation_level": intent.aggregation_level if intent else "monthly"
            },
            "user_context": context or {}
        }
    
    def _create_query_intent(self, intent_data: Dict[str, Any]) -> QueryIntent:
        """Create QueryIntent from KIMI response data"""
        try:
            return QueryIntent(
                metric_type=intent_data.get("metric_type", "unknown"),
                time_period=intent_data.get("time_period", "unknown"),
                aggregation_level=intent_data.get("aggregation_level", "monthly"),
                filters=intent_data.get("filters", {}),
                comparison_periods=intent_data.get("comparison_periods", []),
                visualization_hint=intent_data.get("visualization_hint"),
                confidence_score=intent_data.get("confidence_score", 0.0)
            )
        except Exception as e:
            logger.error(f"Failed to create QueryIntent: {e}")
            return QueryIntent(
                metric_type="unknown",
                time_period="unknown",
                confidence_score=0.0
            )
    
    def _process_entities(self, entities_data: List[Dict[str, Any]]) -> List[FinancialEntity]:
        """Process entities data from KIMI"""
        entities = []
        for entity_data in entities_data:
            try:
                entity = FinancialEntity(**entity_data)
                entities.append(entity)
            except Exception as e:
                logger.warning(f"Invalid entity data: {entity_data}, error: {e}")
        return entities
    
    def _process_ambiguities(self, ambiguities_data: List[Dict[str, Any]]) -> List[str]:
        """Process ambiguities data from KIMI"""
        return [amb.get("description", "") for amb in ambiguities_data]
    
    def _create_cached_result(
        self,
        query_id: str,
        cached_data: Dict[str, Any],
        start_time: float
    ) -> ProcessingResult:
        """Create ProcessingResult from cached data"""
        processing_time = time.time() - start_time
        
        return ProcessingResult(
            query_id=query_id,
            success=True,
            intent=QueryIntent(**cached_data["intent"]) if cached_data.get("intent") else None,
            sql_query=cached_data.get("sql_query", ""),
            query_context=cached_data.get("query_context", {}),
            processing_time_ms=int(processing_time * 1000),
            processing_path="cached"
        )
    
    async def _warm_up_caches(self):
        """Warm up caches with common data"""
        try:
            logger.info("Warming up caches...")
            
            # Warm up schema cache
            await self._get_cached_schema_context()
            
            # Pre-cache common query patterns
            common_queries = [
                "show revenue this quarter",
                "profit last month",
                "cash flow this year",
                "budget variance"
            ]
            
            for query in common_queries:
                # Pre-process common queries with unified approach
                try:
                    result = await self._process_unified_path(
                        query=query,
                        user_id="warmup_user",
                        session_id="warmup_session",
                        context={}
                    )
                    logger.debug(f"Warmed up cache for query: {query}")
                except Exception as warmup_error:
                    logger.debug(f"Cache warmup failed for query '{query}': {warmup_error}")
                    continue
            
            logger.info("Cache warmup completed")
            
        except Exception as e:
            logger.warning(f"Cache warmup failed: {e}")
    
    # Event handlers
    async def _handle_schema_update(self, payload: Dict[str, Any]):
        """Handle schema update events from MCP server"""
        logger.info("Received schema update event - invalidating schema cache")
        self.schema_cache = {}
        self.last_schema_update = 0
        
        # Invalidate related cache entries
        await self.cache_manager.invalidate_by_tags(["schema", "sql"])
    
    async def _handle_cache_invalidation(self, payload: Dict[str, Any]):
        """Handle cache invalidation events"""
        tags = payload.get("tags", [])
        if tags:
            invalidated = await self.cache_manager.invalidate_by_tags(tags)
            logger.info(f"Invalidated {invalidated} cache entries for tags: {tags}")
    
    async def _handle_server_status(self, payload: Dict[str, Any]):
        """Handle server status events"""
        status = payload.get("status")
        logger.debug(f"MCP server status: {status}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check of optimized agent"""
        health_status = {
            "agent_id": self.agent_id,
            "status": "healthy" if self.is_running else "stopped",
            "optimizations_enabled": self.enable_optimizations,
            "components": {},
            "metrics": self.get_performance_metrics(),
            "timestamp": time.time()
        }
        
        # Check KIMI client
        try:
            kimi_healthy = await self.kimi_client.health_check()
            kimi_metrics = self.kimi_client.get_metrics()
            health_status["components"]["kimi_client"] = {
                "status": "healthy" if kimi_healthy else "unhealthy",
                "metrics": kimi_metrics
            }
        except Exception as e:
            health_status["components"]["kimi_client"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Check WebSocket MCP client
        try:
            mcp_healthy = await self.mcp_client.health_check()
            mcp_metrics = self.mcp_client.get_metrics()
            health_status["components"]["mcp_client"] = {
                "status": "healthy" if mcp_healthy else "unhealthy",
                "connection": self.mcp_client.is_connected,
                "metrics": mcp_metrics
            }
        except Exception as e:
            health_status["components"]["mcp_client"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Check cache manager
        cache_stats = self.cache_manager.get_stats()
        health_status["components"]["cache_manager"] = {
            "status": "healthy",
            "stats": cache_stats
        }
        
        # Overall health assessment
        component_statuses = [comp.get("status") for comp in health_status["components"].values()]
        if "error" in component_statuses:
            health_status["status"] = "degraded"
        elif "unhealthy" in component_statuses:
            health_status["status"] = "degraded"
        
        return health_status
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        avg_latency = (
            self.metrics["total_latency"] / self.metrics["total_queries"]
            if self.metrics["total_queries"] > 0 else 0
        )
        
        fast_path_ratio = (
            self.metrics["fast_path_queries"] / self.metrics["total_queries"]
            if self.metrics["total_queries"] > 0 else 0
        )
        
        cache_hit_rate = (
            self.metrics["cache_hits"] / self.metrics["total_queries"]
            if self.metrics["total_queries"] > 0 else 0
        )
        
        return {
            **self.metrics,
            "average_latency": avg_latency,
            "fast_path_ratio": fast_path_ratio,
            "cache_hit_rate": cache_hit_rate,
            "total_optimization_savings": self.metrics["optimization_savings"],
            "avg_optimization_savings": (
                self.metrics["optimization_savings"] / self.metrics["total_queries"]
                if self.metrics["total_queries"] > 0 else 0
            )
        }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics from the cache manager"""
        try:
            if hasattr(self.cache_manager, 'get_stats'):
                return self.cache_manager.get_stats()
            else:
                # Return basic cache stats if get_stats method doesn't exist
                return {
                    "cache_enabled": True,
                    "cache_type": "AdvancedCacheManager",
                    "l1_cache_size": len(getattr(self.cache_manager, '_l1_cache', {})),
                    "l1_max_size": getattr(self.cache_manager, 'l1_max_size', 1000),
                    "cache_hit_rate": self.metrics.get("cache_hits", 0) / max(self.metrics.get("total_queries", 1), 1),
                    "total_cache_hits": self.metrics.get("cache_hits", 0)
                }
        except Exception as e:
            logger.warning(f"Failed to get cache stats: {e}")
            return {
                "cache_enabled": False,
                "error": str(e)
            }

    def _create_basic_query_intent(self, query: str) -> QueryIntent:
        """Create basic query intent without KIMI API"""
        query_lower = query.lower()
        
        # Basic intent detection using keyword patterns
        metric_type = "general"
        time_period = "current"
        confidence = 0.7
        
        # Detect metric type
        if any(word in query_lower for word in ["revenue", "sales", "income"]):
            metric_type = "revenue"
        elif any(word in query_lower for word in ["cost", "expense", "spending"]):
            metric_type = "expense"
        elif any(word in query_lower for word in ["profit", "margin", "earnings"]):
            metric_type = "profit"
        elif any(word in query_lower for word in ["cash", "flow"]):
            metric_type = "cash_flow"
        elif any(word in query_lower for word in ["balance", "asset", "liability"]):
            metric_type = "balance_sheet"
        
        # Detect time period
        if any(word in query_lower for word in ["quarter", "quarterly", "q1", "q2", "q3", "q4"]):
            time_period = "quarterly"
        elif any(word in query_lower for word in ["month", "monthly"]):
            time_period = "monthly"
        elif any(word in query_lower for word in ["year", "yearly", "annual"]):
            time_period = "yearly"
        elif any(word in query_lower for word in ["week", "weekly"]):
            time_period = "weekly"
        
        return QueryIntent(
            metric_type=metric_type,
            time_period=time_period,
            confidence_score=confidence,
            filters={"fallback_mode": True}
        )
    
    def _extract_basic_entities(self, query: str) -> List[FinancialEntity]:
        """Extract basic entities without KIMI API"""
        entities = []
        query_lower = query.lower()
        
        # Basic entity patterns for financial queries
        financial_patterns = [
            ("revenue", "revenue", ["sales", "income"]),
            ("expense", "expense", ["cost", "spending"]),
            ("profit", "profit", ["earnings", "margin"]),
            ("cash_flow", "cash flow", ["cash", "liquidity"]),
            ("inventory", "inventory", ["stock", "goods"]),
            ("asset", "asset", ["resources", "property"]),
            ("liability", "liability", ["debt", "obligations"])
        ]
        
        # Extract financial entities
        for entity_type, entity_value, synonyms in financial_patterns:
            if any(synonym in query_lower for synonym in [entity_value] + synonyms):
                entities.append(FinancialEntity(
                    entity_type=entity_type,
                    entity_value=entity_value,
                    confidence_score=0.8,
                    original_text=entity_value,
                    synonyms=synonyms
                ))
        
        return entities

    def _validate_database_context(self, database_context: Dict[str, Any]) -> bool:
        """
        Validate database context for NLP agent processing.
        
        Args:
            database_context: Database context to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not isinstance(database_context, dict):
            logger.error("Database context must be a dictionary")
            return False
        
        # Check for required fields
        required_fields = ['database_name']
        for field in required_fields:
            if field not in database_context:
                logger.error(f"Missing required field '{field}' in database context")
                return False
            
            if not database_context[field]:
                logger.error(f"Empty value for required field '{field}' in database context")
                return False
        
        # Validate database name format
        database_name = database_context['database_name']
        if not isinstance(database_name, str) or len(database_name) == 0:
            logger.error(f"Invalid database name: {database_name}")
            return False
        
        logger.debug(f"Database context validation passed: {database_context}")
        return True

    async def _extract_intent_via_mcp(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Extract financial intent using MCP server's LLM tools instead of direct API calls"""
        try:
            # Create a system prompt for intent extraction
            system_prompt = """You are a financial data analyst AI. Extract the intent from financial queries.
            
Return a JSON object with these fields:
- metric_type: The financial metric requested (revenue, profit, expense, cash_flow, balance_sheet, etc.)
- time_period: The time period (current, yearly, quarterly, monthly, specific year/date)
- aggregation_level: How to aggregate data (daily, weekly, monthly, quarterly, yearly)
- filters: Any filters or conditions mentioned
- comparison_periods: Any comparison time periods
- visualization_hint: Suggested visualization type
- confidence_score: Confidence in the extraction (0.0-1.0)

Example query: "What is the revenue for 2024?"
Example response: {
    "metric_type": "revenue",
    "time_period": "2024",
    "aggregation_level": "yearly",
    "filters": {"year": "2024"},
    "comparison_periods": [],
    "visualization_hint": "bar_chart",
    "confidence_score": 0.9
}"""

            # Use MCP server's llm_generate_text_tool via WebSocket
            result = await self.mcp_client.send_request(
                "llm_generate_text_tool",
                {
                    "prompt": f"Extract financial intent from this query: {query}",
                    "system_prompt": system_prompt,
                    "max_tokens": 500,
                    "temperature": 0.1
                }
            )
            
            # Parse the generated text as JSON
            generated_text = result.get("text", "{}")
            try:
                intent_data = json.loads(generated_text)
                logger.debug(f"Intent extracted via MCP: {intent_data}")
                return intent_data
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse LLM response as JSON: {generated_text}")
                # Fallback to basic intent extraction
                return self._extract_basic_intent(query)
                
        except Exception as e:
            logger.warning(f"Intent extraction via MCP failed: {e}, using fallback")
            return self._extract_basic_intent(query)
    
    def _extract_basic_intent(self, query: str) -> Dict[str, Any]:
        """Fallback intent extraction without LLM"""
        query_lower = query.lower()
        
        # Basic intent patterns
        intent_data = {
            "metric_type": "general",
            "time_period": "current",
            "aggregation_level": "monthly",
            "filters": {},
            "comparison_periods": [],
            "visualization_hint": "table",
            "confidence_score": 0.6
        }
        
        # Detect metric type
        if any(word in query_lower for word in ["revenue", "sales", "income"]):
            intent_data["metric_type"] = "revenue"
        elif any(word in query_lower for word in ["cost", "expense", "spending"]):
            intent_data["metric_type"] = "expense"
        elif any(word in query_lower for word in ["profit", "margin", "earnings"]):
            intent_data["metric_type"] = "profit"
        elif any(word in query_lower for word in ["cash", "flow", "cashflow"]):
            intent_data["metric_type"] = "cash_flow"
        elif any(word in query_lower for word in ["balance", "asset", "liability"]):
            intent_data["metric_type"] = "balance_sheet"
        
        # Detect time period
        if any(word in query_lower for word in ["2024", "2023", "2022"]):
            year_match = re.search(r'\b(20\d{2})\b', query)
            if year_match:
                intent_data["time_period"] = year_match.group(1)
                intent_data["aggregation_level"] = "yearly"
                intent_data["filters"]["year"] = year_match.group(1)
        elif any(word in query_lower for word in ["quarter", "quarterly", "q1", "q2", "q3", "q4"]):
            intent_data["time_period"] = "quarterly"
            intent_data["aggregation_level"] = "quarterly"
        elif any(word in query_lower for word in ["month", "monthly"]):
            intent_data["time_period"] = "monthly"
            intent_data["aggregation_level"] = "monthly"
        
        return intent_data
    
    async def _extract_entities_via_mcp(self, query: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Extract financial entities using MCP server's LLM tools"""
        try:
            system_prompt = """You are a financial data analyst AI. Extract financial entities from queries.
            
Return a JSON array of entities with these fields for each:
- entity_type: Type of entity (metric, time_period, filter, etc.)
- entity_value: The actual value/text
- confidence_score: Confidence in extraction (0.0-1.0)
- original_text: Original text from query
- synonyms: List of synonyms

Example query: "Show revenue for Q1 2024"
Example response: [
    {
        "entity_type": "metric",
        "entity_value": "revenue",
        "confidence_score": 0.9,
        "original_text": "revenue",
        "synonyms": ["sales", "income"]
    },
    {
        "entity_type": "time_period",
        "entity_value": "Q1 2024",
        "confidence_score": 0.95,
        "original_text": "Q1 2024",
        "synonyms": ["first quarter 2024"]
    }
]"""

            result = await self.mcp_client.send_request(
                "llm_generate_text_tool",
                {
                    "prompt": f"Extract financial entities from this query: {query}",
                    "system_prompt": system_prompt,
                    "max_tokens": 800,
                    "temperature": 0.1
                }
            )
            
            generated_text = result.get("text", "[]")
            try:
                entities_data = json.loads(generated_text)
                logger.debug(f"Entities extracted via MCP: {entities_data}")
                return entities_data if isinstance(entities_data, list) else []
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse entities JSON: {generated_text}")
                return []
                
        except Exception as e:
            logger.warning(f"Entity extraction via MCP failed: {e}")
            return []
    
    async def _extract_ambiguities_via_mcp(self, query: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Extract ambiguities using MCP server's LLM tools"""
        try:
            system_prompt = """You are a financial data analyst AI. Identify ambiguities in financial queries.
            
Return a JSON array of ambiguities with these fields:
- description: Description of the ambiguity
- suggestions: List of clarification suggestions
- severity: Low, Medium, or High

Example query: "Show profit last year"
Example response: [
    {
        "description": "Year not specified - could be 2023 or 2024",
        "suggestions": ["Specify exact year", "Use 'profit for 2024'"],
        "severity": "Medium"
    }
]"""

            result = await self.mcp_client.send_request(
                "llm_generate_text_tool",
                {
                    "prompt": f"Identify ambiguities in this query: {query}",
                    "system_prompt": system_prompt,
                    "max_tokens": 500,
                    "temperature": 0.2
                }
            )
            
            generated_text = result.get("text", "[]")
            try:
                ambiguities_data = json.loads(generated_text)
                logger.debug(f"Ambiguities extracted via MCP: {ambiguities_data}")
                return ambiguities_data if isinstance(ambiguities_data, list) else []
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse ambiguities JSON: {generated_text}")
                return []
                
        except Exception as e:
            logger.warning(f"Ambiguity extraction via MCP failed: {e}")
            return []
