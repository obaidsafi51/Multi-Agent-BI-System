"""Main entry point for Universal MCP Server with HTTP API support."""

import argparse
import asyncio
import logging
import os
import signal
import sys
from typing import Optional

import uvicorn

from .config import load_config
from .exceptions import ConfigurationError, DatabaseConnectionError
from .mcp_server import UniversalMCPServer


def setup_logging(log_level: str, log_format: str) -> None:
    """Set up logging configuration with structured logging."""
    level = getattr(logging, log_level.upper())
    
    if log_format == "json":
        # JSON structured logging format
        format_str = (
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"logger": "%(name)s", "message": "%(message)s", '
            '"module": "%(module)s", "function": "%(funcName)s", "line": %(lineno)d}'
        )
    else:
        # Human-readable text format
        format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s [%(module)s:%(funcName)s:%(lineno)d]"
    
    logging.basicConfig(
        level=level,
        format=format_str,
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Set specific log levels for external libraries
    logging.getLogger("pymysql").setLevel(logging.WARNING)
    logging.getLogger("fastmcp").setLevel(logging.INFO)


async def main_async(config=None) -> int:
    """Async main entry point for the Universal MCP Server with HTTP API."""
    server: Optional[UniversalMCPServer] = None
    
    try:
        # Load configuration if not provided
        if config is None:
            config = load_config()
        
        logger = logging.getLogger(__name__)
        
        # Check if HTTP API mode is enabled
        use_http_api = os.getenv('USE_HTTP_API', 'true').lower() == 'true'
        
        if use_http_api:
            logger.info(
                f"Starting Universal MCP Server v{config.mcp_server_version} with HTTP API "
                f"connecting to {config.tidb_host}:{config.tidb_port}",
                extra={
                    "server_version": config.mcp_server_version,
                    "tidb_host": config.tidb_host,
                    "tidb_port": config.tidb_port,
                    "log_level": config.log_level,
                    "http_api_enabled": True,
                    "enabled_tools": config.enabled_tools
                }
            )
            
            # Start HTTP API server
            from .http_api import app
            
            # Configure uvicorn
            uvicorn_config = uvicorn.Config(
                app=app,
                host="0.0.0.0",
                port=8000,
                log_level=config.log_level.lower(),
                access_log=True
            )
            
            server_instance = uvicorn.Server(uvicorn_config)
            await server_instance.serve()
            
        else:
            # Original MCP protocol mode
            logger.info(
                f"Starting Universal MCP Server v{config.mcp_server_version} "
                f"connecting to {config.tidb_host}:{config.tidb_port}",
                extra={
                    "server_version": config.mcp_server_version,
                    "tidb_host": config.tidb_host,
                    "tidb_port": config.tidb_port,
                    "log_level": config.log_level,
                    "http_api_enabled": False,
                    "enabled_tools": config.enabled_tools
                }
            )
            
            # Validate configuration
            config.validate_configuration()
            logger.info("Configuration validation successful")
            
            # Initialize and start MCP server
            server = UniversalMCPServer(config)
            
            # Set up signal handlers for graceful shutdown
            def signal_handler(signum, frame):
                logger.info(f"Received signal {signum}, initiating graceful shutdown...")
                if server:
                    asyncio.create_task(server.shutdown())
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            # Start the server
            await server.start()
        
        return 0
        
    except ConfigurationError as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Configuration error: {e}", extra={"error_type": "configuration"})
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1
    except DatabaseConnectionError as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Database connection error: {e}", extra={"error_type": "database_connection"})
        print(f"Database connection error: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.exception(f"Unexpected error: {e}", extra={"error_type": "unexpected"})
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 3
    finally:
        if server:
            try:
                await server.shutdown()
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.error(f"Error during server shutdown: {e}")


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="TiDB MCP Server - Model Context Protocol server for TiDB Cloud",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  TIDB_HOST          TiDB Cloud host (required)
  TIDB_PORT          TiDB Cloud port (default: 4000)
  TIDB_USER          TiDB Cloud username (required)
  TIDB_PASSWORD      TiDB Cloud password (required)
  TIDB_DATABASE      TiDB Cloud database name (required)
  TIDB_SSL_CA        Path to SSL CA certificate (optional)
  MCP_SERVER_NAME    MCP server name (default: tidb-mcp-server)
  MCP_SERVER_VERSION MCP server version (default: 0.1.0)
  LOG_LEVEL          Logging level (default: INFO)
  LOG_FORMAT         Logging format: text or json (default: text)
  CACHE_TTL          Cache TTL in seconds (default: 300)
  CACHE_MAX_SIZE     Maximum cache size (default: 1000)
  RATE_LIMIT_REQUESTS Rate limit requests per minute (default: 100)
  RATE_LIMIT_WINDOW  Rate limit window in seconds (default: 60)

Examples:
  tidb-mcp-server
  tidb-mcp-server --log-level DEBUG
  tidb-mcp-server --validate-config
        """
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set logging level (overrides LOG_LEVEL env var)"
    )
    
    parser.add_argument(
        "--log-format",
        choices=["text", "json"],
        help="Set logging format (overrides LOG_FORMAT env var)"
    )
    
    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="Validate configuration and exit"
    )
    
    parser.add_argument(
        "--check-connection",
        action="store_true",
        help="Test database connection and exit"
    )
    
    return parser.parse_args()


async def validate_config_and_connection(config) -> int:
    """Validate configuration and test database connection."""
    logger = logging.getLogger(__name__)
    
    try:
        # Validate configuration
        config.validate_configuration()
        logger.info("✓ Configuration validation successful")
        
        # Test database connection
        from .query_executor import QueryExecutor
        executor = QueryExecutor(config)
        
        await executor.test_connection()
        logger.info("✓ Database connection test successful")
        
        return 0
        
    except ConfigurationError as e:
        logger.error(f"✗ Configuration error: {e}")
        return 1
    except DatabaseConnectionError as e:
        logger.error(f"✗ Database connection error: {e}")
        return 2
    except Exception as e:
        logger.error(f"✗ Unexpected error: {e}")
        return 3


def main() -> int:
    """Main entry point for the TiDB MCP Server."""
    args = parse_arguments()
    
    try:
        # Load configuration
        config = load_config()
        
        # Override config with command-line arguments
        if args.log_level:
            config.log_level = args.log_level
        if args.log_format:
            config.log_format = args.log_format
        
        # Setup logging early
        setup_logging(config.log_level, config.log_format)
        
        # Handle validation-only mode
        if args.validate_config or args.check_connection:
            return asyncio.run(validate_config_and_connection(config))
        
        # Run the main server
        return asyncio.run(main_async(config))
        
    except KeyboardInterrupt:
        print("\nServer interrupted by user", file=sys.stderr)
        return 130  # Standard exit code for SIGINT
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())