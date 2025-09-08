"""
Performance tracking and monitoring for MCP schema management operations.

This module provides detailed performance monitoring, trend analysis,
and optimization recommendations for MCP operations.
"""

import asyncio
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import statistics

from .logger import get_logger
from .metrics import get_metrics_collector


@dataclass
class PerformanceSnapshot:
    """Snapshot of performance metrics at a point in time."""
    
    timestamp: datetime
    operation: str
    duration_ms: float
    success: bool
    cache_hit: Optional[bool] = None
    database_time_ms: Optional[float] = None
    network_time_ms: Optional[float] = None
    validation_time_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'operation': self.operation,
            'duration_ms': self.duration_ms,
            'success': self.success,
            'cache_hit': self.cache_hit,
            'database_time_ms': self.database_time_ms,
            'network_time_ms': self.network_time_ms,
            'validation_time_ms': self.validation_time_ms,
            'metadata': self.metadata
        }


@dataclass
class PerformanceTrend:
    """Performance trend analysis for an operation."""
    
    operation: str
    time_window_minutes: int
    samples_count: int
    average_duration_ms: float
    median_duration_ms: float
    p95_duration_ms: float
    p99_duration_ms: float
    success_rate: float
    trend_direction: str  # 'improving', 'degrading', 'stable'
    trend_magnitude: float  # Change percentage
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'operation': self.operation,
            'time_window_minutes': self.time_window_minutes,
            'samples_count': self.samples_count,
            'average_duration_ms': self.average_duration_ms,
            'median_duration_ms': self.median_duration_ms,
            'p95_duration_ms': self.p95_duration_ms,
            'p99_duration_ms': self.p99_duration_ms,
            'success_rate': self.success_rate,
            'trend_direction': self.trend_direction,
            'trend_magnitude': self.trend_magnitude
        }


@dataclass
class OptimizationRecommendation:
    """Performance optimization recommendation."""
    
    category: str
    priority: str  # 'high', 'medium', 'low'
    title: str
    description: str
    impact: str
    effort: str
    metrics: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'category': self.category,
            'priority': self.priority,
            'title': self.title,
            'description': self.description,
            'impact': self.impact,
            'effort': self.effort,
            'metrics': self.metrics
        }


