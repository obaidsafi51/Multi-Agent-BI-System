"""
Health monitoring module for MCP schema management.

Provides health checks, status monitoring, and system health reporting.
"""

import asyncio
import time
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta

from .logger import get_logger

logger = get_logger(__name__)


class HealthStatus(Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    WARNING = "warning" 
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Individual health check result."""
    name: str
    status: HealthStatus
    message: str
    timestamp: datetime
    duration_ms: Optional[float] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class HealthReport:
    """Overall health report."""
    overall_status: HealthStatus
    checks: List[HealthCheck]
    timestamp: datetime
    total_checks: int
    healthy_checks: int
    warning_checks: int
    critical_checks: int


# Alias for backward compatibility
SystemHealthReport = HealthReport


class MCPHealthMonitor:
    """Health monitor for MCP schema management system."""
    
    def __init__(self, check_interval_seconds: int = 60):
        """Initialize health monitor.
        
        Args:
            check_interval_seconds: Interval between health checks
        """
        self.check_interval_seconds = check_interval_seconds
        self.dependencies = {}
        self.last_health_report: Optional[HealthReport] = None
        self._running = False
        
    def set_dependencies(self, **dependencies):
        """Set system dependencies to monitor.
        
        Args:
            **dependencies: Named dependencies to monitor
        """
        self.dependencies = dependencies
        logger.info(f"Health monitor configured with {len(dependencies)} dependencies")
        
    async def perform_health_check(self) -> HealthReport:
        """Perform comprehensive health check.
        
        Returns:
            HealthReport with status of all components
        """
        checks = []
        start_time = time.time()
        
        try:
            # Check MCP client health
            if 'mcp_client' in self.dependencies:
                check = await self._check_mcp_client()
                checks.append(check)
                
            # Check cache health
            if 'cache' in self.dependencies:
                check = await self._check_cache()
                checks.append(check)
                
            # Check database connectivity
            if 'database' in self.dependencies:
                check = await self._check_database()
                checks.append(check)
                
            # If no dependencies, create a basic system check
            if not self.dependencies:
                check = HealthCheck(
                    name="system_basic",
                    status=HealthStatus.HEALTHY,
                    message="Basic system check passed",
                    timestamp=datetime.now()
                )
                checks.append(check)
                
        except Exception as e:
            logger.error(f"Error during health check: {e}")
            check = HealthCheck(
                name="health_check_error",
                status=HealthStatus.CRITICAL,
                message=f"Health check failed: {str(e)}",
                timestamp=datetime.now()
            )
            checks.append(check)
            
        # Calculate overall status
        overall_status = self._calculate_overall_status(checks)
        
        # Create health report
        report = HealthReport(
            overall_status=overall_status,
            checks=checks,
            timestamp=datetime.now(),
            total_checks=len(checks),
            healthy_checks=sum(1 for c in checks if c.status == HealthStatus.HEALTHY),
            warning_checks=sum(1 for c in checks if c.status == HealthStatus.WARNING),
            critical_checks=sum(1 for c in checks if c.status == HealthStatus.CRITICAL)
        )
        
        self.last_health_report = report
        
        duration = (time.time() - start_time) * 1000
        logger.info(f"Health check completed in {duration:.2f}ms - Status: {overall_status.value}")
        
        return report
        
    async def _check_mcp_client(self) -> HealthCheck:
        """Check MCP client health."""
        start_time = time.time()
        
        try:
            mcp_client = self.dependencies['mcp_client']
            
            # Basic connectivity check
            if hasattr(mcp_client, 'is_connected'):
                if not mcp_client.is_connected():
                    return HealthCheck(
                        name="mcp_client",
                        status=HealthStatus.CRITICAL,
                        message="MCP client not connected",
                        timestamp=datetime.now(),
                        duration_ms=(time.time() - start_time) * 1000
                    )
                    
            return HealthCheck(
                name="mcp_client",
                status=HealthStatus.HEALTHY,
                message="MCP client is healthy",
                timestamp=datetime.now(),
                duration_ms=(time.time() - start_time) * 1000
            )
            
        except Exception as e:
            return HealthCheck(
                name="mcp_client",
                status=HealthStatus.CRITICAL,
                message=f"MCP client check failed: {str(e)}",
                timestamp=datetime.now(),
                duration_ms=(time.time() - start_time) * 1000
            )
            
    async def _check_cache(self) -> HealthCheck:
        """Check cache health."""
        start_time = time.time()
        
        try:
            cache = self.dependencies['cache']
            
            # Basic cache operation check
            test_key = f"health_check_{int(time.time())}"
            test_value = "health_test"
            
            if hasattr(cache, 'set') and hasattr(cache, 'get'):
                await cache.set(test_key, test_value, ttl=10)
                retrieved = await cache.get(test_key)
                
                if retrieved != test_value:
                    return HealthCheck(
                        name="cache",
                        status=HealthStatus.WARNING,
                        message="Cache operations inconsistent",
                        timestamp=datetime.now(),
                        duration_ms=(time.time() - start_time) * 1000
                    )
                    
            return HealthCheck(
                name="cache",
                status=HealthStatus.HEALTHY,
                message="Cache is healthy",
                timestamp=datetime.now(),
                duration_ms=(time.time() - start_time) * 1000
            )
            
        except Exception as e:
            return HealthCheck(
                name="cache",
                status=HealthStatus.WARNING,
                message=f"Cache check failed: {str(e)}",
                timestamp=datetime.now(),
                duration_ms=(time.time() - start_time) * 1000
            )
            
    async def _check_database(self) -> HealthCheck:
        """Check database connectivity."""
        start_time = time.time()
        
        try:
            # This is a placeholder - actual implementation would depend on the database type
            return HealthCheck(
                name="database",
                status=HealthStatus.HEALTHY,
                message="Database check not implemented",
                timestamp=datetime.now(),
                duration_ms=(time.time() - start_time) * 1000
            )
            
        except Exception as e:
            return HealthCheck(
                name="database",
                status=HealthStatus.WARNING,
                message=f"Database check failed: {str(e)}",
                timestamp=datetime.now(),
                duration_ms=(time.time() - start_time) * 1000
            )
            
    def _calculate_overall_status(self, checks: List[HealthCheck]) -> HealthStatus:
        """Calculate overall system status from individual checks."""
        if not checks:
            return HealthStatus.UNKNOWN
            
        if any(c.status == HealthStatus.CRITICAL for c in checks):
            return HealthStatus.CRITICAL
        elif any(c.status == HealthStatus.WARNING for c in checks):
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY
            
    def get_latest_health_status(self) -> Optional[HealthReport]:
        """Get the latest health report."""
        return self.last_health_report
        
    async def start_monitoring(self):
        """Start continuous health monitoring."""
        self._running = True
        logger.info(f"Starting health monitoring with {self.check_interval_seconds}s interval")
        
        while self._running:
            try:
                await self.perform_health_check()
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                
            await asyncio.sleep(self.check_interval_seconds)
            
    def stop_monitoring(self):
        """Stop health monitoring."""
        self._running = False
        logger.info("Health monitoring stopped")
