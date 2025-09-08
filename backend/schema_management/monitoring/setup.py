"""
Monitoring setup and initialization for MCP schema management.

This module provides comprehensive setup functions for initializing all
monitoring components with proper configuration and error handling.
"""

import asyncio
import logging
import os
import sys
from typing import Dict, Optional, Tuple

from .config import MonitoringConfig, setup_monitoring_environment
from .logger import setup_mcp_logging, get_logger
from .metrics import get_metrics_collector
from .health_monitor import MCPHealthMonitor
from .alerting import (
    MCPAlertManager, EmailAlertChannel, WebhookAlertChannel, 
    SlackAlertChannel, LogAlertChannel
)
from .performance_tracker import MCPPerformanceTracker


def initialize_monitoring(
    config: Optional[MonitoringConfig] = None,
    force_enable: bool = False
) -> Tuple[bool, Dict[str, any]]:
    """
    Initialize comprehensive monitoring system for MCP schema management.
    
    Args:
        config: Monitoring configuration (defaults to environment-based)
        force_enable: Force enable monitoring even if disabled in config
        
    Returns:
        Tuple of (success, components_dict)
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        if config is None:
            config = setup_monitoring_environment()
        
        # Check if monitoring should be enabled
        if not config.enable_monitoring and not force_enable:
            logger.info("Monitoring is disabled in configuration")
            return False, {}
        
        # Initialize logging first
        if config.logging.enable_json_logging or config.logging.enable_file_logging:
            loggers = setup_mcp_logging(
                enable_json=config.logging.enable_json_logging,
                log_level=config.logging.log_level,
                enable_file_logging=config.logging.enable_file_logging,
                log_file=config.logging.log_file_path
            )
            logger.info("Structured logging initialized")
        
        # Initialize metrics collector
        metrics_collector = None
        if config.metrics.enable_metrics:
            metrics_collector = get_metrics_collector()
            logger.info("Metrics collector initialized")
        
        # Initialize performance tracker
        performance_tracker = None
        if config.performance.enable_performance_tracking:
            performance_tracker = MCPPerformanceTracker(
                max_snapshots=config.performance.max_snapshots,
                trend_window_minutes=config.performance.trend_window_minutes
            )
            logger.info("Performance tracker initialized")
        
        # Initialize health monitor
        health_monitor = None
        if config.health_monitor.enable_health_monitoring:
            health_monitor = MCPHealthMonitor(
                check_interval_seconds=config.health_monitor.health_check_interval_seconds,
                connectivity_timeout=config.health_monitor.connectivity_timeout_seconds,
                performance_threshold_ms=config.health_monitor.performance_threshold_ms,
                cache_hit_rate_threshold=config.health_monitor.cache_hit_rate_threshold,
                validation_success_threshold=config.health_monitor.validation_success_threshold,
                error_rate_threshold=config.health_monitor.error_rate_threshold
            )
            logger.info("Health monitor initialized")
        
        # Initialize alert manager
        alert_manager = None
        if config.alerting.enable_alerting:
            alert_manager = MCPAlertManager()
            
            # Add alert channels based on configuration
            if config.alerting.enable_email_alerts and _validate_email_config(config.alerting):
                email_channel = EmailAlertChannel(
                    smtp_host=config.alerting.smtp_host,
                    smtp_port=config.alerting.smtp_port,
                    smtp_user=config.alerting.smtp_user,
                    smtp_password=config.alerting.smtp_password,
                    from_email=config.alerting.email_from,
                    to_emails=config.alerting.email_recipients,
                    use_tls=config.alerting.smtp_use_tls
                )
                alert_manager.add_channel(email_channel)
                logger.info("Email alert channel added")
            
            if config.alerting.enable_webhook_alerts and config.alerting.webhook_url:
                webhook_channel = WebhookAlertChannel(
                    webhook_url=config.alerting.webhook_url,
                    headers=config.alerting.webhook_headers
                )
                alert_manager.add_channel(webhook_channel)
                logger.info("Webhook alert channel added")
            
            if config.alerting.enable_slack_alerts and config.alerting.slack_webhook_url:
                slack_channel = SlackAlertChannel(
                    webhook_url=config.alerting.slack_webhook_url,
                    channel=config.alerting.slack_channel
                )
                alert_manager.add_channel(slack_channel)
                logger.info("Slack alert channel added")
            
            logger.info("Alert manager initialized")
        
        # Create components dictionary
        components = {
            'config': config,
            'metrics_collector': metrics_collector,
            'performance_tracker': performance_tracker,
            'health_monitor': health_monitor,
            'alert_manager': alert_manager,
            'monitoring_enabled': True
        }
        
        logger.info("MCP monitoring system initialized successfully")
        return True, components
    
    except Exception as e:
        logger.error(f"Failed to initialize monitoring system: {e}")
        return False, {'error': str(e), 'monitoring_enabled': False}


def _validate_email_config(alert_config) -> bool:
    """Validate email alert configuration."""
    required_fields = [
        alert_config.smtp_host,
        alert_config.smtp_user,
        alert_config.smtp_password,
        alert_config.email_from
    ]
    
    return all(required_fields) and len(alert_config.email_recipients) > 0


async def start_monitoring_services(components: Dict[str, any]) -> bool:
    """
    Start background monitoring services.
    
    Args:
        components: Dictionary of monitoring components
        
    Returns:
        True if services started successfully
    """
    logger = get_logger('monitoring')
    
    try:
        health_monitor = components.get('health_monitor')
        alert_manager = components.get('alert_manager')
        
        if not health_monitor or not alert_manager:
            logger.warning("Health monitor or alert manager not available")
            return False
        
        # Start monitoring loop
        monitoring_task = asyncio.create_task(_monitoring_service_loop(health_monitor, alert_manager))
        
        components['monitoring_task'] = monitoring_task
        
        logger.info("Monitoring services started")
        return True
    
    except Exception as e:
        logger.error(f"Failed to start monitoring services: {e}")
        return False


async def _monitoring_service_loop(health_monitor: MCPHealthMonitor, alert_manager: MCPAlertManager):
    """Background monitoring service loop."""
    logger = get_logger('monitoring')
    
    try:
        while True:
            try:
                # Perform health check
                health_report = await health_monitor.perform_health_check()
                
                # Check for alerts
                await alert_manager.check_alerts(health_report)
                
                # Wait for next iteration
                await asyncio.sleep(health_monitor.check_interval_seconds)
            
            except asyncio.CancelledError:
                logger.info("Monitoring service loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in monitoring service loop: {e}")
                # Wait before retrying
                await asyncio.sleep(60)
    
    except Exception as e:
        logger.error(f"Fatal error in monitoring service loop: {e}")


def stop_monitoring_services(components: Dict[str, any]):
    """Stop background monitoring services."""
    logger = get_logger('monitoring')
    
    monitoring_task = components.get('monitoring_task')
    if monitoring_task and not monitoring_task.done():
        monitoring_task.cancel()
        logger.info("Monitoring services stopped")


def get_monitoring_dashboard_data(components: Dict[str, any]) -> Dict[str, any]:
    """
    Get comprehensive monitoring data for dashboard display.
    
    Args:
        components: Dictionary of monitoring components
        
    Returns:
        Dictionary with dashboard data
    """
    dashboard_data = {
        'timestamp': os.path.time(),
        'monitoring_enabled': components.get('monitoring_enabled', False),
        'system_status': 'unknown',
        'metrics': {},
        'health': {},
        'performance': {},
        'alerts': {},
        'recommendations': []
    }
    
    try:
        # Get metrics data
        metrics_collector = components.get('metrics_collector')
        if metrics_collector:
            dashboard_data['metrics'] = metrics_collector.get_comprehensive_metrics()
            dashboard_data['system_status'] = 'healthy'  # Will be overridden by health check
        
        # Get health data
        health_monitor = components.get('health_monitor')
        if health_monitor:
            latest_health = health_monitor.get_latest_health_status()
            if latest_health:
                dashboard_data['health'] = latest_health.to_dict()
                dashboard_data['system_status'] = latest_health.overall_status.value
        
        # Get performance data
        performance_tracker = components.get('performance_tracker')
        if performance_tracker:
            dashboard_data['performance'] = performance_tracker.get_performance_summary()
            
            # Get optimization recommendations
            recommendations = performance_tracker.get_optimization_recommendations()
            dashboard_data['recommendations'] = [rec.to_dict() for rec in recommendations]
        
        # Get alert data
        alert_manager = components.get('alert_manager')
        if alert_manager:
            dashboard_data['alerts'] = {
                'active_alerts': [alert.to_dict() for alert in alert_manager.get_active_alerts()],
                'alert_summary': alert_manager.get_alert_summary()
            }
    
    except Exception as e:
        dashboard_data['error'] = str(e)
    
    return dashboard_data


def generate_monitoring_report(components: Dict[str, any], format: str = 'dict') -> any:
    """
    Generate comprehensive monitoring report.
    
    Args:
        components: Dictionary of monitoring components
        format: Output format ('dict', 'json', 'markdown')
        
    Returns:
        Report in specified format
    """
    from datetime import datetime
    
    report_data = get_monitoring_dashboard_data(components)
    
    if format == 'json':
        import json
        return json.dumps(report_data, indent=2, default=str)
    
    elif format == 'markdown':
        return _generate_markdown_report(report_data)
    
    else:  # dict format
        return report_data


def _generate_markdown_report(data: Dict[str, any]) -> str:
    """Generate markdown-formatted monitoring report."""
    from datetime import datetime
    
    report = f"""# MCP Schema Management Monitoring Report

