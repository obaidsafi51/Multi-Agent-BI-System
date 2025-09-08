"""
Configuration for MCP monitoring and observability features.

This module provides configuration options for all monitoring components
including logging, metrics, alerting, and performance tracking.
"""

import os
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import logging


@dataclass
class LoggingConfig:
    """Configuration for structured logging."""
    
    enable_json_logging: bool = True
    log_level: str = "INFO"
    enable_file_logging: bool = True
    log_file_path: Optional[str] = None
    max_log_file_size_mb: int = 100
    log_rotation_count: int = 5
    enable_request_id_tracking: bool = True
    sensitive_fields: List[str] = None
    
    def __post_init__(self):
        if self.sensitive_fields is None:
            self.sensitive_fields = ['password', 'token', 'secret', 'key']
        
        if self.log_file_path is None:
            self.log_file_path = os.path.join("logs", "mcp_schema_management.log")
    
    @classmethod
    def from_env(cls) -> "LoggingConfig":
        """Create logging configuration from environment variables."""
        return cls(
            enable_json_logging=os.getenv("MCP_ENABLE_JSON_LOGGING", "true").lower() == "true",
            log_level=os.getenv("MCP_LOG_LEVEL", "INFO").upper(),
            enable_file_logging=os.getenv("MCP_ENABLE_FILE_LOGGING", "true").lower() == "true",
            log_file_path=os.getenv("MCP_LOG_FILE_PATH"),
            max_log_file_size_mb=int(os.getenv("MCP_LOG_FILE_SIZE_MB", "100")),
            log_rotation_count=int(os.getenv("MCP_LOG_ROTATION_COUNT", "5")),
            enable_request_id_tracking=os.getenv("MCP_ENABLE_REQUEST_ID_TRACKING", "true").lower() == "true"
        )


@dataclass
class MetricsConfig:
    """Configuration for metrics collection."""
    
    enable_metrics: bool = True
    metrics_retention_hours: int = 24
    max_performance_snapshots: int = 10000
    enable_cache_metrics: bool = True
    enable_performance_metrics: bool = True
    enable_validation_metrics: bool = True
    enable_error_metrics: bool = True
    metrics_collection_interval_seconds: int = 60
    
    @classmethod
    def from_env(cls) -> "MetricsConfig":
        """Create metrics configuration from environment variables."""
        return cls(
            enable_metrics=os.getenv("MCP_ENABLE_METRICS", "true").lower() == "true",
            metrics_retention_hours=int(os.getenv("MCP_METRICS_RETENTION_HOURS", "24")),
            max_performance_snapshots=int(os.getenv("MCP_MAX_PERFORMANCE_SNAPSHOTS", "10000")),
            enable_cache_metrics=os.getenv("MCP_ENABLE_CACHE_METRICS", "true").lower() == "true",
            enable_performance_metrics=os.getenv("MCP_ENABLE_PERFORMANCE_METRICS", "true").lower() == "true",
            enable_validation_metrics=os.getenv("MCP_ENABLE_VALIDATION_METRICS", "true").lower() == "true",
            enable_error_metrics=os.getenv("MCP_ENABLE_ERROR_METRICS", "true").lower() == "true",
            metrics_collection_interval_seconds=int(os.getenv("MCP_METRICS_COLLECTION_INTERVAL", "60"))
        )


@dataclass
class HealthMonitorConfig:
    """Configuration for health monitoring."""
    
    enable_health_monitoring: bool = True
    health_check_interval_seconds: int = 30
    connectivity_timeout_seconds: int = 5
    performance_threshold_ms: float = 1000.0
    cache_hit_rate_threshold: float = 70.0
    validation_success_threshold: float = 95.0
    error_rate_threshold: float = 5.0
    enable_system_resource_monitoring: bool = True
    health_history_retention_hours: int = 48
    
    @classmethod
    def from_env(cls) -> "HealthMonitorConfig":
        """Create health monitor configuration from environment variables."""
        return cls(
            enable_health_monitoring=os.getenv("MCP_ENABLE_HEALTH_MONITORING", "true").lower() == "true",
            health_check_interval_seconds=int(os.getenv("MCP_HEALTH_CHECK_INTERVAL", "30")),
            connectivity_timeout_seconds=int(os.getenv("MCP_CONNECTIVITY_TIMEOUT", "5")),
            performance_threshold_ms=float(os.getenv("MCP_PERFORMANCE_THRESHOLD_MS", "1000.0")),
            cache_hit_rate_threshold=float(os.getenv("MCP_CACHE_HIT_RATE_THRESHOLD", "70.0")),
            validation_success_threshold=float(os.getenv("MCP_VALIDATION_SUCCESS_THRESHOLD", "95.0")),
            error_rate_threshold=float(os.getenv("MCP_ERROR_RATE_THRESHOLD", "5.0")),
            enable_system_resource_monitoring=os.getenv("MCP_ENABLE_SYSTEM_RESOURCE_MONITORING", "true").lower() == "true",
            health_history_retention_hours=int(os.getenv("MCP_HEALTH_HISTORY_RETENTION_HOURS", "48"))
        )


