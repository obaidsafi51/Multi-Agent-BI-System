#!/usr/bin/env python3
"""
Startup script that validates MCP configuration and waits for server availability.
"""

import asyncio
import sys
import logging
import os

# Add the backend directory to the path
sys.path.insert(0, '/app')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Main startup function with MCP validation."""
    try:
        logger.info("Starting MCP Schema Management validation...")
        
        # Validate configuration
        from schema_management.validate_config import validate_environment_variables, validate_configurations
        
        env_results = validate_environment_variables()
        if not env_results["valid"]:
            logger.error(f"Missing required environment variables: {env_results['missing_required']}")
            sys.exit(1)
        
        config_results = validate_configurations()
        if not config_results["mcp_config"]["valid"]:
            logger.error(f"Invalid MCP configuration: {config_results['mcp_config']['error']}")
            sys.exit(1)
        
        logger.info("Configuration validation passed")
        
        # Wait for MCP server to be available
        from schema_management.health_check import wait_for_mcp_server
        from schema_management.config import load_mcp_config
        
        config = load_mcp_config()
        logger.info(f"Waiting for MCP server at {config.mcp_server_url}...")
        
        if await wait_for_mcp_server(config, max_wait_seconds=60):
            logger.info("MCP server is available and healthy")
            print("MCP_READY")  # Signal for Docker health check
            sys.exit(0)
        else:
            logger.error("MCP server did not become available within timeout")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Startup validation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())