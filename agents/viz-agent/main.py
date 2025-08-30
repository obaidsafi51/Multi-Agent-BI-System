"""
Visualization Agent with Plotly
Dynamic chart generation with CFO-specific styling and interactive features
"""

import asyncio
import logging
import os
import signal
import sys
import json
from typing import Dict, Any
from dotenv import load_dotenv
import redis
import pika
from src.visualization_agent import VisualizationAgent
from src.models import VisualizationRequest

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

class VisualizationAgentService:
    """Service wrapper for the Visualization Agent"""
    
    def __init__(self):
        self.agent = VisualizationAgent()
        self.redis_client = None
        self.rabbitmq_connection = None
        self.rabbitmq_channel = None
    
    async def initialize(self):
        """Initialize connections and services"""
        try:
            # Initialize Redis connection
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            
            # Test Redis connection
            self.redis_client.ping()
            logger.info("Redis connection established")
            
            # Initialize RabbitMQ connection
            rabbitmq_url = os.getenv('RABBITMQ_URL', 'amqp://localhost:5672')
            self.rabbitmq_connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
            self.rabbitmq_channel = self.rabbitmq_connection.channel()
            
            # Declare queues
            self.rabbitmq_channel.queue_declare(queue='visualization_requests', durable=True)
            self.rabbitmq_channel.queue_declare(queue='visualization_responses', durable=True)
            
            logger.info("RabbitMQ connection established")
            
            # Set up message consumption
            self.rabbitmq_channel.basic_consume(
                queue='visualization_requests',
                on_message_callback=self.handle_visualization_request,
                auto_ack=False
            )
            
            logger.info("Visualization Agent initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Visualization Agent: {e}")
            raise
    
    def handle_visualization_request(self, ch, method, properties, body):
        """Handle incoming visualization requests"""
        try:
            # Parse request
            request_data = json.loads(body.decode('utf-8'))
            request = VisualizationRequest(**request_data)
            
            logger.info(f"Processing visualization request {request.request_id}")
            
            # Process request asynchronously
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response = loop.run_until_complete(self.agent.process_visualization_request(request))
            loop.close()
            
            # Send response
            response_data = response.model_dump()
            self.rabbitmq_channel.basic_publish(
                exchange='',
                routing_key='visualization_responses',
                body=json.dumps(response_data),
                properties=pika.BasicProperties(
                    correlation_id=properties.correlation_id,
                    delivery_mode=2  # Make message persistent
                )
            )
            
            # Acknowledge message
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
            logger.info(f"Completed visualization request {request.request_id}")
            
        except Exception as e:
            logger.error(f"Error processing visualization request: {e}")
            # Reject message and requeue
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    async def run(self):
        """Run the visualization agent service"""
        try:
            logger.info("Starting message consumption...")
            
            # Start consuming messages in a separate thread
            import threading
            
            def consume_messages():
                try:
                    self.rabbitmq_channel.start_consuming()
                except Exception as e:
                    logger.error(f"Error in message consumption: {e}")
            
            consumer_thread = threading.Thread(target=consume_messages)
            consumer_thread.daemon = True
            consumer_thread.start()
            
            # Keep the service running
            while not shutdown_event.is_set():
                await asyncio.sleep(1)
                
                # Perform health checks
                if hasattr(self, '_last_health_check'):
                    if asyncio.get_event_loop().time() - self._last_health_check > 300:  # 5 minutes
                        await self.perform_health_check()
                else:
                    await self.perform_health_check()
            
        except Exception as e:
            logger.error(f"Error running visualization agent service: {e}")
            raise
        finally:
            await self.cleanup()
    
    async def perform_health_check(self):
        """Perform periodic health check"""
        try:
            health_status = await self.agent.health_check()
            logger.info(f"Health check: {health_status['status']}")
            
            # Store health status in Redis
            if self.redis_client:
                self.redis_client.setex(
                    'viz_agent_health',
                    300,  # 5 minutes TTL
                    json.dumps(health_status)
                )
            
            self._last_health_check = asyncio.get_event_loop().time()
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
    
    async def cleanup(self):
        """Clean up connections and resources"""
        logger.info("Cleaning up Visualization Agent...")
        
        try:
            if self.rabbitmq_channel:
                self.rabbitmq_channel.stop_consuming()
                self.rabbitmq_channel.close()
            
            if self.rabbitmq_connection:
                self.rabbitmq_connection.close()
            
            if self.redis_client:
                self.redis_client.close()
                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

async def main():
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Visualization Agent starting...")
    
    # Validate environment variables
    required_env_vars = ['REDIS_URL', 'RABBITMQ_URL']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        sys.exit(1)
    
    logger.info("Environment variables validated successfully")
    
    # Initialize and run the service
    service = VisualizationAgentService()
    
    try:
        await service.initialize()
        await service.run()
    except Exception as e:
        logger.error(f"Visualization Agent failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Visualization Agent stopped by user")
    except Exception as e:
        logger.error(f"Visualization Agent failed: {e}")
        sys.exit(1)