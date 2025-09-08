"""
AI CFO Backend Package

This package contains the FastAPI backend for the AI CFO BI Agent,
including database utilities, models, and API endpoints.
"""

__version__ = "0.1.0"

# Import configuration utilities for easy access
from .schema_management.config import (
    MCPSchemaConfig,
    SchemaValidationConfig,
    load_mcp_config,
    load_validation_config
)

__all__ = [
    "MCPSchemaConfig",
    "SchemaValidationConfig", 
    "load_mcp_config",
    "load_validation_config"
]