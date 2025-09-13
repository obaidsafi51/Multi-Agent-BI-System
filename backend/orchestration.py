"""
Enhanced orchestration patterns for WebSocket-native workflow management.

This module provides circuit breakers, retry logic, and orchestration utilities
that work seamlessly with the WebSocket architecture.
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional, Callable, Union, List
from datetime import datetime, timedelta
from enum import Enum
import json
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, rejecting calls
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    consecutive_failures: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    state_changes: int = 0
    
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_calls == 0:
            return 100.0
        return (self.successful_calls / self.total_calls) * 100


class CircuitBreakerException(Exception):
    """Exception raised when circuit breaker is open"""
    pass


class CircuitBreaker:
    """
    Circuit breaker implementation for protecting against cascading failures.
    
    Monitors failure rates and automatically prevents calls to failing services,
    allowing them time to recover while providing fast-fail behavior.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Union[Exception, tuple] = Exception,
        success_threshold: int = 1,
        timeout: float = 30.0,
        name: str = "CircuitBreaker"
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before trying half-open state
            expected_exception: Exception types that count as failures
            success_threshold: Successful calls needed to close circuit from half-open
            timeout: Default timeout for calls
            name: Identifier for logging and metrics
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.name = name
        
        self.state = CircuitBreakerState.CLOSED
        self.stats = CircuitBreakerStats()
        self._half_open_successes = 0
        self._lock = asyncio.Lock()
        
        logger.info(f"CircuitBreaker '{name}' initialized with {failure_threshold} failure threshold")
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker protection.
        
        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerException: When circuit is open
            TimeoutError: When call exceeds timeout
        """
        async with self._lock:
            # Check if circuit should transition from open to half-open
            if self.state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    self._transition_to_half_open()
                else:
                    time_since_failure = self._time_since_last_failure()
                    failure_msg = "no previous failures" if time_since_failure < 0 else f"{time_since_failure:.1f}s ago"
                    raise CircuitBreakerException(
                        f"Circuit breaker '{self.name}' is OPEN. "
                        f"Last failure: {failure_msg}"
                    )
        
        # Execute the function with timeout
        start_time = time.time()
        try:
            self.stats.total_calls += 1
            
            # Execute with timeout protection
            result = await asyncio.wait_for(func(*args, **kwargs), timeout=self.timeout)
            
            # Record success
            await self._record_success()
            
            execution_time = time.time() - start_time
            logger.debug(f"CircuitBreaker '{self.name}' call succeeded in {execution_time:.2f}s")
            
            return result
            
        except asyncio.TimeoutError:
            await self._record_failure()
            raise TimeoutError(f"Call timed out after {self.timeout}s")
            
        except self.expected_exception as e:
            await self._record_failure()
            logger.warning(f"CircuitBreaker '{self.name}' recorded failure: {e}")
            raise
            
        except Exception as e:
            # Unexpected exceptions don't count as circuit breaker failures
            logger.error(f"Unexpected exception in CircuitBreaker '{self.name}': {e}")
            raise
    
    async def _record_success(self):
        """Record successful call"""
        async with self._lock:
            self.stats.successful_calls += 1
            self.stats.consecutive_failures = 0
            self.stats.last_success_time = time.time()
            
            if self.state == CircuitBreakerState.HALF_OPEN:
                self._half_open_successes += 1
                if self._half_open_successes >= self.success_threshold:
                    self._transition_to_closed()
    
    async def _record_failure(self):
        """Record failed call"""
        async with self._lock:
            self.stats.failed_calls += 1
            self.stats.consecutive_failures += 1
            self.stats.last_failure_time = time.time()
            
            # Check if we should open the circuit
            if (self.state == CircuitBreakerState.CLOSED and
                self.stats.consecutive_failures >= self.failure_threshold):
                self._transition_to_open()
            elif self.state == CircuitBreakerState.HALF_OPEN:
                # Failure in half-open state goes back to open
                self._transition_to_open()
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.stats.last_failure_time is None:
            return True
        
        return time.time() - self.stats.last_failure_time >= self.recovery_timeout
    
    def _time_since_last_failure(self) -> float:
        """Get time since last failure in seconds"""
        if self.stats.last_failure_time is None:
            return -1.0  # Use -1 to indicate no previous failure (JSON safe)
        return time.time() - self.stats.last_failure_time
    
    def _transition_to_open(self):
        """Transition to OPEN state"""
        self.state = CircuitBreakerState.OPEN
        self.stats.state_changes += 1
        logger.warning(f"CircuitBreaker '{self.name}' transitioned to OPEN state")
    
    def _transition_to_half_open(self):
        """Transition to HALF_OPEN state"""
        self.state = CircuitBreakerState.HALF_OPEN
        self._half_open_successes = 0
        self.stats.state_changes += 1
        logger.info(f"CircuitBreaker '{self.name}' transitioned to HALF_OPEN state")
    
    def _transition_to_closed(self):
        """Transition to CLOSED state"""
        self.state = CircuitBreakerState.CLOSED
        self.stats.state_changes += 1
        logger.info(f"CircuitBreaker '{self.name}' transitioned to CLOSED state")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics"""
        return {
            "name": self.name,
            "state": self.state.value,
            "stats": {
                "total_calls": self.stats.total_calls,
                "successful_calls": self.stats.successful_calls,
                "failed_calls": self.stats.failed_calls,
                "consecutive_failures": self.stats.consecutive_failures,
                "success_rate": self.stats.success_rate(),
                "state_changes": self.stats.state_changes
            },
            "config": {
                "failure_threshold": self.failure_threshold,
                "recovery_timeout": self.recovery_timeout,
                "success_threshold": self.success_threshold,
                "timeout": self.timeout
            },
            "timing": {
                "last_failure_time": self.stats.last_failure_time,
                "last_success_time": self.stats.last_success_time,
                "time_since_last_failure": self._time_since_last_failure()
            }
        }


