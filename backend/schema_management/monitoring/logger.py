"""
Structured logging for MCP schema management operations.

This module provides enhanced logging capabilities with structured output,
context tracking, and performance monitoring for all MCP operations.
"""

import json
import logging
import sys
import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Optional, Union
from functools import wraps


class MCPStructuredLogger:
    """
    Structured logger for MCP operations with context tracking and performance monitoring.
    
    Provides JSON-formatted logging with automatic context enrichment and
    execution time tracking for MCP schema management operations.
    """
    
    def __init__(self, name: str, enable_json: bool = True):
        """
        Initialize structured logger.
        
        Args:
            name: Logger name
            enable_json: Whether to use JSON formatting
        """
        self.logger = logging.getLogger(name)
        self.enable_json = enable_json
        self._context: Dict[str, Any] = {}
        
        # Set up formatters if not already configured
        if not self.logger.handlers:
            self._setup_formatters()
    
    def _setup_formatters(self):
        """Set up logging formatters."""
        if self.enable_json:
            formatter = JSONFormatter()
        else:
            formatter = StructuredTextFormatter()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # Set level from environment or default to INFO
        import os
        log_level = os.getenv('MCP_LOG_LEVEL', 'INFO').upper()
        self.logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    def set_context(self, **kwargs):
        """Set persistent context that will be included in all log entries."""
        self._context.update(kwargs)
    
    def clear_context(self):
        """Clear all persistent context."""
        self._context.clear()
    
    def _enrich_record(self, record, extra: Optional[Dict[str, Any]] = None):
        """Enrich log record with context and metadata."""
        # Add timestamp
        record.timestamp = datetime.utcnow().isoformat() + 'Z'
        
        # Add persistent context
        for key, value in self._context.items():
            setattr(record, key, value)
        
        # Add extra data
        if extra:
            for key, value in extra.items():
                setattr(record, key, value)
        
        # Add request ID if not present
        if not hasattr(record, 'request_id'):
            record.request_id = str(uuid.uuid4())[:8]
        
        return record
    
    def debug(self, message: str, **extra):
        """Log debug message with structured data."""
        record = self.logger.makeRecord(
            self.logger.name, logging.DEBUG, "", 0, message, None, None
        )
        self._enrich_record(record, extra)
        self.logger.handle(record)
    
    def info(self, message: str, **extra):
        """Log info message with structured data."""
        record = self.logger.makeRecord(
            self.logger.name, logging.INFO, "", 0, message, None, None
        )
        self._enrich_record(record, extra)
        self.logger.handle(record)
    
    def warning(self, message: str, **extra):
        """Log warning message with structured data."""
        record = self.logger.makeRecord(
            self.logger.name, logging.WARNING, "", 0, message, None, None
        )
        self._enrich_record(record, extra)
        self.logger.handle(record)
    
    def error(self, message: str, **extra):
        """Log error message with structured data."""
        record = self.logger.makeRecord(
            self.logger.name, logging.ERROR, "", 0, message, None, None
        )
        self._enrich_record(record, extra)
        self.logger.handle(record)
    
    def critical(self, message: str, **extra):
        """Log critical message with structured data."""
        record = self.logger.makeRecord(
            self.logger.name, logging.CRITICAL, "", 0, message, None, None
        )
        self._enrich_record(record, extra)
        self.logger.handle(record)
    
    @contextmanager
    def operation_context(self, operation: str, **context):
        """
        Context manager for operation logging with automatic timing.
        
        Args:
            operation: Operation name
            **context: Additional context data
        """
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        
        self.info(
            f"Starting {operation}",
            operation=operation,
            request_id=request_id,
            **context
        )
        
        try:
            yield request_id
            
            duration_ms = (time.time() - start_time) * 1000
            self.info(
                f"Completed {operation}",
                operation=operation,
                request_id=request_id,
                duration_ms=duration_ms,
                success=True,
                **context
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.error(
                f"Failed {operation}",
                operation=operation,
                request_id=request_id,
                duration_ms=duration_ms,
                success=False,
                error_type=type(e).__name__,
                error_message=str(e),
                **context
            )
            raise


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""
    
    def format(self, record):
        """Format log record as JSON."""
        log_entry = {
            'timestamp': getattr(record, 'timestamp', datetime.utcnow().isoformat() + 'Z'),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        
        # Add all custom attributes
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'getMessage', 'exc_info', 
                          'exc_text', 'stack_info']:
                try:
                    # Try to serialize the value
                    json.dumps(value)
                    log_entry[key] = value
                except (TypeError, ValueError):
                    # If not serializable, convert to string
                    log_entry[key] = str(value)
        
        return json.dumps(log_entry, default=str)


class StructuredTextFormatter(logging.Formatter):
    """Human-readable structured log formatter."""
    
    def format(self, record):
        """Format log record as structured text."""
        timestamp = getattr(record, 'timestamp', datetime.utcnow().isoformat() + 'Z')
        
        # Base format
        base_msg = f"{timestamp} - {record.name} - {record.levelname} - {record.getMessage()}"
        
        # Add structured data
        extras = []
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'getMessage', 'exc_info', 
                          'exc_text', 'stack_info', 'timestamp']:
                extras.append(f"{key}={value}")
        
        if extras:
            return f"{base_msg} [{', '.join(extras)}]"
        return base_msg


