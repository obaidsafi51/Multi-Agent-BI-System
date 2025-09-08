"""
Metrics collection and performance monitoring for MCP schema management.

This module provides comprehensive metrics collection, performance tracking,
and statistical analysis for all MCP operations.
"""

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Dict, List, Optional, Union
import statistics


@dataclass
class PerformanceMetrics:
    """Performance metrics for MCP operations."""
    
    operation: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_duration_ms: float = 0.0
    min_duration_ms: float = float('inf')
    max_duration_ms: float = 0.0
    response_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate percentage."""
        return 100.0 - self.success_rate
    
    @property
    def average_duration_ms(self) -> float:
        """Calculate average duration in milliseconds."""
        if self.total_requests == 0:
            return 0.0
        return self.total_duration_ms / self.total_requests
    
    @property
    def p95_duration_ms(self) -> float:
        """Calculate 95th percentile duration."""
        if not self.response_times:
            return 0.0
        sorted_times = sorted(self.response_times)
        index = int(0.95 * len(sorted_times))
        return sorted_times[min(index, len(sorted_times) - 1)]
    
    @property
    def p99_duration_ms(self) -> float:
        """Calculate 99th percentile duration."""
        if not self.response_times:
            return 0.0
        sorted_times = sorted(self.response_times)
        index = int(0.99 * len(sorted_times))
        return sorted_times[min(index, len(sorted_times) - 1)]
    
    def add_request(self, duration_ms: float, success: bool = True):
        """Add a request to the metrics."""
        self.total_requests += 1
        self.total_duration_ms += duration_ms
        self.response_times.append(duration_ms)
        
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        self.min_duration_ms = min(self.min_duration_ms, duration_ms)
        self.max_duration_ms = max(self.max_duration_ms, duration_ms)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'operation': self.operation,
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'success_rate': self.success_rate,
            'failure_rate': self.failure_rate,
            'average_duration_ms': self.average_duration_ms,
            'min_duration_ms': self.min_duration_ms if self.min_duration_ms != float('inf') else 0.0,
            'max_duration_ms': self.max_duration_ms,
            'p95_duration_ms': self.p95_duration_ms,
            'p99_duration_ms': self.p99_duration_ms,
        }


@dataclass
class ValidationMetrics:
    """Metrics for schema validation operations."""
    
    total_validations: int = 0
    successful_validations: int = 0
    failed_validations: int = 0
    validation_errors: List[str] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)
    validation_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    @property
    def success_rate(self) -> float:
        """Calculate validation success rate."""
        if self.total_validations == 0:
            return 0.0
        return (self.successful_validations / self.total_validations) * 100
    
    @property
    def average_validation_time_ms(self) -> float:
        """Calculate average validation time."""
        if not self.validation_times:
            return 0.0
        return statistics.mean(self.validation_times)
    
    def add_validation(self, duration_ms: float, success: bool, errors: List[str] = None, warnings: List[str] = None):
        """Add validation result to metrics."""
        self.total_validations += 1
        self.validation_times.append(duration_ms)
        
        if success:
            self.successful_validations += 1
        else:
            self.failed_validations += 1
        
        if errors:
            self.validation_errors.extend(errors[-10:])  # Keep last 10 errors
        if warnings:
            self.validation_warnings.extend(warnings[-10:])  # Keep last 10 warnings
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert validation metrics to dictionary."""
        return {
            'total_validations': self.total_validations,
            'successful_validations': self.successful_validations,
            'failed_validations': self.failed_validations,
            'success_rate': self.success_rate,
            'average_validation_time_ms': self.average_validation_time_ms,
            'recent_errors': self.validation_errors[-5:],  # Last 5 errors
            'recent_warnings': self.validation_warnings[-5:],  # Last 5 warnings
        }


