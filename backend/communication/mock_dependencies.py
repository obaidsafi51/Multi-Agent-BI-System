"""
Mock dependencies for testing communication protocols without external services.
"""

import asyncio
import json
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock


class MockRedis:
    """Mock Redis client for testing"""
    
    def __init__(self):
        self._data: Dict[str, str] = {}
        self._sets: Dict[str, set] = {}
        self._ttls: Dict[str, float] = {}
    
    async def ping(self):
        return True
    
    async def setex(self, key: str, ttl: int, value: str):
        self._data[key] = value
        self._ttls[key] = ttl
        return True
    
    async def get(self, key: str) -> Optional[str]:
        return self._data.get(key)
    
    async def delete(self, key: str) -> int:
        if key in self._data:
            del self._data[key]
            return 1
        return 0
    
    async def sadd(self, key: str, value: str):
        if key not in self._sets:
            self._sets[key] = set()
        self._sets[key].add(value)
        return 1
    
    async def srem(self, key: str, value: str):
        if key in self._sets:
            self._sets[key].discard(value)
        return 1
    
    async def smembers(self, key: str) -> set:
        return self._sets.get(key, set())
    
    async def expire(self, key: str, ttl: int):
        self._ttls[key] = ttl
        return True
    
    async def ttl(self, key: str) -> int:
        return self._ttls.get(key, -1)
    
    async def keys(self, pattern: str) -> List[str]:
        return [k for k in self._data.keys() if pattern.replace('*', '') in k]
    
    async def memory_usage(self, key: str) -> int:
        return len(str(self._data.get(key, '')))
    
    async def flushdb(self):
        self._data.clear()
        self._sets.clear()
        self._ttls.clear()
    
    async def close(self):
        pass


class MockRabbitMQConnection:
    """Mock RabbitMQ connection for testing"""
    
    def __init__(self):
        self.is_closed = False
        self._channels = []
    
    async def channel(self):
        channel = MockRabbitMQChannel()
        self._channels.append(channel)
        return channel
    
    async def close(self):
        self.is_closed = True


class MockRabbitMQChannel:
    """Mock RabbitMQ channel for testing"""
    
    def __init__(self):
        self.is_closed = False
        self._exchanges = {}
        self._queues = {}
        self._published_messages = []
    
    async def set_qos(self, prefetch_count: int):
        pass
    
    async def declare_exchange(self, name: str, exchange_type, durable: bool = True):
        exchange = MockRabbitMQExchange(name)
        self._exchanges[name] = exchange
        return exchange
    
    async def declare_queue(self, name: str = None, durable: bool = True, 
                          exclusive: bool = False, arguments: Dict = None):
        if name is None:
            name = f"temp_queue_{len(self._queues)}"
        
        queue = MockRabbitMQQueue(name)
        self._queues[name] = queue
        return queue
    
    async def close(self):
        self.is_closed = True


class MockRabbitMQExchange:
    """Mock RabbitMQ exchange for testing"""
    
    def __init__(self, name: str):
        self.name = name
        self._published_messages = []
    
    async def publish(self, message, routing_key: str):
        self._published_messages.append({
            'message': message,
            'routing_key': routing_key,
            'timestamp': datetime.utcnow()
        })
        return True


class MockRabbitMQQueue:
    """Mock RabbitMQ queue for testing"""
    
    def __init__(self, name: str):
        self.name = name
        self._messages = []
        self._consumers = []
        self._bindings = []
    
    async def bind(self, exchange, routing_key: str):
        self._bindings.append({
            'exchange': exchange,
            'routing_key': routing_key
        })
    
    async def consume(self, callback):
        consumer_tag = f"consumer_{len(self._consumers)}"
        self._consumers.append({
            'tag': consumer_tag,
            'callback': callback
        })
        return consumer_tag
    
    async def cancel(self, consumer_tag: str):
        self._consumers = [c for c in self._consumers if c['tag'] != consumer_tag]
    
    async def delete(self):
        pass
    
    async def get_info(self):
        return MockQueueInfo(len(self._messages), len(self._consumers))


class MockQueueInfo:
    """Mock queue info for testing"""
    
    def __init__(self, message_count: int, consumer_count: int):
        self.message_count = message_count
        self.consumer_count = consumer_count


class MockCeleryApp:
    """Mock Celery app for testing"""
    
    def __init__(self, *args, **kwargs):
        self.conf = MagicMock()
        self.conf.update = MagicMock()
        self._tasks = {}
        self.control = MagicMock()
        
        # Mock inspect
        inspect_mock = MagicMock()
        inspect_mock.stats.return_value = {"worker1": {}}
        inspect_mock.active.return_value = {"worker1": []}
        self.control.inspect.return_value = inspect_mock
    
    def task(self, bind=False, name=None):
        def decorator(func):
            task_mock = MagicMock()
            task_mock.delay = AsyncMock(return_value=MagicMock(id="mock_task_id"))
            task_mock.apply_async = AsyncMock(return_value=MagicMock(id="mock_task_id"))
            self._tasks[name or func.__name__] = task_mock
            return task_mock
        return decorator


# Mock module imports
class MockAioPika:
    """Mock aio_pika module"""
    
    @staticmethod
    async def connect_robust(url: str):
        return MockRabbitMQConnection()
    
    class Message:
        def __init__(self, body, **kwargs):
            self.body = body
            self.message_id = kwargs.get('message_id')
            self.correlation_id = kwargs.get('correlation_id')
            self.reply_to = kwargs.get('reply_to')
            self.timestamp = kwargs.get('timestamp')
            self.expiration = kwargs.get('expiration')
            self.headers = kwargs.get('headers', {})
    
    class DeliveryMode:
        PERSISTENT = 2
    
    class ExchangeType:
        TOPIC = "topic"
    
    class IncomingMessage:
        def __init__(self, body: bytes):
            self.body = body
        
        def process(self):
            return AsyncMock()


class MockRedisModule:
    """Mock redis module"""
    
    class asyncio:
        @staticmethod
        def from_url(url: str, **kwargs):
            return MockRedis()


# Patch imports for testing
import sys

# Create mock modules
sys.modules['aio_pika'] = MockAioPika()
sys.modules['aio_pika.exceptions'] = MagicMock()
sys.modules['redis.asyncio'] = MockRedisModule.asyncio
sys.modules['redis.exceptions'] = MagicMock()
sys.modules['celery'] = MagicMock(Celery=MockCeleryApp)
sys.modules['celery.exceptions'] = MagicMock()
sys.modules['kombu'] = MagicMock(Queue=MagicMock)