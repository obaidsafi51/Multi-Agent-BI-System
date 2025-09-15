"""
Hybrid MCP Operations Adapter with WebSocket-first and HTTP fallback support.
This ensures reliable MCP communication even when WebSocket connections fail.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from .enhanced_websocket_client import EnhancedWebSocketMCPClient
from .http_mcp_client import HTTPMCPClient

logger = logging.getLogger(__name__)


class HybridMCPOperationsAdapter:
    """
    Hybrid MCP operations adapter that provides intelligent failover between
    WebSocket and HTTP communication methods for maximum reliability.
    """
    
    def __init__(
        self,
        # WebSocket settings
        ws_url: str = "ws://tidb-mcp-server:8000/ws",
        # HTTP settings  
        http_url: str = "http://tidb-mcp-server:8000",
        agent_id: str = "nlp-agent",
        # Fallback settings - more aggressive WebSocket preference
        ws_failure_threshold: int = 10,  # Increased threshold - prefer WebSocket longer
        ws_retry_cooldown: float = 30.0,  # Reduced cooldown - retry WebSocket sooner
        prefer_websocket: bool = True
    ):
        self.agent_id = agent_id
        self.ws_failure_threshold = ws_failure_threshold
        self.ws_retry_cooldown = ws_retry_cooldown
        self.prefer_websocket = prefer_websocket
        
        # Initialize clients
        self.websocket_client = EnhancedWebSocketMCPClient(
            ws_url=ws_url,
            agent_id=agent_id,
            connection_timeout=30.0,  # Increased for stability
            request_timeout=180.0,    # Increased for KIMI API processing (3 minutes)
            heartbeat_interval=45.0,  # More frequent than health checks
            health_check_interval=300.0,  # Much less frequent health checks (5 minutes)
            ping_timeout=20.0,  # Increased ping timeout
            circuit_breaker_threshold=8,  # More tolerant to occasional failures
            circuit_breaker_timeout=120.0  # Longer cooldown
        )
        
        self.http_client = HTTPMCPClient(
            base_url=http_url,
            agent_id=agent_id,
            timeout=180.0,  # Match WebSocket timeout for consistency
            max_retries=2
        )
        
        # State tracking
        self.ws_consecutive_failures = 0
        self.ws_last_failure_time = 0
        self.current_mode = "websocket" if prefer_websocket else "http"
        self.fallback_active = False
        
        # Statistics
        self.stats = {
            "websocket_requests": 0,
            "websocket_successes": 0,
            "websocket_failures": 0,
            "http_requests": 0,
            "http_successes": 0,
            "http_failures": 0,
            "mode_switches": 0,
            "total_requests": 0
        }
        
        logger.info(f"Hybrid MCP Adapter initialized (prefer: {self.current_mode})")
    
    @property
    def is_websocket_available(self) -> bool:
        """Check if WebSocket mode is available"""
        if self.ws_consecutive_failures >= self.ws_failure_threshold:
            # Check if cooldown period has passed
            current_time = asyncio.get_event_loop().time()
            if current_time - self.ws_last_failure_time < self.ws_retry_cooldown:
                return False
            else:
                # Reset failure count after cooldown
                self.ws_consecutive_failures = 0
                logger.info("WebSocket cooldown period expired - retrying")
        
        return self.websocket_client.is_connected or not self.fallback_active
    
    def _should_use_websocket(self) -> bool:
        """Determine if WebSocket should be used for the next request"""
        if not self.prefer_websocket:
            return False
        
        return self.is_websocket_available and (
            self.websocket_client.is_connected or 
            self.ws_consecutive_failures < self.ws_failure_threshold
        )
    
    async def _execute_with_websocket(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """Execute request using WebSocket client"""
        try:
            # Ensure connection
            if not self.websocket_client.is_connected:
                connected = await self.websocket_client.connect()
                if not connected:
                    raise ConnectionError("Failed to establish WebSocket connection")
            
            # Execute request
            result = await self.websocket_client.send_request(
                method=method,
                params=params or {},
                timeout=timeout,
                use_batching=False  # Disable batching for reliability
            )
            
            # Success - reset failure count
            self.ws_consecutive_failures = 0
            self.stats["websocket_requests"] += 1
            self.stats["websocket_successes"] += 1
            
            logger.info(f"✅ WebSocket request successful: {method} (mode: websocket)")
            return result
            
        except Exception as e:
            # Handle WebSocket failure
            self.ws_consecutive_failures += 1
            self.ws_last_failure_time = asyncio.get_event_loop().time()
            self.stats["websocket_requests"] += 1
            self.stats["websocket_failures"] += 1
            
            logger.warning(f"WebSocket request failed ({self.ws_consecutive_failures}/{self.ws_failure_threshold}): {e}")
            
            # Check if we should switch to HTTP fallback
            if self.ws_consecutive_failures >= self.ws_failure_threshold:
                self.fallback_active = True
                logger.error(f"WebSocket failure threshold reached - activating HTTP fallback")
            
            raise
    
    async def _execute_with_http(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """Execute request using HTTP client"""
        try:
            # Map method names to HTTP client methods
            if method == "llm_generate_text_tool":
                result = await self.http_client.generate_text(
                    prompt=params.get("prompt", ""),
                    system_prompt=params.get("system_prompt"),
                    max_tokens=params.get("max_tokens"),
                    temperature=params.get("temperature")
                )
            elif method == "llm_generate_sql_tool":
                result = await self.http_client.generate_sql(
                    natural_language_query=params.get("natural_language_query", ""),
                    schema_info=params.get("schema_info"),
                    examples=params.get("examples")
                )
            elif method == "discover_databases":
                result = await self.http_client.discover_databases()
            elif method == "discover_tables":
                result = await self.http_client.discover_tables(params.get("database"))
            elif method == "get_table_schema":
                result = await self.http_client.get_table_schema(
                    params.get("database"), params.get("table")
                )
            elif method == "execute_query_tool" or method == "execute_query":
                result = await self.http_client.execute_query(
                    params.get("query"), params.get("timeout")
                )
            elif method == "health_check":
                result = await self.http_client.health_check()
            elif method == "build_schema_context":
                # build_schema_context doesn't exist - use discover_databases + get_table_schema instead
                result = await self._build_schema_context_fallback(params.get("databases", []))
            elif method == "validate_query_tool":
                result = await self.http_client.execute_tool("validate_query_tool", params or {})
            elif method == "llm_analyze_data_tool":
                result = await self.http_client.execute_tool("llm_analyze_data_tool", params or {})
            else:
                # Generic tool execution
                result = await self.http_client.execute_tool(method, params or {})
            
            self.stats["http_requests"] += 1
            self.stats["http_successes"] += 1
            
            logger.info(f"📡 HTTP request successful: {method} (mode: http)")
            return result
            
        except Exception as e:
            self.stats["http_requests"] += 1
            self.stats["http_failures"] += 1
            
            logger.error(f"HTTP request failed: {e}")
            raise
    
    async def send_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        force_http: bool = False
    ) -> Dict[str, Any]:
        """
        Send request using WebSocket-first approach with HTTP fallback.
        
        Args:
            method: MCP method name
            params: Method parameters
            timeout: Request timeout
            force_http: Force use of HTTP client
        
        Returns:
            Response from MCP server
        """
        self.stats["total_requests"] += 1
        original_mode = self.current_mode
        
        # Determine which client to use
        use_websocket = not force_http and self._should_use_websocket()
        
        try:
            if use_websocket:
                self.current_mode = "websocket"
                return await self._execute_with_websocket(method, params, timeout)
            else:
                # Use HTTP fallback
                if self.current_mode != "http":
                    self.current_mode = "http"
                    self.stats["mode_switches"] += 1
                    logger.info(f"Switching to HTTP mode for request: {method}")
                
                return await self._execute_with_http(method, params, timeout)
                
        except Exception as e:
            # If WebSocket failed and we haven't tried HTTP yet, try HTTP
            if use_websocket and not force_http:
                logger.warning(f"WebSocket failed, trying HTTP fallback: {e}")
                self.current_mode = "http"
                self.stats["mode_switches"] += 1
                
                try:
                    return await self._execute_with_http(method, params, timeout)
                except Exception as http_error:
                    logger.error(f"Both WebSocket and HTTP failed: WS={e}, HTTP={http_error}")
                    raise Exception(f"All communication methods failed: WebSocket={e}, HTTP={http_error}")
            else:
                raise
        finally:
            # Track mode changes
            if original_mode != self.current_mode:
                logger.info(f"MCP communication mode changed: {original_mode} -> {self.current_mode}")
    
    # Convenience methods for common operations
    
    async def generate_sql(
        self,
        natural_language_query: str,
        schema_info: Optional[Dict[str, Any]] = None,
        examples: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Generate SQL from natural language query"""
        params = {"natural_language_query": natural_language_query}
        if schema_info:
            params["schema_info"] = schema_info
        if examples:
            params["examples"] = examples
        
        return await self.send_request("llm_generate_sql_tool", params)
    
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """Generate text using LLM"""
        params = {"prompt": prompt}
        if system_prompt:
            params["system_prompt"] = system_prompt
        if max_tokens:
            params["max_tokens"] = max_tokens
        if temperature:
            params["temperature"] = temperature
        
        return await self.send_request("llm_generate_text_tool", params)
    
    async def discover_databases(self) -> Dict[str, Any]:
        """Discover available databases"""
        return await self.send_request("discover_databases")
    
    async def build_schema_context(self, databases: Optional[List[str]] = None) -> Dict[str, Any]:
        """Build schema context"""
        params = {}
        if databases:
            params["databases"] = databases
        return await self.send_request("build_schema_context", params)
    
    async def get_schema_context(self, database: str = "default") -> Dict[str, Any]:
        """Get schema context for a database"""
        try:
            return await self.build_schema_context([database])
        except Exception as e:
            logger.error(f"Failed to get schema context for {database}: {e}")
            return {"error": str(e), "schema_context": None}
    
    async def health_check(self) -> Dict[str, Any]:
        """Check server health"""
        return await self.send_request("health_check")
    
    async def validate_query(self, query: str) -> Dict[str, Any]:
        """Validate SQL query"""
        return await self.send_request("validate_query_tool", {"query": query})
    
    async def analyze_query_result(self, **kwargs) -> Dict[str, Any]:
        """Analyze query results"""
        return await self.send_request("llm_analyze_data_tool", kwargs)
    
    async def analyze_data(self, **kwargs) -> Dict[str, Any]:
        """Analyze data - alias for analyze_query_result"""
        return await self.analyze_query_result(**kwargs)
    
    async def _build_schema_context_fallback(self, databases: List[str]) -> Dict[str, Any]:
        """Build schema context using available tools when build_schema_context is not available"""
        try:
            logger.info("Building schema context using fallback method")
            
            # If no databases specified, discover them
            if not databases:
                discover_result = await self.send_request("discover_databases_tool")
                databases = discover_result.get("databases", [])
            
            schema_context = {
                "success": True,
                "databases": {},
                "tables": [],
                "total_tables": 0,
                "total_columns": 0
            }
            
            for db_name in databases[:1]:  # Limit to first database to avoid timeout
                try:
                    # Get tables for this database
                    tables_result = await self.send_request("discover_tables_tool", {"database": db_name})
                    tables = tables_result.get("tables", [])
                    
                    db_info = {
                        "name": db_name,
                        "tables": {},
                        "table_count": len(tables)
                    }
                    
                    # Get schema for each table (limit to first 5 to prevent timeout)
                    for table_name in tables[:5]:
                        try:
                            schema_result = await self.send_request("get_table_schema_tool", {
                                "database": db_name, 
                                "table": table_name
                            })
                            if schema_result.get("success"):
                                db_info["tables"][table_name] = schema_result.get("schema", {})
                                schema_context["total_tables"] += 1
                        except Exception as e:
                            logger.warning(f"Failed to get schema for {db_name}.{table_name}: {e}")
                            continue
                    
                    schema_context["databases"][db_name] = db_info
                    
                except Exception as e:
                    logger.warning(f"Failed to process database {db_name}: {e}")
                    continue
            
            logger.info(f"Built fallback schema context: {schema_context['total_tables']} tables")
            return schema_context
            
        except Exception as e:
            logger.error(f"Schema context fallback failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "databases": {},
                "tables": [],
                "total_tables": 0,
                "total_columns": 0
            }
    
    # Lifecycle management
    
    async def analyze_data(self, **kwargs) -> Dict[str, Any]:
        """Analyze data using LLM"""
        return await self.send_request("llm_analyze_data_tool", kwargs)
    
    # Lifecycle management
    
    async def start(self):
        """Start the hybrid adapter"""
        logger.info("Starting Hybrid MCP Adapter")
        
        # Try to connect WebSocket if preferred
        if self.prefer_websocket:
            try:
                await self.websocket_client.connect()
                logger.info("WebSocket client connected successfully")
            except Exception as e:
                logger.warning(f"WebSocket connection failed, will use HTTP: {e}")
                self.current_mode = "http"
                self.fallback_active = True
        
        # Test HTTP client
        try:
            http_ok = await self.http_client.test_connection()
            if http_ok:
                logger.info("HTTP client connection test successful")
            else:
                logger.warning("HTTP client connection test failed")
        except Exception as e:
            logger.warning(f"HTTP client test failed: {e}")
    
    async def stop(self):
        """Stop the hybrid adapter"""
        logger.info("Stopping Hybrid MCP Adapter")
        
        # Close WebSocket connection
        if self.websocket_client:
            await self.websocket_client.disconnect()
        
        # Close HTTP session
        if self.http_client:
            await self.http_client.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        ws_success_rate = 0.0
        if self.stats["websocket_requests"] > 0:
            ws_success_rate = (
                self.stats["websocket_successes"] / self.stats["websocket_requests"] * 100
            )
        
        http_success_rate = 0.0
        if self.stats["http_requests"] > 0:
            http_success_rate = (
                self.stats["http_successes"] / self.stats["http_requests"] * 100
            )
        
        overall_success_rate = 0.0
        total_successes = self.stats["websocket_successes"] + self.stats["http_successes"]
        if self.stats["total_requests"] > 0:
            overall_success_rate = (total_successes / self.stats["total_requests"] * 100)
        
        return {
            "current_mode": self.current_mode,
            "fallback_active": self.fallback_active,
            "websocket_available": self.is_websocket_available,
            "ws_consecutive_failures": self.ws_consecutive_failures,
            "statistics": {
                "total_requests": self.stats["total_requests"],
                "mode_switches": self.stats["mode_switches"],
                "websocket": {
                    "requests": self.stats["websocket_requests"],
                    "successes": self.stats["websocket_successes"],
                    "failures": self.stats["websocket_failures"],
                    "success_rate_percent": ws_success_rate
                },
                "http": {
                    "requests": self.stats["http_requests"],
                    "successes": self.stats["http_successes"],
                    "failures": self.stats["http_failures"],
                    "success_rate_percent": http_success_rate
                },
                "overall_success_rate_percent": overall_success_rate
            },
            "client_stats": {
                "websocket": self.websocket_client.get_connection_stats() if self.websocket_client else {},
                "http": self.http_client.get_stats() if self.http_client else {}
            }
        }