**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
**System Status:** {data.get('system_status', 'unknown').upper()}

## System Health

"""
    
    health_data = data.get('health', {})
    if health_data:
        report += f"""
- **Overall Status:** {health_data.get('overall_status', 'unknown')}
- **Uptime:** {health_data.get('uptime_seconds', 0) / 3600:.1f} hours
- **Healthy Checks:** {health_data.get('healthy_checks', 0)}/{health_data.get('total_checks', 0)}
"""
    
    # Performance metrics
    performance_data = data.get('performance', {})
    if performance_data:
        report += f"""
## Performance Summary

- **Total Operations:** {performance_data.get('total_operations_tracked', 0)}
- **Operations (Last Hour):** {performance_data.get('operations_last_hour', 0)}
- **Success Rate:** {performance_data.get('overall_success_rate', 0):.1f}%
"""
    
    # Active alerts
    alerts_data = data.get('alerts', {})
    active_alerts = alerts_data.get('active_alerts', [])
    if active_alerts:
        report += f"""
## Active Alerts ({len(active_alerts)})

"""
        for alert in active_alerts[:5]:  # Show top 5
            report += f"- **{alert.get('level', 'unknown').upper()}:** {alert.get('title', 'Unknown')}\n"
    
    # Recommendations
    recommendations = data.get('recommendations', [])
    if recommendations:
        report += f"""