@dataclass
class AlertConfig:
    """Configuration for alerting system."""
    
    enable_alerting: bool = True
    enable_email_alerts: bool = False
    enable_webhook_alerts: bool = False
    enable_slack_alerts: bool = False
    alert_cooldown_minutes: int = 5
    max_alert_history: int = 1000
    
    # Email configuration
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True
    email_from: Optional[str] = None
    email_recipients: List[str] = None
    
    # Webhook configuration
    webhook_url: Optional[str] = None
    webhook_headers: Dict[str, str] = None
    
    # Slack configuration
    slack_webhook_url: Optional[str] = None
    slack_channel: Optional[str] = None
    
    def __post_init__(self):
        if self.email_recipients is None:
            self.email_recipients = []
        if self.webhook_headers is None:
            self.webhook_headers = {}
    
    @classmethod
    def from_env(cls) -> "AlertConfig":
        """Create alert configuration from environment variables."""
        email_recipients = []
        if os.getenv("MCP_ALERT_EMAIL_RECIPIENTS"):
            email_recipients = [
                email.strip() for email in 
                os.getenv("MCP_ALERT_EMAIL_RECIPIENTS", "").split(",")
                if email.strip()
            ]
        
        webhook_headers = {}
        if os.getenv("MCP_WEBHOOK_HEADERS"):
            try:
                import json
                webhook_headers = json.loads(os.getenv("MCP_WEBHOOK_HEADERS"))
            except (json.JSONDecodeError, TypeError):
                logging.warning("Invalid MCP_WEBHOOK_HEADERS format, using empty headers")
        
        return cls(
            enable_alerting=os.getenv("MCP_ENABLE_ALERTING", "true").lower() == "true",
            enable_email_alerts=os.getenv("MCP_ENABLE_EMAIL_ALERTS", "false").lower() == "true",
            enable_webhook_alerts=os.getenv("MCP_ENABLE_WEBHOOK_ALERTS", "false").lower() == "true",
            enable_slack_alerts=os.getenv("MCP_ENABLE_SLACK_ALERTS", "false").lower() == "true",
            alert_cooldown_minutes=int(os.getenv("MCP_ALERT_COOLDOWN_MINUTES", "5")),
            max_alert_history=int(os.getenv("MCP_MAX_ALERT_HISTORY", "1000")),
            
            # Email settings
            smtp_host=os.getenv("MCP_SMTP_HOST"),
            smtp_port=int(os.getenv("MCP_SMTP_PORT", "587")),
            smtp_user=os.getenv("MCP_SMTP_USER"),
            smtp_password=os.getenv("MCP_SMTP_PASSWORD"),
            smtp_use_tls=os.getenv("MCP_SMTP_USE_TLS", "true").lower() == "true",
            email_from=os.getenv("MCP_ALERT_EMAIL_FROM"),
            email_recipients=email_recipients,
            
            # Webhook settings
            webhook_url=os.getenv("MCP_WEBHOOK_URL"),
            webhook_headers=webhook_headers,
            
            # Slack settings
            slack_webhook_url=os.getenv("MCP_SLACK_WEBHOOK_URL"),
            slack_channel=os.getenv("MCP_SLACK_CHANNEL")
        )


@dataclass
class PerformanceConfig:
    """Configuration for performance tracking."""
    
    enable_performance_tracking: bool = True
    max_snapshots: int = 10000
    trend_window_minutes: int = 60
    trend_cache_ttl_minutes: int = 5
    anomaly_threshold_multiplier: float = 2.0
    enable_optimization_recommendations: bool = True
    baseline_sample_threshold: int = 10
    
    @classmethod
    def from_env(cls) -> "PerformanceConfig":
        """Create performance configuration from environment variables."""
        return cls(
            enable_performance_tracking=os.getenv("MCP_ENABLE_PERFORMANCE_TRACKING", "true").lower() == "true",
            max_snapshots=int(os.getenv("MCP_PERFORMANCE_MAX_SNAPSHOTS", "10000")),
            trend_window_minutes=int(os.getenv("MCP_PERFORMANCE_TREND_WINDOW_MINUTES", "60")),
            trend_cache_ttl_minutes=int(os.getenv("MCP_PERFORMANCE_TREND_CACHE_TTL_MINUTES", "5")),
            anomaly_threshold_multiplier=float(os.getenv("MCP_ANOMALY_THRESHOLD_MULTIPLIER", "2.0")),
            enable_optimization_recommendations=os.getenv("MCP_ENABLE_OPTIMIZATION_RECOMMENDATIONS", "true").lower() == "true",
            baseline_sample_threshold=int(os.getenv("MCP_BASELINE_SAMPLE_THRESHOLD", "10"))
        )


