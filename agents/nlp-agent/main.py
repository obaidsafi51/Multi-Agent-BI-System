"""
NLP Agent with KIMI Integration
This is a placeholder main.py file for Docker container startup.
Actual implementation will be done in task 4.
"""

import asyncio
import logging
import os
import signal
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_event = asyncio.Event()

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_event.set()

async def main():
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("NLP Agent starting...")
    logger.info("KIMI integration placeholder - waiting for implementation")
    
    # Validate environment variables
    required_env_vars = ['KIMI_API_KEY', 'REDIS_URL', 'RABBITMQ_URL']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        sys.exit(1)
    
    logger.info("Environment variables validated successfully")
    
    # Keep the container running until shutdown signal
    try:
        while not shutdown_event.is_set():
            await asyncio.sleep(60)
            logger.info("NLP Agent heartbeat - ready for implementation")
    except asyncio.CancelledError:
        logger.info("NLP Agent task cancelled")
    finally:
        logger.info("NLP Agent shutting down...")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("NLP Agent stopped by user")
    except Exception as e:
        logger.error(f"NLP Agent failed: {e}")
        sys.exit(1)