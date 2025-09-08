# MCP Schema Management Monitoring System

## Overview

The MCP Schema Management Monitoring System provides comprehensive observability for the Model Context Protocol (MCP) schema management operations. This system implements structured logging, performance metrics collection, health monitoring, alerting, and performance tracking as specified in Task 8.

## Features

### 1. Structured Logging (`logger.py`)

- **JSON and Text Formatters**: Supports both human-readable and machine-parseable log formats
- **Context Management**: Tracks request IDs, user context, and operation parameters
- **Performance Logging**: Automatic timing and performance tracking for operations
- **Correlation IDs**: Links related log entries across distributed operations

#### Usage Example:

```python
from backend.schema_management.monitoring import MCPStructuredLogger

logger = MCPStructuredLogger("mcp.schema", enable_json=True)

# Context management
logger.set_context(user_id="user123", operation="schema_discovery")

# Operation tracking with automatic timing
with logger.operation_context("discover_databases", database_count=5) as request_id:
    # Your operation code here
    databases = await discover_databases()
    logger.info("Successfully discovered databases",
                database_count=len(databases),
                request_id=request_id)
```

### 2. Metrics Collection (`metrics.py`)

- **Performance Metrics**: Track operation durations, success rates, and throughput
- **Cache Metrics**: Monitor cache hit rates, memory usage, and cache effectiveness
- **Validation Metrics**: Track validation success rates and timing
- **Error Metrics**: Categorize and count different types of errors
- **Health Scoring**: Comprehensive health scoring based on all metrics

#### Key Metrics:

```python
from backend.schema_management.monitoring import get_metrics_collector

metrics = get_metrics_collector()

# Record operation performance
metrics.record_operation("discover_databases", duration_ms=150.0, success=True)

# Record cache operations
metrics.record_cache_hit(25.0)  # 25ms cache hit
metrics.record_cache_miss(100.0)  # 100ms cache miss

# Record validation results
metrics.record_validation(75.0, success=True)

# Record errors
metrics.record_error("ConnectionError", "connect_mcp", "Server unreachable")

# Get comprehensive metrics
report = metrics.get_comprehensive_metrics()
```

### 3. Health Monitoring (`health_monitor.py`)

- **MCP Connectivity**: Monitor connection health and response times
- **Performance Health**: Track operation performance against thresholds
- **Cache Health**: Monitor cache performance and memory usage
- **Validation Health**: Track validation success rates
- **Resource Health**: Monitor system resource usage (CPU, memory)

#### Health Checks:

```python
from backend.schema_management.monitoring import MCPHealthMonitor

health_monitor = MCPHealthMonitor(
    check_interval_seconds=30,
    connectivity_timeout=5
)

# Set dependencies
health_monitor.set_dependencies(
    mcp_client=mcp_client,
    schema_manager=schema_manager
)

# Perform comprehensive health check
health_report = await health_monitor.perform_health_check()

print(f"Overall Status: {health_report.overall_status}")
print(f"Health Score: {health_report.health_score}/100")
```

### 4. Alerting System (`alerting.py`)

- **Multi-Channel Alerts**: Support for log, email, webhook, and Slack notifications
- **Intelligent Rules**: Configurable alert rules with conditions and cooldowns
- **Auto-Resolution**: Automatic alert resolution when conditions improve
- **Alert Management**: Track active alerts and alert history

#### Alert Configuration:

```python
from backend.schema_management.monitoring import MCPAlertManager, AlertLevel

alert_manager = MCPAlertManager()

# Configure email alerts
alert_manager.configure_email_alerts(
    smtp_host="smtp.company.com",
    smtp_port=587,
    username="alerts@company.com",
    password="password",
    recipients=["admin@company.com"]
)

# Configure webhook alerts
alert_manager.configure_webhook_alerts(
    webhook_url="https://hooks.slack.com/services/...",
    webhook_headers={"Authorization": "Bearer token"}
)

# Check for alerts based on current metrics
await alert_manager.check_alerts()

# Get active alerts
active_alerts = alert_manager.get_active_alerts()
```

### 5. Performance Tracking (`performance_tracker.py`)

