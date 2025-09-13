#!/usr/bin/env python3
"""
Simple heartbeat test to debug heartbeat message handling.
"""

import asyncio
import json
import websockets
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_individual_heartbeat(agent_name: str, endpoint: str):
    """Test individual agent heartbeat"""
    logger.info(f"Testing {agent_name} heartbeat...")
    
    try:
        async with websockets.connect(endpoint) as websocket:
            logger.info(f"✓ {agent_name}: Connected")
            
            # Wait for connection established message
            try:
                welcome = await asyncio.wait_for(websocket.recv(), timeout=5)
                logger.info(f"✓ {agent_name}: Welcome message - {json.loads(welcome).get('type')}")
            except asyncio.TimeoutError:
                logger.info(f"⚠ {agent_name}: No welcome message")
            
            # Send heartbeat
            heartbeat_msg = {
                "type": "heartbeat",
                "timestamp": 1726212000.0,
                "correlation_id": f"test_{agent_name}_heartbeat"
            }
            
            logger.info(f"Sending heartbeat to {agent_name}: {heartbeat_msg}")
            await websocket.send(json.dumps(heartbeat_msg))
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                response_data = json.loads(response)
                logger.info(f"✓ {agent_name}: Heartbeat response - {response_data}")
                
                if response_data.get("type") == "heartbeat_response":
                    logger.info(f"✅ {agent_name}: HEARTBEAT WORKING")
                    return True
                else:
                    logger.info(f"⚠ {agent_name}: Got response but not heartbeat_response")
                    return False
                    
            except asyncio.TimeoutError:
                logger.error(f"❌ {agent_name}: No heartbeat response within 10s")
                return False
            except websockets.exceptions.ConnectionClosedError as e:
                logger.error(f"❌ {agent_name}: Connection closed: {e}")
                return False
            except Exception as e:
                logger.error(f"❌ {agent_name}: Unexpected error: {e}")
                return False
                
    except Exception as e:
        logger.error(f"❌ {agent_name}: Connection failed: {e}")
        return False

async def main():
    """Test heartbeats for all agents"""
    logger.info("=" * 60)
    logger.info("SIMPLE HEARTBEAT TEST")
    logger.info("=" * 60)
    
    agents = {
        'nlp-agent': 'ws://localhost:8011/ws',
        'data-agent': 'ws://localhost:8012/ws', 
        'viz-agent': 'ws://localhost:8013/ws',
        'tidb-mcp-server': 'ws://localhost:8000/ws'
    }
    
    results = {}
    
    for agent_name, endpoint in agents.items():
        success = await test_individual_heartbeat(agent_name, endpoint)
        results[agent_name] = success
        logger.info("-" * 60)
    
    logger.info("SUMMARY:")
    for agent_name, success in results.items():
        status = "✅ WORKING" if success else "❌ FAILED"
        logger.info(f"  {agent_name:15} | Heartbeat: {status}")
    
    working_count = sum(results.values())
    total_count = len(results)
    logger.info(f"\nOverall: {working_count}/{total_count} agents have working heartbeats")

if __name__ == "__main__":
    asyncio.run(main())
