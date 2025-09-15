#!/usr/bin/env python3
"""
WebSocket Connection Test for Data Agent

This script tests the WebSocket connection to the data agent 
and verifies that it can receive responses.
"""

import asyncio
import json
import websockets
import websockets.exceptions
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_websocket_connection():
    """Test WebSocket connection to data agent"""
    uri = "ws://localhost:8012"
    
    try:
        logger.info(f"Connecting to WebSocket at {uri}")
        
        async with websockets.connect(uri) as websocket:
            logger.info("Connected to WebSocket successfully!")
            
            # Wait for welcome message
            try:
                welcome_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                logger.info(f"Received welcome message: {welcome_msg}")
            except asyncio.TimeoutError:
                logger.warning("No welcome message received within 5 seconds")
            
            # Send test message
            test_message = {
                "type": "test_message",
                "message": "Hello from test client",
                "timestamp": "2025-09-13T16:40:00Z"
            }
            
            logger.info(f"Sending test message: {test_message}")
            await websocket.send(json.dumps(test_message))
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                logger.info(f"Received response: {response}")
                
                # Try to parse response
                try:
                    response_data = json.loads(response)
                    logger.info(f"Response type: {response_data.get('type', 'unknown')}")
                    return True
                except json.JSONDecodeError:
                    logger.warning(f"Response is not valid JSON: {response}")
                    return True  # Still counts as success
                    
            except asyncio.TimeoutError:
                logger.error("No response received within 10 seconds")
                return False
                
    except websockets.exceptions.ConnectionClosed as e:
        logger.error(f"WebSocket connection closed: {e}")
        return False
    except Exception as e:
        logger.error(f"WebSocket connection failed: {e}")
        return False


async def test_health_check():
    """Test health check via WebSocket"""
    uri = "ws://localhost:8012"
    
    try:
        logger.info("Testing health check via WebSocket")
        
        async with websockets.connect(uri) as websocket:
            # Skip welcome message
            try:
                await asyncio.wait_for(websocket.recv(), timeout=2.0)
            except asyncio.TimeoutError:
                pass
            
            # Send health check
            health_check = {
                "type": "health_check",
                "message_id": "test_health_001"
            }
            
            logger.info("Sending health check request")
            await websocket.send(json.dumps(health_check))
            
            # Wait for health response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                response_data = json.loads(response)
                
                if response_data.get("type") == "health_check_response":
                    health_data = response_data.get("data", {})
                    logger.info(f"Health check successful:")
                    logger.info(f"  Status: {health_data.get('status')}")
                    logger.info(f"  Agent Ready: {health_data.get('agent_ready')}")
                    logger.info(f"  Connections: {health_data.get('connections')}")
                    logger.info(f"  Queries Processed: {health_data.get('queries_processed')}")
                    return True
                else:
                    logger.warning(f"Unexpected response type: {response_data.get('type')}")
                    return False
                    
            except asyncio.TimeoutError:
                logger.error("Health check timed out")
                return False
                
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return False


async def main():
    """Main test function"""
    logger.info("Starting WebSocket connection tests for Data Agent")
    
    print("\n" + "="*60)
    print("WEBSOCKET CONNECTION TEST FOR DATA AGENT")
    print("="*60)
    
    # Test 1: Basic connection
    print("\n[TEST 1] Basic WebSocket Connection Test")
    print("-" * 40)
    connection_success = await test_websocket_connection()
    print(f"Result: {'✅ PASSED' if connection_success else '❌ FAILED'}")
    
    # Test 2: Health check
    print("\n[TEST 2] Health Check via WebSocket")
    print("-" * 40)
    health_success = await test_health_check()
    print(f"Result: {'✅ PASSED' if health_success else '❌ FAILED'}")
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum([connection_success, health_success])
    total = 2
    
    print(f"Tests Passed: {passed}/{total}")
    print(f"Overall Status: {'✅ ALL TESTS PASSED' if passed == total else '⚠️  SOME TESTS FAILED'}")
    
    if passed == total:
        print("\n🎉 WebSocket connection to Data Agent is working correctly!")
        print("The backend should now be able to connect via WebSocket.")
    else:
        print("\n⚠️  There are issues with the WebSocket connection.")
        print("Please check the data agent logs for more details.")


if __name__ == "__main__":
    asyncio.run(main())
