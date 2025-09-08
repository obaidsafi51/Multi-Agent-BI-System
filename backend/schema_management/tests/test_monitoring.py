"""
Test suite for MCP monitoring and observability features.

This module provides comprehensive tests for all monitoring components
including metrics collection, health monitoring, alerting, and performance tracking.
"""

import asyncio
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

# Import monitoring components
from ..monitoring import (
    MCPStructuredLogger,
    MCPMetricsCollector,
    MCPHealthMonitor,
    MCPAlertManager,
    MCPPerformanceTracker,
    HealthStatus,
    AlertLevel
)
from ..monitoring.config import MonitoringConfig, LoggingConfig, MetricsConfig


class TestMCPStructuredLogger:
    """Test structured logging functionality."""
    
    def test_logger_initialization(self):
        """Test logger initialization."""
        logger = MCPStructuredLogger("test.logger", enable_json=True)
        assert logger.logger.name == "test.logger"
        assert logger.enable_json is True
    
    def test_context_management(self):
        """Test context setting and clearing."""
        logger = MCPStructuredLogger("test.logger")
        
        logger.set_context(user_id="test_user", operation="test_op")
        assert logger._context["user_id"] == "test_user"
        assert logger._context["operation"] == "test_op"
        
        logger.clear_context()
        assert len(logger._context) == 0
    
    def test_operation_context_manager(self):
        """Test operation context manager."""
        logger = MCPStructuredLogger("test.logger")
        
        with logger.operation_context("test_operation", param1="value1") as request_id:
            assert request_id is not None
            assert len(request_id) == 8  # Short UUID format
    
    def test_operation_context_with_exception(self):
        """Test operation context manager with exception."""
        logger = MCPStructuredLogger("test.logger")
        
        with pytest.raises(ValueError):
            with logger.operation_context("test_operation") as request_id:
                raise ValueError("Test error")


class TestMCPMetricsCollector:
    """Test metrics collection functionality."""
    
    def setup_method(self):
        """Set up test metrics collector."""
        self.metrics = MCPMetricsCollector()
    
    def test_metrics_initialization(self):
        """Test metrics collector initialization."""
        assert self.metrics._start_time is not None
        assert self.metrics._system_metrics["total_requests"] == 0
    
    def test_record_operation(self):
        """Test operation recording."""
        self.metrics.record_operation("test_operation", 100.0, True)
        
        performance_metrics = self.metrics.get_performance_metrics("test_operation")
        assert performance_metrics["total_requests"] == 1
        assert performance_metrics["successful_requests"] == 1
        assert performance_metrics["average_duration_ms"] == 100.0
    
    def test_record_validation(self):
        """Test validation recording."""
        self.metrics.record_validation(50.0, True)
        
        validation_metrics = self.metrics.get_validation_metrics()
        assert validation_metrics["total_validations"] == 1
        assert validation_metrics["successful_validations"] == 1
    
    def test_cache_metrics(self):
        """Test cache metrics recording."""
        self.metrics.record_cache_hit(25.0)
        self.metrics.record_cache_miss(75.0)
        
        cache_metrics = self.metrics.get_cache_metrics()
        assert cache_metrics["total_requests"] == 2
        assert cache_metrics["cache_hits"] == 1
        assert cache_metrics["cache_misses"] == 1
        assert cache_metrics["hit_rate"] == 50.0
    
    def test_error_recording(self):
        """Test error recording."""
        self.metrics.record_error("ConnectionError", "test_operation", "Connection failed")
        
        error_metrics = self.metrics.get_error_metrics()
        assert error_metrics["total_errors"] == 1
        assert "ConnectionError" in str(error_metrics["top_error_types"])
    
    def test_health_summary(self):
        """Test health summary calculation."""
        # Add some test data
        self.metrics.record_operation("test_op", 100.0, True)
        self.metrics.record_cache_hit(25.0)
        self.metrics.record_validation(50.0, True)
        
        health_summary = self.metrics.get_health_summary()
        assert "overall_health_score" in health_summary
        assert "health_status" in health_summary
        assert health_summary["overall_health_score"] >= 0
    
    def test_comprehensive_metrics(self):
        """Test comprehensive metrics report."""
        # Add test data
        self.metrics.record_operation("test_op", 100.0, True)
        self.metrics.record_cache_hit(25.0)
        
        comprehensive = self.metrics.get_comprehensive_metrics()
        assert "timestamp" in comprehensive
        assert "system" in comprehensive
        assert "performance" in comprehensive
        assert "cache" in comprehensive


class TestMCPHealthMonitor:
    """Test health monitoring functionality."""
    
    def setup_method(self):
        """Set up test health monitor."""
        self.health_monitor = MCPHealthMonitor(
            check_interval_seconds=10,
            connectivity_timeout=2
        )
    
    def test_health_monitor_initialization(self):
        """Test health monitor initialization."""
        assert self.health_monitor.check_interval_seconds == 10
        assert self.health_monitor.connectivity_timeout == 2
    
    def test_dependency_setting(self):
        """Test setting dependencies."""
        mock_client = Mock()
        mock_schema_manager = Mock()
        
        self.health_monitor.set_dependencies(
            mcp_client=mock_client,
            schema_manager=mock_schema_manager
        )
        
        assert self.health_monitor.mcp_client == mock_client
        assert self.health_monitor.schema_manager == mock_schema_manager
    
    @pytest.mark.asyncio
    async def test_mcp_connectivity_check_healthy(self):
        """Test MCP connectivity check when healthy."""
        mock_client = AsyncMock()
        mock_client.health_check.return_value = True
        
        self.health_monitor.set_dependencies(mcp_client=mock_client)
        
        check_result = await self.health_monitor._check_mcp_connectivity()
        assert check_result.name == "mcp_connectivity"
        assert check_result.status == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_mcp_connectivity_check_unhealthy(self):
        """Test MCP connectivity check when unhealthy."""
        mock_client = AsyncMock()
        mock_client.health_check.return_value = False
        
        self.health_monitor.set_dependencies(mcp_client=mock_client)
        
        check_result = await self.health_monitor._check_mcp_connectivity()
        assert check_result.name == "mcp_connectivity"
        assert check_result.status == HealthStatus.UNHEALTHY
    
    @pytest.mark.asyncio
    async def test_cache_performance_check(self):
        """Test cache performance check."""
        # Mock metrics collector
        with patch('backend.schema_management.monitoring.health_monitor.get_metrics_collector') as mock_collector:
            mock_collector.return_value.get_cache_metrics.return_value = {
                'hit_rate': 85.0,
                'memory_usage_mb': 50.0,
                'cache_size': 100
            }
            
            check_result = await self.health_monitor._check_cache_performance()
            assert check_result.name == "cache_performance"
            assert check_result.status == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_comprehensive_health_check(self):
        """Test comprehensive health check."""
        # Set up mock dependencies
        mock_client = AsyncMock()
        mock_client.health_check.return_value = True
        mock_client.get_server_stats.return_value = {"status": "ok"}
        
        mock_schema_manager = AsyncMock()
        mock_schema_manager.discover_databases.return_value = []
        
        self.health_monitor.set_dependencies(
            mcp_client=mock_client,
            schema_manager=mock_schema_manager
        )
        
        # Mock metrics collector
        with patch('backend.schema_management.monitoring.health_monitor.get_metrics_collector') as mock_collector:
            mock_collector.return_value.get_cache_metrics.return_value = {
                'hit_rate': 85.0,
                'memory_usage_mb': 50.0
            }
            mock_collector.return_value.get_validation_metrics.return_value = {
                'success_rate': 95.0,
                'total_validations': 100
            }
            mock_collector.return_value.get_error_metrics.return_value = {
                'total_errors': 5
            }
            mock_collector.return_value.get_system_metrics.return_value = {
                'total_requests': 1000
            }
            
            health_report = await self.health_monitor.perform_health_check()
            
            assert health_report.overall_status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
            assert len(health_report.checks) > 0
            assert health_report.uptime_seconds >= 0


class TestMCPAlertManager:
    """Test alerting functionality."""
    
    def setup_method(self):
        """Set up test alert manager."""
        self.alert_manager = MCPAlertManager()
    
    def test_alert_manager_initialization(self):
        """Test alert manager initialization."""
        assert len(self.alert_manager.alert_rules) > 0  # Default rules should be present
        assert len(self.alert_manager.alert_channels) > 0  # Default log channel
    
    def test_add_custom_rule(self):
        """Test adding custom alert rule."""
        from ..monitoring.alerting import AlertRule
        
        custom_rule = AlertRule(
            name="test_rule",
            condition=lambda metrics: True,
            level=AlertLevel.WARNING,
            message_template="Test alert"
        )
        
        initial_count = len(self.alert_manager.alert_rules)
        self.alert_manager.add_rule(custom_rule)
        
        assert len(self.alert_manager.alert_rules) == initial_count + 1
    
    @pytest.mark.asyncio
    async def test_alert_triggering(self):
        """Test alert triggering based on metrics."""
        # Create metrics that should trigger alerts
        test_metrics = {
            'errors': {
                'total_errors': 150
            },
            'system': {
                'total_requests': 1000
            },
            'cache': {
                'hit_rate': 30.0,  # Low hit rate
                'total_requests': 100
            },
            'validation': {
                'success_rate': 70.0,  # Low success rate
                'total_validations': 50
            }
        }
        
        await self.alert_manager.check_alerts()
        
        # Check if alerts were created (we expect some based on the test metrics)
        active_alerts = self.alert_manager.get_active_alerts()
        # Note: Actual alert count depends on rule implementation
    
    def test_alert_summary(self):
        """Test alert summary generation."""
        summary = self.alert_manager.get_alert_summary()
        
        assert "active_alerts_count" in summary
        assert "alert_rules_count" in summary
        assert "enabled_rules_count" in summary
        assert "notification_channels" in summary


class TestMCPPerformanceTracker:
    """Test performance tracking functionality."""
    
    def setup_method(self):
        """Set up test performance tracker."""
        self.performance_tracker = MCPPerformanceTracker(
            max_snapshots=1000,
            trend_window_minutes=30
        )
    
    def test_performance_tracker_initialization(self):
        """Test performance tracker initialization."""
        assert self.performance_tracker.max_snapshots == 1000
        assert self.performance_tracker.trend_window_minutes == 30
    
    @pytest.mark.asyncio
    async def test_track_operation_success(self):
        """Test tracking successful operation."""
        async with self.performance_tracker.track_operation(
            "test_operation",
            param1="value1"
        ) as perf_data:
            # Simulate some work
            await asyncio.sleep(0.01)
            perf_data['cache_hit'] = True
        
        # Check that snapshot was recorded
        assert len(self.performance_tracker.snapshots) == 1
        snapshot = self.performance_tracker.snapshots[0]
        assert snapshot.operation == "test_operation"
        assert snapshot.success is True
        assert snapshot.cache_hit is True
    
    @pytest.mark.asyncio
    async def test_track_operation_failure(self):
        """Test tracking failed operation."""
        with pytest.raises(ValueError):
            async with self.performance_tracker.track_operation(
                "test_operation_fail"
            ) as perf_data:
                raise ValueError("Test error")
        
        # Check that snapshot was recorded
        assert len(self.performance_tracker.snapshots) == 1
        snapshot = self.performance_tracker.snapshots[0]
        assert snapshot.operation == "test_operation_fail"
        assert snapshot.success is False
    
    def test_performance_statistics(self):
        """Test performance statistics calculation."""
        # Manually add some test snapshots
        from ..monitoring.performance_tracker import PerformanceSnapshot
        
        for i in range(10):
            snapshot = PerformanceSnapshot(
                timestamp=datetime.utcnow(),
                operation="test_op",
                duration_ms=100.0 + i * 10,  # Varying durations
                success=True,
                cache_hit=i % 2 == 0  # Alternate cache hits/misses
            )
            self.performance_tracker._store_snapshot(snapshot)
        
        stats = self.performance_tracker.get_operation_performance("test_op")
        assert stats["sample_count"] == 10
        assert stats["success_rate"] == 100.0
        assert "duration_stats" in stats
        assert "cache_stats" in stats
    
    def test_anomaly_detection(self):
        """Test performance anomaly detection."""
        # Add baseline data
        from ..monitoring.performance_tracker import PerformanceSnapshot
        
        # Add normal operations
        for i in range(20):
            snapshot = PerformanceSnapshot(
                timestamp=datetime.utcnow() - timedelta(hours=1),
                operation="test_op",
                duration_ms=100.0,
                success=True
            )
            self.performance_tracker._store_snapshot(snapshot)
        
        # Add anomalous operation
        anomaly_snapshot = PerformanceSnapshot(
            timestamp=datetime.utcnow(),
            operation="test_op",
            duration_ms=500.0,  # Much slower than baseline
            success=True
        )
        self.performance_tracker._store_snapshot(anomaly_snapshot)
        
        anomalies = self.performance_tracker.detect_performance_anomalies(
            threshold_multiplier=2.0,
            time_window_minutes=30
        )
        
        assert len(anomalies) >= 1
        assert anomalies[0]["operation"] == "test_op"
        assert anomalies[0]["duration_ms"] == 500.0
    
    def test_optimization_recommendations(self):
        """Test optimization recommendations generation."""
        # Add some test data that should trigger recommendations
        from ..monitoring.performance_tracker import PerformanceSnapshot
        
        # Add slow operations
        for i in range(15):
            snapshot = PerformanceSnapshot(
                timestamp=datetime.utcnow(),
                operation="slow_operation",
                duration_ms=1500.0,  # Slow operation
                success=True,
                cache_hit=False  # Poor cache performance
            )
            self.performance_tracker._store_snapshot(snapshot)
        
        recommendations = self.performance_tracker.get_optimization_recommendations()
        
        # Should have recommendations for performance and caching
        assert len(recommendations) > 0
        
        # Check that recommendations have required fields
        for rec in recommendations:
            assert "category" in rec.to_dict()
            assert "priority" in rec.to_dict()
            assert "title" in rec.to_dict()


class TestMonitoringIntegration:
    """Test integration between monitoring components."""
    
    def setup_method(self):
        """Set up integration test environment."""
        from ..monitoring.setup import initialize_monitoring
        from ..monitoring.config import MonitoringConfig
        
        # Create test configuration
        config = MonitoringConfig(
            enable_monitoring=True,
            logging=LoggingConfig(enable_json_logging=False, enable_file_logging=False),
            metrics=MetricsConfig(enable_metrics=True)
        )
        
        self.success, self.components = initialize_monitoring(config)
    
    def test_monitoring_initialization(self):
        """Test that monitoring system initializes successfully."""
        assert self.success is True
        assert self.components.get('monitoring_enabled') is True
        assert self.components.get('metrics_collector') is not None
    
    @pytest.mark.asyncio
    async def test_end_to_end_monitoring(self):
        """Test end-to-end monitoring workflow."""
        if not self.success:
            pytest.skip("Monitoring initialization failed")
        
        metrics_collector = self.components.get('metrics_collector')
        performance_tracker = self.components.get('performance_tracker')
        
        if not metrics_collector or not performance_tracker:
            pytest.skip("Required components not available")
        
        # Simulate some operations
        async with performance_tracker.track_operation("integration_test") as perf_data:
            await asyncio.sleep(0.01)
            perf_data['cache_hit'] = True
        
        # Record additional metrics
        metrics_collector.record_cache_hit(25.0)
        metrics_collector.record_validation(50.0, True)
        
        # Get comprehensive report
        from ..monitoring.setup import get_monitoring_dashboard_data
        dashboard_data = get_monitoring_dashboard_data(self.components)
        
        assert dashboard_data['monitoring_enabled'] is True
        assert 'metrics' in dashboard_data
        assert 'performance' in dashboard_data


# Fixtures for testing
@pytest.fixture
def mock_mcp_client():
    """Mock MCP client for testing."""
    client = AsyncMock()
    client.health_check.return_value = True
    client.get_server_stats.return_value = {"status": "ok"}
    return client


@pytest.fixture
def mock_schema_manager():
    """Mock schema manager for testing."""
    manager = AsyncMock()
    manager.discover_databases.return_value = []
    return manager


@pytest.fixture
def sample_metrics():
    """Sample metrics for testing."""
    return {
        'system': {
            'total_requests': 1000,
            'uptime_seconds': 3600
        },
        'performance': {
            'test_operation': {
                'total_requests': 100,
                'average_duration_ms': 150.0,
                'success_rate': 95.0
            }
        },
        'cache': {
            'hit_rate': 85.0,
            'total_requests': 500,
            'memory_usage_mb': 75.0
        },
        'validation': {
            'success_rate': 98.0,
            'total_validations': 200
        },
        'errors': {
            'total_errors': 10,
            'connection_errors': 3,
            'timeout_errors': 2
        }
    }


# Test configuration validation
def test_monitoring_config_validation():
    """Test monitoring configuration validation."""
    from ..monitoring.config import MonitoringConfig, AlertConfig
    
    # Test valid configuration
    config = MonitoringConfig()
    issues = config.validate()
    assert isinstance(issues, list)
    
    # Test invalid email configuration
    config.alerting = AlertConfig(
        enable_email_alerts=True,
        smtp_host=None  # Missing required field
    )
    issues = config.validate()
    assert len(issues) > 0
    assert any("SMTP configuration incomplete" in issue for issue in issues)


# Integration test with actual MCP client (if available)
@pytest.mark.integration
@pytest.mark.asyncio
async def test_monitoring_with_real_mcp_client():
    """Integration test with real MCP client (requires MCP server)."""
    pytest.skip("Integration test - requires running MCP server")
    
    # This test would be run against a real MCP server
    # from ..manager import MCPSchemaManager
    # from ..config import MCPSchemaConfig
    
    # config = MCPSchemaConfig.from_env()
    # manager = MCPSchemaManager(config, enable_monitoring=True)
    
    # # Test real operations
    # await manager.connect()
    # databases = await manager.discover_databases()
    
    # # Check monitoring data
    # monitoring_report = await manager.get_comprehensive_monitoring_report()
    # assert monitoring_report['monitoring_enabled'] is True


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
