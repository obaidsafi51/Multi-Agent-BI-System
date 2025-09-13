#!/usr/bin/env python3
"""
Simple heartbeat test for WebSocket agents
"""

import asyncio
import json
import websockets
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_heartbeat(endpoint, agent_name):
    """Test heartbeat functionality for a specific agent"""
    try:
        logger.info(f"Testing {agent_name} heartbeat at {endpoint}")
        
        async with websockets.connect(endpoint) as websocket:
            # Wait for welcome message
            welcome = await websocket.recv()
            logger.info(f"{agent_name}: Welcome - {welcome}")
            
            # Send heartbeat message
            heartbeat_msg = {
                "type": "heartbeat", 
                "timestamp": "2025-09-13T08:00:00.000Z"
            }
            
            await websocket.send(json.dumps(heartbeat_msg))
            logger.info(f"{agent_name}: Heartbeat sent")
            
            # Wait for heartbeat response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                logger.info(f"{agent_name}: Heartbeat response - {response_data}")
                
                if response_data.get("type") == "heartbeat_response":
                    return True, f"✓ Heartbeat working"
                else:
                    return False, f"✗ Unexpected response: {response_data.get('type')}"
                    
            except asyncio.TimeoutError:
                return False, f"✗ No heartbeat response (timeout)"
                
    except Exception as e:
        return False, f"✗ Connection error: {str(e)}"

async def main():
    """Test heartbeat for all agents"""
    agents = {
        'nlp-agent': 'ws://localhost:8011/ws',
        'data-agent': 'ws://localhost:8012/ws', 
        'viz-agent': 'ws://localhost:8013/ws'
    }
    
    logger.info("="*60)
    logger.info("HEARTBEAT TEST")
    logger.info("="*60)
    
    for agent_name, endpoint in agents.items():
        success, message = await test_heartbeat(endpoint, agent_name)
        status = "✓ PASS" if success else "✗ FAIL"
        logger.info(f"{agent_name:15} | {status} | {message}")
        logger.info("-" * 60)

if __name__ == "__main__":
    asyncio.run(main())
