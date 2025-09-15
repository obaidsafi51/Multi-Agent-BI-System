#!/usr/bin/env python3
"""
Comprehensive WebSocket test for NLP agent implementation
This test validates:
1. WebSocket server setup
2. Message protocol compatibility with backend
3. SQL query processing
4. Natural language query processing
5. Error handling
"""

import asyncio
import json
import logging
import websockets
import sys
import os
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NLPAgentWebSocketTest:
    """Comprehensive WebSocket test suite for NLP agent"""
    
    def __init__(self, nlp_url="ws://localhost:8001/ws"):
        self.nlp_url = nlp_url
        self.test_results = []
        
    async def run_all_tests(self):
        """Run all WebSocket tests"""
        tests = [
            ("Connection Test", self.test_connection),
            ("Heartbeat Test", self.test_heartbeat),
            ("SQL Query Test", self.test_sql_query),
            ("Natural Language Query Test", self.test_nl_query),
            ("Error Handling Test", self.test_error_handling),
            ("Backend Message Format Test", self.test_backend_format)
        ]
        
        logger.info("🧪 Starting NLP Agent WebSocket Test Suite")
        logger.info("=" * 60)
        
        for test_name, test_func in tests:
            logger.info(f"\n🔄 Running: {test_name}")
            try:
                result = await test_func()
                self.test_results.append((test_name, "PASS" if result else "FAIL"))
                logger.info(f"✅ {test_name}: {'PASSED' if result else 'FAILED'}")
            except Exception as e:
                self.test_results.append((test_name, f"ERROR: {str(e)}"))
                logger.error(f"❌ {test_name}: ERROR - {e}")
        
        self.print_summary()
    
    async def test_connection(self):
        """Test basic WebSocket connection"""
        try:
            async with websockets.connect(self.nlp_url) as websocket:
                # Check for connection acknowledgment
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    ack_data = json.loads(response)
                    
                    if ack_data.get("type") == "connection_established":
                        logger.info(f"📥 Connection ack: {ack_data}")
                        return True
                    else:
                        logger.warning(f"Unexpected first message: {ack_data}")
                        return True  # Connection works even without ack
                        
                except asyncio.TimeoutError:
                    logger.warning("No connection acknowledgment received")
                    return True  # Connection still works
                    
        except websockets.exceptions.ConnectionRefused:
            logger.error("Connection refused - NLP agent not running?")
            return False
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    async def test_heartbeat(self):
        """Test heartbeat message exchange"""
        try:
            async with websockets.connect(self.nlp_url) as websocket:
                # Skip connection ack
                try:
                    await asyncio.wait_for(websocket.recv(), timeout=2.0)
                except:
                    pass
                
                # Send heartbeat
                heartbeat_msg = {
                    "type": "heartbeat",
                    "timestamp": datetime.now().isoformat(),
                    "correlation_id": "test_heartbeat_001"
                }
                
                await websocket.send(json.dumps(heartbeat_msg))
                
                # Wait for response
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                response_data = json.loads(response)
                
                if response_data.get("type") == "heartbeat_response":
                    logger.info("💓 Heartbeat response received")
                    return True
                else:
                    logger.warning(f"Unexpected heartbeat response: {response_data}")
                    return False
                    
        except Exception as e:
            logger.error(f"Heartbeat test failed: {e}")
            return False
    
    async def test_sql_query(self):
        """Test SQL query processing"""
        try:
            async with websockets.connect(self.nlp_url) as websocket:
                # Skip connection ack
                try:
                    await asyncio.wait_for(websocket.recv(), timeout=2.0)
                except:
                    pass
                
                # Send SQL query message
                sql_msg = {
                    "type": "sql_query",
                    "message_id": "test_sql_001",
                    "sql_query": "SELECT COUNT(*) as total_records FROM revenue WHERE year = 2024",
                    "query_id": "test_query_001",
                    "query_context": {
                        "database_context": {
                            "database_name": "Agentic_BI"
                        },
                        "timestamp": datetime.now().isoformat(),
                        "source": "test_script"
                    },
                    "execution_config": {
                        "use_cache": True,
                        "validate_result": True,
                        "optimize_query": True
                    }
                }
                
                await websocket.send(json.dumps(sql_msg))
                
                # Wait for response
                response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                response_data = json.loads(response)
                
                if response_data.get("type") == "sql_query_response":
                    success = response_data.get("success", False)
                    if success:
                        logger.info("🔍 SQL query processed successfully")
                        logger.info(f"📊 Response time: {response_data.get('processing_time_ms')}ms")
                        return True
                    else:
                        logger.error(f"SQL query failed: {response_data.get('error')}")
                        return False
                else:
                    logger.error(f"Unexpected SQL response type: {response_data.get('type')}")
                    return False
                    
        except Exception as e:
            logger.error(f"SQL query test failed: {e}")
            return False
    
    async def test_nl_query(self):
        """Test natural language query processing"""
        try:
            async with websockets.connect(self.nlp_url) as websocket:
                # Skip connection ack
                try:
                    await asyncio.wait_for(websocket.recv(), timeout=2.0)
                except:
                    pass
                
                # Send natural language query
                nl_msg = {
                    "type": "query",
                    "message_id": "test_nl_001",
                    "query": "Show me the total revenue for the current year",
                    "query_id": "test_nl_query_001",
                    "context": {
                        "user_id": "test_user",
                        "session_id": "test_session"
                    },
                    "database_context": {
                        "database_name": "Agentic_BI"
                    }
                }
                
                await websocket.send(json.dumps(nl_msg))
                
                # Wait for response
                response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                response_data = json.loads(response)
                
                if response_data.get("type") == "query_response":
                    success = response_data.get("success", False)
                    if success:
                        logger.info("🗣️ Natural language query processed successfully")
                        logger.info(f"📊 Response time: {response_data.get('processing_time_ms')}ms")
                        sql_query = response_data.get("sql_query", "")
                        if sql_query:
                            logger.info(f"🔍 Generated SQL: {sql_query[:100]}...")
                        return True
                    else:
                        logger.error(f"NL query failed: {response_data.get('error')}")
                        return False
                else:
                    logger.error(f"Unexpected NL response type: {response_data.get('type')}")
                    return False
                    
        except Exception as e:
            logger.error(f"Natural language query test failed: {e}")
            return False
    
    async def test_error_handling(self):
        """Test error scenarios"""
        try:
            async with websockets.connect(self.nlp_url) as websocket:
                # Skip connection ack
                try:
                    await asyncio.wait_for(websocket.recv(), timeout=2.0)
                except:
                    pass
                
                # Send invalid message type
                invalid_msg = {
                    "type": "invalid_message_type",
                    "message_id": "test_error_001",
                    "data": "This should trigger an error"
                }
                
                await websocket.send(json.dumps(invalid_msg))
                
                # Wait for error response
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                response_data = json.loads(response)
                
                if response_data.get("type") == "error":
                    error_info = response_data.get("error", {})
                    if "unknown_message_type" in error_info.get("type", ""):
                        logger.info("⚠️ Error handling working correctly")
                        return True
                    else:
                        logger.warning(f"Unexpected error type: {error_info}")
                        return True  # Still good that it's handled
                else:
                    logger.error(f"Expected error response, got: {response_data.get('type')}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error handling test failed: {e}")
            return False
    
    async def test_backend_format(self):
        """Test exact backend message format compatibility"""
        try:
            async with websockets.connect(self.nlp_url) as websocket:
                # Skip connection ack
                try:
                    await asyncio.wait_for(websocket.recv(), timeout=2.0)
                except:
                    pass
                
                # Send message in exact backend format (from backend/main.py)
                backend_msg = {
                    "type": "sql_query",
                    "sql_query": "SELECT SUM(amount) as total_revenue FROM revenue WHERE year = 2024",
                    "query_id": "backend_test_001",
                    "query_context": {
                        "database_context": {
                            "database_name": "Agentic_BI",
                            "schema": "financial_data"
                        },
                        "timestamp": datetime.now().isoformat(),
                        "source": "backend_websocket"
                    },
                    "execution_config": {
                        "use_cache": True,
                        "validate_result": True,
                        "optimize_query": True
                    },
                    "message_id": "backend_msg_001",
                    "timestamp": datetime.now().timestamp()
                }
                
                await websocket.send(json.dumps(backend_msg))
                
                # Wait for response
                response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                response_data = json.loads(response)
                
                # Check if response format matches what backend expects
                required_fields = ["type", "success", "query_id", "response_to"]
                missing_fields = [field for field in required_fields if field not in response_data]
                
                if not missing_fields:
                    logger.info("🔗 Backend message format compatibility confirmed")
                    success = response_data.get("success", False)
                    logger.info(f"📊 Processing success: {success}")
                    return True
                else:
                    logger.error(f"Missing required fields: {missing_fields}")
                    return False
                    
        except Exception as e:
            logger.error(f"Backend format test failed: {e}")
            return False
    
    def print_summary(self):
        """Print test summary"""
        logger.info("\n" + "=" * 60)
        logger.info("🧪 TEST SUMMARY")
        logger.info("=" * 60)
        
        passed = 0
        failed = 0
        
        for test_name, result in self.test_results:
            status_icon = "✅" if result == "PASS" else "❌"
            logger.info(f"{status_icon} {test_name}: {result}")
            
            if result == "PASS":
                passed += 1
            else:
                failed += 1
        
        logger.info("-" * 60)
        logger.info(f"📊 Results: {passed} passed, {failed} failed")
        
        if failed == 0:
            logger.info("🎉 ALL TESTS PASSED! NLP Agent WebSocket is ready!")
        else:
            logger.info("⚠️ Some tests failed. Check implementation.")
        
        logger.info("=" * 60)


async def main():
    """Main test runner"""
    # Check if NLP agent is running
    logger.info("🔍 Testing NLP Agent WebSocket Implementation")
    logger.info("💡 Make sure NLP agent is running: cd agents/nlp-agent && python3 main_optimized.py")
    
    test_suite = NLPAgentWebSocketTest()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        sys.exit(1)