@dataclass
class MonitoringConfig:
    """Comprehensive monitoring configuration."""
    
    enable_monitoring: bool = True
    logging: LoggingConfig = None
    metrics: MetricsConfig = None
    health_monitor: HealthMonitorConfig = None
    alerting: AlertConfig = None
    performance: PerformanceConfig = None
    
    def __post_init__(self):
        if self.logging is None:
            self.logging = LoggingConfig.from_env()
        if self.metrics is None:
            self.metrics = MetricsConfig.from_env()
        if self.health_monitor is None:
            self.health_monitor = HealthMonitorConfig.from_env()
        if self.alerting is None:
            self.alerting = AlertConfig.from_env()
        if self.performance is None:
            self.performance = PerformanceConfig.from_env()
    
    @classmethod
    def from_env(cls) -> "MonitoringConfig":
        """Create comprehensive monitoring configuration from environment variables."""
        return cls(
            enable_monitoring=os.getenv("MCP_ENABLE_MONITORING", "true").lower() == "true",
            logging=LoggingConfig.from_env(),
            metrics=MetricsConfig.from_env(),
            health_monitor=HealthMonitorConfig.from_env(),
            alerting=AlertConfig.from_env(),
            performance=PerformanceConfig.from_env()
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'enable_monitoring': self.enable_monitoring,
            'logging': self.logging.__dict__,
            'metrics': self.metrics.__dict__,
            'health_monitor': self.health_monitor.__dict__,
            'alerting': {
                **self.alerting.__dict__,
                # Mask sensitive fields
                'smtp_password': '***' if self.alerting.smtp_password else None,
                'webhook_headers': {k: '***' if 'auth' in k.lower() or 'token' in k.lower() else v
                                   for k, v in self.alerting.webhook_headers.items()}
            },
            'performance': self.performance.__dict__
        }
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of issues."""
        issues = []
        
        # Validate logging configuration
        if self.logging.enable_file_logging and not self.logging.log_file_path:
            issues.append("File logging enabled but no log file path specified")
        
        # Validate alert configuration
        if self.alerting.enable_email_alerts:
            if not all([self.alerting.smtp_host, self.alerting.smtp_user, self.alerting.email_from]):
                issues.append("Email alerts enabled but SMTP configuration incomplete")
            if not self.alerting.email_recipients:
                issues.append("Email alerts enabled but no recipients specified")
        
        if self.alerting.enable_webhook_alerts and not self.alerting.webhook_url:
            issues.append("Webhook alerts enabled but no webhook URL specified")
        
        if self.alerting.enable_slack_alerts and not self.alerting.slack_webhook_url:
            issues.append("Slack alerts enabled but no Slack webhook URL specified")
        
        # Validate thresholds
        if self.health_monitor.cache_hit_rate_threshold < 0 or self.health_monitor.cache_hit_rate_threshold > 100:
            issues.append("Cache hit rate threshold must be between 0 and 100")
        
        if self.health_monitor.validation_success_threshold < 0 or self.health_monitor.validation_success_threshold > 100:
            issues.append("Validation success threshold must be between 0 and 100")
        
        if self.health_monitor.error_rate_threshold < 0 or self.health_monitor.error_rate_threshold > 100:
            issues.append("Error rate threshold must be between 0 and 100")
        
        return issues


def load_monitoring_config() -> MonitoringConfig:
    """Load and validate monitoring configuration."""
    config = MonitoringConfig.from_env()
    
    # Validate configuration
    issues = config.validate()
    if issues:
        logger = logging.getLogger(__name__)
        logger.warning(f"Monitoring configuration issues: {'; '.join(issues)}")
    
    return config


def setup_monitoring_environment():
    """Set up monitoring environment with proper logging and error handling."""
    try:
        config = load_monitoring_config()
        
        # Ensure log directory exists
        if config.logging.enable_file_logging and config.logging.log_file_path:
            import os
            os.makedirs(os.path.dirname(config.logging.log_file_path), exist_ok=True)
        
        return config
    
    except Exception as e:
        # Fallback to basic configuration
        logging.error(f"Failed to load monitoring configuration: {e}")
        return MonitoringConfig(
            enable_monitoring=False,
            logging=LoggingConfig(enable_json_logging=False, enable_file_logging=False),
            metrics=MetricsConfig(enable_metrics=False),
            health_monitor=HealthMonitorConfig(enable_health_monitoring=False),
            alerting=AlertConfig(enable_alerting=False),
            performance=PerformanceConfig(enable_performance_tracking=False)
        )
