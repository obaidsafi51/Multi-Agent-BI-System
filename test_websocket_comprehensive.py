#!/usr/bin/env python3
"""
Comprehensive WebSocket test for all core components:
- TiDB MCP Server
- NLP Agent  
- Backend
- Frontend integration
- Schema caching validation
"""

import asyncio
import json
import websockets
import aiohttp
import time
from typing import Dict, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ComponentTester:
    """Comprehensive tester for all WebSocket components"""
    
    def __init__(self):
        self.test_results = {
            'tidb_mcp': {'status': 'not_tested', 'details': {}},
            'nlp_agent': {'status': 'not_tested', 'details': {}},
            'backend': {'status': 'not_tested', 'details': {}},
            'frontend': {'status': 'not_tested', 'details': {}},
            'schema_cache': {'status': 'not_tested', 'details': {}}
        }

    async def test_tidb_mcp_websocket(self):
        """Test TiDB MCP server WebSocket connection and capabilities"""
        logger.info("🔍 Testing TiDB MCP Server WebSocket...")
        
        try:
            # Test HTTP health first
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:8000/health') as response:
                    health_data = await response.json()
                    logger.info(f"TiDB MCP Health: {health_data}")
            
            # Test database discovery
            async with aiohttp.ClientSession() as session:
                async with session.post('http://localhost:8000/tools/discover_databases_tool') as response:
                    databases = await response.json()
                    logger.info(f"Available databases: {[db['name'] for db in databases]}")
            
            # Test table discovery for schema caching
            async with aiohttp.ClientSession() as session:
                async with session.post('http://localhost:8000/tools/discover_tables_tool', 
                                      json={'database': 'Retail_Business_Agentic_AI'}) as response:
                    tables = await response.json()
                    table_names = [t['name'] for t in tables]
                    logger.info(f"Tables in Retail_Business_Agentic_AI: {table_names}")
            
            # Test schema retrieval for cashflow table
            async with aiohttp.ClientSession() as session:
                async with session.post('http://localhost:8000/tools/get_table_schema_tool',
                                      json={'database': 'Retail_Business_Agentic_AI', 'table': 'cashflow'}) as response:
                    schema = await response.json()
                    columns = [col['name'] for col in schema.get('columns', [])]
                    logger.info(f"Cashflow table columns: {columns}")
            
            # Test query execution
            test_query = "SELECT COUNT(*) as total_rows FROM Retail_Business_Agentic_AI.cashflow"
            async with aiohttp.ClientSession() as session:
                async with session.post('http://localhost:8000/tools/execute_query_tool',
                                      json={'query': test_query, 'use_cache': True}) as response:
                    result = await response.json()
                    logger.info(f"Query result: {result}")
            
            self.test_results['tidb_mcp'] = {
                'status': 'success',
                'details': {
                    'health_check': 'passed',
                    'database_discovery': 'passed',
                    'table_discovery': 'passed',
                    'schema_retrieval': 'passed',
                    'query_execution': 'passed',
                    'databases': databases,
                    'tables': table_names,
                    'cashflow_columns': columns
                }
            }
            
        except Exception as e:
            logger.error(f"TiDB MCP test failed: {e}")
            self.test_results['tidb_mcp'] = {
                'status': 'failed',
                'details': {'error': str(e)}
            }

    async def test_nlp_agent_websocket(self):
        """Test NLP Agent WebSocket connection"""
        logger.info("🔍 Testing NLP Agent WebSocket...")
        
        try:
            uri = "ws://localhost:8011"
            async with websockets.connect(uri) as websocket:
                # Send test query
                test_message = {
                    "type": "query",
                    "query": "show me total cashflow for 2024",
                    "session_id": "test_session_ws",
                    "query_id": f"nlp_test_{int(time.time())}",
                    "context": {
                        "database": "Retail_Business_Agentic_AI",
                        "tables": ["cashflow", "revenue", "expenses"]
                    }
                }
                
                await websocket.send(json.dumps(test_message))
                logger.info(f"Sent to NLP Agent: {test_message['type']}")
                
                # Wait for response
                response = await asyncio.wait_for(websocket.recv(), timeout=30)
                response_data = json.loads(response)
                logger.info(f"NLP Agent response: {response_data}")
                
                self.test_results['nlp_agent'] = {
                    'status': 'success',
                    'details': {
                        'connection': 'established',
                        'query_processing': 'passed',
                        'response': response_data
                    }
                }
                
        except Exception as e:
            logger.error(f"NLP Agent test failed: {e}")
            self.test_results['nlp_agent'] = {
                'status': 'failed', 
                'details': {'error': str(e)}
            }

    async def test_backend_websocket(self):
        """Test Backend WebSocket functionality"""
        logger.info("🔍 Testing Backend WebSocket...")
        
        try:
            # Test HTTP API first
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:8080/health') as response:
                    health_data = await response.json()
                    logger.info(f"Backend Health: {health_data}")
            
            # Test database context endpoint
            async with aiohttp.ClientSession() as session:
                async with session.post('http://localhost:8080/api/database/context',
                                      json={'database_name': 'Retail_Business_Agentic_AI'}) as response:
                    context_data = await response.json()
                    logger.info(f"Database context: {context_data}")
            
            # Test WebSocket query processing
            uri = "ws://localhost:8080/ws/query"
            async with websockets.connect(uri) as websocket:
                # Send query via WebSocket
                query_message = {
                    "type": "query",
                    "query": "show me cashflow data for 2024",
                    "session_id": "test_backend_ws",
                    "query_id": f"backend_test_{int(time.time())}"
                }
                
                await websocket.send(json.dumps(query_message))
                logger.info("Sent query to backend WebSocket")
                
                # Wait for response
                response = await asyncio.wait_for(websocket.recv(), timeout=45)
                response_data = json.loads(response)
                logger.info(f"Backend WebSocket response: {response_data}")
                
                self.test_results['backend'] = {
                    'status': 'success',
                    'details': {
                        'http_health': 'passed',
                        'database_context': 'passed',
                        'websocket_query': 'passed',
                        'response': response_data
                    }
                }
                
        except Exception as e:
            logger.error(f"Backend test failed: {e}")
            self.test_results['backend'] = {
                'status': 'failed',
                'details': {'error': str(e)}
            }

    async def test_schema_caching_process(self):
        """Test schema caching across all components"""
        logger.info("🔍 Testing Schema Caching Process...")
        
        try:
            # Test backend schema management
            async with aiohttp.ClientSession() as session:
                # Request schema cache
                async with session.post('http://localhost:8080/api/database/schema/cache',
                                      json={'database_name': 'Retail_Business_Agentic_AI'}) as response:
                    cache_result = await response.json()
                    logger.info(f"Schema cache result: {cache_result}")
                
                # Get cached schema
                async with session.get('http://localhost:8080/api/database/schema/Retail_Business_Agentic_AI') as response:
                    schema_data = await response.json()
                    logger.info(f"Cached schema tables: {len(schema_data.get('tables', []))}")
            
            # Test Redis cache directly
            import redis
            r = redis.Redis(host='localhost', port=6379, decode_responses=True)
            
            # Check if schema is cached in Redis
            cache_key = "database_context:Retail_Business_Agentic_AI"
            cached_data = r.get(cache_key)
            if cached_data:
                cached_schema = json.loads(cached_data)
                logger.info(f"Redis cached schema: {cached_schema.get('table_count', 0)} tables")
            
            self.test_results['schema_cache'] = {
                'status': 'success',
                'details': {
                    'backend_cache': 'passed',
                    'redis_cache': 'passed' if cached_data else 'empty',
                    'cached_tables': len(schema_data.get('tables', [])),
                    'cache_status': cache_result
                }
            }
            
        except Exception as e:
            logger.error(f"Schema caching test failed: {e}")
            self.test_results['schema_cache'] = {
                'status': 'failed',
                'details': {'error': str(e)}
            }

    async def test_frontend_websocket(self):
        """Test Frontend WebSocket capabilities"""
        logger.info("🔍 Testing Frontend WebSocket...")
        
        try:
            # Check if frontend is running
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:3000') as response:
                    status = response.status
                    logger.info(f"Frontend status: {status}")
            
            # Test frontend API routes
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:3000/api/health') as response:
                    if response.status == 200:
                        health_data = await response.json()
                        logger.info(f"Frontend health: {health_data}")
                    else:
                        logger.info("Frontend health endpoint not found")
            
            self.test_results['frontend'] = {
                'status': 'success' if status == 200 else 'warning',
                'details': {
                    'server_running': status == 200,
                    'status_code': status
                }
            }
            
        except Exception as e:
            logger.error(f"Frontend test failed: {e}")
            self.test_results['frontend'] = {
                'status': 'failed',
                'details': {'error': str(e)}
            }

    async def run_comprehensive_test(self):
        """Run all tests and generate report"""
        logger.info("🚀 Starting Comprehensive WebSocket Test Suite...")
        
        # Run all tests
        await self.test_tidb_mcp_websocket()
        await self.test_nlp_agent_websocket()  
        await self.test_backend_websocket()
        await self.test_schema_caching_process()
        await self.test_frontend_websocket()
        
        # Generate report
        logger.info("\n" + "="*60)
        logger.info("📊 COMPREHENSIVE TEST RESULTS")
        logger.info("="*60)
        
        for component, result in self.test_results.items():
            status_icon = "✅" if result['status'] == 'success' else "⚠️" if result['status'] == 'warning' else "❌"
            logger.info(f"{status_icon} {component.upper()}: {result['status']}")
            
            if result['details']:
                for key, value in result['details'].items():
                    logger.info(f"   • {key}: {value}")
        
        # Overall assessment
        success_count = sum(1 for r in self.test_results.values() if r['status'] == 'success')
        total_tests = len(self.test_results)
        
        logger.info(f"\n🎯 OVERALL: {success_count}/{total_tests} components working correctly")
        
        return self.test_results

async def main():
    """Main test execution"""
    tester = ComponentTester()
    results = await tester.run_comprehensive_test()
    
    # Save results to file
    with open('/home/obaidsafi31/Desktop/Agentic BI /websocket_test_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info("\n📄 Test results saved to: websocket_test_results.json")

if __name__ == "__main__":
    asyncio.run(main())
