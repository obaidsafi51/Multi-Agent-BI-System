"""Main NLP Agent service with KIMI integration and MCP context sharing"""

import asyncio
import json
import logging
import os
import uuid
from typing import Any, Dict, List, Optional

from .context_builder import ContextBuilder
from .kimi_client import KimiClient, KimiAPIError
from .models import ProcessingResult, QueryContext
from .query_parser import QueryParser
from .mcp_context_client import get_mcp_context_client

logger = logging.getLogger(__name__)


class NLPAgent:
    """NLP Agent with KIMI integration and MCP context sharing for financial query processing"""
    
    def __init__(
        self,
        kimi_api_key: Optional[str] = None,
        redis_url: Optional[str] = None
    ):
        # Initialize KIMI client
        self.kimi_client = KimiClient(api_key=kimi_api_key)
        
        # Initialize query parser and context builder
        self.query_parser = QueryParser(self.kimi_client)
        self.context_builder = ContextBuilder()
        
        # MCP Context Client for context sharing
        self.mcp_context_client = get_mcp_context_client()
        
        # Backend URL for cached schema access
        self.backend_url = os.getenv("BACKEND_URL", "http://backend:8001")
        
        # Agent configuration
        self.agent_id = f"nlp-agent-{uuid.uuid4().hex[:8]}"
        self.is_running = False
        
        logger.info(f"NLP Agent initialized with ID: {self.agent_id}")

    async def get_cached_schema(self) -> Dict[str, Any]:
        """Get schema from backend cache for fast access"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.backend_url}/api/schema/cached",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        schema_data = await response.json()
                        if schema_data.get("success"):
                            logger.info(f"Schema loaded from {schema_data.get('source', 'unknown')}")
                            return schema_data.get("schema", {})
                        else:
                            logger.warning(f"Schema fetch failed: {schema_data.get('error', 'Unknown error')}")
                            return {}
                    else:
                        logger.error(f"Schema endpoint returned {response.status}")
                        return {}
        except Exception as e:
            logger.error(f"Failed to fetch cached schema: {e}")
            return {}
    
    async def start(self):
        """Start the NLP Agent"""
        try:
            logger.info("Starting NLP Agent...")
            
            # Initialize MCP context connection
            await self._init_mcp_context()
            
            # Verify KIMI API connectivity
            if not await self.kimi_client.health_check():
                raise Exception("KIMI API health check failed")
            logger.info("KIMI API health check passed")
            
            self.is_running = True
            logger.info("NLP Agent started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start NLP Agent: {e}")
            raise
    
    async def stop(self):
        """Stop the NLP Agent"""
        logger.info("Stopping NLP Agent...")
        
        self.is_running = False
        
        # Close connections
        if self.mcp_context_client:
            await self.mcp_context_client.disconnect()
        
        if self.kimi_client:
            await self.kimi_client.close()
        
        logger.info("NLP Agent stopped")
    
    async def _init_mcp_context(self):
        """Initialize MCP context connection"""
        try:
            connected = await self.mcp_context_client.connect()
            if connected:
                logger.info("MCP context store connection established")
            else:
                logger.warning("Failed to connect to MCP context store")
        except Exception as e:
            logger.error(f"MCP context initialization failed: {e}")
            raise
    
    async def process_query(
        self,
        query: str,
        user_id: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ProcessingResult:
        """Process a natural language query and store context via MCP"""
        query_id = f"q_{uuid.uuid4().hex[:8]}"
        
        try:
            logger.info(f"Processing query {query_id}: {query}")
            
            # Get cached schema context first
            schema_context = await self.get_cached_schema()
            
            # Retrieve session context for continuity
            session_context = await self.mcp_context_client.get_session_context(session_id)
            
            # Create initial query context
            query_context = QueryContext(
                query_id=query_id,
                user_id=user_id,
                session_id=session_id,
                original_query=query,
                context=context or {},
                session_context=session_context
            )
            
            # Parse query using KIMI with schema context
            try:
                intent = await self.query_parser.parse_intent(query, query_context, schema_context)
                logger.info(f"Query intent parsed for {query_id}: {intent.metric_type} (with schema context)")
            except KimiAPIError as e:
                logger.error(f"KIMI API error for query {query_id}: {e}")
                # Fallback to basic parsing
                intent = self._fallback_intent_parsing(query)
            
            # Build comprehensive context including schema
            comprehensive_context = self.context_builder.build_query_context(
                query=query,
                intent=intent,
                user_context=context,
                session_context=session_context,
                schema_context=schema_context
            )
            
            # Generate SQL query
            sql_query = self.context_builder.generate_sql_query(intent, comprehensive_context)
            
            # Store context via MCP for other agents
            await self._store_mcp_context(query_context, intent, comprehensive_context, sql_query)
            
            # Create processing result
            result = ProcessingResult(
                query_id=query_id,
                success=True,
                intent=intent,
                sql_query=sql_query,
                query_context=comprehensive_context,
                mcp_context_stored=True,
                processing_time_ms=0  # Will be calculated by caller
            )
            
            logger.info(f"Query {query_id} processed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Query processing failed for {query_id}: {e}")
            
            # Return error result
            return ProcessingResult(
                query_id=query_id,
                success=False,
                error=str(e),
                intent=None,
                sql_query="",
                query_context={},
                mcp_context_stored=False,
                processing_time_ms=0
            )
    
    async def _store_mcp_context(
        self,
        query_context: QueryContext,
        intent,
        comprehensive_context: Dict[str, Any],
        sql_query: str
    ):
        """Store query context in MCP context store for other agents"""
        try:
            mcp_context_data = {
                "query_id": query_context.query_id,
                "original_query": query_context.original_query,
                "intent": intent.model_dump() if intent else None,
                "sql_query": sql_query,
                "comprehensive_context": comprehensive_context,
                "agent_source": "nlp-agent",
                "processing_status": "completed"
            }
            
            metadata = {
                "agent_id": self.agent_id,
                "processing_timestamp": query_context.created_at.isoformat(),
                "intent_confidence": getattr(intent, 'confidence_score', 0.8) if intent else 0.5,
                "session_context_used": query_context.session_context is not None
            }
            
            success = await self.mcp_context_client.store_context(
                context_id=query_context.query_id,
                session_id=query_context.session_id,
                user_id=query_context.user_id,
                context_data=mcp_context_data,
                metadata=metadata,
                ttl=3600  # 1 hour TTL
            )
            
            if success:
                logger.debug(f"MCP context stored for query {query_context.query_id}")
            else:
                logger.warning(f"Failed to store MCP context for query {query_context.query_id}")
            
        except Exception as e:
            logger.error(f"Failed to store MCP context: {e}")
    
    def _fallback_intent_parsing(self, query: str):
        """Fallback intent parsing when KIMI API is unavailable"""
        from .models import QueryIntent
        
        query_lower = query.lower()
        
        # Simple keyword-based intent detection
        if any(word in query_lower for word in ["revenue", "sales", "income"]):
            metric_type = "revenue"
        elif any(word in query_lower for word in ["profit", "earnings", "net"]):
            metric_type = "profit"
        elif any(word in query_lower for word in ["expense", "cost", "spending"]):
            metric_type = "expenses"
        elif any(word in query_lower for word in ["cash", "flow"]):
            metric_type = "cash_flow"
        else:
            metric_type = "revenue"
        
        # Determine time period
        if any(word in query_lower for word in ["month", "monthly"]):
            time_period = "monthly"
        elif any(word in query_lower for word in ["quarter", "quarterly"]):
            time_period = "quarterly"
        elif any(word in query_lower for word in ["year", "yearly", "annual"]):
            time_period = "yearly"
        else:
            time_period = "monthly"
        
        return QueryIntent(
            metric_type=metric_type,
            time_period=time_period,
            aggregation_level=time_period,
            visualization_hint="line_chart",
            confidence_score=0.6  # Lower confidence for fallback
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check of all NLP Agent components"""
        health_status = {
            "agent_id": self.agent_id,
            "status": "healthy" if self.is_running else "stopped",
            "components": {},
            "timestamp": asyncio.get_event_loop().time()
        }
        
        # Check KIMI API
        try:
            kimi_healthy = await self.kimi_client.health_check()
            health_status["components"]["kimi_api"] = {
                "status": "healthy" if kimi_healthy else "unhealthy",
                "api_key_configured": bool(self.kimi_client.api_key)
            }
        except Exception as e:
            health_status["components"]["kimi_api"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Check MCP context store
        try:
            mcp_healthy = await self.mcp_context_client.health_check()
            health_status["components"]["mcp_context_store"] = {
                "status": "healthy" if mcp_healthy else "unhealthy",
                "connected": self.mcp_context_client.is_connected
            }
        except Exception as e:
            health_status["components"]["mcp_context_store"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Overall status
        component_statuses = [comp.get("status") for comp in health_status["components"].values()]
        if "error" in component_statuses or "unhealthy" in component_statuses:
            health_status["status"] = "degraded"
        
        return health_status
    
    async def get_user_context_history(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent context history for a user via MCP"""
        try:
            return await self.mcp_context_client.list_user_contexts(user_id, limit)
        except Exception as e:
            logger.error(f"Failed to get user context history: {e}")
            return []


# Global NLP agent instance
_nlp_agent: Optional[NLPAgent] = None


async def get_nlp_agent() -> NLPAgent:
    """Get or create global NLP agent instance"""
    global _nlp_agent
    if _nlp_agent is None:
        _nlp_agent = NLPAgent()
        await _nlp_agent.start()
    return _nlp_agent


async def close_nlp_agent():
    """Close global NLP agent"""
    global _nlp_agent
    if _nlp_agent:
        await _nlp_agent.stop()
        _nlp_agent = None
