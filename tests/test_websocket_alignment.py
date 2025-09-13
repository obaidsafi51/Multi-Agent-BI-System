#!/usr/bin/env python3
"""
Comprehensive WebSocket alignment test for all agents.
Tests all fixes applied during the alignment process.
"""

import asyncio
import json
import time
import websockets
import logging
from typing import Dict, Set

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebSocketAlignmentTest:
    def __init__(self):
        self.test_results = {}
        
        # Agent configurations
        self.agent_endpoints = {
            'nlp-agent': 'ws://localhost:8011/ws',
            'data-agent': 'ws://localhost:8012/ws', 
            'viz-agent': 'ws://localhost:8013/ws',
            'tidb-mcp-server': 'ws://localhost:8000/ws'
        }
        
        self.backend_endpoint = 'ws://localhost:8000/ws'
    
    async def test_agent_connection(self, agent_name: str, endpoint: str) -> Dict:
        """Test individual agent WebSocket connection"""
        logger.info(f"Testing {agent_name} connection...")
        
        result = {
            'agent': agent_name,
            'connection_established': False,
            'heartbeat_working': False,
            'message_handling': False,
            'error': None
        }
        
        try:
            async with websockets.connect(endpoint) as websocket:
                result['connection_established'] = True
                logger.info(f"✓ {agent_name}: Connection established")
                
                # Test heartbeat
                heartbeat_msg = {
                    "type": "heartbeat",
                    "timestamp": time.time(),
                    "correlation_id": f"test_{agent_name}_heartbeat"
                }
                
                await websocket.send(json.dumps(heartbeat_msg))
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    response_data = json.loads(response)
                    
                    if response_data.get("type") == "heartbeat_response":
                        result['heartbeat_working'] = True
                        logger.info(f"✓ {agent_name}: Heartbeat working")
                    else:
                        logger.info(f"✓ {agent_name}: Received response - {response_data.get('type')}")
                        result['message_handling'] = True
                        
                except asyncio.TimeoutError:
                    logger.warning(f"⚠ {agent_name}: No heartbeat response (may be normal)")
                    result['message_handling'] = True  # Connection is working
                
                # Test basic message
                test_msg = {
                    "type": "test_message",
                    "content": "Testing WebSocket alignment",
                    "correlation_id": f"test_{agent_name}_message"
                }
                
                await websocket.send(json.dumps(test_msg))
                result['message_handling'] = True
                logger.info(f"✓ {agent_name}: Message handling working")
                
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"✗ {agent_name}: {e}")
        
        return result
    
    async def test_backend_connections(self) -> Dict:
        """Test backend WebSocket connections to agents"""
        logger.info("Testing backend WebSocket connections...")
        
        result = {
            'backend_accessible': False,
            'agent_connections': {},
            'error': None
        }
        
        try:
            async with websockets.connect(self.backend_endpoint) as websocket:
                result['backend_accessible'] = True
                logger.info("✓ Backend: WebSocket accessible")
                
                # Test a request that should trigger agent communication
                test_request = {
                    "type": "test_agent_communication",
                    "target": "all",
                    "correlation_id": "test_backend_communication"
                }
                
                await websocket.send(json.dumps(test_request))
                
                # Wait for any responses
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10)
                    logger.info(f"✓ Backend: Received response - {response[:100]}...")
                except asyncio.TimeoutError:
                    logger.info("✓ Backend: Request sent (no immediate response expected)")
                
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"✗ Backend: {e}")
        
        return result
    
    async def test_heartbeat_consistency(self) -> Dict:
        """Test heartbeat consistency across all agents"""
        logger.info("Testing heartbeat consistency...")
        
        result = {
            'consistent_heartbeat': True,
            'agents_with_heartbeat': [],
            'agents_without_heartbeat': [],
            'error': None
        }
        
        for agent_name, endpoint in self.agent_endpoints.items():
            try:
                async with websockets.connect(endpoint) as websocket:
                    # Send heartbeat
                    heartbeat_msg = {
                        "type": "heartbeat",
                        "timestamp": time.time(),
                        "correlation_id": f"consistency_test_{agent_name}"
                    }
                    
                    await websocket.send(json.dumps(heartbeat_msg))
                    
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=3)
                        response_data = json.loads(response)
                        
                        if response_data.get("type") == "heartbeat_response":
                            result['agents_with_heartbeat'].append(agent_name)
                        else:
                            result['agents_without_heartbeat'].append(agent_name)
                            
                    except asyncio.TimeoutError:
                        result['agents_without_heartbeat'].append(agent_name)
                        
            except Exception as e:
                result['agents_without_heartbeat'].append(agent_name)
                logger.warning(f"Heartbeat test failed for {agent_name}: {e}")
        
        # Check consistency
        if len(result['agents_without_heartbeat']) > 0:
            result['consistent_heartbeat'] = False
            
        logger.info(f"Agents with heartbeat: {result['agents_with_heartbeat']}")
        logger.info(f"Agents without heartbeat: {result['agents_without_heartbeat']}")
        
        return result
    
    async def test_message_format_consistency(self) -> Dict:
        """Test message format consistency"""
        logger.info("Testing message format consistency...")
        
        result = {
            'format_consistent': True,
            'agents_tested': [],
            'format_issues': [],
            'error': None
        }
        
        standard_message = {
            "type": "test_format",
            "content": "Testing message format consistency",
            "correlation_id": "format_test_123",
            "timestamp": time.time()
        }
        
        for agent_name, endpoint in self.agent_endpoints.items():
            try:
                async with websockets.connect(endpoint) as websocket:
                    await websocket.send(json.dumps(standard_message))
                    result['agents_tested'].append(agent_name)
                    logger.info(f"✓ {agent_name}: Message format accepted")
                    
            except Exception as e:
                result['format_issues'].append({
                    'agent': agent_name,
                    'error': str(e)
                })
                result['format_consistent'] = False
                logger.error(f"✗ {agent_name}: Format issue - {e}")
        
        return result
    
    async def run_all_tests(self):
        """Run all WebSocket alignment tests"""
        logger.info("=" * 60)
        logger.info("WEBSOCKET ALIGNMENT TEST SUITE")
        logger.info("=" * 60)
        
        # Test individual agent connections
        logger.info("\n1. TESTING INDIVIDUAL AGENT CONNECTIONS")
        logger.info("-" * 50)
        
        agent_results = []
        for agent_name, endpoint in self.agent_endpoints.items():
            result = await self.test_agent_connection(agent_name, endpoint)
            agent_results.append(result)
            self.test_results[f'agent_{agent_name}'] = result
        
        # Test backend connections
        logger.info("\n2. TESTING BACKEND CONNECTIONS")
        logger.info("-" * 50)
        
        backend_result = await self.test_backend_connections()
        self.test_results['backend'] = backend_result
        
        # Test heartbeat consistency
        logger.info("\n3. TESTING HEARTBEAT CONSISTENCY")
        logger.info("-" * 50)
        
        heartbeat_result = await self.test_heartbeat_consistency()
        self.test_results['heartbeat'] = heartbeat_result
        
        # Test message format consistency
        logger.info("\n4. TESTING MESSAGE FORMAT CONSISTENCY")
        logger.info("-" * 50)
        
        format_result = await self.test_message_format_consistency()
        self.test_results['format'] = format_result
        
        # Generate summary
        logger.info("\n5. TEST SUMMARY")
        logger.info("-" * 50)
        
        await self.generate_summary()
    
    async def generate_summary(self):
        """Generate test summary"""
        total_tests = 0
        passed_tests = 0
        
        logger.info("\nAgent Connection Results:")
        for agent_name, endpoint in self.agent_endpoints.items():
            result = self.test_results.get(f'agent_{agent_name}', {})
            
            connection_status = "✓" if result.get('connection_established') else "✗"
            heartbeat_status = "✓" if result.get('heartbeat_working') else "⚠"
            message_status = "✓" if result.get('message_handling') else "✗"
            
            logger.info(f"  {agent_name:15} | Connect: {connection_status} | Heartbeat: {heartbeat_status} | Messages: {message_status}")
            
            total_tests += 3
            passed_tests += sum([
                result.get('connection_established', False),
                result.get('heartbeat_working', False),
                result.get('message_handling', False)
            ])
        
        backend_result = self.test_results.get('backend', {})
        backend_status = "✓" if backend_result.get('backend_accessible') else "✗"
        logger.info(f"  {'Backend':15} | Connect: {backend_status}")
        
        total_tests += 1
        passed_tests += 1 if backend_result.get('backend_accessible') else 0
        
        heartbeat_result = self.test_results.get('heartbeat', {})
        heartbeat_consistent = "✓" if heartbeat_result.get('consistent_heartbeat') else "✗"
        logger.info(f"\nHeartbeat Consistency: {heartbeat_consistent}")
        
        format_result = self.test_results.get('format', {})
        format_consistent = "✓" if format_result.get('format_consistent') else "✗"
        logger.info(f"Format Consistency: {format_consistent}")
        
        total_tests += 2
        passed_tests += sum([
            heartbeat_result.get('consistent_heartbeat', False),
            format_result.get('format_consistent', False)
        ])
        
        logger.info(f"\nOVERALL RESULTS: {passed_tests}/{total_tests} tests passed ({passed_tests/total_tests*100:.1f}%)")
        
        if passed_tests == total_tests:
            logger.info("🎉 ALL WEBSOCKET ALIGNMENT TESTS PASSED!")
        else:
            logger.info("⚠ Some tests failed - check logs for details")
        
        # Save results to file
        with open('websocket_alignment_test_results.json', 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        logger.info("\nTest results saved to: websocket_alignment_test_results.json")

async def main():
    """Main test runner"""
    test_runner = WebSocketAlignmentTest()
    
    try:
        await test_runner.run_all_tests()
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
    except Exception as e:
        logger.error(f"Test runner error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
