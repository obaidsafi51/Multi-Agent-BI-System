"""
Simplified NLP Agent - Single Path Processing
This removes the complex multi-path routing and uses one optimized processing flow.
"""

async def process_query_unified(
    self,
    query: str,
    user_id: str,
    session_id: str,
    context: Optional[Dict[str, Any]] = None
) -> ProcessingResult:
    """
    Unified query processing - single path for all queries.
    Optimized but simple approach without complex routing.
    """
    start_time = time.time()
    query_id = f"q_{uuid.uuid4().hex[:8]}"
    
    try:
        logger.info(f"Processing query {query_id}: {query}")
        
        # Step 1: Check semantic cache first (simple caching strategy)
        cached_result = await self._check_cache(query)
        if cached_result:
            logger.info(f"Query {query_id} served from cache")
            return self._create_cached_result(query_id, cached_result, start_time)
        
        # Step 2: Get schema context (cached for performance)
        schema_context = await self._get_cached_schema_context()
        
        # Step 3: Extract intent via MCP (with fallback)
        intent_data = await self._extract_intent_via_mcp(query, context)
        intent = self._create_query_intent(intent_data)
        
        # Step 4: Generate SQL via MCP WebSocket
        sql_result = await self.mcp_ops.generate_sql(
            natural_language_query=query,
            schema_info=self._format_schema_for_llm(schema_context)
        )
        
        # Step 5: Build context (standard approach for all queries)
        query_context = self.context_builder.build_query_context(
            query=query,
            intent=intent,
            user_context=context,
            schema_context=schema_context
        )
        
        # Step 6: Create result
        result = ProcessingResult(
            query_id=query_id,
            success=True,
            intent=intent,
            sql_query=sql_result.get("sql", ""),
            query_context=query_context,
            processing_path="unified"
        )
        
        # Step 7: Cache result
        await self._cache_result(query, result)
        
        processing_time = time.time() - start_time
        result.processing_time_ms = int(processing_time * 1000)
        
        logger.info(f"Query {query_id} processed in {processing_time:.2f}s via unified path")
        
        return result
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Query processing failed for {query_id}: {e}")
        
        return ProcessingResult(
            query_id=query_id,
            success=False,
            error=str(e),
            processing_time_ms=int(processing_time * 1000),
            processing_path="unified_error"
        )
