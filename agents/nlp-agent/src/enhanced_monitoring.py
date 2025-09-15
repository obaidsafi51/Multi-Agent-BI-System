"""
Enhanced monitoring and analytics system for the NLP Agent with comprehensive
performance tracking, real-time metrics, and intelligent alerting capabilities.
"""

import asyncio
import json
import time
import logging
from typing import Any, Dict, List, Optional, Callable, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from collections import deque
import statistics

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(Enum):
    """Types of metrics to track"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class MetricValue:
    """Individual metric value with metadata"""
    value: float
    timestamp: datetime
    labels: Dict[str, str]
    metadata: Dict[str, Any]


@dataclass
class Alert:
    """Alert information"""
    id: str
    level: AlertLevel
    message: str
    metric_name: str
    threshold_value: float
    actual_value: float
    timestamp: datetime
    acknowledged: bool = False
    resolved: bool = False
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "level": self.level.value,
            "message": self.message,
            "metric_name": self.metric_name,
            "threshold_value": self.threshold_value,
            "actual_value": self.actual_value,
            "timestamp": self.timestamp.isoformat(),
            "acknowledged": self.acknowledged,
            "resolved": self.resolved,
            "metadata": self.metadata or {}
        }


@dataclass
class PerformanceSnapshot:
    """Point-in-time performance snapshot"""
    timestamp: datetime
    response_time_ms: float
    cache_hit_rate: float
    websocket_connected: bool
    active_requests: int
    memory_usage_mb: float
    cpu_usage_percent: float
    error_rate: float
    throughput_qps: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ThresholdRule:
    """Threshold-based alerting rule"""
    
    def __init__(
        self,
        name: str,
        metric_name: str,
        operator: str,  # "gt", "lt", "eq", "gte", "lte"
        threshold: float,
        alert_level: AlertLevel,
        duration_seconds: float = 0,  # How long threshold must be breached
        message_template: str = None
    ):
        self.name = name
        self.metric_name = metric_name
        self.operator = operator
        self.threshold = threshold
        self.alert_level = alert_level
        self.duration_seconds = duration_seconds
        self.message_template = message_template or f"{metric_name} {operator} {threshold}"
        
        # State tracking
        self.breach_start_time: Optional[datetime] = None
        self.last_alert_time: Optional[datetime] = None
        self.alert_cooldown = 300  # 5 minutes between similar alerts
    
    def evaluate(self, value: float) -> Optional[Alert]:
        """Evaluate rule against value and return alert if triggered"""
        now = datetime.now()
        breached = self._check_threshold(value)
        
        if breached:
            if not self.breach_start_time:
                self.breach_start_time = now
            
            # Check if duration requirement is met
            breach_duration = (now - self.breach_start_time).total_seconds()
            if breach_duration >= self.duration_seconds:
                # Check cooldown period
                if (not self.last_alert_time or 
                    (now - self.last_alert_time).total_seconds() >= self.alert_cooldown):
                    
                    alert = Alert(
                        id=f"{self.name}_{int(time.time())}",
                        level=self.alert_level,
                        message=self.message_template.format(
                            metric_name=self.metric_name,
                            value=value,
                            threshold=self.threshold,
                            operator=self.operator
                        ),
                        metric_name=self.metric_name,
                        threshold_value=self.threshold,
                        actual_value=value,
                        timestamp=now,
                        metadata={
                            "rule_name": self.name,
                            "breach_duration_seconds": breach_duration
                        }
                    )
                    
                    self.last_alert_time = now
                    return alert
        else:
            # Reset breach tracking if threshold is no longer breached
            self.breach_start_time = None
        
        return None
    
    def _check_threshold(self, value: float) -> bool:
        """Check if value breaches threshold"""
        if self.operator == "gt":
            return value > self.threshold
        elif self.operator == "gte":
            return value >= self.threshold
        elif self.operator == "lt":
            return value < self.threshold
        elif self.operator == "lte":
            return value <= self.threshold
        elif self.operator == "eq":
            return value == self.threshold
        else:
            return False


class EnhancedMonitoringSystem:
    """
    Enhanced monitoring system with:
    - Real-time performance metrics collection
    - Intelligent alerting with threshold rules
    - Historical trend analysis
    - Performance anomaly detection
    - Comprehensive health dashboard
    - Export capabilities for external monitoring systems
    """
    
    def __init__(
        self,
        metrics_retention_hours: int = 24,
        snapshot_interval_seconds: int = 30,
        alert_handlers: Optional[List[Callable]] = None,
        enable_anomaly_detection: bool = True,
        performance_baseline_hours: int = 1
    ):
        # Configuration
        self.metrics_retention_hours = metrics_retention_hours
        self.snapshot_interval_seconds = snapshot_interval_seconds
        self.enable_anomaly_detection = enable_anomaly_detection
        self.performance_baseline_hours = performance_baseline_hours
        
        # Metrics storage
        self.metrics: Dict[str, deque] = {}
        self.metric_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Performance snapshots
        self.performance_snapshots: deque = deque(maxlen=24*60*60//snapshot_interval_seconds)  # 24 hours
        
        # Alerting
        self.threshold_rules: List[ThresholdRule] = []
        self.active_alerts: List[Alert] = []
        self.alert_history: deque = deque(maxlen=1000)  # Keep last 1000 alerts
        self.alert_handlers = alert_handlers or []
        
        # Background tasks
        self.monitoring_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        self.anomaly_detection_task: Optional[asyncio.Task] = None
        
        # Performance tracking
        self.start_time = datetime.now()
        self.request_counter = 0
        self.error_counter = 0
        self.last_throughput_calculation = time.time()
        self.last_request_count = 0
        
        # Setup default alerting rules
        self._setup_default_alert_rules()
        
        logger.info("Enhanced monitoring system initialized")
    
    def _setup_default_alert_rules(self):
        """Setup default alerting rules"""
        default_rules = [
            ThresholdRule(
                name="high_response_time",
                metric_name="response_time_ms",
                operator="gt",
                threshold=5000,  # 5 seconds
                alert_level=AlertLevel.WARNING,
                duration_seconds=60,  # 1 minute
                message_template="High response time: {value:.1f}ms > {threshold}ms"
            ),
            ThresholdRule(
                name="very_high_response_time",
                metric_name="response_time_ms",
                operator="gt",
                threshold=10000,  # 10 seconds
                alert_level=AlertLevel.ERROR,
                duration_seconds=30,
                message_template="Very high response time: {value:.1f}ms > {threshold}ms"
            ),
            ThresholdRule(
                name="low_cache_hit_rate",
                metric_name="cache_hit_rate",
                operator="lt",
                threshold=0.3,  # 30%
                alert_level=AlertLevel.WARNING,
                duration_seconds=300,  # 5 minutes
                message_template="Low cache hit rate: {value:.2f} < {threshold:.2f}"
            ),
            ThresholdRule(
                name="websocket_disconnected",
                metric_name="websocket_connected",
                operator="eq",
                threshold=0,
                alert_level=AlertLevel.ERROR,
                duration_seconds=30,
                message_template="WebSocket connection lost"
            ),
            ThresholdRule(
                name="high_error_rate",
                metric_name="error_rate",
                operator="gt",
                threshold=0.1,  # 10%
                alert_level=AlertLevel.ERROR,
                duration_seconds=60,
                message_template="High error rate: {value:.2f} > {threshold:.2f}"
            ),
            ThresholdRule(
                name="low_throughput",
                metric_name="throughput_qps",
                operator="lt",
                threshold=0.1,  # 0.1 queries per second
                alert_level=AlertLevel.WARNING,
                duration_seconds=600,  # 10 minutes
                message_template="Low throughput: {value:.2f} QPS < {threshold:.2f} QPS"
            )
        ]
        
        self.threshold_rules.extend(default_rules)
    
    async def start(self):
        """Start monitoring system"""
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        if self.enable_anomaly_detection:
            self.anomaly_detection_task = asyncio.create_task(self._anomaly_detection_loop())
        
        logger.info("Enhanced monitoring system started")
    
    async def stop(self):
        """Stop monitoring system"""
        tasks = [self.monitoring_task, self.cleanup_task, self.anomaly_detection_task]
        
        for task in tasks:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        logger.info("Enhanced monitoring system stopped")
    
    def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        labels: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record a metric value"""
        if name not in self.metrics:
            self.metrics[name] = deque(maxlen=self.metrics_retention_hours * 3600 // 10)  # 10-second resolution
            self.metric_metadata[name] = {
                "type": metric_type.value,
                "created_at": datetime.now().isoformat()
            }
        
        metric_value = MetricValue(
            value=value,
            timestamp=datetime.now(),
            labels=labels or {},
            metadata=metadata or {}
        )
        
        self.metrics[name].append(metric_value)
    
    def increment_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment a counter metric"""
        # Get current value if exists
        current_value = 0.0
        if name in self.metrics and self.metrics[name]:
            current_value = self.metrics[name][-1].value
        
        self.record_metric(
            name=name,
            value=current_value + value,
            metric_type=MetricType.COUNTER,
            labels=labels
        )
    
    def record_timer(self, name: str, duration_seconds: float, labels: Optional[Dict[str, str]] = None):
        """Record a timer metric"""
        self.record_metric(
            name=name,
            value=duration_seconds * 1000,  # Convert to milliseconds
            metric_type=MetricType.TIMER,
            labels=labels
        )
    
    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a histogram metric"""
        self.record_metric(
            name=name,
            value=value,
            metric_type=MetricType.HISTOGRAM,
            labels=labels
        )
    
    def get_metric_values(
        self,
        name: str,
        duration_minutes: Optional[int] = None
    ) -> List[MetricValue]:
        """Get metric values for the specified duration"""
        if name not in self.metrics:
            return []
        
        values = list(self.metrics[name])
        
        if duration_minutes:
            cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
            values = [v for v in values if v.timestamp >= cutoff_time]
        
        return values
    
    def get_metric_stats(
        self,
        name: str,
        duration_minutes: int = 60
    ) -> Optional[Dict[str, float]]:
        """Get statistical summary of metric"""
        values = self.get_metric_values(name, duration_minutes)
        
        if not values:
            return None
        
        metric_values = [v.value for v in values]
        
        return {
            "count": len(metric_values),
            "min": min(metric_values),
            "max": max(metric_values),
            "mean": statistics.mean(metric_values),
            "median": statistics.median(metric_values),
            "std_dev": statistics.stdev(metric_values) if len(metric_values) > 1 else 0.0,
            "percentile_95": self._percentile(metric_values, 0.95),
            "percentile_99": self._percentile(metric_values, 0.99)
        }
    
    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile value"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int(percentile * len(sorted_values))
        index = min(index, len(sorted_values) - 1)
        return sorted_values[index]
    
    async def capture_performance_snapshot(
        self,
        response_time_ms: float,
        cache_hit_rate: float,
        websocket_connected: bool,
        active_requests: int,
        memory_usage_mb: float = 0.0,
        cpu_usage_percent: float = 0.0
    ) -> PerformanceSnapshot:
        """Capture a comprehensive performance snapshot"""
        # Calculate error rate
        total_requests = self.request_counter
        error_rate = self.error_counter / max(total_requests, 1)
        
        # Calculate throughput
        now = time.time()
        time_diff = now - self.last_throughput_calculation
        request_diff = total_requests - self.last_request_count
        throughput_qps = request_diff / max(time_diff, 1)
        
        self.last_throughput_calculation = now
        self.last_request_count = total_requests
        
        snapshot = PerformanceSnapshot(
            timestamp=datetime.now(),
            response_time_ms=response_time_ms,
            cache_hit_rate=cache_hit_rate,
            websocket_connected=websocket_connected,
            active_requests=active_requests,
            memory_usage_mb=memory_usage_mb,
            cpu_usage_percent=cpu_usage_percent,
            error_rate=error_rate,
            throughput_qps=throughput_qps
        )
        
        self.performance_snapshots.append(snapshot)
        
        # Record individual metrics
        self.record_metric("response_time_ms", response_time_ms, MetricType.TIMER)
        self.record_metric("cache_hit_rate", cache_hit_rate, MetricType.GAUGE)
        self.record_metric("websocket_connected", 1 if websocket_connected else 0, MetricType.GAUGE)
        self.record_metric("active_requests", active_requests, MetricType.GAUGE)
        self.record_metric("error_rate", error_rate, MetricType.GAUGE)
        self.record_metric("throughput_qps", throughput_qps, MetricType.GAUGE)
        
        # Evaluate alerting rules
        await self._evaluate_alert_rules(snapshot)
        
        return snapshot
    
    async def _evaluate_alert_rules(self, snapshot: PerformanceSnapshot):
        """Evaluate all alerting rules against performance snapshot"""
        snapshot_dict = snapshot.to_dict()
        
        for rule in self.threshold_rules:
            if rule.metric_name in snapshot_dict:
                value = snapshot_dict[rule.metric_name]
                alert = rule.evaluate(value)
                
                if alert:
                    await self._handle_alert(alert)
    
    async def _handle_alert(self, alert: Alert):
        """Handle triggered alert"""
        self.active_alerts.append(alert)
        self.alert_history.append(alert)
        
        logger.warning(f"Alert triggered: {alert.message}")
        
        # Call alert handlers
        for handler in self.alert_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler: {e}")
    

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an active alert"""
        for alert in self.active_alerts:
            if alert.id == alert_id and not alert.acknowledged:
                alert.acknowledged = True
                logger.info(f"Alert acknowledged: {alert_id}")
                return True
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an active alert"""
        for i, alert in enumerate(self.active_alerts):
            if alert.id == alert_id:
                alert.resolved = True
                # Move to history and remove from active
                if alert not in self.alert_history:
                    self.alert_history.append(alert)
                del self.active_alerts[i]
                logger.info(f"Alert resolved: {alert_id}")
                return True
        return False
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        now = datetime.now()
        uptime_seconds = (now - self.start_time).total_seconds()
        
        # Get recent performance stats
        recent_snapshots = [
            s for s in self.performance_snapshots
            if (now - s.timestamp).total_seconds() <= 300  # Last 5 minutes
        ]
        
        avg_response_time = 0.0
        avg_cache_hit_rate = 0.0
        websocket_status = False
        avg_error_rate = 0.0
        avg_throughput = 0.0
        
        if recent_snapshots:
            avg_response_time = sum(s.response_time_ms for s in recent_snapshots) / len(recent_snapshots)
            avg_cache_hit_rate = sum(s.cache_hit_rate for s in recent_snapshots) / len(recent_snapshots)
            websocket_status = any(s.websocket_connected for s in recent_snapshots)
            avg_error_rate = sum(s.error_rate for s in recent_snapshots) / len(recent_snapshots)
            avg_throughput = sum(s.throughput_qps for s in recent_snapshots) / len(recent_snapshots)
        
        # Calculate overall health score
        health_score = self._calculate_health_score(
            avg_response_time, avg_cache_hit_rate, websocket_status, avg_error_rate
        )
        
        return {
            "status": "healthy" if health_score > 0.7 else "degraded" if health_score > 0.4 else "unhealthy",
            "health_score": health_score,
            "uptime_seconds": uptime_seconds,
            "timestamp": now.isoformat(),
            "metrics": {
                "avg_response_time_ms": avg_response_time,
                "avg_cache_hit_rate": avg_cache_hit_rate,
                "websocket_connected": websocket_status,
                "avg_error_rate": avg_error_rate,
                "avg_throughput_qps": avg_throughput,
                "total_requests": self.request_counter,
                "total_errors": self.error_counter
            },
            "alerts": {
                "active_count": len(self.active_alerts),
                "active_critical": len([a for a in self.active_alerts if a.level == AlertLevel.CRITICAL]),
                "active_errors": len([a for a in self.active_alerts if a.level == AlertLevel.ERROR]),
                "active_warnings": len([a for a in self.active_alerts if a.level == AlertLevel.WARNING])
            },
            "performance_trend": self._get_performance_trend()
        }
    
    def _calculate_health_score(
        self,
        response_time: float,
        cache_hit_rate: float,
        websocket_connected: bool,
        error_rate: float
    ) -> float:
        """Calculate overall health score (0.0 to 1.0)"""
        score = 0.0
        
        # Response time score (0.3 weight)
        if response_time <= 1000:  # <= 1s is excellent
            score += 0.3
        elif response_time <= 3000:  # <= 3s is good
            score += 0.2
        elif response_time <= 5000:  # <= 5s is okay
            score += 0.1
        
        # Cache hit rate score (0.2 weight)
        if cache_hit_rate >= 0.7:  # >= 70% is excellent
            score += 0.2
        elif cache_hit_rate >= 0.5:  # >= 50% is good
            score += 0.15
        elif cache_hit_rate >= 0.3:  # >= 30% is okay
            score += 0.1
        
        # WebSocket connection score (0.3 weight)
        if websocket_connected:
            score += 0.3
        
        # Error rate score (0.2 weight)
        if error_rate <= 0.01:  # <= 1% is excellent
            score += 0.2
        elif error_rate <= 0.05:  # <= 5% is good
            score += 0.15
        elif error_rate <= 0.1:  # <= 10% is okay
            score += 0.1
        
        return min(score, 1.0)
    
    def _get_performance_trend(self) -> str:
        """Get performance trend analysis"""
        if len(self.performance_snapshots) < 10:
            return "insufficient_data"
        
        # Compare recent vs historical performance
        recent_snapshots = list(self.performance_snapshots)[-10:]  # Last 10 snapshots
        historical_snapshots = list(self.performance_snapshots)[-30:-10] if len(self.performance_snapshots) >= 30 else []
        
        if not historical_snapshots:
            return "insufficient_data"
        
        # Calculate average response times
        recent_avg = sum(s.response_time_ms for s in recent_snapshots) / len(recent_snapshots)
        historical_avg = sum(s.response_time_ms for s in historical_snapshots) / len(historical_snapshots)
        
        # Determine trend
        improvement_threshold = 0.1  # 10% improvement/degradation
        if recent_avg < historical_avg * (1 - improvement_threshold):
            return "improving"
        elif recent_avg > historical_avg * (1 + improvement_threshold):
            return "degrading"
        else:
            return "stable"
    
    async def _monitoring_loop(self):
        """Background monitoring loop"""
        while True:
            try:
                await asyncio.sleep(self.snapshot_interval_seconds)
                
                # This would be called by the main application
                # For now, just maintain the loop structure
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
    
    async def _cleanup_loop(self):
        """Background cleanup loop"""
        while True:
            try:
                await asyncio.sleep(3600)  # Cleanup every hour
                
                cutoff_time = datetime.now() - timedelta(hours=self.metrics_retention_hours)
                
                # Cleanup old metrics
                for metric_name, metric_values in self.metrics.items():
                    # Remove old values
                    while metric_values and metric_values[0].timestamp < cutoff_time:
                        metric_values.popleft()
                
                # Cleanup resolved alerts older than 24 hours
                alert_cutoff = datetime.now() - timedelta(hours=24)
                self.alert_history = deque(
                    [a for a in self.alert_history if a.timestamp >= alert_cutoff],
                    maxlen=1000
                )
                
                logger.debug("Completed monitoring data cleanup")
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    async def _anomaly_detection_loop(self):
        """Background anomaly detection loop"""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                # Perform anomaly detection
                await self._detect_anomalies()
                
            except Exception as e:
                logger.error(f"Error in anomaly detection loop: {e}")
    
    async def _detect_anomalies(self):
        """Detect performance anomalies"""
        if len(self.performance_snapshots) < 20:
            return  # Need sufficient data
        
        # Get baseline performance (historical average)
        baseline_end = datetime.now() - timedelta(minutes=30)
        baseline_start = baseline_end - timedelta(hours=self.performance_baseline_hours)
        
        baseline_snapshots = [
            s for s in self.performance_snapshots
            if baseline_start <= s.timestamp <= baseline_end
        ]
        
        if len(baseline_snapshots) < 10:
            return  # Insufficient baseline data
        
        # Get recent performance
        recent_snapshots = [
            s for s in self.performance_snapshots
            if (datetime.now() - s.timestamp).total_seconds() <= 300  # Last 5 minutes
        ]
        
        if len(recent_snapshots) < 3:
            return
        
        # Calculate baseline metrics
        baseline_response_time = sum(s.response_time_ms for s in baseline_snapshots) / len(baseline_snapshots)
        baseline_std = statistics.stdev([s.response_time_ms for s in baseline_snapshots])
        
        # Calculate recent metrics
        recent_response_time = sum(s.response_time_ms for s in recent_snapshots) / len(recent_snapshots)
        
        # Detect anomalies (response time significantly higher than baseline)
        anomaly_threshold = baseline_response_time + (2 * baseline_std)  # 2 standard deviations
        
        if recent_response_time > anomaly_threshold:
            anomaly_alert = Alert(
                id=f"anomaly_{int(time.time())}",
                level=AlertLevel.WARNING,
                message=f"Performance anomaly detected: Response time {recent_response_time:.1f}ms is significantly higher than baseline {baseline_response_time:.1f}ms",
                metric_name="response_time_anomaly",
                threshold_value=anomaly_threshold,
                actual_value=recent_response_time,
                timestamp=datetime.now(),
                metadata={
                    "anomaly_type": "response_time_spike",
                    "baseline_response_time": baseline_response_time,
                    "baseline_std_dev": baseline_std
                }
            )
            
            await self._handle_alert(anomaly_alert)
    
    def export_metrics(self, format_type: str = "json") -> str:
        """Export metrics in various formats"""
        if format_type == "json":
            return self._export_json()
        elif format_type == "prometheus":
            return self._export_prometheus()
        else:
            raise ValueError(f"Unsupported export format: {format_type}")
    
    def _export_json(self) -> str:
        """Export metrics as JSON"""
        export_data = {
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "metrics": {},
            "alerts": {
                "active": [a.to_dict() for a in self.active_alerts],
                "history": [a.to_dict() for a in list(self.alert_history)[-50:]]  # Last 50 alerts
            },
            "health": self.get_health_status()
        }
        
        # Export last 100 values for each metric
        for metric_name, metric_values in self.metrics.items():
            recent_values = list(metric_values)[-100:]  # Last 100 values
            export_data["metrics"][metric_name] = [
                {
                    "value": v.value,
                    "timestamp": v.timestamp.isoformat(),
                    "labels": v.labels,
                    "metadata": v.metadata
                }
                for v in recent_values
            ]
        
        return json.dumps(export_data, indent=2)
    
    def _export_prometheus(self) -> str:
        """Export metrics in Prometheus format"""
        output = []
        
        for metric_name, metric_values in self.metrics.items():
            if not metric_values:
                continue
            
            latest_value = metric_values[-1]
            metric_type = self.metric_metadata.get(metric_name, {}).get("type", "gauge")
            
            # Add metric help and type
            output.append(f"# HELP nlp_agent_{metric_name} NLP Agent metric")
            output.append(f"# TYPE nlp_agent_{metric_name} {metric_type}")
            
            # Add metric value with labels
            labels = []
            for key, value in latest_value.labels.items():
                labels.append(f'{key}="{value}"')
            
            label_str = "{" + ",".join(labels) + "}" if labels else ""
            output.append(f"nlp_agent_{metric_name}{label_str} {latest_value.value}")
        
        return "\n".join(output)
    
    # Context manager methods for tracking request performance
    def track_request(self):
        """Context manager for tracking request performance"""
        return RequestTracker(self)


class RequestTracker:
    """Context manager for tracking individual request performance"""
    
    def __init__(self, monitoring_system: EnhancedMonitoringSystem):
        self.monitoring_system = monitoring_system
        self.start_time = None
    
    async def __aenter__(self):
        self.start_time = time.time()
        self.monitoring_system.increment_counter("requests_started")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        
        self.monitoring_system.increment_counter("requests_completed")
        self.monitoring_system.record_timer("request_duration", duration)
        self.monitoring_system.request_counter += 1
        
        if exc_type is not None:
            self.monitoring_system.increment_counter("requests_failed")
            self.monitoring_system.error_counter += 1
        
        return False  # Don't suppress exceptions
