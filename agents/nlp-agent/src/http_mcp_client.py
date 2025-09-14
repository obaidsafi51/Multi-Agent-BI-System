"""
HTTP MCP Client - Fallback mechanism for when WebSocket connections fail.
This client uses the TiDB MCP Server's HTTP API endpoints.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional
from datetime import datetime
import aiohttp

logger = logging.getLogger(__name__)


class HTTPMCPClient:
    """
    HTTP client for MCP server operations as fallback when WebSocket fails.
    Uses the TiDB MCP Server's HTTP API endpoints.
    """
    
    def __init__(
        self,
        base_url: str = "http://tidb-mcp-server:8000",
        agent_id: str = "nlp-agent",
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        self.base_url = base_url.rstrip('/')
        self.agent_id = agent_id
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Session for connection pooling
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Statistics
        self.stats = {
            "requests_made": 0,
            "requests_successful": 0,
            "requests_failed": 0,
            "avg_response_time": 0.0,
            "last_response_time": 0.0
        }
        
        logger.info(f"HTTP MCP Client initialized for {agent_id} -> {base_url}")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    "User-Agent": f"NLP-Agent-HTTP-Client/{self.agent_id}",
                    "Content-Type": "application/json"
                }
            )
        return self._session
    
    async def close(self):
        """Close HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic"""
        start_time = time.time()
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                session = await self._get_session()
                url = f"{self.base_url}{endpoint}"
                
                # Add agent identification to request
                if data is None:
                    data = {}
                data["agent_id"] = self.agent_id
                data["timestamp"] = datetime.now().isoformat()
                
                logger.debug(f"HTTP {method} {url} (attempt {attempt + 1})")
                
                async with session.request(
                    method=method,
                    url=url,
                    json=data if method in ["POST", "PUT", "PATCH"] else None,
                    params=params
                ) as response:
                    response_text = await response.text()
                    
                    if response.status >= 400:
                        error_msg = f"HTTP {response.status}: {response_text}"
                        logger.error(f"HTTP request failed: {error_msg}")
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                            message=error_msg
                        )
                    
                    # Parse JSON response
                    try:
                        result = json.loads(response_text)
                    except json.JSONDecodeError:
                        result = {"success": True, "data": response_text}
                    
                    # Update statistics
                    response_time = time.time() - start_time
                    self.stats["requests_made"] += 1
                    self.stats["requests_successful"] += 1
                    self.stats["last_response_time"] = response_time
                    self._update_avg_response_time(response_time)
                    
                    logger.debug(f"HTTP request successful in {response_time:.3f}s")
                    return result
                    
            except Exception as e:
                last_error = e
                logger.warning(f"HTTP request attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    await asyncio.sleep(delay)
                else:
                    # Final attempt failed
                    self.stats["requests_made"] += 1
                    self.stats["requests_failed"] += 1
                    response_time = time.time() - start_time
                    self.stats["last_response_time"] = response_time
                    
                    logger.error(f"HTTP request failed after {self.max_retries + 1} attempts")
                    raise last_error
    
    def _update_avg_response_time(self, response_time: float):
        """Update average response time with exponential moving average"""
        alpha = 0.1
        if self.stats["avg_response_time"] == 0:
            self.stats["avg_response_time"] = response_time
        else:
            self.stats["avg_response_time"] = (
                alpha * response_time + 
                (1 - alpha) * self.stats["avg_response_time"]
            )
    
    # MCP Tool Methods
    
    async def health_check(self) -> Dict[str, Any]:
        """Check server health"""
        return await self._make_request("GET", "/health")
    
    async def get_tools(self) -> Dict[str, Any]:
        """Get available tools"""
        return await self._make_request("GET", "/tools")
    
    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific tool"""
        return await self._make_request("POST", f"/tools/{tool_name}", data=params)
    
    # Database Tools
    
    async def discover_databases(self) -> Dict[str, Any]:
        """Discover available databases"""
        return await self.execute_tool("discover_databases", {})
    
    async def discover_tables(self, database: str) -> Dict[str, Any]:
        """Discover tables in database"""
        return await self.execute_tool("discover_tables", {"database": database})
    
    async def get_table_schema(self, database: str, table: str) -> Dict[str, Any]:
        """Get table schema"""
        return await self.execute_tool("get_table_schema", {
            "database": database,
            "table": table
        })
    
    async def get_sample_data(self, database: str, table: str, limit: int = 10) -> Dict[str, Any]:
        """Get sample data from table"""
        return await self.execute_tool("get_sample_data", {
            "database": database,
            "table": table,
            "limit": limit
        })
    
    async def execute_query(self, query: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """Execute SQL query"""
        params = {"query": query}
        if timeout:
            params["timeout"] = timeout
        return await self.execute_tool("execute_query_tool", params)
    
    async def validate_query(self, query: str) -> Dict[str, Any]:
        """Validate SQL query"""
        return await self.execute_tool("validate_query_tool", {"query": query})
    
    # LLM Tools
    
    async def generate_sql(
        self,
        natural_language_query: str,
        schema_info: Optional[Dict[str, Any]] = None,
        examples: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Generate SQL from natural language"""
        params = {"natural_language_query": natural_language_query}
        if schema_info:
            params["schema_info"] = schema_info
        if examples:
            params["examples"] = examples
        return await self.execute_tool("llm_generate_sql_tool", params)
    
    async def analyze_data(
        self,
        data: str,
        analysis_type: str = "general",
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze data using LLM"""
        params = {
            "data": data,
            "analysis_type": analysis_type
        }
        if context:
            params["context"] = context
        return await self.execute_tool("llm_analyze_data_tool", params)
    
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
        return await self.execute_tool("llm_generate_text_tool", params)
    
    async def explain_results(
        self,
        query: str,
        results: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Explain query results"""
        params = {
            "query": query,
            "results": results
        }
        if context:
            params["context"] = context
        return await self.execute_tool("llm_explain_results_tool", params)
    
    # Schema Intelligence
    
    async def build_schema_context(self, databases: Optional[List[str]] = None) -> Dict[str, Any]:
        """Build comprehensive schema context"""
        params = {}
        if databases:
            params["databases"] = databases
        return await self.execute_tool("build_schema_context", params)
    
    # Utility Methods
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics"""
        success_rate = 0.0
        if self.stats["requests_made"] > 0:
            success_rate = (
                self.stats["requests_successful"] / self.stats["requests_made"] * 100
            )
        
        return {
            "base_url": self.base_url,
            "agent_id": self.agent_id,
            "requests_made": self.stats["requests_made"],
            "requests_successful": self.stats["requests_successful"],
            "requests_failed": self.stats["requests_failed"],
            "success_rate_percent": success_rate,
            "avg_response_time_ms": self.stats["avg_response_time"] * 1000,
            "last_response_time_ms": self.stats["last_response_time"] * 1000
        }
    
    async def test_connection(self) -> bool:
        """Test connection to MCP server"""
        try:
            result = await self.health_check()
            return result.get("status") == "healthy" or "success" in result
        except Exception as e:
            logger.error(f"HTTP MCP client connection test failed: {e}")
            return False
