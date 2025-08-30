"""
A2A (Agent-to-Agent) protocol implementation using RabbitMQ.

Provides message broker functionality with topic exchanges and routing.
"""

import json
import logging
import asyncio
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime
import aio_pika
from aio_pika import Message, DeliveryMode, ExchangeType
from aio_pika.exceptions import AMQPException

from .models import AgentMessage, MessageType, AgentType, HealthCheckResponse


logger = logging.getLogger(__name__)


class A2AMessageBroker:
    """RabbitMQ-based message broker for A2A protocol"""
    
    def __init__(self, rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"):
        """
        Initialize A2A message broker.
        
        Args:
            rabbitmq_url: RabbitMQ connection URL
        """
        self.rabbitmq_url = rabbitmq_url
        self._connection: Optional[aio_pika.Connection] = None
        self._channel: Optional[aio_pika.Channel] = None
        self._exchange: Optional[aio_pika.Exchange] = None
        self._message_handlers: Dict[MessageType, Callable] = {}
        self._agent_type: Optional[AgentType] = None
        self._consumer_tags: List[str] = []
        
    async def connect(self, agent_type: AgentType) -> None:
        """
        Establish RabbitMQ connection and setup exchanges.
        
        Args:
            agent_type: Type of agent connecting
        """
        try:
            self._agent_type = agent_type
            self._connection = await aio_pika.connect_robust(self.rabbitmq_url)
            self._channel = await self._connection.channel()
            
            # Set QoS for fair dispatch
            await self._channel.set_qos(prefetch_count=10)
            
            # Create topic exchange for agent communication
            self._exchange = await self._channel.declare_exchange(
                "agent_communication",
                ExchangeType.TOPIC,
                durable=True
            )
            
            # Create agent-specific queue
            queue_name = f"agent.{agent_type.value}"
            self._queue = await self._channel.declare_queue(
                queue_name,
                durable=True,
                arguments={"x-message-ttl": 300000}  # 5 minutes TTL
            )
            
            # Bind queue to exchange with routing patterns
            await self._queue.bind(self._exchange, f"agent.{agent_type.value}")
            await self._queue.bind(self._exchange, "agent.broadcast")
            
            logger.info(f"Connected to RabbitMQ as {agent_type.value} agent")
            
        except AMQPException as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close RabbitMQ connection"""
        try:
            # Cancel all consumers
            for tag in self._consumer_tags:
                await self._queue.cancel(tag)
            
            if self._connection and not self._connection.is_closed:
                await self._connection.close()
            
            logger.info("Disconnected from RabbitMQ")
            
        except AMQPException as e:
            logger.error(f"Error disconnecting from RabbitMQ: {e}")
    
    def register_handler(self, message_type: MessageType, handler: Callable) -> None:
        """
        Register message handler for specific message type.
        
        Args:
            message_type: Type of message to handle
            handler: Async function to handle the message
        """
        self._message_handlers[message_type] = handler
        logger.debug(f"Registered handler for {message_type}")
    
    async def send_message(self, message: AgentMessage) -> bool:
        """
        Send message to another agent.
        
        Args:
            message: Message to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self._exchange:
            raise RuntimeError("RabbitMQ connection not established")
        
        try:
            # Set sender if not already set
            if not message.sender and self._agent_type:
                message.sender = self._agent_type
            
            # Create routing key
            routing_key = f"agent.{message.recipient.value}"
            
            # Create AMQP message
            body = message.json().encode()
            amqp_message = Message(
                body,
                delivery_mode=DeliveryMode.PERSISTENT,
                message_id=message.message_id,
                correlation_id=message.correlation_id,
                reply_to=message.reply_to,
                timestamp=message.timestamp,
                expiration=str(message.ttl * 1000) if message.ttl else None,
                headers={
                    "message_type": message.message_type.value,
                    "sender": message.sender.value,
                    "recipient": message.recipient.value,
                    "retry_count": message.retry_count
                }
            )
            
            # Send message
            await self._exchange.publish(amqp_message, routing_key=routing_key)
            
            logger.debug(f"Sent {message.message_type} message from {message.sender} to {message.recipient}")
            return True
            
        except AMQPException as e:
            logger.error(f"Failed to send message: {e}")
            return False
    
    async def broadcast_message(self, message: AgentMessage) -> bool:
        """
        Broadcast message to all agents.
        
        Args:
            message: Message to broadcast
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self._exchange:
            raise RuntimeError("RabbitMQ connection not established")
        
        try:
            # Set sender if not already set
            if not message.sender and self._agent_type:
                message.sender = self._agent_type
            
            # Create AMQP message
            body = message.json().encode()
            amqp_message = Message(
                body,
                delivery_mode=DeliveryMode.PERSISTENT,
                message_id=message.message_id,
                timestamp=message.timestamp,
                headers={
                    "message_type": message.message_type.value,
                    "sender": message.sender.value,
                    "broadcast": True
                }
            )
            
            # Broadcast to all agents
            await self._exchange.publish(amqp_message, routing_key="agent.broadcast")
            
            logger.debug(f"Broadcast {message.message_type} message from {message.sender}")
            return True
            
        except AMQPException as e:
            logger.error(f"Failed to broadcast message: {e}")
            return False
    
    async def start_consuming(self) -> None:
        """Start consuming messages from the queue"""
        if not self._queue:
            raise RuntimeError("RabbitMQ connection not established")
        
        try:
            consumer_tag = await self._queue.consume(self._handle_message)
            self._consumer_tags.append(consumer_tag)
            logger.info(f"Started consuming messages for {self._agent_type}")
            
        except AMQPException as e:
            logger.error(f"Failed to start consuming: {e}")
            raise
    
    async def _handle_message(self, message: aio_pika.IncomingMessage) -> None:
        """
        Handle incoming message.
        
        Args:
            message: Incoming AMQP message
        """
        try:
            async with message.process():
                # Parse message
                body = message.body.decode()
                agent_message = AgentMessage(**json.loads(body))
                
                logger.debug(f"Received {agent_message.message_type} message from {agent_message.sender}")
                
                # Check if we have a handler for this message type
                handler = self._message_handlers.get(agent_message.message_type)
                if handler:
                    try:
                        await handler(agent_message)
                    except Exception as e:
                        logger.error(f"Error handling {agent_message.message_type} message: {e}")
                        
                        # Send error response if reply_to is set
                        if agent_message.reply_to:
                            error_message = AgentMessage(
                                message_type=MessageType.ERROR_NOTIFICATION,
                                sender=self._agent_type,
                                recipient=agent_message.sender,
                                payload={"error": str(e), "original_message_id": agent_message.message_id},
                                correlation_id=agent_message.correlation_id
                            )
                            await self.send_message(error_message)
                else:
                    logger.warning(f"No handler registered for {agent_message.message_type}")
                    
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse message: {e}")
        except Exception as e:
            logger.error(f"Unexpected error handling message: {e}")
    
    async def send_request_response(self, request: AgentMessage, timeout: int = 30) -> Optional[AgentMessage]:
        """
        Send request and wait for response.
        
        Args:
            request: Request message
            timeout: Timeout in seconds
            
        Returns:
            Response message if received, None if timeout
        """
        if not self._exchange:
            raise RuntimeError("RabbitMQ connection not established")
        
        try:
            # Create temporary response queue
            response_queue = await self._channel.declare_queue(exclusive=True)
            request.reply_to = response_queue.name
            
            # Send request
            await self.send_message(request)
            
            # Wait for response
            response_future = asyncio.Future()
            
            async def response_handler(message: aio_pika.IncomingMessage):
                async with message.process():
                    body = message.body.decode()
                    response_message = AgentMessage(**json.loads(body))
                    if response_message.correlation_id == request.correlation_id:
                        response_future.set_result(response_message)
            
            consumer_tag = await response_queue.consume(response_handler)
            
            try:
                response = await asyncio.wait_for(response_future, timeout=timeout)
                return response
            except asyncio.TimeoutError:
                logger.warning(f"Request {request.message_id} timed out")
                return None
            finally:
                await response_queue.cancel(consumer_tag)
                await response_queue.delete()
                
        except AMQPException as e:
            logger.error(f"Failed to send request-response: {e}")
            return None
    
    async def health_check(self) -> HealthCheckResponse:
        """
        Perform health check of the message broker.
        
        Returns:
            Health check response
        """
        try:
            if not self._connection or self._connection.is_closed:
                return HealthCheckResponse(
                    agent_type=self._agent_type,
                    status="unhealthy",
                    details={"error": "No connection to RabbitMQ"}
                )
            
            # Check channel
            if not self._channel or self._channel.is_closed:
                return HealthCheckResponse(
                    agent_type=self._agent_type,
                    status="unhealthy",
                    details={"error": "No channel to RabbitMQ"}
                )
            
            # Get queue info
            queue_info = await self._queue.get_info()
            
            return HealthCheckResponse(
                agent_type=self._agent_type,
                status="healthy",
                details={
                    "queue_name": self._queue.name,
                    "message_count": queue_info.message_count,
                    "consumer_count": queue_info.consumer_count
                }
            )
            
        except Exception as e:
            return HealthCheckResponse(
                agent_type=self._agent_type,
                status="unhealthy",
                details={"error": str(e)}
            )
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get queue statistics.
        
        Returns:
            Dictionary with queue statistics
        """
        try:
            if not self._queue:
                return {}
            
            queue_info = await self._queue.get_info()
            
            return {
                "queue_name": self._queue.name,
                "message_count": queue_info.message_count,
                "consumer_count": queue_info.consumer_count,
                "connection_state": "open" if self._connection and not self._connection.is_closed else "closed",
                "channel_state": "open" if self._channel and not self._channel.is_closed else "closed"
            }
            
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {"error": str(e)}