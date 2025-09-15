#!/usr/bin/env python3
"""
Test WebSocket fixes across Frontend -> Backend -> TiDB MCP Server
Validates the fixes implemented for WebSocket inconsistencies and bugs.
"""

import asyncio
import json
import logging
import websockets
from datetime import datetime
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebSocketTester:
    """Test WebSocket connections and message flow"""
    
    def __init__(self):
        self.backend_url = "ws://localhost:8080"
        self.tidb_mcp_url = "ws://localhost:8000/ws"
        
    async def test_frontend_to_backend_connection(self):
        """Test frontend-style connection to backend"""
        logger.info("Testing Frontend -> Backend WebSocket connection...")
        
        try:
            uri = f"{self.backend_url}/ws/chat/test_user"
            
            async with websockets.connect(uri) as websocket:
                logger.info(f"Connected to backend at {uri}")
                
                # Send connection handshake (like frontend does)
                handshake = {
                    "type": "connection_handshake",
                    "agent_id": "frontend_test_user_session_123",
                    "agent_type": "frontend",
                    "user_id": "test_user",
                    "capabilities": ["query_processing", "real_time_updates", "heartbeat"],
                    "timestamp": datetime.now().isoformat(),
                    "client_info": {
                        "browser": "Test Client",
                        "url": "http://localhost:3000/test"
                    }
                }
                
                await websocket.send(json.dumps(handshake))
                logger.info("Sent handshake to backend")
                
                # Wait for acknowledgment
                response = await websocket.recv()
                response_data = json.loads(response)
                logger.info(f"Received response: {response_data}")
                
                if response_data.get("type") == "connection_acknowledged":
                    logger.info("✅ Handshake successful!")
                    
                    # Test heartbeat
                    heartbeat = {
                        "type": "heartbeat",
                        "timestamp": datetime.now().isoformat(),
                        "correlation_id": "heartbeat_123"
                    }
                    
                    await websocket.send(json.dumps(heartbeat))
                    heartbeat_response = await websocket.recv()
                    heartbeat_data = json.loads(heartbeat_response)
                    
                    if heartbeat_data.get("type") == "heartbeat_response":
                        logger.info("✅ Heartbeat successful!")
                    else:
                        logger.error(f"❌ Unexpected heartbeat response: {heartbeat_data}")
                    
                    # Test query
                    query = {
                        "type": "query",
                        "query": "SELECT * FROM test_table LIMIT 5",
                        "query_id": "query_123",
                        "session_id": "frontend_session_123",
                        "database_context": {"database": "test_db"},
                        "preferences": {"output_format": "json"},
                        "timestamp": datetime.now().isoformat(),
                        "correlation_id": "query_123"
                    }
                    
                    await websocket.send(json.dumps(query))
                    logger.info("Sent test query")
                    
                    # Wait for processing start
                    start_response = await websocket.recv()
                    start_data = json.loads(start_response)
                    logger.info(f"Query processing response: {start_data}")
                    
                    if start_data.get("type") == "query_processing_started":
                        logger.info("✅ Query processing started!")
                        
                        # Wait for final response
                        try:
                            final_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                            final_data = json.loads(final_response)
                            logger.info(f"Final query response: {final_data}")
                            
                            if final_data.get("type") == "query_response":
                                logger.info("✅ Query response received!")
                            else:
                                logger.warning(f"⚠️  Unexpected query response type: {final_data.get('type')}")
                        except asyncio.TimeoutError:
                            logger.warning("⚠️  Query response timeout")
                    
                else:
                    logger.error(f"❌ Unexpected handshake response: {response_data}")
                    
        except Exception as e:
            logger.error(f"❌ Frontend->Backend test failed: {e}")
            
    async def test_backend_to_tidb_connection(self):
        """Test backend-style connection to TiDB MCP Server"""
        logger.info("Testing Backend -> TiDB MCP Server WebSocket connection...")
        
        try:
            async with websockets.connect(self.tidb_mcp_url) as websocket:
                logger.info(f"Connected to TiDB MCP Server at {self.tidb_mcp_url}")
                
                # Send agent connection message (like backend does)
                connection_msg = {
                    "type": "event",
                    "event_name": "agent_connected",
                    "payload": {
                        "agent_id": "backend_test_hash",
                        "agent_type": "backend",
                        "capabilities": [
                            "batch_requests",
                            "event_subscriptions", 
                            "schema_caching",
                            "request_deduplication"
                        ]
                    },
                    "timestamp": time.time()
                }
                
                await websocket.send(json.dumps(connection_msg))
                logger.info("Sent agent connection to TiDB MCP Server")
                
                # Wait for acknowledgment
                response = await websocket.recv()
                response_data = json.loads(response)
                logger.info(f"Received response: {response_data}")
                
                if (response_data.get("type") == "event" and 
                    response_data.get("event_name") == "connection_acknowledged"):
                    logger.info("✅ TiDB MCP connection acknowledged!")
                    
                    # Test discover databases request
                    discover_request = {
                        "type": "request",
                        "request_id": "discover_123",
                        "method": "discover_databases",
                        "params": {},
                        "timestamp": time.time()
                    }
                    
                    await websocket.send(json.dumps(discover_request))
                    logger.info("Sent discover databases request")
                    
                    # Wait for response
                    discover_response = await websocket.recv()
                    discover_data = json.loads(discover_response)
                    logger.info(f"Discover response: {discover_data}")
                    
                    if discover_data.get("type") == "response":
                        payload = discover_data.get("payload", {})
                        if payload.get("success", True):
                            databases = payload.get("databases", [])
                            logger.info(f"✅ Discovered {len(databases)} databases!")
                        else:
                            logger.error(f"❌ Discover databases failed: {payload.get('error')}")
                    else:
                        logger.error(f"❌ Unexpected discover response: {discover_data}")
                        
                else:
                    logger.error(f"❌ Unexpected TiDB connection response: {response_data}")
                    
        except Exception as e:
            logger.error(f"❌ Backend->TiDB test failed: {e}")
            
    async def run_all_tests(self):
        """Run all WebSocket tests"""
        logger.info("🔧 Starting WebSocket fixes validation tests...")
        logger.info("=" * 60)
        
        await asyncio.sleep(2)  # Wait for services to be ready
        
        # Test both connections
        await self.test_frontend_to_backend_connection()
        await asyncio.sleep(1)
        await self.test_backend_to_tidb_connection()
        
        logger.info("=" * 60)
        logger.info("🏁 WebSocket tests completed!")

async def main():
    """Main test function"""
    tester = WebSocketTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
