"""
Health check utilities for MCP server connectivity.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
import aiohttp
from datetime import datetime, timedelta

from .config import MCPSchemaConfig

logger = logging.getLogger(__name__)


class MCPHealthChecker:
    """Health checker for MCP server connectivity."""
    
    def __init__(self, config: MCPSchemaConfig):
        self.config = config
        self._last_check: Optional[datetime] = None
        self._last_status: Optional[bool] = None
        self._check_interval = timedelta(seconds=30)  # Check every 30 seconds
    
    async def check_health(self, force: bool = False) -> Dict[str, Any]:
        """
        Check MCP server health.
        
        Args:
            force: Force a new health check even if recently checked
            
        Returns:
            Dictionary with health status information
        """
        now = datetime.utcnow()
        
        # Use cached result if recent and not forced
        if (not force and 
            self._last_check and 
            self._last_status is not None and
            now - self._last_check < self._check_interval):
            return {
                "status": "healthy" if self._last_status else "unhealthy",
                "server_url": self.config.mcp_server_url,
                "last_checked": self._last_check.isoformat(),
                "cached": True
            }
        
        # Perform actual health check
        health_status = await self._perform_health_check()
        
        # Update cache
        self._last_check = now
        self._last_status = health_status["healthy"]
        
        return {
            "status": "healthy" if health_status["healthy"] else "unhealthy",
            "server_url": self.config.mcp_server_url,
            "last_checked": now.isoformat(),
            "cached": False,
            "details": health_status.get("details", {}),
            "response_time_ms": health_status.get("response_time_ms"),
            "error": health_status.get("error")
        }
    
    async def _perform_health_check(self) -> Dict[str, Any]:
        """Perform the actual health check against MCP server."""
        start_time = datetime.utcnow()
        
        try:
            health_url = self.config.get_health_check_url()
            
            timeout = aiohttp.ClientTimeout(
                total=self.config.connection_timeout,
                connect=self.config.connection_timeout // 2
            )
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(health_url) as response:
                    response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                    
                    if response.status == 200:
                        try:
                            data = await response.json()
                            return {
                                "healthy": True,
                                "response_time_ms": response_time,
                                "details": data
                            }
                        except Exception as e:
                            logger.warning(f"Health check response not JSON: {e}")
                            return {
                                "healthy": True,
                                "response_time_ms": response_time,
                                "details": {"status": "ok", "note": "Non-JSON response"}
                            }
                    else:
                        return {
                            "healthy": False,
                            "response_time_ms": response_time,
                            "error": f"HTTP {response.status}: {response.reason}"
                        }
                        
        except asyncio.TimeoutError:
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return {
                "healthy": False,
                "response_time_ms": response_time,
                "error": f"Timeout after {self.config.connection_timeout}s"
            }
        except aiohttp.ClientError as e:
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return {
                "healthy": False,
                "response_time_ms": response_time,
                "error": f"Connection error: {str(e)}"
            }
        except Exception as e:
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"Unexpected error during health check: {e}")
            return {
                "healthy": False,
                "response_time_ms": response_time,
                "error": f"Unexpected error: {str(e)}"
            }
    
    async def wait_for_healthy(self, max_wait_seconds: int = 60, check_interval: int = 5) -> bool:
        """
        Wait for MCP server to become healthy.
        
        Args:
            max_wait_seconds: Maximum time to wait
            check_interval: Seconds between checks
            
        Returns:
            True if server becomes healthy, False if timeout
        """
        start_time = datetime.utcnow()
        max_wait = timedelta(seconds=max_wait_seconds)
        
        logger.info(f"Waiting for MCP server to become healthy (max {max_wait_seconds}s)")
        
        while datetime.utcnow() - start_time < max_wait:
            health_result = await self.check_health(force=True)
            
            if health_result["status"] == "healthy":
                logger.info(f"MCP server is healthy after {(datetime.utcnow() - start_time).total_seconds():.1f}s")
                return True
            
            logger.debug(f"MCP server not healthy: {health_result.get('error', 'Unknown error')}")
            await asyncio.sleep(check_interval)
        
        logger.error(f"MCP server did not become healthy within {max_wait_seconds}s")
        return False
    
    def is_healthy_cached(self) -> Optional[bool]:
        """Get cached health status without performing a check."""
        if (self._last_check and 
            self._last_status is not None and
            datetime.utcnow() - self._last_check < self._check_interval):
            return self._last_status
        return None


async def check_mcp_server_health(config: Optional[MCPSchemaConfig] = None) -> Dict[str, Any]:
    """
    Convenience function to check MCP server health.
    
    Args:
        config: MCP configuration, will load from env if not provided
        
    Returns:
        Health check result dictionary
    """
    if config is None:
        from .config import load_mcp_config
        config = load_mcp_config()
    
    checker = MCPHealthChecker(config)
    return await checker.check_health()


async def wait_for_mcp_server(config: Optional[MCPSchemaConfig] = None, 
                             max_wait_seconds: int = 60) -> bool:
    """
    Convenience function to wait for MCP server to become healthy.
    
    Args:
        config: MCP configuration, will load from env if not provided
        max_wait_seconds: Maximum time to wait
        
    Returns:
        True if server becomes healthy, False if timeout
    """
    if config is None:
        from .config import load_mcp_config
        config = load_mcp_config()
    
    checker = MCPHealthChecker(config)
    return await checker.wait_for_healthy(max_wait_seconds)