## Optimization Recommendations ({len(recommendations)})

"""
        for rec in recommendations[:3]:  # Show top 3
            report += f"- **{rec.get('priority', 'unknown').upper()}:** {rec.get('title', 'Unknown')}\n"
    
    return report


def export_monitoring_config(components: Dict[str, any], file_path: str):
    """Export monitoring configuration to file."""
    config = components.get('config')
    if not config:
        raise ValueError("No monitoring configuration available")
    
    config_dict = config.to_dict()
    
    if file_path.endswith('.json'):
        import json
        with open(file_path, 'w') as f:
            json.dump(config_dict, f, indent=2)
    elif file_path.endswith('.yaml') or file_path.endswith('.yml'):
        try:
            import yaml
            with open(file_path, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False)
        except ImportError:
            raise ImportError("PyYAML is required for YAML export")
    else:
        raise ValueError("Unsupported file format. Use .json or .yaml/.yml")


def validate_monitoring_setup() -> Dict[str, any]:
    """Validate monitoring setup and return status."""
    validation_result = {
        'valid': True,
        'issues': [],
        'warnings': [],
        'components_available': {}
    }
    
    try:
        # Test configuration loading
        config = setup_monitoring_environment()
        config_issues = config.validate()
        if config_issues:
            validation_result['issues'].extend(config_issues)
            validation_result['valid'] = False
        
        # Test component imports
        try:
            from . import (
                MCPStructuredLogger, MCPMetricsCollector, MCPHealthMonitor,
                MCPAlertManager, MCPPerformanceTracker
            )
            validation_result['components_available']['all'] = True
        except ImportError as e:
            validation_result['issues'].append(f"Component import failed: {e}")
            validation_result['valid'] = False
        
        # Test optional dependencies
        try:
            import psutil
            validation_result['components_available']['system_monitoring'] = True
        except ImportError:
            validation_result['warnings'].append("psutil not available - system resource monitoring disabled")
        
        try:
            import aiohttp
            validation_result['components_available']['http_alerts'] = True
        except ImportError:
            validation_result['warnings'].append("aiohttp not available - webhook/slack alerts disabled")
    
    except Exception as e:
        validation_result['valid'] = False
        validation_result['issues'].append(f"Validation failed: {e}")
    
    return validation_result