def log_mcp_operation(operation_name: str):
    """
    Decorator for automatic MCP operation logging.
    
    Args:
        operation_name: Name of the operation to log
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = MCPStructuredLogger(f"mcp.{operation_name}")
            
            # Extract context from args/kwargs
            context = {}
            if len(args) > 0 and hasattr(args[0], '__dict__'):
                context['class'] = args[0].__class__.__name__
            
            # Add function arguments as context (excluding sensitive data)
            safe_kwargs = {k: v for k, v in kwargs.items() 
                          if k not in ['password', 'token', 'secret']}
            context.update(safe_kwargs)
            
            with logger.operation_context(operation_name, **context):
                return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = MCPStructuredLogger(f"mcp.{operation_name}")
            
            # Extract context from args/kwargs
            context = {}
            if len(args) > 0 and hasattr(args[0], '__dict__'):
                context['class'] = args[0].__class__.__name__
            
            # Add function arguments as context (excluding sensitive data)
            safe_kwargs = {k: v for k, v in kwargs.items() 
                          if k not in ['password', 'token', 'secret']}
            context.update(safe_kwargs)
            
            start_time = time.time()
            request_id = str(uuid.uuid4())[:8]
            
            logger.info(
                f"Starting {operation_name}",
                operation=operation_name,
                request_id=request_id,
                **context
            )
            
            try:
                result = func(*args, **kwargs)
                
                duration_ms = (time.time() - start_time) * 1000
                logger.info(
                    f"Completed {operation_name}",
                    operation=operation_name,
                    request_id=request_id,
                    duration_ms=duration_ms,
                    success=True,
                    **context
                )
                
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"Failed {operation_name}",
                    operation=operation_name,
                    request_id=request_id,
                    duration_ms=duration_ms,
                    success=False,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    **context
                )
                raise
        
        if hasattr(func, '__code__') and 'await' in func.__code__.co_names:
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def setup_mcp_logging(
    enable_json: bool = True,
    log_level: str = "INFO",
    enable_file_logging: bool = False,
    log_file: Optional[str] = None
) -> Dict[str, MCPStructuredLogger]:
    """
    Set up comprehensive MCP logging configuration.
    
    Args:
        enable_json: Whether to use JSON formatting
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_file_logging: Whether to enable file logging
        log_file: Path to log file (defaults to mcp_schema_management.log)
        
    Returns:
        Dictionary of configured loggers by component
    """
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Set up formatters
    if enable_json:
        formatter = JSONFormatter()
    else:
        formatter = StructuredTextFormatter()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler if enabled
    if enable_file_logging:
        import os
        log_dir = os.path.dirname(log_file) if log_file else "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_path = log_file or os.path.join(log_dir, "mcp_schema_management.log")
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Create component-specific loggers
    loggers = {
        'schema_manager': MCPStructuredLogger('mcp.schema_manager', enable_json),
        'client': MCPStructuredLogger('mcp.client', enable_json),
        'validator': MCPStructuredLogger('mcp.validator', enable_json),
        'cache': MCPStructuredLogger('mcp.cache', enable_json),
        'health': MCPStructuredLogger('mcp.health', enable_json),
        'metrics': MCPStructuredLogger('mcp.metrics', enable_json),
        'alerts': MCPStructuredLogger('mcp.alerts', enable_json),
    }
    
    return loggers


# Global logger instances for easy access
_loggers = {}

def get_logger(component: str) -> MCPStructuredLogger:
    """Get or create a logger for a specific component."""
    if component not in _loggers:
        _loggers[component] = MCPStructuredLogger(f'mcp.{component}')
    return _loggers[component]
