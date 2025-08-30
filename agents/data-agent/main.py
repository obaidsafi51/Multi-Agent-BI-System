"""
Data Agent with TiDB Integration
Main entry point for the Data Agent service with comprehensive TiDB integration,
query processing, caching, validation, and optimization capabilities.
"""

import asyncio
import json
import logging
import os
import signal
import sys
from typing import Dict, Any
from dotenv import load_dotenv

import structlog
from src.agent import get_data_agent, close_data_agent

# Load environment variables
load_dotenv()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Global flag for graceful shutdown
shutdown_event = asyncio.Event()
data_agent = None

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info("Received shutdown signal", signal=signum)
    shutdown_event.set()

async def health_check_loop():
    """Periodic health check loop"""
    global data_agent
    
    while not shutdown_event.is_set():
        try:
            if data_agent:
                health_status = await data_agent.health_check()
                
                if health_status['status'] != 'healthy':
                    logger.warning("Data Agent health check warning", health_status=health_status)
                else:
                    logger.debug("Data Agent health check passed")
            
            await asyncio.sleep(60)  # Check every minute
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            await asyncio.sleep(60)

async def metrics_reporting_loop():
    """Periodic metrics reporting loop"""
    global data_agent
    
    while not shutdown_event.is_set():
        try:
            if data_agent:
                metrics = await data_agent.get_metrics()
                logger.info("Data Agent metrics", metrics=metrics)
            
            await asyncio.sleep(300)  # Report every 5 minutes
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Metrics reporting failed", error=str(e))
            await asyncio.sleep(300)

async def process_sample_queries():
    """Process sample queries for testing and demonstration"""
    global data_agent
    
    if not data_agent:
        return
    
    sample_queries = [
        {
            'metric_type': 'revenue',
            'time_period': 'this year',
            'aggregation_level': 'monthly',
            'filters': {},
            'comparison_periods': ['last year']
        },
        {
            'metric_type': 'cash_flow',
            'time_period': 'Q1 2024',
            'aggregation_level': 'monthly',
            'filters': {},
            'comparison_periods': []
        },
        {
            'metric_type': 'budget_variance',
            'time_period': 'this month',
            'aggregation_level': 'daily',
            'filters': {'department': 'sales'},
            'comparison_periods': []
        }
    ]
    
    logger.info("Processing sample queries for demonstration")
    
    for i, query_intent in enumerate(sample_queries):
        try:
            logger.info("Processing sample query", query_number=i+1, query_intent=query_intent)
            
            result = await data_agent.process_query(query_intent)
            
            logger.info(
                "Sample query completed",
                query_number=i+1,
                success=result['success'],
                row_count=result.get('row_count', 0),
                processing_time_ms=result['metadata']['processing_time_ms']
            )
            
        except Exception as e:
            logger.error("Sample query failed", query_number=i+1, error=str(e))
        
        # Small delay between queries
        await asyncio.sleep(2)

async def main():
    global data_agent
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Data Agent starting...")
    
    # Validate environment variables
    required_env_vars = ['DATABASE_URL', 'REDIS_URL']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error("Missing required environment variables", missing_vars=missing_vars)
        sys.exit(1)
    
    logger.info("Environment variables validated successfully")
    
    try:
        # Initialize Data Agent
        logger.info("Initializing Data Agent...")
        data_agent = await get_data_agent()
        logger.info("Data Agent initialized successfully")
        
        # Start background tasks
        health_task = asyncio.create_task(health_check_loop())
        metrics_task = asyncio.create_task(metrics_reporting_loop())
        
        # Process sample queries for demonstration
        await process_sample_queries()
        
        logger.info("Data Agent is ready and running")
        
        # Keep the service running until shutdown signal
        while not shutdown_event.is_set():
            await asyncio.sleep(10)
            logger.debug("Data Agent heartbeat")
        
        logger.info("Shutdown signal received, stopping Data Agent...")
        
        # Cancel background tasks
        health_task.cancel()
        metrics_task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(health_task, metrics_task, return_exceptions=True)
        
    except Exception as e:
        logger.error("Data Agent initialization failed", error=str(e))
        sys.exit(1)
    
    finally:
        # Cleanup
        if data_agent:
            try:
                await close_data_agent()
                logger.info("Data Agent closed successfully")
            except Exception as e:
                logger.error("Error closing Data Agent", error=str(e))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Data Agent stopped by user")
    except Exception as e:
        logger.error("Data Agent failed", error=str(e))
        sys.exit(1)