"""
Rate limiter for TiDB MCP Server.

This module provides rate limiting functionality to prevent database overload
and ensure fair resource usage across clients.
"""

import logging
import threading
import time
from collections import defaultdict, deque
from typing import Dict, Any

from .exceptions import RateLimitError

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter with per-client tracking.
    
    Implements rate limiting to prevent database overload by limiting the number
    of requests per client per time window.
    """
    
    def __init__(self, requests_per_minute: int = 60, window_size_seconds: int = 60):
        """
        Initialize the rate limiter.
        
        Args:
            requests_per_minute: Maximum requests per minute per client
            window_size_seconds: Time window size in seconds for rate limiting
        """
        self.requests_per_minute = requests_per_minute
        self.window_size_seconds = window_size_seconds
        self.max_requests_per_window = requests_per_minute
        
        # Per-client request tracking using sliding window
        self._client_requests: Dict[str, deque] = defaultdict(deque)
        self._lock = threading.RLock()
        
        # Statistics
        self._total_requests = 0
        self._blocked_requests = 0
        self._start_time = time.time()
        
        logger.info(
            f"RateLimiter initialized with {requests_per_minute} requests/minute, "
            f"window size: {window_size_seconds}s"
        )
    
    def allow_request(self, client_id: str = "default") -> bool:
        """
        Check if a request should be allowed for the given client.
        
        Args:
            client_id: Unique identifier for the client
            
        Returns:
            True if request is allowed, False if rate limit exceeded
            
        Raises:
            RateLimitError: If rate limit is exceeded (when configured to raise)
        """
        with self._lock:
            current_time = time.time()
            self._total_requests += 1
            
            # Get or create request queue for client
            client_queue = self._client_requests[client_id]
            
            # Remove old requests outside the time window
            cutoff_time = current_time - self.window_size_seconds
            while client_queue and client_queue[0] < cutoff_time:
                client_queue.popleft()
            
            # Check if client has exceeded rate limit
            if len(client_queue) >= self.max_requests_per_window:
                self._blocked_requests += 1
                
                logger.warning(
                    f"Rate limit exceeded for client '{client_id}'",
                    extra={
                        "client_id": client_id,
                        "requests_in_window": len(client_queue),
                        "max_requests": self.max_requests_per_window,
                        "window_size_seconds": self.window_size_seconds
                    }
                )
                
                return False
            
            # Allow the request and record it
            client_queue.append(current_time)
            
            logger.debug(
                f"Request allowed for client '{client_id}'",
                extra={
                    "client_id": client_id,
                    "requests_in_window": len(client_queue),
                    "max_requests": self.max_requests_per_window
                }
            )
            
            return True
    
    def get_client_stats(self, client_id: str = "default") -> Dict[str, Any]:
        """
        Get rate limiting statistics for a specific client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Dictionary with client-specific statistics
        """
        with self._lock:
            current_time = time.time()
            client_queue = self._client_requests.get(client_id, deque())
            
            # Remove old requests outside the time window
            cutoff_time = current_time - self.window_size_seconds
            while client_queue and client_queue[0] < cutoff_time:
                client_queue.popleft()
            
            requests_in_window = len(client_queue)
            remaining_requests = max(0, self.max_requests_per_window - requests_in_window)
            
            # Calculate time until next request is allowed
            time_until_reset = 0
            if requests_in_window >= self.max_requests_per_window and client_queue:
                oldest_request = client_queue[0]
                time_until_reset = max(0, (oldest_request + self.window_size_seconds) - current_time)
            
            return {
                "client_id": client_id,
                "requests_in_window": requests_in_window,
                "max_requests_per_window": self.max_requests_per_window,
                "remaining_requests": remaining_requests,
                "window_size_seconds": self.window_size_seconds,
                "time_until_reset_seconds": time_until_reset,
                "rate_limited": requests_in_window >= self.max_requests_per_window
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get overall rate limiter statistics.
        
        Returns:
            Dictionary with overall statistics
        """
        with self._lock:
            uptime_seconds = time.time() - self._start_time
            
            # Clean up old client data
            self._cleanup_old_clients()
            
            return {
                "requests_per_minute": self.requests_per_minute,
                "window_size_seconds": self.window_size_seconds,
                "total_requests": self._total_requests,
                "blocked_requests": self._blocked_requests,
                "allowed_requests": self._total_requests - self._blocked_requests,
                "block_rate_percent": (self._blocked_requests / max(self._total_requests, 1)) * 100,
                "active_clients": len(self._client_requests),
                "uptime_seconds": uptime_seconds,
                "requests_per_second": self._total_requests / max(uptime_seconds, 1)
            }
    
    def reset_client(self, client_id: str) -> None:
        """
        Reset rate limiting for a specific client.
        
        Args:
            client_id: Client identifier to reset
        """
        with self._lock:
            if client_id in self._client_requests:
                del self._client_requests[client_id]
                logger.info(f"Rate limit reset for client '{client_id}'")
    
    def reset_all(self) -> None:
        """Reset rate limiting for all clients."""
        with self._lock:
            client_count = len(self._client_requests)
            self._client_requests.clear()
            self._total_requests = 0
            self._blocked_requests = 0
            self._start_time = time.time()
            
            logger.info(f"Rate limits reset for all clients (was tracking {client_count} clients)")
    
    def _cleanup_old_clients(self) -> None:
        """
        Clean up clients that haven't made requests recently.
        
        This prevents memory leaks from accumulating client data for inactive clients.
        """
        current_time = time.time()
        cutoff_time = current_time - (self.window_size_seconds * 2)  # Keep data for 2x window size
        
        clients_to_remove = []
        
        for client_id, client_queue in self._client_requests.items():
            # Remove old requests from the queue
            while client_queue and client_queue[0] < cutoff_time:
                client_queue.popleft()
            
            # If queue is empty, mark client for removal
            if not client_queue:
                clients_to_remove.append(client_id)
        
        # Remove inactive clients
        for client_id in clients_to_remove:
            del self._client_requests[client_id]
        
        if clients_to_remove:
            logger.debug(f"Cleaned up {len(clients_to_remove)} inactive clients")
    
    def get_time_until_allowed(self, client_id: str = "default") -> float:
        """
        Get the time in seconds until the next request will be allowed for a client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Time in seconds until next request is allowed (0 if immediately allowed)
        """
        client_stats = self.get_client_stats(client_id)
        return client_stats["time_until_reset_seconds"]
    
    def is_rate_limited(self, client_id: str = "default") -> bool:
        """
        Check if a client is currently rate limited.
        
        Args:
            client_id: Client identifier
            
        Returns:
            True if client is rate limited, False otherwise
        """
        client_stats = self.get_client_stats(client_id)
        return client_stats["rate_limited"]