class MCPPerformanceTracker:
    """
    Advanced performance tracker for MCP schema management operations.
    
    Provides detailed performance monitoring, trend analysis, bottleneck detection,
    and optimization recommendations for all MCP operations.
    """
    
    def __init__(self, max_snapshots: int = 10000, trend_window_minutes: int = 60):
        """
        Initialize performance tracker.
        
        Args:
            max_snapshots: Maximum number of performance snapshots to retain
            trend_window_minutes: Time window for trend analysis
        """
        self.logger = get_logger('performance')
        self.metrics_collector = get_metrics_collector()
        
        # Configuration
        self.max_snapshots = max_snapshots
        self.trend_window_minutes = trend_window_minutes
        
        # Performance data storage
        self.snapshots: deque[PerformanceSnapshot] = deque(maxlen=max_snapshots)
        self.operation_snapshots: Dict[str, deque[PerformanceSnapshot]] = defaultdict(
            lambda: deque(maxlen=1000)
        )
        
        # Trend analysis cache
        self.cached_trends: Dict[str, Tuple[PerformanceTrend, datetime]] = {}
        self.trend_cache_ttl_minutes = 5
        
        # Performance baselines (learned over time)
        self.operation_baselines: Dict[str, Dict[str, float]] = {}
        
        self.logger.info("Performance tracker initialized")
    
    @asynccontextmanager
    async def track_operation(
        self,
        operation: str,
        **metadata
    ):
        """
        Context manager for tracking operation performance.
        
        Args:
            operation: Operation name
            **metadata: Additional metadata to track
        """
        start_time = time.time()
        start_timestamp = datetime.utcnow()
        
        performance_data = {
            'cache_hit': None,
            'database_time_ms': None,
            'network_time_ms': None,
            'validation_time_ms': None,
        }
        
        self.logger.debug(f"Starting performance tracking for: {operation}")
        
        try:
            yield performance_data
            
            success = True
            
        except Exception as e:
            success = False
            metadata['error'] = str(e)
            raise
            
        finally:
            # Calculate total duration
            total_duration_ms = (time.time() - start_time) * 1000
            
            # Create performance snapshot
            snapshot = PerformanceSnapshot(
                timestamp=start_timestamp,
                operation=operation,
                duration_ms=total_duration_ms,
                success=success,
                cache_hit=performance_data.get('cache_hit'),
                database_time_ms=performance_data.get('database_time_ms'),
                network_time_ms=performance_data.get('network_time_ms'),
                validation_time_ms=performance_data.get('validation_time_ms'),
                metadata=metadata
            )
            
            # Store snapshot
            self._store_snapshot(snapshot)
            
            # Update metrics collector
            self.metrics_collector.record_operation(operation, total_duration_ms, success)
            
            self.logger.debug(
                f"Performance tracking completed for: {operation}",
                duration_ms=total_duration_ms,
                success=success,
                **metadata
            )
    
    def _store_snapshot(self, snapshot: PerformanceSnapshot):
        """Store performance snapshot."""
        self.snapshots.append(snapshot)
        self.operation_snapshots[snapshot.operation].append(snapshot)
        
        # Update baseline if this is a successful operation
        if snapshot.success:
            self._update_baseline(snapshot)
    
    def _update_baseline(self, snapshot: PerformanceSnapshot):
        """Update performance baseline for an operation."""
        operation = snapshot.operation
        
        if operation not in self.operation_baselines:
            self.operation_baselines[operation] = {
                'average_duration_ms': snapshot.duration_ms,
                'sample_count': 1,
                'last_updated': time.time()
            }
        else:
            baseline = self.operation_baselines[operation]
            
            # Calculate rolling average (exponential moving average)
            alpha = 0.1  # Smoothing factor
            baseline['average_duration_ms'] = (
                alpha * snapshot.duration_ms + 
                (1 - alpha) * baseline['average_duration_ms']
            )
            baseline['sample_count'] += 1
            baseline['last_updated'] = time.time()
    
    def get_operation_performance(
        self,
        operation: str,
        time_window_minutes: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get performance statistics for a specific operation.
        
        Args:
            operation: Operation name
            time_window_minutes: Time window for analysis (default: all data)
            
        Returns:
            Performance statistics
        """
        snapshots = self.operation_snapshots[operation]
        
        if time_window_minutes:
            cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
            snapshots = [s for s in snapshots if s.timestamp >= cutoff_time]
        else:
            snapshots = list(snapshots)
        
        if not snapshots:
            return {
                'operation': operation,
                'sample_count': 0,
                'message': 'No performance data available'
            }
        
        # Calculate statistics
        durations = [s.duration_ms for s in snapshots]
        successful_operations = [s for s in snapshots if s.success]
        
        cache_hits = [s for s in snapshots if s.cache_hit is True]
        cache_misses = [s for s in snapshots if s.cache_hit is False]
        
        stats = {
            'operation': operation,
            'sample_count': len(snapshots),
            'time_window_minutes': time_window_minutes,
            'success_rate': len(successful_operations) / len(snapshots) * 100,
            'duration_stats': {
                'average_ms': statistics.mean(durations),
                'median_ms': statistics.median(durations),
                'min_ms': min(durations),
                'max_ms': max(durations),
                'std_dev_ms': statistics.stdev(durations) if len(durations) > 1 else 0
            }
        }
        
        # Add percentiles if enough data
        if len(durations) >= 10:
            sorted_durations = sorted(durations)
            stats['duration_stats'].update({
                'p90_ms': sorted_durations[int(0.9 * len(sorted_durations))],
                'p95_ms': sorted_durations[int(0.95 * len(sorted_durations))],
                'p99_ms': sorted_durations[int(0.99 * len(sorted_durations))]
            })
        
        # Cache statistics
        if cache_hits or cache_misses:
            total_cache_requests = len(cache_hits) + len(cache_misses)
            stats['cache_stats'] = {
                'cache_hit_rate': len(cache_hits) / total_cache_requests * 100,
                'cache_hits': len(cache_hits),
                'cache_misses': len(cache_misses),
                'avg_cache_hit_time_ms': statistics.mean([s.duration_ms for s in cache_hits]) if cache_hits else 0,
                'avg_cache_miss_time_ms': statistics.mean([s.duration_ms for s in cache_misses]) if cache_misses else 0
            }
        
        # Timing breakdown (if available)
        timing_snapshots = [s for s in snapshots if any([
            s.database_time_ms, s.network_time_ms, s.validation_time_ms
        ])]
        
        if timing_snapshots:
            stats['timing_breakdown'] = {
                'avg_database_time_ms': statistics.mean([
                    s.database_time_ms for s in timing_snapshots 
                    if s.database_time_ms is not None
                ]) if any(s.database_time_ms for s in timing_snapshots) else None,
                'avg_network_time_ms': statistics.mean([
                    s.network_time_ms for s in timing_snapshots 
                    if s.network_time_ms is not None
                ]) if any(s.network_time_ms for s in timing_snapshots) else None,
                'avg_validation_time_ms': statistics.mean([
                    s.validation_time_ms for s in timing_snapshots 
                    if s.validation_time_ms is not None
                ]) if any(s.validation_time_ms for s in timing_snapshots) else None
            }
        
        return stats
    
    def get_performance_trends(
        self,
        operations: Optional[List[str]] = None,
        time_window_minutes: Optional[int] = None
    ) -> List[PerformanceTrend]:
        """
        Analyze performance trends for operations.
        
        Args:
            operations: List of operations to analyze (default: all)
            time_window_minutes: Time window for trend analysis
            
        Returns:
            List of performance trends
        """
        if operations is None:
            operations = list(self.operation_snapshots.keys())
        
        time_window = time_window_minutes or self.trend_window_minutes
        trends = []
        
        for operation in operations:
            trend = self._calculate_trend(operation, time_window)
            if trend:
                trends.append(trend)
        
        return trends
    
    def _calculate_trend(self, operation: str, time_window_minutes: int) -> Optional[PerformanceTrend]:
        """Calculate performance trend for an operation."""
        # Check cache first
        cache_key = f"{operation}_{time_window_minutes}"
        if cache_key in self.cached_trends:
            trend, cached_at = self.cached_trends[cache_key]
            if datetime.utcnow() - cached_at < timedelta(minutes=self.trend_cache_ttl_minutes):
                return trend
        
        snapshots = self.operation_snapshots[operation]
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        recent_snapshots = [s for s in snapshots if s.timestamp >= cutoff_time]
        
        if len(recent_snapshots) < 10:  # Not enough data for trend analysis
            return None
        
        # Split into two halves for trend comparison
        mid_point = len(recent_snapshots) // 2
        first_half = recent_snapshots[:mid_point]
        second_half = recent_snapshots[mid_point:]
        
        # Calculate metrics for each half
        first_half_avg = statistics.mean([s.duration_ms for s in first_half])
        second_half_avg = statistics.mean([s.duration_ms for s in second_half])
        
        # Calculate trend
        trend_magnitude = ((second_half_avg - first_half_avg) / first_half_avg) * 100
        
        if abs(trend_magnitude) < 5:  # Less than 5% change
            trend_direction = 'stable'
        elif trend_magnitude > 0:
            trend_direction = 'degrading'
        else:
            trend_direction = 'improving'
            trend_magnitude = abs(trend_magnitude)
        
        # Calculate overall statistics
        all_durations = [s.duration_ms for s in recent_snapshots]
        successful_ops = [s for s in recent_snapshots if s.success]
        
        trend = PerformanceTrend(
            operation=operation,
            time_window_minutes=time_window_minutes,
            samples_count=len(recent_snapshots),
            average_duration_ms=statistics.mean(all_durations),
            median_duration_ms=statistics.median(all_durations),
            p95_duration_ms=sorted(all_durations)[int(0.95 * len(all_durations))],
            p99_duration_ms=sorted(all_durations)[int(0.99 * len(all_durations))],
            success_rate=len(successful_ops) / len(recent_snapshots) * 100,
            trend_direction=trend_direction,
            trend_magnitude=trend_magnitude
        )
        
        # Cache the result
        self.cached_trends[cache_key] = (trend, datetime.utcnow())
        
        return trend
    
    def detect_performance_anomalies(
        self,
        threshold_multiplier: float = 2.0,
        time_window_minutes: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Detect performance anomalies based on historical baselines.
        
        Args:
            threshold_multiplier: Multiplier for baseline to consider anomaly
            time_window_minutes: Time window to check for anomalies
            
        Returns:
            List of detected anomalies
        """
        anomalies = []
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        
        for operation, baseline in self.operation_baselines.items():
            if baseline['sample_count'] < 10:  # Not enough baseline data
                continue
            
            recent_snapshots = [
                s for s in self.operation_snapshots[operation]
                if s.timestamp >= cutoff_time and s.success
            ]
            
            if not recent_snapshots:
                continue
            
            baseline_duration = baseline['average_duration_ms']
            threshold = baseline_duration * threshold_multiplier
            
            for snapshot in recent_snapshots:
                if snapshot.duration_ms > threshold:
                    anomalies.append({
                        'operation': operation,
                        'timestamp': snapshot.timestamp,
                        'duration_ms': snapshot.duration_ms,
                        'baseline_ms': baseline_duration,
                        'threshold_ms': threshold,
                        'severity': 'high' if snapshot.duration_ms > threshold * 1.5 else 'medium',
                        'metadata': snapshot.metadata
                    })
        
        return sorted(anomalies, key=lambda x: x['timestamp'], reverse=True)
    
    def get_optimization_recommendations(self) -> List[OptimizationRecommendation]:
        """
        Generate optimization recommendations based on performance analysis.
        
        Returns:
            List of optimization recommendations
        """
        recommendations = []
        
        # Analyze each operation
        for operation in self.operation_snapshots.keys():
            perf_stats = self.get_operation_performance(operation, 60)  # Last hour
            
            if perf_stats['sample_count'] < 10:
                continue
            
            # Check cache hit rate
            cache_stats = perf_stats.get('cache_stats')
            if cache_stats and cache_stats['cache_hit_rate'] < 70:
                recommendations.append(OptimizationRecommendation(
                    category='caching',
                    priority='high',
                    title=f'Improve cache hit rate for {operation}',
                    description=f'Cache hit rate is {cache_stats["cache_hit_rate"]:.1f}%, consider increasing cache TTL or size',
                    impact='High - can reduce response times by 50-80%',
                    effort='Low - configuration change',
                    metrics={
                        'current_hit_rate': cache_stats['cache_hit_rate'],
                        'cache_hits': cache_stats['cache_hits'],
                        'cache_misses': cache_stats['cache_misses']
                    }
                ))
            
            # Check average response time
            avg_duration = perf_stats['duration_stats']['average_ms']
            if avg_duration > 1000:  # Slower than 1 second
                recommendations.append(OptimizationRecommendation(
                    category='performance',
                    priority='medium' if avg_duration < 2000 else 'high',
                    title=f'Optimize {operation} performance',
                    description=f'Average response time is {avg_duration:.0f}ms, consider query optimization or connection pooling',
                    impact='Medium - can reduce response times by 20-40%',
                    effort='Medium - code optimization required',
                    metrics={
                        'average_duration_ms': avg_duration,
                        'p95_duration_ms': perf_stats['duration_stats'].get('p95_ms'),
                        'success_rate': perf_stats['success_rate']
                    }
                ))
            
            # Check success rate
            if perf_stats['success_rate'] < 95:
                recommendations.append(OptimizationRecommendation(
                    category='reliability',
                    priority='high',
                    title=f'Improve {operation} reliability',
                    description=f'Success rate is {perf_stats["success_rate"]:.1f}%, investigate error causes and add retry logic',
                    impact='High - improves system reliability',
                    effort='Medium - error handling improvements',
                    metrics={
                        'success_rate': perf_stats['success_rate'],
                        'sample_count': perf_stats['sample_count']
                    }
                ))
        
        # Check overall system metrics
        cache_metrics = self.metrics_collector.get_cache_metrics()
        if cache_metrics.get('memory_usage_mb', 0) > 200:
            recommendations.append(OptimizationRecommendation(
                category='memory',
                priority='medium',
                title='Optimize memory usage',
                description=f'Cache memory usage is {cache_metrics["memory_usage_mb"]:.1f}MB, consider reducing cache size',
                impact='Medium - reduces memory pressure',
                effort='Low - configuration change',
                metrics=cache_metrics
            ))
        
        # Sort by priority
        priority_order = {'high': 3, 'medium': 2, 'low': 1}
        recommendations.sort(key=lambda x: priority_order.get(x.priority, 0), reverse=True)
        
        return recommendations
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        total_snapshots = len(self.snapshots)
        if total_snapshots == 0:
            return {'message': 'No performance data available'}
        
        # Overall statistics
        all_durations = [s.duration_ms for s in self.snapshots]
        successful_ops = [s for s in self.snapshots if s.success]
        
        # Recent performance (last hour)
        recent_cutoff = datetime.utcnow() - timedelta(hours=1)
        recent_snapshots = [s for s in self.snapshots if s.timestamp >= recent_cutoff]
        
        summary = {
            'total_operations_tracked': total_snapshots,
            'operations_last_hour': len(recent_snapshots),
            'overall_success_rate': len(successful_ops) / total_snapshots * 100,
            'overall_performance': {
                'average_duration_ms': statistics.mean(all_durations),
                'median_duration_ms': statistics.median(all_durations),
                'p95_duration_ms': sorted(all_durations)[int(0.95 * len(all_durations))] if len(all_durations) >= 20 else None
            },
            'operations_monitored': list(self.operation_snapshots.keys()),
            'baseline_operations': len(self.operation_baselines),
            'recent_anomalies_count': len(self.detect_performance_anomalies(time_window_minutes=60)),
            'recommendations_count': len(self.get_optimization_recommendations())
        }
        
        return summary