@dataclass
class CacheMetrics:
    """Metrics for cache performance."""
    
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    cache_evictions: int = 0
    cache_size: int = 0
    max_cache_size: int = 0
    memory_usage_mb: float = 0.0
    hit_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    miss_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if self.total_requests == 0:
            return 0.0
        return (self.cache_hits / self.total_requests) * 100
    
    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate."""
        return 100.0 - self.hit_rate
    
    @property
    def cache_efficiency(self) -> float:
        """Calculate cache efficiency (hits vs size)."""
        if self.cache_size == 0:
            return 0.0
        return self.cache_hits / self.cache_size
    
    @property
    def average_hit_time_ms(self) -> float:
        """Calculate average cache hit response time."""
        if not self.hit_times:
            return 0.0
        return statistics.mean(self.hit_times)
    
    @property
    def average_miss_time_ms(self) -> float:
        """Calculate average cache miss response time."""
        if not self.miss_times:
            return 0.0
        return statistics.mean(self.miss_times)
    
    def add_cache_hit(self, response_time_ms: float):
        """Record cache hit."""
        self.total_requests += 1
        self.cache_hits += 1
        self.hit_times.append(response_time_ms)
    
    def add_cache_miss(self, response_time_ms: float):
        """Record cache miss."""
        self.total_requests += 1
        self.cache_misses += 1
        self.miss_times.append(response_time_ms)
    
    def add_eviction(self):
        """Record cache eviction."""
        self.cache_evictions += 1
    
    def update_cache_info(self, current_size: int, max_size: int, memory_mb: float):
        """Update cache size and memory information."""
        self.cache_size = current_size
        self.max_cache_size = max_size
        self.memory_usage_mb = memory_mb
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert cache metrics to dictionary."""
        return {
            'total_requests': self.total_requests,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'hit_rate': self.hit_rate,
            'miss_rate': self.miss_rate,
            'cache_efficiency': self.cache_efficiency,
            'cache_evictions': self.cache_evictions,
            'cache_size': self.cache_size,
            'max_cache_size': self.max_cache_size,
            'memory_usage_mb': self.memory_usage_mb,
            'average_hit_time_ms': self.average_hit_time_ms,
            'average_miss_time_ms': self.average_miss_time_ms,
        }