- **Operation Tracking**: Detailed tracking of individual operations
- **Trend Analysis**: Performance trends over time
- **Anomaly Detection**: Identify performance anomalies and outliers
- **Optimization Recommendations**: AI-powered recommendations for performance improvements

#### Performance Tracking:

```python
from backend.schema_management.monitoring import MCPPerformanceTracker

performance_tracker = MCPPerformanceTracker(
    max_snapshots=10000,
    trend_window_minutes=60
)

# Track operation performance
async with performance_tracker.track_operation(
    "discover_databases",
    database_type="mysql"
) as perf_data:
    # Your operation
    databases = await discover_databases()

    # Add custom performance data
    perf_data['cache_hit'] = True
    perf_data['result_count'] = len(databases)

# Get performance statistics
stats = performance_tracker.get_operation_performance("discover_databases")

# Detect anomalies
anomalies = performance_tracker.detect_performance_anomalies(
    threshold_multiplier=2.0,
    time_window_minutes=30
)

# Get optimization recommendations
recommendations = performance_tracker.get_optimization_recommendations()
```

## Configuration

### Environment Variables

```bash
# Enable monitoring
MCP_MONITORING_ENABLED=true

# Logging configuration
MCP_LOG_LEVEL=INFO
MCP_ENABLE_JSON_LOGGING=true
MCP_LOG_FILE_PATH=/var/log/mcp/schema.log

# Metrics configuration
MCP_METRICS_ENABLED=true
MCP_METRICS_RETENTION_HOURS=24

# Health monitoring
MCP_HEALTH_CHECK_INTERVAL=30
MCP_CONNECTIVITY_TIMEOUT=5

# Alerting configuration
MCP_ENABLE_EMAIL_ALERTS=true
MCP_SMTP_HOST=smtp.company.com
MCP_SMTP_PORT=587
MCP_EMAIL_RECIPIENTS=admin@company.com,ops@company.com

# Performance tracking
MCP_PERFORMANCE_MAX_SNAPSHOTS=10000
MCP_PERFORMANCE_TREND_WINDOW=60
```

### Configuration Class

```python
from backend.schema_management.monitoring.config import MonitoringConfig

config = MonitoringConfig(
    enable_monitoring=True,
    logging=LoggingConfig(
        log_level="INFO",
        enable_json_logging=True,
        enable_file_logging=True,
        log_file_path="/var/log/mcp/schema.log"
    ),
    metrics=MetricsConfig(
        enable_metrics=True,
        retention_hours=24
    ),
    health=HealthConfig(
        check_interval_seconds=30,
        connectivity_timeout=5
    ),
    alerting=AlertConfig(
        enable_email_alerts=True,
        smtp_host="smtp.company.com",
        smtp_port=587,
        email_recipients=["admin@company.com"]
    ),
    performance=PerformanceConfig(
        max_snapshots=10000,
        trend_window_minutes=60
    )
)

# Validate configuration
issues = config.validate()
if issues:
    for issue in issues:
        print(f"Configuration issue: {issue}")
```

## Integration with Schema Manager

The monitoring system is fully integrated with the MCP Schema Manager:

```python
from backend.schema_management.manager import MCPSchemaManager
from backend.schema_management.config import MCPSchemaConfig

# Create schema manager with monitoring enabled
config = MCPSchemaConfig.from_env()
manager = MCPSchemaManager(config, enable_monitoring=True)

# All operations are automatically monitored
await manager.connect()  # Logged and tracked
databases = await manager.discover_databases()  # Performance tracked
await manager.validate_schema(schema)  # Validation metrics recorded

# Get comprehensive monitoring report
monitoring_report = await manager.get_comprehensive_monitoring_report()
```

## Dashboard and Reporting

### Real-time Dashboard Data

```python
from backend.schema_management.monitoring.setup import get_monitoring_dashboard_data

dashboard_data = get_monitoring_dashboard_data(monitoring_components)

# Dashboard includes:
# - Real-time metrics
# - Health status
# - Active alerts
# - Performance trends
# - Error summaries
# - Optimization recommendations
```

