"""Main NLP Agent service with KIMI integration"""

import asyncio
import json
import logging
import os
import uuid
from typing import Any, Dict, List, Optional

import redis.asyncio as redis
import pika
from pika.adapters.asyncio_connection import AsyncioConnection

from .context_builder import ContextBuilder
from .kimi_client import KimiClient, KimiAPIError
from .models import ProcessingResult, QueryContext
from .query_parser import QueryParser

logger = logging.getLogger(__name__)


class NLPAgent:
    """NLP Agent with KIMI integration for financial query processing"""
    
    def __init__(
        self,
        kimi_api_key: Optional[str] = None,
        redis_url: Optional[str] = None,
        rabbitmq_url: Optional[str] = None
    ):
        # Initialize KIMI client
        self.kimi_client = KimiClient(api_key=kimi_api_key)
        
        # Initialize query parser and context builder
        self.query_parser = QueryParser(self.kimi_client)
        self.context_builder = ContextBuilder()
        
        # Redis connection for MCP context storage
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client: Optional[redis.Redis] = None
        
        # RabbitMQ connection for A2A communication
        self.rabbitmq_url = rabbitmq_url or os.getenv("RABBITMQ_URL", "amqp://localhost:5672")
        self.rabbitmq_connection: Optional[AsyncioConnection] = None
        self.rabbitmq_channel = None
        
        # Agent configuration
        self.agent_id = f"nlp-agent-{uuid.uuid4().hex[:8]}"
        self.is_running = False
        
        logger.info(f"NLP Agent initialized with ID: {self.agent_id}")
    
    async def start(self):
        """Start the NLP Agent"""
        try:
            logger.info("Starting NLP Agent...")
            
            # Initialize Redis connection
            await self._init_redis()
            
            # Initialize RabbitMQ connection
            await self._init_rabbitmq()
            
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
        if self.redis_client:
            await self.redis_client.close()
        
        if self.kimi_client:
            await self.kimi_client.close()
        
        if self.rabbitmq_connection and not self.rabbitmq_connection.is_closed:
            self.rabbitmq_connection.close()
        
        logger.info("NLP Agent stopped")
    
    async def process_query(
        self,
        query: str,
        user_id: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ProcessingResult:
        """Process a natural language query"""
        if not self.is_running:
            return ProcessingResult(
                success=False,
                error_message="NLP Agent is not running",
                processing_time_ms=0
            )
        
        try:
            logger.info(f"Processing query for user {user_id}: {query}")
            
            # Parse the query using KIMI
            result = await self.query_parser.parse_query(
                query=query,
                user_id=user_id,
                session_id=session_id,
                context=context
            )
            
            if not result.success or not result.query_context:
                return result
            
            # Build contexts for other agents
            query_context = result.query_context
            
            # Store context in MCP (Redis)
            await self._store_mcp_context(query_context)
            
            # Send contexts to other agents via A2A
            await self._send_agent_contexts(query_context)
            
            logger.info(f"Query processing completed for {query_context.query_id}")
            return result
            
        except Exception as e:
            logger.error(f"Query processing failed: {e}")
            return ProcessingResult(
                success=False,
                error_message=f"Query processing failed: {str(e)}",
                processing_time_ms=0
            )
    
    async def get_query_suggestions(
        self,
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Get personalized query suggestions for a user"""
        try:
            # Get user's query history from Redis
            history_key = f"user_history:{user_id}"
            history_data = await self.redis_client.get(history_key)
            
            if not history_data:
                # Return default suggestions for new users
                return [
                    "Show me quarterly revenue for this year",
                    "Compare cash flow this quarter vs last quarter", 
                    "What's our profit margin trend over the last 6 months?",
                    "Show me budget variance by department",
                    "How are our investments performing?"
                ]
            
            # Use KIMI to generate personalized suggestions based on history
            history = json.loads(history_data)
            
            system_prompt = """Based on the user's query history, suggest 5 relevant financial queries they might want to ask next. 
            Focus on natural variations, deeper analysis, or related metrics. Return as a JSON array of strings."""
            
            user_message = f"User's recent queries: {json.dumps(history[-10:])}"  # Last 10 queries
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            response = await self.kimi_client.chat_completion(
                messages=messages,
                temperature=0.3,
                max_tokens=500
            )
            
            assistant_message = response.choices[0]["message"]["content"]
            
            try:
                suggestions = json.loads(assistant_message)
                return suggestions if isinstance(suggestions, list) else []
            except json.JSONDecodeError:
                logger.warning("Could not parse suggestions from KIMI response")
                return []
                
        except Exception as e:
            logger.error(f"Failed to get query suggestions: {e}")
            return []
    
    async def _init_redis(self):
        """Initialize Redis connection for MCP context storage"""
        try:
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def _init_rabbitmq(self):
        """Initialize RabbitMQ connection for A2A communication"""
        try:
            # For now, we'll use a simple connection setup
            # In production, you'd want more robust connection handling
            logger.info("RabbitMQ connection setup (placeholder)")
            # TODO: Implement full RabbitMQ async connection
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise
    
    async def _store_mcp_context(self, query_context: QueryContext):
        """Store query context in MCP (Redis) for other agents"""
        try:
            mcp_context = self.context_builder.build_mcp_context(query_context)
            
            # Store in Redis with TTL
            context_key = f"mcp_context:{query_context.query_id}"
            context_json = json.dumps(mcp_context, default=str)
            
            await self.redis_client.setex(
                context_key,
                3600,  # 1 hour TTL
                context_json
            )
            
            # Also store in user session context
            session_key = f"session_context:{query_context.session_id}"
            session_data = {
                "last_query_id": query_context.query_id,
                "last_intent": query_context.intent.model_dump() if query_context.intent else None,
                "timestamp": query_context.created_at.isoformat()
            }
            
            await self.redis_client.setex(
                session_key,
                1800,  # 30 minutes TTL
                json.dumps(session_data, default=str)
            )
            
            logger.debug(f"Stored MCP context for query {query_context.query_id}")
            
        except Exception as e:
            logger.error(f"Failed to store MCP context: {e}")
    
    async def _send_agent_contexts(self, query_context: QueryContext):
        """Send contexts to other agents via A2A protocol"""
        try:
            # Build contexts for each agent
            data_context = self.context_builder.build_data_agent_context(query_context)
            viz_context = self.context_builder.build_visualization_agent_context(query_context)
            personal_context = self.context_builder.build_personalization_agent_context(query_context)
            
            # For now, store these in Redis for other agents to pick up
            # In production, you'd send via RabbitMQ
            
            contexts = {
                "data_agent": data_context,
                "visualization_agent": viz_context,
                "personalization_agent": personal_context
            }
            
            for agent_name, context in contexts.items():
                context_key = f"agent_context:{agent_name}:{query_context.query_id}"
                await self.redis_client.setex(
                    context_key,
                    1800,  # 30 minutes TTL
                    json.dumps(context, default=str)
                )
            
            logger.debug(f"Sent contexts to agents for query {query_context.query_id}")
            
        except Exception as e:
            logger.error(f"Failed to send agent contexts: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check of all components"""
        health_status = {
            "agent_id": self.agent_id,
            "is_running": self.is_running,
            "timestamp": str(asyncio.get_event_loop().time()),
            "components": {}
        }
        
        # Check KIMI API
        try:
            kimi_healthy = await self.kimi_client.health_check()
            health_status["components"]["kimi_api"] = {
                "status": "healthy" if kimi_healthy else "unhealthy",
                "details": "KIMI API connectivity check"
            }
        except Exception as e:
            health_status["components"]["kimi_api"] = {
                "status": "error",
                "details": str(e)
            }
        
        # Check Redis
        try:
            if self.redis_client:
                await self.redis_client.ping()
                health_status["components"]["redis"] = {
                    "status": "healthy",
                    "details": "Redis connectivity check"
                }
            else:
                health_status["components"]["redis"] = {
                    "status": "not_initialized",
                    "details": "Redis client not initialized"
                }
        except Exception as e:
            health_status["components"]["redis"] = {
                "status": "error",
                "details": str(e)
            }
        
        # Overall health
        component_statuses = [comp["status"] for comp in health_status["components"].values()]
        if all(status == "healthy" for status in component_statuses):
            health_status["overall_status"] = "healthy"
        elif any(status == "error" for status in component_statuses):
            health_status["overall_status"] = "error"
        else:
            health_status["overall_status"] = "degraded"
        
        return health_status