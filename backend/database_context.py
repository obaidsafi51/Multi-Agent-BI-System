"""
Database Context Management for Multi-Agent BI System

This module handles user database selection, validation, and session-based
context persistence using Redis for storage and caching.
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import redis.asyncio as redis
from dataclasses import dataclass, asdict
from mcp_client import get_backend_mcp_client

logger = logging.getLogger(__name__)


@dataclass
class DatabaseContext:
    """Database context information for user sessions."""
    database_name: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    selected_at: Optional[str] = None
    schema_cached: bool = False
    table_count: int = 0
    validation_status: str = "unknown"  # "valid", "invalid", "unknown"
    last_accessed: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DatabaseContext':
        """Create from dictionary for deserialization."""
        return cls(**data)


class DatabaseContextManager:
    """
    Manages database contexts for user sessions with Redis persistence.
    
    Handles database selection, validation, caching, and session management
    for the multi-agent BI system.
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.session_ttl = 3600 * 24  # 24 hours
        self.database_list_ttl = 600  # 10 minutes
        self.context_prefix = "db_context:"
        self.database_list_key = "available_databases"
        
    async def generate_session_id(self) -> str:
        """Generate a unique session ID."""
        return str(uuid.uuid4())
    
    async def validate_database(self, database_name: str) -> Dict[str, Any]:
        """
        Validate that a database exists and is accessible.
        
        Args:
            database_name: Name of the database to validate
            
        Returns:
            Dictionary with validation results
        """
        try:
            logger.info(f"Validating database: {database_name}")
            
            # Get available databases to check if this one exists
            available_databases = await self.get_available_databases()
            
            # Check if database exists in available list
            database_found = None
            for db in available_databases:
                if db.get("name") == database_name:
                    database_found = db
                    break
            
            if not database_found:
                return {
                    "valid": False,
                    "error": f"Database '{database_name}' not found in available databases",
                    "error_type": "not_found"
                }
            
            if not database_found.get("accessible", True):
                return {
                    "valid": False,
                    "error": f"Database '{database_name}' is not accessible",
                    "error_type": "access_denied"
                }
            
            # Try to discover tables to ensure database is truly accessible
            mcp_client = get_backend_mcp_client()
            tables_result = await mcp_client.discover_tables(database_name)
            
            if isinstance(tables_result, dict) and tables_result.get("error"):
                return {
                    "valid": False,
                    "error": f"Cannot access tables in database '{database_name}': {tables_result['error']}",
                    "error_type": "table_discovery_failed"
                }
            
            # Count tables for context metadata
            table_count = len(tables_result) if isinstance(tables_result, list) else 0
            
            logger.info(f"Database '{database_name}' validated successfully with {table_count} tables")
            
            return {
                "valid": True,
                "database_name": database_name,
                "table_count": table_count,
                "accessible": True,
                "charset": database_found.get("charset", "utf8mb4"),
                "collation": database_found.get("collation", "utf8mb4_general_ci")
            }
            
        except Exception as e:
            logger.error(f"Database validation failed for '{database_name}': {e}")
            return {
                "valid": False,
                "error": f"Database validation failed: {str(e)}",
                "error_type": "validation_error"
            }
    
    async def get_available_databases(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Get list of available databases with caching.
        
        Args:
            use_cache: Whether to use cached data if available
            
        Returns:
            List of available database information
        """
        try:
            # Check cache first if enabled
            if use_cache and self.redis_client:
                try:
                    cached_data = await self.redis_client.get(self.database_list_key)
                    if cached_data:
                        logger.debug("Serving database list from cache")
                        return json.loads(cached_data)
                except Exception as cache_error:
                    logger.warning(f"Cache read error for database list: {cache_error}")
            
            # Fetch from MCP server
            logger.info("Fetching database list from MCP server")
            mcp_client = get_backend_mcp_client()
            databases_result = await mcp_client.discover_databases()
            
            if isinstance(databases_result, dict) and databases_result.get("error"):
                logger.error(f"MCP server error getting databases: {databases_result['error']}")
                return []
            
            # Process the results
            if isinstance(databases_result, list):
                databases = databases_result
            else:
                databases = databases_result.get("databases", []) if isinstance(databases_result, dict) else []
            
            # Filter out system databases
            filtered_databases = []
            for db in databases:
                if (db.get("accessible", True) and 
                    db.get("name", "").lower() not in ['information_schema', 'performance_schema', 'mysql', 'sys']):
                    filtered_databases.append({
                        "name": db["name"],
                        "charset": db.get("charset", "utf8mb4"),
                        "collation": db.get("collation", "utf8mb4_general_ci"),
                        "accessible": db.get("accessible", True)
                    })
            
            # Cache the result
            if self.redis_client:
                try:
                    await self.redis_client.setex(
                        self.database_list_key,
                        self.database_list_ttl,
                        json.dumps(filtered_databases)
                    )
                    logger.debug(f"Cached {len(filtered_databases)} databases for {self.database_list_ttl}s")
                except Exception as cache_error:
                    logger.warning(f"Cache write error for database list: {cache_error}")
            
            return filtered_databases
            
        except Exception as e:
            logger.error(f"Error getting available databases: {e}")
            return []
    
    async def select_database(
        self, 
        database_name: str, 
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Select a database and create/update context.
        
        Args:
            database_name: Name of the database to select
            user_id: Optional user identifier
            session_id: Optional existing session ID
            
        Returns:
            Dictionary with selection results and context information
        """
        try:
            # Validate database first
            validation_result = await self.validate_database(database_name)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": validation_result["error"],
                    "error_type": validation_result["error_type"]
                }
            
            # Generate session ID if not provided
            if not session_id:
                session_id = await self.generate_session_id()
            
            # Create database context
            context = DatabaseContext(
                database_name=database_name,
                user_id=user_id,
                session_id=session_id,
                selected_at=datetime.utcnow().isoformat(),
                table_count=validation_result.get("table_count", 0),
                validation_status="valid",
                last_accessed=datetime.utcnow().isoformat(),
                metadata={
                    "charset": validation_result.get("charset"),
                    "collation": validation_result.get("collation"),
                    "accessible": validation_result.get("accessible", True)
                }
            )
            
            # Store context in Redis
            await self.store_context(session_id, context)
            
            logger.info(f"Database '{database_name}' selected successfully for session {session_id}")
            
            return {
                "success": True,
                "database_name": database_name,
                "session_id": session_id,
                "table_count": context.table_count,
                "context": context.to_dict(),
                "message": f"Database '{database_name}' selected successfully"
            }
            
        except Exception as e:
            logger.error(f"Database selection failed for '{database_name}': {e}")
            return {
                "success": False,
                "error": f"Database selection failed: {str(e)}",
                "error_type": "selection_error"
            }
    
    async def store_context(self, session_id: str, context: DatabaseContext) -> bool:
        """
        Store database context in Redis.
        
        Args:
            session_id: Session identifier
            context: Database context to store
            
        Returns:
            True if stored successfully, False otherwise
        """
        if not self.redis_client:
            logger.warning("Redis client not available, context not stored")
            return False
        
        try:
            context_key = f"{self.context_prefix}{session_id}"
            context_data = json.dumps(context.to_dict())
            
            await self.redis_client.setex(context_key, self.session_ttl, context_data)
            logger.debug(f"Stored context for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing context for session {session_id}: {e}")
            return False
    
    async def get_context(self, session_id: str) -> Optional[DatabaseContext]:
        """
        Retrieve database context from Redis.
        
        Args:
            session_id: Session identifier
            
        Returns:
            DatabaseContext if found, None otherwise
        """
        if not self.redis_client:
            logger.warning("Redis client not available, context not retrieved")
            return None
        
        try:
            context_key = f"{self.context_prefix}{session_id}"
            context_data = await self.redis_client.get(context_key)
            
            if context_data:
                context_dict = json.loads(context_data)
                context = DatabaseContext.from_dict(context_dict)
                
                # Update last accessed time
                context.last_accessed = datetime.utcnow().isoformat()
                await self.store_context(session_id, context)
                
                logger.debug(f"Retrieved context for session {session_id}")
                return context
            
            logger.debug(f"No context found for session {session_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving context for session {session_id}: {e}")
            return None
    
    async def clear_context(self, session_id: str) -> bool:
        """
        Clear database context from Redis.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if cleared successfully, False otherwise
        """
        if not self.redis_client:
            return False
        
        try:
            context_key = f"{self.context_prefix}{session_id}"
            result = await self.redis_client.delete(context_key)
            logger.debug(f"Cleared context for session {session_id}")
            return result > 0
            
        except Exception as e:
            logger.error(f"Error clearing context for session {session_id}: {e}")
            return False
    
    async def list_active_sessions(self) -> List[Dict[str, Any]]:
        """
        List all active database contexts.
        
        Returns:
            List of active session information
        """
        if not self.redis_client:
            return []
        
        try:
            pattern = f"{self.context_prefix}*"
            keys = await self.redis_client.keys(pattern)
            
            active_sessions = []
            for key in keys:
                try:
                    context_data = await self.redis_client.get(key)
                    if context_data:
                        context_dict = json.loads(context_data)
                        session_id = key.replace(self.context_prefix, "")
                        
                        active_sessions.append({
                            "session_id": session_id,
                            "database_name": context_dict.get("database_name"),
                            "selected_at": context_dict.get("selected_at"),
                            "last_accessed": context_dict.get("last_accessed"),
                            "table_count": context_dict.get("table_count", 0)
                        })
                except Exception as session_error:
                    logger.warning(f"Error processing session key {key}: {session_error}")
                    continue
            
            return active_sessions
            
        except Exception as e:
            logger.error(f"Error listing active sessions: {e}")
            return []
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired database contexts (Redis handles TTL automatically).
        This method is mainly for logging and monitoring.
        
        Returns:
            Number of sessions checked
        """
        try:
            active_sessions = await self.list_active_sessions()
            logger.info(f"Database context cleanup check: {len(active_sessions)} active sessions")
            return len(active_sessions)
            
        except Exception as e:
            logger.error(f"Error during session cleanup: {e}")
            return 0


# Global instance
_database_context_manager: Optional[DatabaseContextManager] = None


def get_database_context_manager(redis_client: Optional[redis.Redis] = None) -> DatabaseContextManager:
    """Get the global DatabaseContextManager instance."""
    global _database_context_manager
    
    if _database_context_manager is None:
        _database_context_manager = DatabaseContextManager(redis_client)
    
    return _database_context_manager


def initialize_database_context_manager(redis_client: Optional[redis.Redis] = None) -> DatabaseContextManager:
    """Initialize the global DatabaseContextManager instance."""
    global _database_context_manager
    _database_context_manager = DatabaseContextManager(redis_client)
    return _database_context_manager
