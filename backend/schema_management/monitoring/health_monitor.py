"""
Health monitoring for MCP schema management system.

This module provides comprehensive health checking capabilities for all
MCP components including connectivity, performance, and system status.
"""

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .logger import get_logger
from .metrics import get_metrics_collector


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Individual health check result."""
    
    name: str
    status: HealthStatus
    message: str
    response_time_ms: float
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert health check to dictionary."""
        return {
            'name': self.name,
            'status': self.status.value,
            'message': self.message,
            'response_time_ms': self.response_time_ms,
            'timestamp': self.timestamp.isoformat(),
            'details': self.details or {}
        }


@dataclass
class SystemHealthReport:
    """Comprehensive system health report."""
    
    overall_status: HealthStatus
    timestamp: datetime
    checks: List[HealthCheck]
    summary: Dict[str, Any]
    uptime_seconds: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert health report to dictionary."""
        return {
            'overall_status': self.overall_status.value,
            'timestamp': self.timestamp.isoformat(),
            'uptime_seconds': self.uptime_seconds,
            'summary': self.summary,
            'checks': [check.to_dict() for check in self.checks],
            'healthy_checks': len([c for c in self.checks if c.status == HealthStatus.HEALTHY]),
            'degraded_checks': len([c for c in self.checks if c.status == HealthStatus.DEGRADED]),
            'unhealthy_checks': len([c for c in self.checks if c.status == HealthStatus.UNHEALTHY]),
            'total_checks': len(self.checks)
        }


class MCPHealthMonitor:
    """
    Comprehensive health monitor for MCP schema management system.
    
    Monitors connectivity, performance, cache health, validation success rates,
    and overall system status with configurable thresholds and alerting.
    """
    
    def __init__(
        self,
        check_interval_seconds: int = 30,
        connectivity_timeout: int = 5,
        performance_threshold_ms: float = 1000.0,
        cache_hit_rate_threshold: float = 70.0,
        validation_success_threshold: float = 95.0,
        error_rate_threshold: float = 5.0
    ):
        """
        Initialize health monitor.
        
        Args:
            check_interval_seconds: Interval between health checks
            connectivity_timeout: Timeout for connectivity checks
            performance_threshold_ms: Performance threshold in milliseconds
            cache_hit_rate_threshold: Minimum acceptable cache hit rate
            validation_success_threshold: Minimum acceptable validation success rate
            error_rate_threshold: Maximum acceptable error rate percentage
        """
        self.logger = get_logger('health')
        self.metrics_collector = get_metrics_collector()
        
        # Configuration
        self.check_interval_seconds = check_interval_seconds
        self.connectivity_timeout = connectivity_timeout
        self.performance_threshold_ms = performance_threshold_ms
        self.cache_hit_rate_threshold = cache_hit_rate_threshold
        self.validation_success_threshold = validation_success_threshold
        self.error_rate_threshold = error_rate_threshold
        
        # State
        self.start_time = datetime.utcnow()
        self.last_health_check: Optional[SystemHealthReport] = None
        self.health_history: List[SystemHealthReport] = []
        self.max_history_size = 100
        
        # Dependencies (to be injected)
        self.mcp_client = None
        self.schema_manager = None
        self.cache_manager = None
        
        self.logger.info(
            "Health monitor initialized",
            check_interval=check_interval_seconds,
            thresholds={
                'performance_ms': performance_threshold_ms,
                'cache_hit_rate': cache_hit_rate_threshold,
                'validation_success': validation_success_threshold,
                'error_rate': error_rate_threshold
            }
        )
    
    def set_dependencies(self, mcp_client=None, schema_manager=None, cache_manager=None):
        """Set dependencies for health monitoring."""
        self.mcp_client = mcp_client
        self.schema_manager = schema_manager
        self.cache_manager = cache_manager
        
        self.logger.info(
            "Health monitor dependencies configured",
            has_client=mcp_client is not None,
            has_schema_manager=schema_manager is not None,
            has_cache_manager=cache_manager is not None
        )
    
    async def perform_health_check(self) -> SystemHealthReport:
        """
        Perform comprehensive health check of all MCP components.
        
        Returns:
            Complete health report
        """
        self.logger.info("Starting comprehensive health check")
        start_time = time.time()
        
        checks = []
        
        # MCP Server connectivity check
        checks.append(await self._check_mcp_connectivity())
        
        # Schema discovery performance check
        checks.append(await self._check_schema_discovery_performance())
        
        # Cache performance check
        checks.append(await self._check_cache_performance())
        
        # Validation system check
        checks.append(await self._check_validation_system())
        
        # Error rate check
        checks.append(await self._check_error_rates())
        
        # System resources check
        checks.append(await self._check_system_resources())
        
        # Database connectivity check
        checks.append(await self._check_database_connectivity())
        
        # Determine overall status
        overall_status = self._calculate_overall_status(checks)
        
        # Create summary
        summary = self._create_health_summary(checks)
        
        # Calculate uptime
        uptime_seconds = (datetime.utcnow() - self.start_time).total_seconds()
        
        # Create health report
        report = SystemHealthReport(
            overall_status=overall_status,
            timestamp=datetime.utcnow(),
            checks=checks,
            summary=summary,
            uptime_seconds=uptime_seconds
        )
        
        # Store in history
        self.last_health_check = report
        self.health_history.append(report)
        if len(self.health_history) > self.max_history_size:
            self.health_history.pop(0)
        
        duration_ms = (time.time() - start_time) * 1000
        
        self.logger.info(
            "Health check completed",
            overall_status=overall_status.value,
            duration_ms=duration_ms,
            healthy_checks=len([c for c in checks if c.status == HealthStatus.HEALTHY]),
            total_checks=len(checks)
        )
        
        return report
    
    async def _check_mcp_connectivity(self) -> HealthCheck:
        """Check MCP server connectivity."""
        start_time = time.time()
        
        try:
            if not self.mcp_client:
                return HealthCheck(
                    name="mcp_connectivity",
                    status=HealthStatus.UNKNOWN,
                    message="MCP client not configured",
                    response_time_ms=0,
                    timestamp=datetime.utcnow()
                )
            
            # Test connectivity with timeout
            try:
                is_healthy = await asyncio.wait_for(
                    self.mcp_client.health_check(),
                    timeout=self.connectivity_timeout
                )
                
                response_time_ms = (time.time() - start_time) * 1000
                
                if is_healthy:
                    return HealthCheck(
                        name="mcp_connectivity",
                        status=HealthStatus.HEALTHY,
                        message="MCP server is responding normally",
                        response_time_ms=response_time_ms,
                        timestamp=datetime.utcnow(),
                        details={'server_url': getattr(self.mcp_client.config, 'mcp_server_url', 'unknown')}
                    )
                else:
                    return HealthCheck(
                        name="mcp_connectivity",
                        status=HealthStatus.UNHEALTHY,
                        message="MCP server health check failed",
                        response_time_ms=response_time_ms,
                        timestamp=datetime.utcnow()
                    )
            
            except asyncio.TimeoutError:
                response_time_ms = (time.time() - start_time) * 1000
                return HealthCheck(
                    name="mcp_connectivity",
                    status=HealthStatus.UNHEALTHY,
                    message=f"MCP server timeout after {self.connectivity_timeout}s",
                    response_time_ms=response_time_ms,
                    timestamp=datetime.utcnow()
                )
        
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                name="mcp_connectivity",
                status=HealthStatus.UNHEALTHY,
                message=f"MCP connectivity error: {str(e)}",
                response_time_ms=response_time_ms,
                timestamp=datetime.utcnow()
            )
    
    async def _check_schema_discovery_performance(self) -> HealthCheck:
        """Check schema discovery performance."""
        start_time = time.time()
        
        try:
            if not self.schema_manager:
                return HealthCheck(
                    name="schema_discovery_performance",
                    status=HealthStatus.UNKNOWN,
                    message="Schema manager not configured",
                    response_time_ms=0,
                    timestamp=datetime.utcnow()
                )
            
            # Test schema discovery performance
            try:
                # Try to discover databases (lightweight operation)
                databases = await asyncio.wait_for(
                    self.schema_manager.discover_databases(),
                    timeout=self.connectivity_timeout
                )
                
                response_time_ms = (time.time() - start_time) * 1000
                
                if response_time_ms <= self.performance_threshold_ms:
                    status = HealthStatus.HEALTHY
                    message = f"Schema discovery performing well ({response_time_ms:.1f}ms)"
                elif response_time_ms <= self.performance_threshold_ms * 2:
                    status = HealthStatus.DEGRADED
                    message = f"Schema discovery slower than expected ({response_time_ms:.1f}ms)"
                else:
                    status = HealthStatus.UNHEALTHY
                    message = f"Schema discovery too slow ({response_time_ms:.1f}ms)"
                
                return HealthCheck(
                    name="schema_discovery_performance",
                    status=status,
                    message=message,
                    response_time_ms=response_time_ms,
                    timestamp=datetime.utcnow(),
                    details={
                        'databases_discovered': len(databases) if databases else 0,
                        'threshold_ms': self.performance_threshold_ms
                    }
                )
            
            except asyncio.TimeoutError:
                response_time_ms = (time.time() - start_time) * 1000
                return HealthCheck(
                    name="schema_discovery_performance",
                    status=HealthStatus.UNHEALTHY,
                    message="Schema discovery timeout",
                    response_time_ms=response_time_ms,
                    timestamp=datetime.utcnow()
                )
        
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                name="schema_discovery_performance",
                status=HealthStatus.UNHEALTHY,
                message=f"Schema discovery error: {str(e)}",
                response_time_ms=response_time_ms,
                timestamp=datetime.utcnow()
            )
    
    async def _check_cache_performance(self) -> HealthCheck:
        """Check cache performance and health."""
        start_time = time.time()
        
        try:
            cache_metrics = self.metrics_collector.get_cache_metrics()
            response_time_ms = (time.time() - start_time) * 1000
            
            hit_rate = cache_metrics.get('hit_rate', 0)
            memory_usage = cache_metrics.get('memory_usage_mb', 0)
            
            # Determine status based on hit rate
            if hit_rate >= self.cache_hit_rate_threshold:
                status = HealthStatus.HEALTHY
                message = f"Cache performing well (hit rate: {hit_rate:.1f}%)"
            elif hit_rate >= self.cache_hit_rate_threshold * 0.7:
                status = HealthStatus.DEGRADED
                message = f"Cache performance degraded (hit rate: {hit_rate:.1f}%)"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Cache performance poor (hit rate: {hit_rate:.1f}%)"
            
            return HealthCheck(
                name="cache_performance",
                status=status,
                message=message,
                response_time_ms=response_time_ms,
                timestamp=datetime.utcnow(),
                details={
                    'hit_rate': hit_rate,
                    'memory_usage_mb': memory_usage,
                    'cache_size': cache_metrics.get('cache_size', 0),
                    'threshold': self.cache_hit_rate_threshold
                }
            )
        
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                name="cache_performance",
                status=HealthStatus.UNHEALTHY,
                message=f"Cache health check error: {str(e)}",
                response_time_ms=response_time_ms,
                timestamp=datetime.utcnow()
            )
    
    async def _check_validation_system(self) -> HealthCheck:
        """Check validation system health."""
        start_time = time.time()
        
        try:
            validation_metrics = self.metrics_collector.get_validation_metrics()
            response_time_ms = (time.time() - start_time) * 1000
            
            success_rate = validation_metrics.get('success_rate', 0)
            total_validations = validation_metrics.get('total_validations', 0)
            
            # Skip check if no validations have been performed
            if total_validations == 0:
                return HealthCheck(
                    name="validation_system",
                    status=HealthStatus.UNKNOWN,
                    message="No validations performed yet",
                    response_time_ms=response_time_ms,
                    timestamp=datetime.utcnow()
                )
            
            # Determine status based on success rate
            if success_rate >= self.validation_success_threshold:
                status = HealthStatus.HEALTHY
                message = f"Validation system healthy (success rate: {success_rate:.1f}%)"
            elif success_rate >= self.validation_success_threshold * 0.8:
                status = HealthStatus.DEGRADED
                message = f"Validation system degraded (success rate: {success_rate:.1f}%)"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Validation system unhealthy (success rate: {success_rate:.1f}%)"
            
            return HealthCheck(
                name="validation_system",
                status=status,
                message=message,
                response_time_ms=response_time_ms,
                timestamp=datetime.utcnow(),
                details={
                    'success_rate': success_rate,
                    'total_validations': total_validations,
                    'threshold': self.validation_success_threshold
                }
            )
        
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                name="validation_system",
                status=HealthStatus.UNHEALTHY,
                message=f"Validation system check error: {str(e)}",
                response_time_ms=response_time_ms,
                timestamp=datetime.utcnow()
            )
    
    async def _check_error_rates(self) -> HealthCheck:
        """Check system error rates."""
        start_time = time.time()
        
        try:
            error_metrics = self.metrics_collector.get_error_metrics()
            system_metrics = self.metrics_collector.get_system_metrics()
            response_time_ms = (time.time() - start_time) * 1000
            
            total_errors = error_metrics.get('total_errors', 0)
            total_requests = system_metrics.get('total_requests', 0)
            
            # Calculate error rate
            if total_requests == 0:
                error_rate = 0
            else:
                error_rate = (total_errors / total_requests) * 100
            
            # Determine status based on error rate
            if error_rate <= self.error_rate_threshold:
                status = HealthStatus.HEALTHY
                message = f"Error rate acceptable ({error_rate:.2f}%)"
            elif error_rate <= self.error_rate_threshold * 2:
                status = HealthStatus.DEGRADED
                message = f"Error rate elevated ({error_rate:.2f}%)"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Error rate too high ({error_rate:.2f}%)"
            
            return HealthCheck(
                name="error_rates",
                status=status,
                message=message,
                response_time_ms=response_time_ms,
                timestamp=datetime.utcnow(),
                details={
                    'error_rate': error_rate,
                    'total_errors': total_errors,
                    'total_requests': total_requests,
                    'threshold': self.error_rate_threshold
                }
            )
        
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                name="error_rates",
                status=HealthStatus.UNHEALTHY,
                message=f"Error rate check failed: {str(e)}",
                response_time_ms=response_time_ms,
                timestamp=datetime.utcnow()
            )
    
    async def _check_system_resources(self) -> HealthCheck:
        """Check system resource usage."""
        start_time = time.time()
        
        try:
            import psutil
            
            # Get CPU and memory usage
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            response_time_ms = (time.time() - start_time) * 1000
            
            # Determine status based on resource usage
            if cpu_percent <= 70 and memory_percent <= 80:
                status = HealthStatus.HEALTHY
                message = f"System resources healthy (CPU: {cpu_percent:.1f}%, Memory: {memory_percent:.1f}%)"
            elif cpu_percent <= 85 and memory_percent <= 90:
                status = HealthStatus.DEGRADED
                message = f"System resources elevated (CPU: {cpu_percent:.1f}%, Memory: {memory_percent:.1f}%)"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"System resources critical (CPU: {cpu_percent:.1f}%, Memory: {memory_percent:.1f}%)"
            
            return HealthCheck(
                name="system_resources",
                status=status,
                message=message,
                response_time_ms=response_time_ms,
                timestamp=datetime.utcnow(),
                details={
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory_percent,
                    'memory_available_mb': memory.available / (1024 * 1024)
                }
            )
        
        except ImportError:
            # psutil not available
            response_time_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                name="system_resources",
                status=HealthStatus.UNKNOWN,
                message="System resource monitoring not available (psutil not installed)",
                response_time_ms=response_time_ms,
                timestamp=datetime.utcnow()
            )
        
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                name="system_resources",
                status=HealthStatus.UNHEALTHY,
                message=f"System resource check error: {str(e)}",
                response_time_ms=response_time_ms,
                timestamp=datetime.utcnow()
            )
    
    async def _check_database_connectivity(self) -> HealthCheck:
        """Check database connectivity through MCP."""
        start_time = time.time()
        
        try:
            if not self.mcp_client:
                return HealthCheck(
                    name="database_connectivity",
                    status=HealthStatus.UNKNOWN,
                    message="MCP client not configured",
                    response_time_ms=0,
                    timestamp=datetime.utcnow()
                )
            
            # Test database connectivity by trying to get server stats
            server_stats = await asyncio.wait_for(
                self.mcp_client.get_server_stats(),
                timeout=self.connectivity_timeout
            )
            
            response_time_ms = (time.time() - start_time) * 1000
            
            if server_stats and not server_stats.get('error'):
                return HealthCheck(
                    name="database_connectivity",
                    status=HealthStatus.HEALTHY,
                    message="Database connectivity healthy",
                    response_time_ms=response_time_ms,
                    timestamp=datetime.utcnow(),
                    details=server_stats
                )
            else:
                return HealthCheck(
                    name="database_connectivity",
                    status=HealthStatus.UNHEALTHY,
                    message="Database connectivity failed",
                    response_time_ms=response_time_ms,
                    timestamp=datetime.utcnow()
                )
        
        except asyncio.TimeoutError:
            response_time_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                name="database_connectivity",
                status=HealthStatus.UNHEALTHY,
                message="Database connectivity timeout",
                response_time_ms=response_time_ms,
                timestamp=datetime.utcnow()
            )
        
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                name="database_connectivity",
                status=HealthStatus.UNHEALTHY,
                message=f"Database connectivity error: {str(e)}",
                response_time_ms=response_time_ms,
                timestamp=datetime.utcnow()
            )
    
    def _calculate_overall_status(self, checks: List[HealthCheck]) -> HealthStatus:
        """Calculate overall system status from individual checks."""
        if not checks:
            return HealthStatus.UNKNOWN
        
        # Count status types
        unhealthy_count = len([c for c in checks if c.status == HealthStatus.UNHEALTHY])
        degraded_count = len([c for c in checks if c.status == HealthStatus.DEGRADED])
        healthy_count = len([c for c in checks if c.status == HealthStatus.HEALTHY])
        
        # Determine overall status
        if unhealthy_count > 0:
            return HealthStatus.UNHEALTHY
        elif degraded_count > 0:
            return HealthStatus.DEGRADED
        elif healthy_count > 0:
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN
    
    def _create_health_summary(self, checks: List[HealthCheck]) -> Dict[str, Any]:
        """Create health summary from checks."""
        total_checks = len(checks)
        healthy_checks = len([c for c in checks if c.status == HealthStatus.HEALTHY])
        degraded_checks = len([c for c in checks if c.status == HealthStatus.DEGRADED])
        unhealthy_checks = len([c for c in checks if c.status == HealthStatus.UNHEALTHY])
        unknown_checks = len([c for c in checks if c.status == HealthStatus.UNKNOWN])
        
        avg_response_time = sum(c.response_time_ms for c in checks) / max(total_checks, 1)
        
        return {
            'total_checks': total_checks,
            'healthy_checks': healthy_checks,
            'degraded_checks': degraded_checks,
            'unhealthy_checks': unhealthy_checks,
            'unknown_checks': unknown_checks,
            'health_percentage': (healthy_checks / max(total_checks, 1)) * 100,
            'average_response_time_ms': avg_response_time,
            'critical_issues': [c.name for c in checks if c.status == HealthStatus.UNHEALTHY],
            'warnings': [c.name for c in checks if c.status == HealthStatus.DEGRADED]
        }
    
    def get_health_history(self, hours: int = 24) -> List[SystemHealthReport]:
        """Get health history for the specified number of hours."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return [report for report in self.health_history if report.timestamp >= cutoff_time]
    
    def get_latest_health_status(self) -> Optional[SystemHealthReport]:
        """Get the latest health check result."""
        return self.last_health_check
