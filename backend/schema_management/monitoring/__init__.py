"""
Monitoring and observability module for MCP schema management.

This module provides comprehensive monitoring, metrics collection, alerting,
and observability features for the MCP schema management system.
"""

try:
    from .logger import MCPStructuredLogger, setup_mcp_logging, get_logger
    from .metrics import (
        MCPMetricsCollector,
        PerformanceMetrics,
        ValidationMetrics,
        CacheMetrics,
        ErrorMetrics,
        get_metrics_collector
    )
    from .health_monitor import MCPHealthMonitor, HealthStatus
    from .alerting import MCPAlertManager, AlertLevel, Alert
    from .performance_tracker import MCPPerformanceTracker
    
    __all__ = [
        'MCPStructuredLogger',
        'setup_mcp_logging',
        'get_logger',
        'MCPMetricsCollector',
        'PerformanceMetrics',
        'ValidationMetrics',
        'CacheMetrics',
        'ErrorMetrics',
        'get_metrics_collector',
        'MCPHealthMonitor',
        'HealthStatus',
        'MCPAlertManager',
        'AlertLevel',
        'Alert',
        'MCPPerformanceTracker'
    ]
    
except ImportError as e:
    # Handle import errors gracefully during development
    import logging
    logging.warning(f"Failed to import monitoring components: {e}")
    
    # Provide minimal fallback implementations
    class MockLogger:
        def info(self, *args, **kwargs): pass
        def warning(self, *args, **kwargs): pass
        def error(self, *args, **kwargs): pass
        def debug(self, *args, **kwargs): pass
        def critical(self, *args, **kwargs): pass
    
    def get_logger(name):
        return MockLogger()
    
    __all__ = ['get_logger']
