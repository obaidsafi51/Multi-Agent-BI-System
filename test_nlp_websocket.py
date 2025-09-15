#!/usr/bin/env python3
"""
Test script to verify NLP agent WebSocket functionality
"""

import asyncio
import json
import logging
import websockets
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_nlp_websocket():
    """Test NLP agent WebSocket connection and message handling"""
    
    nlp_ws_url = "ws://localhost:8001/ws"
    
    try:
        logger.info(f"Connecting to NLP agent WebSocket: {nlp_ws_url}")
        
        async with websockets.connect(nlp_ws_url) as websocket:
            logger.info("✅ Connected to NLP agent WebSocket!")
            
            # Wait for connection acknowledgment
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                ack_data = json.loads(response)
                logger.info(f"📥 Connection acknowledgment: {ack_data}")
            except asyncio.TimeoutError:
                logger.warning("⚠️ No connection acknowledgment received")
            
            # Test 1: Send heartbeat
            logger.info("\n🔄 Test 1: Heartbeat")
            heartbeat_msg = {
                "type": "heartbeat",
                "timestamp": datetime.now().isoformat(),
                "correlation_id": "test_heartbeat_001"
            }
            
            await websocket.send(json.dumps(heartbeat_msg))
            logger.info(f"📤 Sent heartbeat: {heartbeat_msg}")
            
            response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            response_data = json.loads(response)
            logger.info(f"📥 Heartbeat response: {response_data}")
            
            # Test 2: Send SQL query (matching backend format)
            logger.info("\n🔄 Test 2: SQL Query Processing")
            sql_query_msg = {
                "type": "sql_query",
                "message_id": "test_msg_001",
                "sql_query": "SELECT * FROM revenue WHERE year = 2024 LIMIT 5",
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
            
            await websocket.send(json.dumps(sql_query_msg))
            logger.info(f"📤 Sent SQL query: {sql_query_msg['sql_query']}")
            
            response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
            response_data = json.loads(response)
            logger.info(f"📥 SQL query response: {json.dumps(response_data, indent=2)}")
            
            # Test 3: Send natural language query
            logger.info("\n🔄 Test 3: Natural Language Query Processing")
            nl_query_msg = {
                "type": "query",
                "message_id": "test_msg_002",
                "query": "Show me the total revenue for 2024",
                "query_id": "test_query_002",
                "context": {
                    "user_id": "test_user",
                    "session_id": "test_session"
                },
                "database_context": {
                    "database_name": "Agentic_BI"
                }
            }
            
            await websocket.send(json.dumps(nl_query_msg))
            logger.info(f"📤 Sent natural language query: {nl_query_msg['query']}")
            
            response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
            response_data = json.loads(response)
            logger.info(f"📥 NL query response: {json.dumps(response_data, indent=2)}")
            
            logger.info("\n✅ All WebSocket tests completed successfully!")
            
    except websockets.exceptions.ConnectionRefused:
        logger.error("❌ Connection refused - NLP agent may not be running on port 8001")
        logger.info("💡 Start NLP agent first: cd agents/nlp-agent && python3 main_optimized.py")
    except asyncio.TimeoutError:
        logger.error("❌ WebSocket response timeout")
    except Exception as e:
        logger.error(f"❌ WebSocket test failed: {e}")


async def test_backend_message_format():
    """Test with exact message format that backend sends"""
    
    nlp_ws_url = "ws://localhost:8001/ws"
    
    try:
        logger.info(f"\n🔄 Testing Backend Message Format")
        logger.info(f"Connecting to: {nlp_ws_url}")
        
        async with websockets.connect(nlp_ws_url) as websocket:
            # Skip connection ack
            try:
                await asyncio.wait_for(websocket.recv(), timeout=2.0)
            except:
                pass
            
            # Send message in exact backend format
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
            logger.info(f"📤 Sent backend-format message")
            
            response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
            response_data = json.loads(response)
            
            success = response_data.get("success", False)
            if success:
                logger.info("✅ Backend message format test PASSED")
                logger.info(f"📥 Response type: {response_data.get('type')}")
                logger.info(f"📥 Processing time: {response_data.get('processing_time_ms')}ms")
            else:
                logger.error("❌ Backend message format test FAILED")
                logger.error(f"📥 Error: {response_data.get('error')}")
            
    except Exception as e:
        logger.error(f"❌ Backend format test failed: {e}")


if __name__ == "__main__":
    print("🧪 NLP Agent WebSocket Test Suite")
    print("=" * 50)
    
    try:
        # Run basic WebSocket tests
        asyncio.run(test_nlp_websocket())
        
        # Run backend message format test
        asyncio.run(test_backend_message_format())
        
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