### Sample Dashboard Data Structure

```json
{
  "monitoring_enabled": true,
  "timestamp": "2024-01-15T10:30:00Z",
  "health": {
    "overall_status": "HEALTHY",
    "health_score": 95,
    "checks": [
      {
        "name": "mcp_connectivity",
        "status": "HEALTHY",
        "response_time_ms": 45,
        "last_check": "2024-01-15T10:29:55Z"
      }
    ]
  },
  "metrics": {
    "requests_per_minute": 120,
    "average_response_time": 85.5,
    "cache_hit_rate": 87.3,
    "validation_success_rate": 98.2,
    "error_rate": 0.8
  },
  "alerts": {
    "active_count": 0,
    "resolved_today": 2
  },
  "performance": {
    "trending_operations": [
      {
        "operation": "discover_databases",
        "trend": "improving",
        "average_duration": 120.5
      }
    ],
    "anomalies_detected": 1,
    "recommendations_count": 3
  }
}
```

## Monitoring Best Practices

### 1. Operational Guidelines

- **Regular Monitoring**: Check health status at least every 5 minutes
- **Alert Response**: Respond to critical alerts within 15 minutes
- **Performance Baselines**: Establish performance baselines during low-usage periods
- **Capacity Planning**: Monitor trends for capacity planning decisions

### 2. Alert Configuration

- **Threshold Tuning**: Adjust alert thresholds based on historical data
- **Alert Fatigue**: Use alert cooldowns to prevent notification spam
- **Escalation**: Configure alert escalation for critical issues
- **Auto-Resolution**: Enable auto-resolution for transient issues

### 3. Performance Optimization

- **Cache Monitoring**: Maintain cache hit rate above 80%
- **Response Times**: Keep average response times under 200ms
- **Error Rates**: Maintain error rates below 1%
- **Resource Usage**: Keep memory usage below 80% of available

### 4. Data Retention

- **Metrics**: Retain detailed metrics for 24-48 hours
- **Logs**: Retain logs for 7-30 days depending on compliance requirements
- **Performance Snapshots**: Retain performance data for trend analysis (7-14 days)
- **Alert History**: Retain alert history for analysis and improvement

## Troubleshooting

### Common Issues

1. **High Memory Usage**

   - Check metrics retention settings
   - Verify performance snapshot limits
   - Monitor cache memory usage

2. **Alert Notification Failures**

   - Verify SMTP configuration
   - Check webhook endpoint availability
   - Validate alert channel credentials

3. **Performance Degradation**

   - Review performance trends
   - Check for anomalies
   - Implement optimization recommendations

4. **Missing Metrics**
   - Verify monitoring is enabled
   - Check component initialization
   - Review error logs for failures

### Debug Mode

Enable debug logging for detailed troubleshooting:

```python
from backend.schema_management.monitoring.config import MonitoringConfig, LoggingConfig

config = MonitoringConfig(
    logging=LoggingConfig(
        log_level="DEBUG",
        enable_console_logging=True
    )
)
```

## API Reference

### Core Classes

- `MCPStructuredLogger`: Structured logging with context management
- `MCPMetricsCollector`: Comprehensive metrics collection
- `MCPHealthMonitor`: Health monitoring and status reporting
- `MCPAlertManager`: Multi-channel alerting system
- `MCPPerformanceTracker`: Performance tracking and analysis

### Configuration Classes

- `MonitoringConfig`: Main configuration container
- `LoggingConfig`: Logging-specific configuration
- `MetricsConfig`: Metrics collection configuration
- `HealthConfig`: Health monitoring configuration
- `AlertConfig`: Alerting system configuration
- `PerformanceConfig`: Performance tracking configuration

### Utility Functions

- `initialize_monitoring()`: Initialize monitoring system
- `get_metrics_collector()`: Get global metrics collector instance
- `start_monitoring_services()`: Start background monitoring services
- `get_monitoring_dashboard_data()`: Generate dashboard data
- `validate_monitoring_setup()`: Validate monitoring configuration

This monitoring system provides comprehensive observability for the MCP schema management operations, enabling proactive monitoring, alerting, and performance optimization.
