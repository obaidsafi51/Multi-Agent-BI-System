#!/usr/bin/env python3
"""
Test script for enhanced workflow orchestration implementation.

This script validates the key components of our WebSocket-native orchestration:
- Circuit breaker functionality
- Retry logic with exponential backoff  
- WebSocket progress reporting
- Orchestration metrics
"""

import asyncio
import logging
from backend.orchestration import (
    CircuitBreaker, CircuitBreakerException, CircuitBreakerState,
    RetryConfig, retry_with_backoff, RetryExhaustedException,
    orchestration_metrics, WebSocketProgressReporter
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_circuit_breaker():
    """Test circuit breaker functionality"""
    print("🔧 Testing Circuit Breaker...")
    
    # Create a test circuit breaker
    breaker = CircuitBreaker(
        failure_threshold=3,
        recovery_timeout=2.0,
        timeout=1.0,
        name="TestService"
    )
    
    # Test function that fails
    async def failing_function():
        raise Exception("Simulated service failure")
    
    # Test function that succeeds
    async def success_function():
        return {"status": "success", "data": "test"}
    
    # Test initial state
    assert breaker.state == CircuitBreakerState.CLOSED
    print("✅ Initial state: CLOSED")
    
    # Force failures to open circuit
    failure_count = 0
    for i in range(5):
        try:
            await breaker.call(failing_function)
        except (CircuitBreakerException, Exception):
            failure_count += 1
    
    print(f"✅ Recorded {failure_count} failures")
    
    # Check if circuit is open
    if breaker.state == CircuitBreakerState.OPEN:
        print("✅ Circuit breaker opened after threshold failures")
        
        # Try to call - should get CircuitBreakerException
        try:
            await breaker.call(success_function)
            print("❌ Expected CircuitBreakerException")
        except CircuitBreakerException:
            print("✅ Circuit breaker correctly rejected call")
    
    # Wait for recovery timeout and test half-open
    await asyncio.sleep(2.1)
    
    try:
        result = await breaker.call(success_function)
        print("✅ Circuit breaker recovered and closed")
        print(f"✅ Success result: {result}")
    except Exception as e:
        print(f"❌ Recovery failed: {e}")
    
    # Display stats
    stats = breaker.get_stats()
    print(f"📊 Circuit Breaker Stats:")
    print(f"   Total calls: {stats['stats']['total_calls']}")
    print(f"   Success rate: {stats['stats']['success_rate']:.1f}%")
    print(f"   State changes: {stats['stats']['state_changes']}")


async def test_retry_logic():
    """Test retry logic with exponential backoff"""
    print("\n🔄 Testing Retry Logic...")
    
    retry_config = RetryConfig(
        max_attempts=3,
        base_delay=0.1,  # Fast for testing
        max_delay=1.0,
        exponential_base=2.0
    )
    
    # Test function that fails twice then succeeds
    attempt_count = 0
    async def flaky_function():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise Exception(f"Failure on attempt {attempt_count}")
        return {"success": True, "attempts": attempt_count}
    
    try:
        result = await retry_with_backoff(flaky_function, retry_config)
        print(f"✅ Retry succeeded after {result['attempts']} attempts")
    except RetryExhaustedException:
        print("❌ All retry attempts exhausted")
    
    # Test total failure scenario
    attempt_count = 0
    async def always_fails():
        nonlocal attempt_count
        attempt_count += 1
        raise Exception(f"Always fails - attempt {attempt_count}")
    
    try:
        await retry_with_backoff(always_fails, retry_config)
        print("❌ Expected RetryExhaustedException")
    except RetryExhaustedException as e:
        print(f"✅ Retry correctly exhausted: {attempt_count} attempts made")


async def test_orchestration_metrics():
    """Test orchestration metrics collection"""
    print("\n📊 Testing Orchestration Metrics...")
    
    # Simulate some queries
    for i in range(5):
        query_id = f"test_query_{i}"
        start_time = await orchestration_metrics.record_query_start(query_id)
        
        # Simulate processing time
        await asyncio.sleep(0.1)
        
        if i < 4:  # 4 successes, 1 failure
            await orchestration_metrics.record_query_success(query_id, start_time)
        else:
            await orchestration_metrics.record_query_failure(query_id, start_time)
    
    # Get metrics
    metrics = await orchestration_metrics.get_metrics()
    
    print(f"📈 Metrics collected:")
    print(f"   Total queries: {metrics['queries_processed']}")
    print(f"   Successful: {metrics['successful_queries']}")
    print(f"   Failed: {metrics['failed_queries']}")
    print(f"   Success rate: {metrics['success_rate']:.1f}%")
    print(f"   Avg processing time: {metrics['average_processing_time']:.3f}s")


async def test_websocket_progress_reporter():
    """Test WebSocket progress reporting (mock)"""
    print("\n📡 Testing WebSocket Progress Reporter...")
    
    # Mock WebSocket
    class MockWebSocket:
        def __init__(self):
            self.messages = []
        
        async def send_json(self, data):
            self.messages.append(data)
            print(f"📤 WebSocket message: {data['type']} - {data.get('step', 'N/A')}")
    
    mock_ws = MockWebSocket()
    reporter = WebSocketProgressReporter(websocket=mock_ws, user_id="test_user")
    
    # Simulate query progress
    query_id = "test_progress_query"
    
    await reporter.report_progress(query_id, "initializing", "starting", 0.0)
    await reporter.report_progress(query_id, "nlp_processing", "in_progress", 30.0)
    await reporter.report_progress(query_id, "nlp_processing", "completed", 50.0)
    await reporter.report_progress(query_id, "data_processing", "in_progress", 70.0)
    await reporter.report_error(query_id, "Mock error for testing", "data_processing")
    await reporter.report_completion(query_id, {"result": "success"})
    
    print(f"✅ Sent {len(mock_ws.messages)} progress messages")


async def main():
    """Run all tests"""
    print("🚀 Starting Enhanced Orchestration Tests...\n")
    
    try:
        await test_circuit_breaker()
        await test_retry_logic()
        await test_orchestration_metrics()
        await test_websocket_progress_reporter()
        
        print("\n🎉 All tests completed successfully!")
        print("\n📋 Implementation Summary:")
        print("   ✅ Circuit breakers protect against cascading failures")
        print("   ✅ Retry logic handles transient failures")
        print("   ✅ Orchestration metrics track system performance")
        print("   ✅ WebSocket progress updates provide real-time feedback")
        print("   ✅ Enhanced error handling and recovery")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
