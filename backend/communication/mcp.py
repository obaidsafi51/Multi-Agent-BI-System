"""
MCP (Model Context Protocol) implementation using Redis.

Provides context store functionality with JSON serialization and session management.
"""

import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import redis.asyncio as redis
from redis.exceptions import RedisError

from .models import ContextData


logger = logging.getLogger(__name__)


class MCPContextStore:
    """Redis-based context store for MCP protocol"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379", db: int = 0):
        """
        Initialize MCP context store.
        
        Args:
            redis_url: Redis connection URL
            db: Redis database number
        """
        self.redis_url = redis_url
        self.db = db
        self._redis: Optional[redis.Redis] = None
        self.default_ttl = 3600  # 1 hour default TTL
        
    async def connect(self) -> None:
        """Establish Redis connection"""
        try:
            self._redis = redis.from_url(self.redis_url, db=self.db, decode_responses=True)
            await self._redis.ping()
            logger.info("Connected to Redis for MCP context store")
        except RedisError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
            logger.info("Disconnected from Redis")
    
    def _get_context_key(self, context_id: str) -> str:
        """Generate Redis key for context"""
        return f"mcp:context:{context_id}"
    
    def _get_session_key(self, session_id: str) -> str:
        """Generate Redis key for session contexts"""
        return f"mcp:session:{session_id}"
    
    def _get_user_key(self, user_id: str) -> str:
        """Generate Redis key for user contexts"""
        return f"mcp:user:{user_id}"
    
    async def store_context(self, context: ContextData, ttl: Optional[int] = None) -> bool:
        """
        Store context data in Redis.
        
        Args:
            context: Context data to store
            ttl: Time to live in seconds (optional)
            
        Returns:
            True if stored successfully, False otherwise
        """
        if not self._redis:
            raise RuntimeError("Redis connection not established")
        
        try:
            context.updated_at = datetime.utcnow()
            
            # Calculate TTL
            if ttl is None:
                if context.expires_at:
                    ttl = int((context.expires_at - datetime.utcnow()).total_seconds())
                else:
                    ttl = self.default_ttl
            
            # Store context data
            context_key = self._get_context_key(context.context_id)
            context_json = context.json()
            
            await self._redis.setex(context_key, ttl, context_json)
            
            # Add to session index
            if context.session_id:
                session_key = self._get_session_key(context.session_id)
                await self._redis.sadd(session_key, context.context_id)
                await self._redis.expire(session_key, ttl)
            
            # Add to user index
            if context.user_id:
                user_key = self._get_user_key(context.user_id)
                await self._redis.sadd(user_key, context.context_id)
                await self._redis.expire(user_key, ttl)
            
            logger.debug(f"Stored context {context.context_id} with TTL {ttl}")
            return True
            
        except RedisError as e:
            logger.error(f"Failed to store context {context.context_id}: {e}")
            return False
    
    async def get_context(self, context_id: str) -> Optional[ContextData]:
        """
        Retrieve context data from Redis.
        
        Args:
            context_id: Context identifier
            
        Returns:
            Context data if found, None otherwise
        """
        if not self._redis:
            raise RuntimeError("Redis connection not established")
        
        try:
            context_key = self._get_context_key(context_id)
            context_json = await self._redis.get(context_key)
            
            if context_json:
                context_dict = json.loads(context_json)
                return ContextData(**context_dict)
            
            return None
            
        except (RedisError, json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to get context {context_id}: {e}")
            return None
    
    async def update_context(self, context_id: str, data: Dict[str, Any], 
                           metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update existing context data.
        
        Args:
            context_id: Context identifier
            data: Data to update
            metadata: Metadata to update (optional)
            
        Returns:
            True if updated successfully, False otherwise
        """
        context = await self.get_context(context_id)
        if not context:
            logger.warning(f"Context {context_id} not found for update")
            return False
        
        # Update data and metadata
        context.data.update(data)
        if metadata:
            context.metadata.update(metadata)
        
        context.version += 1
        context.updated_at = datetime.utcnow()
        
        return await self.store_context(context)
    
    async def delete_context(self, context_id: str) -> bool:
        """
        Delete context from Redis.
        
        Args:
            context_id: Context identifier
            
        Returns:
            True if deleted successfully, False otherwise
        """
        if not self._redis:
            raise RuntimeError("Redis connection not established")
        
        try:
            # Get context to find session and user IDs
            context = await self.get_context(context_id)
            
            # Delete context
            context_key = self._get_context_key(context_id)
            deleted = await self._redis.delete(context_key)
            
            # Remove from indexes
            if context:
                if context.session_id:
                    session_key = self._get_session_key(context.session_id)
                    await self._redis.srem(session_key, context_id)
                
                if context.user_id:
                    user_key = self._get_user_key(context.user_id)
                    await self._redis.srem(user_key, context_id)
            
            logger.debug(f"Deleted context {context_id}")
            return deleted > 0
            
        except RedisError as e:
            logger.error(f"Failed to delete context {context_id}: {e}")
            return False
    
    async def get_session_contexts(self, session_id: str) -> List[ContextData]:
        """
        Get all contexts for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of context data for the session
        """
        if not self._redis:
            raise RuntimeError("Redis connection not established")
        
        try:
            session_key = self._get_session_key(session_id)
            context_ids = await self._redis.smembers(session_key)
            
            contexts = []
            for context_id in context_ids:
                context = await self.get_context(context_id)
                if context:
                    contexts.append(context)
            
            return contexts
            
        except RedisError as e:
            logger.error(f"Failed to get session contexts for {session_id}: {e}")
            return []
    
    async def get_user_contexts(self, user_id: str, limit: int = 100) -> List[ContextData]:
        """
        Get contexts for a user.
        
        Args:
            user_id: User identifier
            limit: Maximum number of contexts to return
            
        Returns:
            List of context data for the user
        """
        if not self._redis:
            raise RuntimeError("Redis connection not established")
        
        try:
            user_key = self._get_user_key(user_id)
            context_ids = await self._redis.smembers(user_key)
            
            contexts = []
            for context_id in list(context_ids)[:limit]:
                context = await self.get_context(context_id)
                if context:
                    contexts.append(context)
            
            # Sort by updated_at descending
            contexts.sort(key=lambda x: x.updated_at, reverse=True)
            return contexts
            
        except RedisError as e:
            logger.error(f"Failed to get user contexts for {user_id}: {e}")
            return []
    
    async def cleanup_expired_contexts(self) -> int:
        """
        Clean up expired contexts and their indexes.
        
        Returns:
            Number of contexts cleaned up
        """
        if not self._redis:
            raise RuntimeError("Redis connection not established")
        
        try:
            # Get all context keys
            context_keys = await self._redis.keys("mcp:context:*")
            cleaned_count = 0
            
            for key in context_keys:
                ttl = await self._redis.ttl(key)
                if ttl == -2:  # Key doesn't exist (expired)
                    context_id = key.split(":")[-1]
                    await self.delete_context(context_id)
                    cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} expired contexts")
            return cleaned_count
            
        except RedisError as e:
            logger.error(f"Failed to cleanup expired contexts: {e}")
            return 0
    
    async def get_context_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored contexts.
        
        Returns:
            Dictionary with context statistics
        """
        if not self._redis:
            raise RuntimeError("Redis connection not established")
        
        try:
            context_keys = await self._redis.keys("mcp:context:*")
            session_keys = await self._redis.keys("mcp:session:*")
            user_keys = await self._redis.keys("mcp:user:*")
            
            return {
                "total_contexts": len(context_keys),
                "active_sessions": len(session_keys),
                "active_users": len(user_keys),
                "redis_memory_usage": await self._redis.memory_usage("mcp:*") if context_keys else 0
            }
            
        except RedisError as e:
            logger.error(f"Failed to get context stats: {e}")
            return {}