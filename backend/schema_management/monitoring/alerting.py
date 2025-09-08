"""
Alerting system for MCP schema management.

This module provides comprehensive alerting capabilities for MCP operations,
including connectivity issues, performance degradation, and error tracking.
"""

import asyncio
import json
import smtplib
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from urllib.parse import urljoin

import aiohttp

from .logger import get_logger
from .health_monitor import HealthStatus, SystemHealthReport
from .metrics import get_metrics_collector


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Individual alert definition."""
    
    id: str
    level: AlertLevel
    title: str
    message: str
    timestamp: datetime
    source: str
    details: Dict[str, Any]
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            'id': self.id,
            'level': self.level.value,
            'title': self.title,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'details': self.details,
            'resolved': self.resolved,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }


@dataclass
class AlertRule:
    """Alert rule configuration."""
    
    name: str
    condition: Callable[[Dict[str, Any]], bool]
    level: AlertLevel
    message_template: str
    cooldown_minutes: int = 5
    auto_resolve: bool = True
    enabled: bool = True


class AlertChannel:
    """Base class for alert notification channels."""
    
    async def send_alert(self, alert: Alert) -> bool:
        """Send alert notification. Returns True if successful."""
        raise NotImplementedError


class LogAlertChannel(AlertChannel):
    """Log-based alert channel."""
    
    def __init__(self):
        self.logger = get_logger('alerts')
    
    async def send_alert(self, alert: Alert) -> bool:
        """Send alert to logs."""
        try:
            log_method = {
                AlertLevel.INFO: self.logger.info,
                AlertLevel.WARNING: self.logger.warning,
                AlertLevel.ERROR: self.logger.error,
                AlertLevel.CRITICAL: self.logger.critical
            }.get(alert.level, self.logger.info)
            
            log_method(
                f"ALERT: {alert.title}",
                alert_id=alert.id,
                level=alert.level.value,
                message=alert.message,
                source=alert.source,
                details=alert.details
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to send log alert: {e}")
            return False


class EmailAlertChannel(AlertChannel):
    """Email-based alert channel."""
    
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        from_email: str,
        to_emails: List[str],
        use_tls: bool = True
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_email = from_email
        self.to_emails = to_emails
        self.use_tls = use_tls
        self.logger = get_logger('alerts')
    
    async def send_alert(self, alert: Alert) -> bool:
        """Send alert via email."""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            msg['Subject'] = f"[{alert.level.value.upper()}] MCP Alert: {alert.title}"
            
            # Create email body
            body = self._create_email_body(alert)
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            if self.use_tls:
                server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)
            server.quit()
            
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to send email alert: {e}")
            return False
    
    def _create_email_body(self, alert: Alert) -> str:
        """Create HTML email body for alert."""
        color_map = {
            AlertLevel.INFO: '#17a2b8',
            AlertLevel.WARNING: '#ffc107',
            AlertLevel.ERROR: '#dc3545',
            AlertLevel.CRITICAL: '#dc3545'
        }
        
        color = color_map.get(alert.level, '#17a2b8')
        
        details_html = ""
        if alert.details:
            details_html = "<h3>Details:</h3><ul>"
            for key, value in alert.details.items():
                details_html += f"<li><strong>{key}:</strong> {value}</li>"
            details_html += "</ul>"
        
        return f"""
        <html>
        <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px;">
                <div style="background-color: {color}; color: white; padding: 20px; border-radius: 5px 5px 0 0;">
                    <h2 style="margin: 0;">MCP Schema Management Alert</h2>
                    <p style="margin: 10px 0 0 0; font-size: 14px;">Level: {alert.level.value.upper()}</p>
                </div>
                <div style="padding: 20px; border: 1px solid #ddd; border-radius: 0 0 5px 5px;">
                    <h3>{alert.title}</h3>
                    <p>{alert.message}</p>
                    {details_html}
                    <hr>
                    <p style="font-size: 12px; color: #666;">
                        <strong>Alert ID:</strong> {alert.id}<br>
                        <strong>Source:</strong> {alert.source}<br>
                        <strong>Timestamp:</strong> {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}
                    </p>
                </div>
            </div>
        </body>
        </html>
        """


class WebhookAlertChannel(AlertChannel):
    """Webhook-based alert channel."""
    
    def __init__(self, webhook_url: str, headers: Optional[Dict[str, str]] = None):
        self.webhook_url = webhook_url
        self.headers = headers or {}
        self.logger = get_logger('alerts')
    
    async def send_alert(self, alert: Alert) -> bool:
        """Send alert via webhook."""
        try:
            payload = {
                'alert': alert.to_dict(),
                'timestamp': datetime.utcnow().isoformat(),
                'service': 'mcp_schema_management'
            }
            
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers=self.headers
                ) as response:
                    if 200 <= response.status < 300:
                        return True
                    else:
                        self.logger.error(f"Webhook returned status {response.status}")
                        return False
        
        except Exception as e:
            self.logger.error(f"Failed to send webhook alert: {e}")
            return False


class SlackAlertChannel(AlertChannel):
    """Slack-based alert channel."""
    
    def __init__(self, webhook_url: str, channel: Optional[str] = None):
        self.webhook_url = webhook_url
        self.channel = channel
        self.logger = get_logger('alerts')
    
    async def send_alert(self, alert: Alert) -> bool:
        """Send alert to Slack."""
        try:
            color_map = {
                AlertLevel.INFO: '#36a64f',
                AlertLevel.WARNING: '#ff9500',
                AlertLevel.ERROR: '#ff0000',
                AlertLevel.CRITICAL: '#ff0000'
            }
            
            payload = {
                'text': f"MCP Alert: {alert.title}",
                'attachments': [{
                    'color': color_map.get(alert.level, '#36a64f'),
                    'fields': [
                        {
                            'title': 'Level',
                            'value': alert.level.value.upper(),
                            'short': True
                        },
                        {
                            'title': 'Source',
                            'value': alert.source,
                            'short': True
                        },
                        {
                            'title': 'Message',
                            'value': alert.message,
                            'short': False
                        }
                    ],
                    'ts': int(alert.timestamp.timestamp())
                }]
            }
            
            if self.channel:
                payload['channel'] = self.channel
            
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if 200 <= response.status < 300:
                        return True
                    else:
                        self.logger.error(f"Slack webhook returned status {response.status}")
                        return False
        
        except Exception as e:
            self.logger.error(f"Failed to send Slack alert: {e}")
            return False


class MCPAlertManager:
    """
    Comprehensive alert manager for MCP schema management system.
    
    Monitors system health, performance metrics, and error rates to generate
    intelligent alerts with configurable channels and rules.
    """
    
    def __init__(self):
        """Initialize alert manager."""
        self.logger = get_logger('alerts')
        self.metrics_collector = get_metrics_collector()
        
        # Alert state
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.max_history_size = 1000
        
        # Alert rules and channels
        self.alert_rules: List[AlertRule] = []
        self.alert_channels: List[AlertChannel] = []
        
        # Cooldown tracking
        self.rule_cooldowns: Dict[str, datetime] = {}
        
        # Default channels
        self.alert_channels.append(LogAlertChannel())
        
        # Initialize default rules
        self._initialize_default_rules()
        
        self.logger.info("Alert manager initialized")
    
    def add_channel(self, channel: AlertChannel):
        """Add alert notification channel."""
        self.alert_channels.append(channel)
        self.logger.info(f"Added alert channel: {type(channel).__name__}")
    
    def add_rule(self, rule: AlertRule):
        """Add custom alert rule."""
        self.alert_rules.append(rule)
        self.logger.info(f"Added alert rule: {rule.name}")
    
    def _initialize_default_rules(self):
        """Initialize default alert rules."""
        
        # MCP Server connectivity
        self.alert_rules.append(AlertRule(
            name="mcp_server_down",
            condition=lambda metrics: self._check_mcp_connectivity_failure(metrics),
            level=AlertLevel.CRITICAL,
            message_template="MCP server is not responding",
            cooldown_minutes=5
        ))
        
        # High error rate
        self.alert_rules.append(AlertRule(
            name="high_error_rate",
            condition=lambda metrics: self._check_high_error_rate(metrics),
            level=AlertLevel.ERROR,
            message_template="Error rate exceeded threshold",
            cooldown_minutes=10
        ))
        
        # Low cache hit rate
        self.alert_rules.append(AlertRule(
            name="low_cache_hit_rate",
            condition=lambda metrics: self._check_low_cache_hit_rate(metrics),
            level=AlertLevel.WARNING,
            message_template="Cache hit rate below threshold",
            cooldown_minutes=15
        ))
        
        # Slow performance
        self.alert_rules.append(AlertRule(
            name="slow_performance",
            condition=lambda metrics: self._check_slow_performance(metrics),
            level=AlertLevel.WARNING,
            message_template="Performance degraded",
            cooldown_minutes=10
        ))
        
        # Validation failures
        self.alert_rules.append(AlertRule(
            name="validation_failures",
            condition=lambda metrics: self._check_validation_failures(metrics),
            level=AlertLevel.ERROR,
            message_template="High validation failure rate",
            cooldown_minutes=10
        ))
        
        # Memory usage
        self.alert_rules.append(AlertRule(
            name="high_memory_usage",
            condition=lambda metrics: self._check_high_memory_usage(metrics),
            level=AlertLevel.WARNING,
            message_template="Memory usage is high",
            cooldown_minutes=20
        ))
    
    def _check_mcp_connectivity_failure(self, metrics: Dict[str, Any]) -> bool:
        """Check for MCP server connectivity issues."""
        # This would be set by health monitor
        return metrics.get('mcp_server_healthy', True) is False
    
    def _check_high_error_rate(self, metrics: Dict[str, Any]) -> bool:
        """Check for high error rate."""
        error_metrics = metrics.get('errors', {})
        system_metrics = metrics.get('system', {})
        
        total_errors = error_metrics.get('total_errors', 0)
        total_requests = system_metrics.get('total_requests', 0)
        
        if total_requests < 10:  # Not enough data
            return False
        
        error_rate = (total_errors / total_requests) * 100
        return error_rate > 10.0  # 10% error rate threshold
    
    def _check_low_cache_hit_rate(self, metrics: Dict[str, Any]) -> bool:
        """Check for low cache hit rate."""
        cache_metrics = metrics.get('cache', {})
        total_requests = cache_metrics.get('total_requests', 0)
        
        if total_requests < 20:  # Not enough data
            return False
        
        hit_rate = cache_metrics.get('hit_rate', 0)
        return hit_rate < 60.0  # 60% hit rate threshold
    
    def _check_slow_performance(self, metrics: Dict[str, Any]) -> bool:
        """Check for slow performance."""
        performance_metrics = metrics.get('performance', {})
        
        for operation, perf_data in performance_metrics.items():
            if isinstance(perf_data, dict):
                avg_duration = perf_data.get('average_duration_ms', 0)
                total_requests = perf_data.get('total_requests', 0)
                
                if total_requests >= 5 and avg_duration > 2000:  # 2 second threshold
                    return True
        
        return False
    
    def _check_validation_failures(self, metrics: Dict[str, Any]) -> bool:
        """Check for high validation failure rate."""
        validation_metrics = metrics.get('validation', {})
        total_validations = validation_metrics.get('total_validations', 0)
        
        if total_validations < 10:  # Not enough data
            return False
        
        success_rate = validation_metrics.get('success_rate', 100)
        return success_rate < 80.0  # 80% success rate threshold
    
    def _check_high_memory_usage(self, metrics: Dict[str, Any]) -> bool:
        """Check for high memory usage."""
        cache_metrics = metrics.get('cache', {})
        memory_usage = cache_metrics.get('memory_usage_mb', 0)
        
        # Alert if cache is using more than 500MB
        return memory_usage > 500.0
    
    async def check_alerts(self, health_report: Optional[SystemHealthReport] = None):
        """Check all alert rules and trigger alerts if necessary."""
        try:
            # Get current metrics
            metrics = self.metrics_collector.get_comprehensive_metrics()
            
            # Add health report data if available
            if health_report:
                metrics['health_status'] = health_report.overall_status.value
                metrics['mcp_server_healthy'] = any(
                    check.name == 'mcp_connectivity' and check.status == HealthStatus.HEALTHY
                    for check in health_report.checks
                )
            
            # Check each rule
            for rule in self.alert_rules:
                if not rule.enabled:
                    continue
                
                # Check cooldown
                if self._is_rule_in_cooldown(rule.name):
                    continue
                
                try:
                    # Evaluate rule condition
                    if rule.condition(metrics):
                        await self._trigger_alert(rule, metrics)
                    else:
                        # Check for auto-resolve
                        if rule.auto_resolve:
                            await self._auto_resolve_alerts(rule.name)
                
                except Exception as e:
                    self.logger.error(f"Error evaluating rule {rule.name}: {e}")
        
        except Exception as e:
            self.logger.error(f"Error checking alerts: {e}")
    
    async def _trigger_alert(self, rule: AlertRule, metrics: Dict[str, Any]):
        """Trigger an alert for a rule."""
        alert_id = f"{rule.name}_{int(time.time())}"
        
        # Create alert
        alert = Alert(
            id=alert_id,
            level=rule.level,
            title=rule.name.replace('_', ' ').title(),
            message=rule.message_template,
            timestamp=datetime.utcnow(),
            source="mcp_schema_manager",
            details=self._extract_relevant_metrics(rule.name, metrics)
        )
        
        # Store alert
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        
        # Trim history
        if len(self.alert_history) > self.max_history_size:
            self.alert_history.pop(0)
        
        # Set cooldown
        self.rule_cooldowns[rule.name] = datetime.utcnow() + timedelta(minutes=rule.cooldown_minutes)
        
        # Send notifications
        await self._send_alert_notifications(alert)
        
        self.logger.warning(
            f"Alert triggered: {alert.title}",
            alert_id=alert_id,
            level=rule.level.value,
            rule=rule.name
        )
    
    async def _auto_resolve_alerts(self, rule_name: str):
        """Auto-resolve alerts for a rule when condition is no longer met."""
        resolved_alerts = []
        
        for alert_id, alert in self.active_alerts.items():
            if (not alert.resolved and 
                alert.title.lower().replace(' ', '_') == rule_name):
                
                alert.resolved = True
                alert.resolved_at = datetime.utcnow()
                resolved_alerts.append(alert)
        
        # Remove resolved alerts from active alerts
        for alert in resolved_alerts:
            if alert.id in self.active_alerts:
                del self.active_alerts[alert.id]
        
        if resolved_alerts:
            self.logger.info(f"Auto-resolved {len(resolved_alerts)} alerts for rule: {rule_name}")
    
    def _is_rule_in_cooldown(self, rule_name: str) -> bool:
        """Check if rule is in cooldown period."""
        cooldown_end = self.rule_cooldowns.get(rule_name)
        if cooldown_end is None:
            return False
        return datetime.utcnow() < cooldown_end
    
    def _extract_relevant_metrics(self, rule_name: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant metrics for an alert."""
        relevant_metrics = {}
        
        if 'error' in rule_name:
            relevant_metrics.update(metrics.get('errors', {}))
        
        if 'cache' in rule_name:
            relevant_metrics.update(metrics.get('cache', {}))
        
        if 'performance' in rule_name:
            relevant_metrics.update(metrics.get('performance', {}))
        
        if 'validation' in rule_name:
            relevant_metrics.update(metrics.get('validation', {}))
        
        if 'memory' in rule_name:
            relevant_metrics['memory_usage_mb'] = metrics.get('cache', {}).get('memory_usage_mb', 0)
        
        # Always include system metrics
        relevant_metrics.update(metrics.get('system', {}))
        
        return relevant_metrics
    
    async def _send_alert_notifications(self, alert: Alert):
        """Send alert to all configured channels."""
        for channel in self.alert_channels:
            try:
                success = await channel.send_alert(alert)
                if not success:
                    self.logger.warning(f"Failed to send alert via {type(channel).__name__}")
            except Exception as e:
                self.logger.error(f"Error sending alert via {type(channel).__name__}: {e}")
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active (unresolved) alerts."""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, hours: int = 24) -> List[Alert]:
        """Get alert history for the specified number of hours."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return [alert for alert in self.alert_history if alert.timestamp >= cutoff_time]
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Manually resolve an alert."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = datetime.utcnow()
            del self.active_alerts[alert_id]
            
            self.logger.info(f"Alert resolved manually: {alert_id}")
            return True
        
        return False
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of alert status."""
        active_alerts = self.get_active_alerts()
        recent_history = self.get_alert_history(24)
        
        return {
            'active_alerts_count': len(active_alerts),
            'active_alerts_by_level': {
                level.value: len([a for a in active_alerts if a.level == level])
                for level in AlertLevel
            },
            'alerts_last_24h': len(recent_history),
            'most_recent_alert': active_alerts[0].to_dict() if active_alerts else None,
            'alert_rules_count': len(self.alert_rules),
            'enabled_rules_count': len([r for r in self.alert_rules if r.enabled]),
            'notification_channels': len(self.alert_channels)
        }
