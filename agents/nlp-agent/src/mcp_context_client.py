"""
MCP Context Client for NLP Agent.
Handles context sharing through the MCP protocol via Redis.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional
import redis.asyncio as redis
from datetime import datetime

logger = logging.getLogger(__name__)


class MCPContextClient:
    """
    MCP Context Client for sharing query context across agents.
    Uses Redis as the MCP context store.
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client: Optional[redis.Redis] = None
        self.is_connected = False
        
    async def connect(self) -> bool:
        """Connect to Redis MCP context store."""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis_client.ping()
            self.is_connected = True
            logger.info("Connected to MCP context store (Redis)")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MCP context store: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from Redis MCP context store."""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
        self.is_connected = False
        logger.info("Disconnected from MCP context store")
    
    async def store_context(
        self,
        context_id: str,
        session_id: str,
        user_id: str,
        context_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        ttl: int = 3600
    ) -> bool:
        """
        Store query context in MCP context store.
        
        Args:
            context_id: Unique context identifier (usually query_id)
            session_id: User session identifier
            user_id: User identifier
            context_data: The context data to store
            metadata: Optional metadata
            ttl: Time to live in seconds (default 1 hour)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.is_connected:
                await self.connect()
            
            mcp_context = {
                "context_id": context_id,
                "session_id": session_id,
                "user_id": user_id,
                "data": context_data,
                "metadata": metadata or {},
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0",
                "agent_source": "nlp-agent"
            }
            
            # Store in Redis with TTL
            context_key = f"mcp_context:{context_id}"
            context_json = json.dumps(mcp_context, default=str)
            
            success = await self.redis_client.setex(
                context_key,
                ttl,
                context_json
            )
            
            # Also store in session context for session continuity
            session_key = f"session_context:{session_id}"
            session_data = {
                "last_context_id": context_id,
                "last_query_timestamp": datetime.utcnow().isoformat(),
                "user_id": user_id
            }
            
            await self.redis_client.setex(
                session_key,
                1800,  # 30 minutes TTL for session
                json.dumps(session_data, default=str)
            )
            
            if success:
                logger.debug(f"Stored MCP context for {context_id}")
                return True
            else:
                logger.warning(f"Failed to store MCP context for {context_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error storing MCP context: {e}")
            return False
    
    async def retrieve_context(self, context_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve context from MCP context store.
        
        Args:
            context_id: Context identifier to retrieve
            
        Returns:
            Context data if found, None otherwise
        """
        try:
            if not self.is_connected:
                await self.connect()
            
            context_key = f"mcp_context:{context_id}"
            context_json = await self.redis_client.get(context_key)
            
            if context_json:
                context = json.loads(context_json)
                logger.debug(f"Retrieved MCP context for {context_id}")
                return context
            else:
                logger.debug(f"No MCP context found for {context_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving MCP context: {e}")
            return None
    
    async def update_context(
        self,
        context_id: str,
        updates: Dict[str, Any],
        metadata_updates: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update existing context in MCP context store.
        
        Args:
            context_id: Context identifier to update
            updates: Data updates to apply
            metadata_updates: Optional metadata updates
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Retrieve existing context
            existing_context = await self.retrieve_context(context_id)
            if not existing_context:
                logger.warning(f"Cannot update non-existent context {context_id}")
                return False
            
            # Apply updates
            existing_context["data"].update(updates)
            if metadata_updates:
                existing_context["metadata"].update(metadata_updates)
            
            existing_context["timestamp"] = datetime.utcnow().isoformat()
            existing_context["version"] = "1.1"  # Version bump for updates
            
            # Store updated context
            context_key = f"mcp_context:{context_id}"
            context_json = json.dumps(existing_context, default=str)
            
            # Keep original TTL
            ttl = await self.redis_client.ttl(context_key)
            if ttl > 0:
                success = await self.redis_client.setex(context_key, ttl, context_json)
            else:
                success = await self.redis_client.set(context_key, context_json)
            
            if success:
                logger.debug(f"Updated MCP context for {context_id}")
                return True
            else:
                logger.warning(f"Failed to update MCP context for {context_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating MCP context: {e}")
            return False
    
    async def get_session_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session context for continuity.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session context if found, None otherwise
        """
        try:
            if not self.is_connected:
                await self.connect()
            
            session_key = f"session_context:{session_id}"
            session_json = await self.redis_client.get(session_key)
            
            if session_json:
                session_data = json.loads(session_json)
                logger.debug(f"Retrieved session context for {session_id}")
                return session_data
            else:
                logger.debug(f"No session context found for {session_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving session context: {e}")
            return None
    
    async def list_user_contexts(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        List recent contexts for a user.
        
        Args:
            user_id: User identifier
            limit: Maximum number of contexts to return
            
        Returns:
            List of context summaries
        """
        try:
            if not self.is_connected:
                await self.connect()
            
            # Search for user contexts (this is a simplified implementation)
            pattern = "mcp_context:*"
            keys = []
            async for key in self.redis_client.scan_iter(match=pattern):
                keys.append(key)
                if len(keys) >= limit * 2:  # Get more to filter
                    break
            
            user_contexts = []
            for key in keys[:limit * 2]:
                try:
                    context_json = await self.redis_client.get(key)
                    if context_json:
                        context = json.loads(context_json)
                        if context.get("user_id") == user_id:
                            # Return summary only
                            summary = {
                                "context_id": context.get("context_id"),
                                "timestamp": context.get("timestamp"),
                                "query_type": context.get("data", {}).get("intent", {}).get("metric_type"),
                                "session_id": context.get("session_id")
                            }
                            user_contexts.append(summary)
                            
                            if len(user_contexts) >= limit:
                                break
                except Exception:
                    continue  # Skip invalid contexts
            
            # Sort by timestamp (most recent first)
            user_contexts.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            return user_contexts[:limit]
            
        except Exception as e:
            logger.error(f"Error listing user contexts: {e}")
            return []
    
    async def health_check(self) -> bool:
        """Check MCP context store health."""
        try:
            if not self.redis_client:
                return False
            
            await self.redis_client.ping()
            return True
        except Exception:
            return False


# Global MCP context client instance
_mcp_context_client: Optional[MCPContextClient] = None


def get_mcp_context_client() -> MCPContextClient:
    """Get the global MCP context client instance."""
    global _mcp_context_client
    if _mcp_context_client is None:
        _mcp_context_client = MCPContextClient()
    return _mcp_context_client


async def close_mcp_context_client():
    """Close the global MCP context client instance."""
    global _mcp_context_client
    if _mcp_context_client:
        await _mcp_context_client.disconnect()
        _mcp_context_client = None
