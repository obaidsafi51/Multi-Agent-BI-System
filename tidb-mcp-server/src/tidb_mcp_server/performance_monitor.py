"""Performance monitoring and metrics collection for TiDB MCP Server."""

import time
import threading
import psutil
import os
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import logging
import asyncio
from contextlib import asynccontextmanager, contextmanager

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Represents a single metric measurement."""
    
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'timestamp': self.timestamp,
            'value': self.value,
            'labels': self.labels.copy()
        }


@dataclass
class PerformanceStats:
    """Performance statistics for a specific operation or time period."""
    
    operation: str
    count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    avg_time: float = 0.0
    p95_time: float = 0.0
    p99_time: float = 0.0
    error_count: int = 0
    last_updated: float = field(default_factory=time.time)
    
    def update(self, execution_time: float, is_error: bool = False) -> None:
        """Update statistics with a new measurement."""
        self.count += 1
        self.total_time += execution_time
        self.min_time = min(self.min_time, execution_time)
        self.max_time = max(self.max_time, execution_time)
        self.avg_time = self.total_time / self.count
        self.last_updated = time.time()
        
        if is_error:
            self.error_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'operation': self.operation,
            'count': self.count,
            'total_time': self.total_time,
            'min_time': self.min_time if self.min_time != float('inf') else 0.0,
            'max_time': self.max_time,
            'avg_time': self.avg_time,
            'p95_time': self.p95_time,
            'p99_time': self.p99_time,
            'error_count': self.error_count,
            'error_rate': (self.error_count / self.count * 100) if self.count > 0 else 0.0,
            'last_updated': self.last_updated
        }


class PerformanceMonitor:
    """Comprehensive performance monitoring system."""
    
    def __init__(self, max_history_size: int = 10000):
        """Initialize the performance monitor."""
        self._max_history_size = max_history_size
        self._lock = threading.RLock()
        
        # Performance statistics by operation
        self._stats: Dict[str, PerformanceStats] = {}
        
        # Historical measurements for percentile calculations
        self._history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history_size))
        
        # System metrics
        self._system_metrics: Dict[str, deque] = {
            'cpu_percent': deque(maxlen=1000),
            'memory_percent': deque(maxlen=1000),
            'memory_mb': deque(maxlen=1000),
        }
        
        # Custom metrics
        self._custom_metrics: Dict[str, List[MetricPoint]] = defaultdict(list)
        
        # Monitoring state
        self._monitoring_active = False
        self._monitoring_thread: Optional[threading.Thread] = None
        self._process = psutil.Process(os.getpid())
        
        logger.info(f"PerformanceMonitor initialized with max_history_size={max_history_size}")
    
    def start_monitoring(self, interval: float = 5.0) -> None:
        """Start background system monitoring."""
        if self._monitoring_active:
            logger.warning("Performance monitoring is already active")
            return
        
        self._monitoring_active = True
        self._monitoring_thread = threading.Thread(
            target=self._monitor_system_metrics,
            args=(interval,),
            daemon=True
        )
        self._monitoring_thread.start()
        logger.info(f"Started performance monitoring with {interval}s interval")
    
    def stop_monitoring(self) -> None:
        """Stop background system monitoring."""
        if not self._monitoring_active:
            return
        
        self._monitoring_active = False
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=1.0)
        logger.info("Stopped performance monitoring")
    
    @contextmanager
    def measure_sync(self, operation: str, labels: Optional[Dict[str, str]] = None):
        """Context manager for measuring synchronous operation performance."""
        start_time = time.time()
        error_occurred = False
        
        try:
            yield
        except Exception as e:
            error_occurred = True
            raise
        finally:
            execution_time = time.time() - start_time
            self.record_measurement(operation, execution_time, error_occurred, labels)
    
    @asynccontextmanager
    async def measure_async(self, operation: str, labels: Optional[Dict[str, str]] = None):
        """Async context manager for measuring asynchronous operation performance."""
        start_time = time.time()
        error_occurred = False
        
        try:
            yield
        except Exception as e:
            error_occurred = True
            raise
        finally:
            execution_time = time.time() - start_time
            self.record_measurement(operation, execution_time, error_occurred, labels)
    
    def record_measurement(self, operation: str, execution_time: float, 
                          is_error: bool = False, labels: Optional[Dict[str, str]] = None) -> None:
        """Record a performance measurement."""
        with self._lock:
            # Update or create performance statistics
            if operation not in self._stats:
                self._stats[operation] = PerformanceStats(operation=operation)
            
            self._stats[operation].update(execution_time, is_error)
            
            # Add to history for percentile calculations
            self._history[operation].append(execution_time)
            
            # Update percentiles if we have enough data
            if len(self._history[operation]) >= 10:
                self._update_percentiles(operation)
            
            # Record custom metric if labels provided
            if labels:
                metric_point = MetricPoint(
                    timestamp=time.time(),
                    value=execution_time,
                    labels=labels
                )
                self._custom_metrics[operation].append(metric_point)
                
                # Limit custom metrics history
                if len(self._custom_metrics[operation]) > self._max_history_size:
                    self._custom_metrics[operation] = self._custom_metrics[operation][-self._max_history_size:]
        
        logger.debug(f"Recorded measurement for {operation}: {execution_time:.3f}s (error: {is_error})")
    
    def get_operation_stats(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """Get performance statistics for operations."""
        with self._lock:
            if operation:
                if operation in self._stats:
                    return self._stats[operation].to_dict()
                else:
                    return {}
            else:
                return {op: stats.to_dict() for op, stats in self._stats.items()}
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get a comprehensive performance summary."""
        with self._lock:
            # Operation statistics
            operation_stats = self.get_operation_stats()
            
            # Top slowest operations
            slowest_ops = sorted(
                [(op, stats['avg_time']) for op, stats in operation_stats.items()],
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            return {
                'timestamp': time.time(),
                'operation_count': len(operation_stats),
                'total_operations': sum(stats['count'] for stats in operation_stats.values()),
                'total_errors': sum(stats['error_count'] for stats in operation_stats.values()),
                'slowest_operations': slowest_ops,
                'monitoring_active': self._monitoring_active
            }
    
    def _update_percentiles(self, operation: str) -> None:
        """Update percentile calculations for an operation."""
        if operation not in self._history or len(self._history[operation]) < 10:
            return
        
        times = sorted(self._history[operation])
        count = len(times)
        
        # Calculate P95 and P99
        p95_index = int(count * 0.95)
        p99_index = int(count * 0.99)
        
        self._stats[operation].p95_time = times[min(p95_index, count - 1)]
        self._stats[operation].p99_time = times[min(p99_index, count - 1)]
    
    def _monitor_system_metrics(self, interval: float) -> None:
        """Background thread for monitoring system metrics."""
        logger.info("Started system metrics monitoring thread")
        
        while self._monitoring_active:
            try:
                current_time = time.time()
                
                # CPU and Memory metrics
                cpu_percent = self._process.cpu_percent()
                memory_info = self._process.memory_info()
                memory_percent = self._process.memory_percent()
                
                # Record CPU and memory metrics
                self._system_metrics['cpu_percent'].append(
                    MetricPoint(current_time, cpu_percent)
                )
                self._system_metrics['memory_percent'].append(
                    MetricPoint(current_time, memory_percent)
                )
                self._system_metrics['memory_mb'].append(
                    MetricPoint(current_time, memory_info.rss / 1024 / 1024)
                )
                
            except Exception as e:
                logger.error(f"Error collecting system metrics: {e}")
            
            time.sleep(interval)
        
        logger.info("Stopped system metrics monitoring thread")


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor