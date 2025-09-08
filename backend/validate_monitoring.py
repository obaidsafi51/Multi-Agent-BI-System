#!/usr/bin/env python3
"""
Quick validation script for MCP monitoring system.

This script validates that all monitoring components are properly configured
and can be imported and initialized successfully.
"""

import sys
import os
import asyncio
from datetime import datetime

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Test that all monitoring components can be imported."""
    print("Testing imports...")
    
    try:
        from schema_management.monitoring import (
            MCPStructuredLogger,
            MCPMetricsCollector,
            MCPHealthMonitor,
            MCPAlertManager,
            MCPPerformanceTracker
        )
        print("✓ Core monitoring components imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import core components: {e}")
        return False
    
    try:
        from schema_management.monitoring.config import MonitoringConfig
        print("✓ Configuration classes imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import configuration: {e}")
        return False
    
    try:
        from schema_management.monitoring.setup import (
            initialize_monitoring,
            validate_monitoring_setup
        )
        print("✓ Setup utilities imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import setup utilities: {e}")
        return False
    
    return True

def test_basic_functionality():
    """Test basic functionality of monitoring components."""
    print("\nTesting basic functionality...")
    
    try:
        # Test logger
        from schema_management.monitoring import MCPStructuredLogger
        logger = MCPStructuredLogger("test.validation")
        logger.info("Test log message")
        print("✓ Structured logger working")
    except Exception as e:
        print(f"✗ Logger failed: {e}")
        return False
    
    try:
        # Test metrics collector
        from schema_management.monitoring import MCPMetricsCollector
        metrics = MCPMetricsCollector()
        metrics.record_operation("test_operation", 100.0, True)
        performance_metrics = metrics.get_performance_metrics("test_operation")
        assert performance_metrics["total_requests"] == 1
        print("✓ Metrics collector working")
    except Exception as e:
        print(f"✗ Metrics collector failed: {e}")
        return False
    
    try:
        # Test health monitor
        from schema_management.monitoring import MCPHealthMonitor
        health_monitor = MCPHealthMonitor()
        # Just test initialization, not full health check
        print("✓ Health monitor working")
    except Exception as e:
        print(f"✗ Health monitor failed: {e}")
        return False
    
    try:
        # Test alert manager
        from schema_management.monitoring import MCPAlertManager
        alert_manager = MCPAlertManager()
        summary = alert_manager.get_alert_summary()
        assert "active_alerts_count" in summary
        print("✓ Alert manager working")
    except Exception as e:
        print(f"✗ Alert manager failed: {e}")
        return False
    
    try:
        # Test performance tracker
        from schema_management.monitoring import MCPPerformanceTracker
        perf_tracker = MCPPerformanceTracker()
        # Test basic snapshot creation
        from schema_management.monitoring.performance_tracker import PerformanceSnapshot
        snapshot = PerformanceSnapshot(
            timestamp=datetime.utcnow(),
            operation="test",
            duration_ms=100.0,
            success=True
        )
        perf_tracker._store_snapshot(snapshot)
        print("✓ Performance tracker working")
    except Exception as e:
        print(f"✗ Performance tracker failed: {e}")
        return False
    
    return True

async def test_async_functionality():
    """Test async functionality of monitoring components."""
    print("\nTesting async functionality...")
    
    try:
        from schema_management.monitoring import MCPPerformanceTracker
        perf_tracker = MCPPerformanceTracker()
        
        # Test async context manager
        async with perf_tracker.track_operation("test_async_op") as perf_data:
            await asyncio.sleep(0.001)  # Simulate async work
            perf_data['test_param'] = True
        
        # Verify snapshot was created
        assert len(perf_tracker.snapshots) == 1
        print("✓ Async performance tracking working")
    except Exception as e:
        print(f"✗ Async performance tracking failed: {e}")
        return False
    
    try:
        from schema_management.monitoring import MCPHealthMonitor
        health_monitor = MCPHealthMonitor()
        
        # Test basic health check without dependencies
        health_report = await health_monitor.perform_health_check()
        assert health_report is not None
        print("✓ Async health monitoring working")
    except Exception as e:
        print(f"✗ Async health monitoring failed: {e}")
        return False
    
    return True

def test_configuration():
    """Test monitoring configuration."""
    print("\nTesting configuration...")
    
    try:
        from schema_management.monitoring.config import MonitoringConfig
        
        # Test default configuration
        config = MonitoringConfig()
        issues = config.validate()
        assert isinstance(issues, list)
        print("✓ Configuration validation working")
    except Exception as e:
        print(f"✗ Configuration failed: {e}")
        return False
    
    return True

def test_initialization():
    """Test monitoring system initialization."""
    print("\nTesting system initialization...")
    
    try:
        from schema_management.monitoring.setup import initialize_monitoring
        from schema_management.monitoring.config import MonitoringConfig
        
        # Test basic initialization
        config = MonitoringConfig(enable_monitoring=True)
        success, components = initialize_monitoring(config)
        
        assert success is True
        assert 'monitoring_enabled' in components
        assert components['monitoring_enabled'] is True
        print("✓ System initialization working")
    except Exception as e:
        print(f"✗ System initialization failed: {e}")
        return False
    
    return True

async def main():
    """Main validation function."""
    print("MCP Monitoring System Validation")
    print("=" * 40)
    
    # Run all tests
    tests = [
        test_imports,
        test_basic_functionality,
        test_configuration,
        test_initialization
    ]
    
    async_tests = [
        test_async_functionality
    ]
    
    all_passed = True
    
    # Run synchronous tests
    for test in tests:
        if not test():
            all_passed = False
    
    # Run asynchronous tests
    for test in async_tests:
        if not await test():
            all_passed = False
    
    # Final summary
    print("\n" + "=" * 40)
    if all_passed:
        print("✓ All validation tests passed!")
        print("✓ MCP monitoring system is ready for use")
        return 0
    else:
        print("✗ Some validation tests failed")
        print("✗ Please check the errors above")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