@dataclass
class ErrorMetrics:
    """Metrics for error tracking and analysis."""
    
    total_errors: int = 0
    error_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    error_by_operation: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    recent_errors: deque = field(default_factory=lambda: deque(maxlen=100))
    connection_errors: int = 0
    timeout_errors: int = 0
    validation_errors: int = 0
    
    def add_error(self, error_type: str, operation: str, error_message: str, timestamp: Optional[datetime] = None):
        """Add error to metrics."""
        self.total_errors += 1
        self.error_by_type[error_type] += 1
        self.error_by_operation[operation] += 1
        
        error_info = {
            'timestamp': timestamp or datetime.utcnow(),
            'type': error_type,
            'operation': operation,
            'message': error_message
        }
        self.recent_errors.append(error_info)
        
        # Categorize specific error types
        if 'connection' in error_type.lower() or 'connect' in error_message.lower():
            self.connection_errors += 1
        elif 'timeout' in error_type.lower() or 'timeout' in error_message.lower():
            self.timeout_errors += 1
        elif 'validation' in error_type.lower() or 'validation' in error_message.lower():
            self.validation_errors += 1
    
    def get_top_errors(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top error types by frequency."""
        sorted_errors = sorted(self.error_by_type.items(), key=lambda x: x[1], reverse=True)
        return [{'type': error_type, 'count': count} for error_type, count in sorted_errors[:limit]]
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent errors."""
        return list(self.recent_errors)[-limit:]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error metrics to dictionary."""
        return {
            'total_errors': self.total_errors,
            'connection_errors': self.connection_errors,
            'timeout_errors': self.timeout_errors,
            'validation_errors': self.validation_errors,
            'top_error_types': self.get_top_errors(),
            'top_error_operations': sorted(self.error_by_operation.items(), key=lambda x: x[1], reverse=True)[:5],
            'recent_errors': self.get_recent_errors(),
        }


class MCPMetricsCollector:
    """
    Central metrics collector for MCP schema management operations.
    
    Collects, aggregates, and provides access to comprehensive metrics
    for monitoring MCP performance, errors, and system health.
    """
    
    def __init__(self):
        """Initialize metrics collector."""
        self._lock = Lock()
        self._start_time = datetime.utcnow()
        
        # Performance metrics by operation
        self._performance_metrics: Dict[str, PerformanceMetrics] = defaultdict(
            lambda: PerformanceMetrics("")
        )
        
        # Specialized metrics
        self._validation_metrics = ValidationMetrics()
        self._cache_metrics = CacheMetrics()
        self._error_metrics = ErrorMetrics()
        
        # System metrics
        self._system_metrics = {
            'uptime_seconds': 0,
            'total_requests': 0,
            'requests_per_second': 0.0,
        }
    
    def record_operation(self, operation: str, duration_ms: float, success: bool = True):
        """Record an operation's performance metrics."""
        with self._lock:
            if operation not in self._performance_metrics:
                self._performance_metrics[operation] = PerformanceMetrics(operation)
            
            self._performance_metrics[operation].add_request(duration_ms, success)
            self._system_metrics['total_requests'] += 1
            
            # Update requests per second
            uptime = (datetime.utcnow() - self._start_time).total_seconds()
            self._system_metrics['uptime_seconds'] = uptime
            self._system_metrics['requests_per_second'] = self._system_metrics['total_requests'] / max(uptime, 1)
    
    def record_validation(self, duration_ms: float, success: bool, errors: List[str] = None, warnings: List[str] = None):
        """Record validation metrics."""
        with self._lock:
            self._validation_metrics.add_validation(duration_ms, success, errors, warnings)
    
    def record_cache_hit(self, response_time_ms: float):
        """Record cache hit."""
        with self._lock:
            self._cache_metrics.add_cache_hit(response_time_ms)
    
    def record_cache_miss(self, response_time_ms: float):
        """Record cache miss."""
        with self._lock:
            self._cache_metrics.add_cache_miss(response_time_ms)
    
    def record_cache_eviction(self):
        """Record cache eviction."""
        with self._lock:
            self._cache_metrics.add_eviction()
    
    def update_cache_info(self, current_size: int, max_size: int, memory_mb: float):
        """Update cache size and memory information."""
        with self._lock:
            self._cache_metrics.update_cache_info(current_size, max_size, memory_mb)
    
    def record_error(self, error_type: str, operation: str, error_message: str):
        """Record error metrics."""
        with self._lock:
            self._error_metrics.add_error(error_type, operation, error_message)
    
    def get_performance_metrics(self, operation: Optional[str] = None) -> Union[Dict[str, Any], Dict[str, Dict[str, Any]]]:
        """Get performance metrics for specific operation or all operations."""
        with self._lock:
            if operation:
                if operation in self._performance_metrics:
                    return self._performance_metrics[operation].to_dict()
                return {}
            
            return {op: metrics.to_dict() for op, metrics in self._performance_metrics.items()}
    
    def get_validation_metrics(self) -> Dict[str, Any]:
        """Get validation metrics."""
        with self._lock:
            return self._validation_metrics.to_dict()
    
    def get_cache_metrics(self) -> Dict[str, Any]:
        """Get cache metrics."""
        with self._lock:
            return self._cache_metrics.to_dict()
    
    def get_error_metrics(self) -> Dict[str, Any]:
        """Get error metrics."""
        with self._lock:
            return self._error_metrics.to_dict()
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system-level metrics."""
        with self._lock:
            uptime = (datetime.utcnow() - self._start_time).total_seconds()
            self._system_metrics['uptime_seconds'] = uptime
            return self._system_metrics.copy()
    
    def get_comprehensive_metrics(self) -> Dict[str, Any]:
        """Get all metrics in a comprehensive report."""
        with self._lock:
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'system': self.get_system_metrics(),
                'performance': self.get_performance_metrics(),
                'validation': self.get_validation_metrics(),
                'cache': self.get_cache_metrics(),
                'errors': self.get_error_metrics(),
            }
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary with key indicators."""
        with self._lock:
            cache_metrics = self.get_cache_metrics()
            error_metrics = self.get_error_metrics()
            validation_metrics = self.get_validation_metrics()
            
            # Calculate overall health score (0-100)
            health_factors = []
            
            # Cache performance (0-30 points)
            cache_hit_rate = cache_metrics.get('hit_rate', 0)
            health_factors.append(min(30, cache_hit_rate * 0.3))
            
            # Validation success rate (0-30 points)
            validation_success_rate = validation_metrics.get('success_rate', 0)
            health_factors.append(min(30, validation_success_rate * 0.3))
            
            # Error rate (0-40 points, higher is better)
            total_requests = self._system_metrics['total_requests']
            total_errors = error_metrics.get('total_errors', 0)
            error_rate = (total_errors / max(total_requests, 1)) * 100
            error_score = max(0, 40 - error_rate * 4)  # Penalty for errors
            health_factors.append(error_score)
            
            overall_health = sum(health_factors)
            
            return {
                'overall_health_score': overall_health,
                'health_status': 'excellent' if overall_health >= 90 else 
                                'good' if overall_health >= 70 else 
                                'fair' if overall_health >= 50 else 'poor',
                'cache_hit_rate': cache_hit_rate,
                'validation_success_rate': validation_success_rate,
                'error_rate': error_rate,
                'uptime_hours': self._system_metrics['uptime_seconds'] / 3600,
                'requests_per_second': self._system_metrics['requests_per_second'],
            }
    
    def reset_metrics(self):
        """Reset all metrics (useful for testing)."""
        with self._lock:
            self._performance_metrics.clear()
            self._validation_metrics = ValidationMetrics()
            self._cache_metrics = CacheMetrics()
            self._error_metrics = ErrorMetrics()
            self._start_time = datetime.utcnow()
            self._system_metrics = {
                'uptime_seconds': 0,
                'total_requests': 0,
                'requests_per_second': 0.0,
            }


# Global metrics collector instance
_metrics_collector = None

def get_metrics_collector() -> MCPMetricsCollector:
    """Get global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MCPMetricsCollector()
    return _metrics_collector
