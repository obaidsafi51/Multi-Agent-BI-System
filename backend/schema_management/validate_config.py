#!/usr/bin/env python3
"""
Configuration validation utility for MCP schema management.
"""

import os
import sys
import logging
from typing import List, Dict, Any

from .config import MCPSchemaConfig, SchemaValidationConfig

logger = logging.getLogger(__name__)


def validate_environment_variables() -> Dict[str, Any]:
    """
    Validate that all required environment variables are set.
    
    Returns:
        Dictionary with validation results
    """
    required_vars = [
        "TIDB_HOST",
        "TIDB_USER", 
        "TIDB_PASSWORD",
        "TIDB_DATABASE"
    ]
    
    optional_vars = [
        "TIDB_MCP_SERVER_URL",
        "MCP_CONNECTION_TIMEOUT",
        "MCP_REQUEST_TIMEOUT",
        "MCP_MAX_RETRIES",
        "MCP_RETRY_DELAY",
        "MCP_CACHE_TTL",
        "MCP_ENABLE_CACHING",
        "MCP_FALLBACK_ENABLED",
        "SCHEMA_STRICT_MODE",
        "SCHEMA_VALIDATE_TYPES",
        "SCHEMA_VALIDATE_CONSTRAINTS",
        "SCHEMA_VALIDATE_RELATIONSHIPS",
        "SCHEMA_ALLOW_UNKNOWN_COLUMNS"
    ]
    
    missing_required = []
    present_optional = []
    missing_optional = []
    
    # Check required variables
    for var in required_vars:
        if not os.getenv(var):
            missing_required.append(var)
    
    # Check optional variables
    for var in optional_vars:
        if os.getenv(var):
            present_optional.append(var)
        else:
            missing_optional.append(var)
    
    return {
        "valid": len(missing_required) == 0,
        "missing_required": missing_required,
        "present_optional": present_optional,
        "missing_optional": missing_optional,
        "total_required": len(required_vars),
        "total_optional": len(optional_vars)
    }


def validate_configurations() -> Dict[str, Any]:
    """
    Validate MCP and schema validation configurations.
    
    Returns:
        Dictionary with validation results
    """
    results = {
        "mcp_config": {"valid": False, "error": None, "config": None},
        "validation_config": {"valid": False, "error": None, "config": None}
    }
    
    # Validate MCP configuration
    try:
        mcp_config = MCPSchemaConfig.from_env()
        results["mcp_config"]["valid"] = True
        results["mcp_config"]["config"] = {
            "mcp_server_url": mcp_config.mcp_server_url,
            "connection_timeout": mcp_config.connection_timeout,
            "request_timeout": mcp_config.request_timeout,
            "max_retries": mcp_config.max_retries,
            "retry_delay": mcp_config.retry_delay,
            "cache_ttl": mcp_config.cache_ttl,
            "enable_caching": mcp_config.enable_caching,
            "fallback_enabled": mcp_config.fallback_enabled
        }
    except Exception as e:
        results["mcp_config"]["error"] = str(e)
    
    # Validate schema validation configuration
    try:
        validation_config = SchemaValidationConfig.from_env()
        results["validation_config"]["valid"] = True
        results["validation_config"]["config"] = {
            "strict_mode": validation_config.strict_mode,
            "validate_types": validation_config.validate_types,
            "validate_constraints": validation_config.validate_constraints,
            "validate_relationships": validation_config.validate_relationships,
            "allow_unknown_columns": validation_config.allow_unknown_columns
        }
    except Exception as e:
        results["validation_config"]["error"] = str(e)
    
    return results


def print_validation_report(env_results: Dict[str, Any], config_results: Dict[str, Any]) -> None:
    """Print a formatted validation report."""
    print("=" * 60)
    print("MCP SCHEMA MANAGEMENT CONFIGURATION VALIDATION")
    print("=" * 60)
    
    # Environment variables report
    print("\n📋 ENVIRONMENT VARIABLES:")
    if env_results["valid"]:
        print("✅ All required environment variables are set")
    else:
        print("❌ Missing required environment variables:")
        for var in env_results["missing_required"]:
            print(f"   - {var}")
    
    print(f"\n📊 SUMMARY:")
    print(f"   Required variables: {len(env_results['missing_required']) == 0} "
          f"({len(env_results['missing_required'])} missing)")
    print(f"   Optional variables: {len(env_results['present_optional'])} present, "
          f"{len(env_results['missing_optional'])} using defaults")
    
    # Configuration validation report
    print("\n⚙️  CONFIGURATION VALIDATION:")
    
    # MCP Config
    mcp_result = config_results["mcp_config"]
    if mcp_result["valid"]:
        print("✅ MCP Schema Configuration: Valid")
        config = mcp_result["config"]
        print(f"   Server URL: {config['mcp_server_url']}")
        print(f"   Timeouts: {config['connection_timeout']}s / {config['request_timeout']}s")
        print(f"   Retries: {config['max_retries']} (delay: {config['retry_delay']}s)")
        print(f"   Caching: {'Enabled' if config['enable_caching'] else 'Disabled'} (TTL: {config['cache_ttl']}s)")
        print(f"   Fallback: {'Enabled' if config['fallback_enabled'] else 'Disabled'}")
    else:
        print("❌ MCP Schema Configuration: Invalid")
        print(f"   Error: {mcp_result['error']}")
    
    # Validation Config
    validation_result = config_results["validation_config"]
    if validation_result["valid"]:
        print("✅ Schema Validation Configuration: Valid")
        config = validation_result["config"]
        print(f"   Strict mode: {'Enabled' if config['strict_mode'] else 'Disabled'}")
        print(f"   Validation: Types={config['validate_types']}, "
              f"Constraints={config['validate_constraints']}, "
              f"Relationships={config['validate_relationships']}")
        print(f"   Unknown columns: {'Allowed' if config['allow_unknown_columns'] else 'Rejected'}")
    else:
        print("❌ Schema Validation Configuration: Invalid")
        print(f"   Error: {validation_result['error']}")
    
    # Overall status
    overall_valid = (env_results["valid"] and 
                    config_results["mcp_config"]["valid"] and 
                    config_results["validation_config"]["valid"])
    
    print(f"\n🎯 OVERALL STATUS: {'✅ VALID' if overall_valid else '❌ INVALID'}")
    print("=" * 60)


def main():
    """Main validation function."""
    logging.basicConfig(level=logging.INFO)
    
    print("Validating MCP Schema Management Configuration...")
    
    # Validate environment variables
    env_results = validate_environment_variables()
    
    # Validate configurations
    config_results = validate_configurations()
    
    # Print report
    print_validation_report(env_results, config_results)
    
    # Exit with appropriate code
    overall_valid = (env_results["valid"] and 
                    config_results["mcp_config"]["valid"] and 
                    config_results["validation_config"]["valid"])
    
    sys.exit(0 if overall_valid else 1)


if __name__ == "__main__":
    main()