@dataclass
class RetryConfig:
    """Configuration for retry logic"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retry_exceptions: tuple = (Exception,)


class RetryExhaustedException(Exception):
    """Exception raised when all retry attempts are exhausted"""
    pass


async def retry_with_backoff(
    func: Callable,
    config: RetryConfig,
    *args,
    **kwargs
) -> Any:
    """
    Execute function with exponential backoff retry logic.
    
    Args:
        func: Async function to execute
        config: Retry configuration
        *args: Function arguments
        **kwargs: Function keyword arguments
        
    Returns:
        Function result
        
    Raises:
        RetryExhaustedException: When all attempts fail
    """
    last_exception = None
    
    for attempt in range(config.max_attempts):
        try:
            result = await func(*args, **kwargs)
            if attempt > 0:
                logger.info(f"Function succeeded on attempt {attempt + 1}")
            return result
            
        except config.retry_exceptions as e:
            last_exception = e
            
            if attempt == config.max_attempts - 1:
                # Last attempt failed
                break
                
            # Calculate delay with exponential backoff
            delay = min(
                config.base_delay * (config.exponential_base ** attempt),
                config.max_delay
            )
            
            # Add jitter to prevent thundering herd
            if config.jitter:
                import random
                delay *= (0.5 + random.random() * 0.5)
            
            logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s")
            await asyncio.sleep(delay)
            
        except Exception as e:
            # Non-retryable exception
            logger.error(f"Non-retryable exception on attempt {attempt + 1}: {e}")
            raise
    
    # All attempts exhausted
    raise RetryExhaustedException(
        f"All {config.max_attempts} retry attempts failed. Last error: {last_exception}"
    )


class OrchestrationMetrics:
    """Collect and manage orchestration metrics"""
    
    def __init__(self):
        self._metrics: Dict[str, Any] = {
            "queries_processed": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "average_processing_time": 0.0,
            "circuit_breakers": {},
            "agent_stats": {},
            "processing_times": []
        }
        self._lock = asyncio.Lock()
    
    async def record_query_start(self, query_id: str) -> float:
        """Record query start time"""
        start_time = time.time()
        async with self._lock:
            self._metrics["queries_processed"] += 1
        return start_time
    
    async def record_query_success(self, query_id: str, start_time: float):
        """Record successful query completion"""
        processing_time = time.time() - start_time
        
        async with self._lock:
            self._metrics["successful_queries"] += 1
            self._metrics["processing_times"].append(processing_time)
            
            # Keep only last 100 processing times
            if len(self._metrics["processing_times"]) > 100:
                self._metrics["processing_times"] = self._metrics["processing_times"][-100:]
            
            # Update average
            self._metrics["average_processing_time"] = sum(
                self._metrics["processing_times"]
            ) / len(self._metrics["processing_times"])
    
    async def record_query_failure(self, query_id: str, start_time: float):
        """Record failed query"""
        async with self._lock:
            self._metrics["failed_queries"] += 1
    
    async def update_circuit_breaker_stats(self, breaker: CircuitBreaker):
        """Update circuit breaker statistics"""
        async with self._lock:
            self._metrics["circuit_breakers"][breaker.name] = breaker.get_stats()
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get all orchestration metrics"""
        async with self._lock:
            total_queries = self._metrics["queries_processed"]
            success_rate = 0.0
            if total_queries > 0:
                success_rate = (self._metrics["successful_queries"] / total_queries) * 100
            
            return {
                **self._metrics,
                "success_rate": success_rate,
                "timestamp": datetime.utcnow().isoformat()
            }


# Global metrics instance
orchestration_metrics = OrchestrationMetrics()


class WebSocketProgressReporter:
    """Report real-time progress updates via WebSocket"""
    
    def __init__(self, websocket=None, user_id: str = None):
        self.websocket = websocket
        self.user_id = user_id
    
    async def report_progress(
        self,
        query_id: str,
        step: str,
        status: str,
        progress: float = 0.0,
        data: Optional[Dict[str, Any]] = None
    ):
        """Send progress update via WebSocket"""
        if not self.websocket:
            return
        
        try:
            message = {
                "type": "query_progress",
                "query_id": query_id,
                "step": step,
                "status": status,
                "progress": progress,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if data:
                message["data"] = data
            
            await self.websocket.send_json(message)
            logger.debug(f"Sent progress update: {step} - {status}")
            
        except Exception as e:
            logger.warning(f"Failed to send WebSocket progress update: {e}")
    
    async def report_error(self, query_id: str, error: str, step: str = None):
        """Send error update via WebSocket"""
        await self.report_progress(
            query_id=query_id,
            step=step or "error",
            status="error",
            data={"error": error}
        )
    
    async def report_completion(self, query_id: str, result: Dict[str, Any]):
        """Send completion update via WebSocket"""
        await self.report_progress(
            query_id=query_id,
            step="completed",
            status="success",
            progress=100.0,
            data=result
        )
