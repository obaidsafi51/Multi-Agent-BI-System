"""
NLP Agent with KIMI Integration
Main entry point for the NLP Agent service
"""

import asyncio
import logging
import os
import signal
import sys
from dotenv import load_dotenv

from src.nlp_agent import NLPAgent

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global references
nlp_agent: NLPAgent = None
shutdown_event = asyncio.Event()

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_event.set()

async def main():
    global nlp_agent
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("NLP Agent starting...")
    
    # Validate environment variables
    required_env_vars = ['KIMI_API_KEY', 'REDIS_URL', 'RABBITMQ_URL']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        sys.exit(1)
    
    logger.info("Environment variables validated successfully")
    
    try:
        # Initialize and start NLP Agent
        nlp_agent = NLPAgent(
            kimi_api_key=os.getenv('KIMI_API_KEY'),
            redis_url=os.getenv('REDIS_URL'),
            rabbitmq_url=os.getenv('RABBITMQ_URL')
        )
        
        await nlp_agent.start()
        
        # Run health checks periodically
        async def health_check_loop():
            while not shutdown_event.is_set():
                try:
                    health_status = await nlp_agent.health_check()
                    if health_status["overall_status"] != "healthy":
                        logger.warning(f"Health check status: {health_status['overall_status']}")
                    else:
                        logger.debug("Health check passed")
                except Exception as e:
                    logger.error(f"Health check failed: {e}")
                
                await asyncio.sleep(60)  # Check every minute
        
        # Start health check loop
        health_task = asyncio.create_task(health_check_loop())
        
        # Wait for shutdown signal
        await shutdown_event.wait()
        
        # Cancel health check task
        health_task.cancel()
        try:
            await health_task
        except asyncio.CancelledError:
            pass
        
    except Exception as e:
        logger.error(f"NLP Agent startup failed: {e}")
        sys.exit(1)
    finally:
        if nlp_agent:
            await nlp_agent.stop()
        logger.info("NLP Agent shutdown complete")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("NLP Agent stopped by user")
    except Exception as e:
        logger.error(f"NLP Agent failed: {e}")
        sys.exit(1)