class AdaptiveRateLimiter(RateLimiter):
    """
    Adaptive rate limiter that adjusts limits based on system load.
    
    Extends the basic rate limiter with adaptive behavior that can increase
    or decrease rate limits based on system performance metrics.
    """
    
    def __init__(self, requests_per_minute: int = 60, window_size_seconds: int = 60,
                 min_requests_per_minute: int = 10, max_requests_per_minute: int = 120):
        """
        Initialize the adaptive rate limiter.
        
        Args:
            requests_per_minute: Initial requests per minute per client
            window_size_seconds: Time window size in seconds
            min_requests_per_minute: Minimum allowed requests per minute
            max_requests_per_minute: Maximum allowed requests per minute
        """
        super().__init__(requests_per_minute, window_size_seconds)
        
        self.min_requests_per_minute = min_requests_per_minute
        self.max_requests_per_minute = max_requests_per_minute
        self.base_requests_per_minute = requests_per_minute
        
        # Adaptive behavior tracking
        self._error_rate_threshold = 0.1  # 10% error rate threshold
        self._load_adjustment_factor = 0.1  # 10% adjustment per adaptation
        self._last_adaptation_time = time.time()
        self._adaptation_interval = 60  # Adapt every 60 seconds
        
        logger.info(
            f"AdaptiveRateLimiter initialized with adaptive range: "
            f"{min_requests_per_minute}-{max_requests_per_minute} requests/minute"
        )
    
    def adapt_to_load(self, error_rate: float, response_time_ms: float) -> None:
        """
        Adapt rate limits based on system load metrics.
        
        Args:
            error_rate: Current error rate (0.0 to 1.0)
            response_time_ms: Average response time in milliseconds
        """
        current_time = time.time()
        
        # Only adapt at specified intervals
        if current_time - self._last_adaptation_time < self._adaptation_interval:
            return
        
        with self._lock:
            old_limit = self.requests_per_minute
            
            # Decrease limit if error rate is high or response time is slow
            if error_rate > self._error_rate_threshold or response_time_ms > 5000:
                adjustment = -self._load_adjustment_factor
                reason = f"high_error_rate({error_rate:.2%})" if error_rate > self._error_rate_threshold else f"slow_response({response_time_ms:.0f}ms)"
            
            # Increase limit if system is performing well
            elif error_rate < self._error_rate_threshold / 2 and response_time_ms < 1000:
                adjustment = self._load_adjustment_factor
                reason = "good_performance"
            
            else:
                # No adjustment needed
                self._last_adaptation_time = current_time
                return
            
            # Calculate new limit
            new_limit = int(self.base_requests_per_minute * (1 + adjustment))
            new_limit = max(self.min_requests_per_minute, min(new_limit, self.max_requests_per_minute))
            
            # Update limits
            self.requests_per_minute = new_limit
            self.max_requests_per_window = new_limit
            self._last_adaptation_time = current_time
            
            logger.info(
                f"Adapted rate limit: {old_limit} -> {new_limit} requests/minute",
                extra={
                    "reason": reason,
                    "error_rate": error_rate,
                    "response_time_ms": response_time_ms,
                    "adjustment_factor": adjustment
                }
            )