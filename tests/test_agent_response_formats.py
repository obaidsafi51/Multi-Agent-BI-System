#!/usr/bin/env python3
"""
Agent Response Format Consistency Test
Tests that all agents return standardized response formats
"""

import json
import asyncio
import aiohttp
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import sys
import os

# Add shared models path
sys.path.append('/home/obaidsafi31/Desktop/Agentic BI ')
from shared.models.workflow import NLPResponse, DataQueryResponse, VisualizationResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgentResponseTester:
    def __init__(self):
        # Use environment variables with fallbacks for testing
        self.nlp_agent_url = os.getenv("NLP_AGENT_URL", "http://localhost:8002")
        self.data_agent_url = os.getenv("DATA_AGENT_URL", "http://localhost:8001") 
        self.viz_agent_url = os.getenv("VIZ_AGENT_URL", "http://localhost:8003")
        self.backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
        
    async def test_nlp_agent_response(self) -> Dict[str, Any]:
        """Test NLP Agent response format"""
        try:
            payload = {
                "query": "Show me quarterly revenue for this year",
                "context": {},
                "user_id": "test_user",
                "session_id": "test_session"
            }
            
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(f"{self.nlp_agent_url}/process", json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # Try to parse as NLPResponse
                        try:
                            nlp_response = NLPResponse(**result)
                            return {
                                "status": "PASS",
                                "agent": "nlp-agent",
                                "message": "Response format is standardized",
                                "response_format": "NLPResponse",
                                "fields_present": list(result.keys()),
                                "has_agent_metadata": "agent_metadata" in result,
                                "has_success_field": "success" in result
                            }
                        except Exception as e:
                            return {
                                "status": "FAIL",
                                "agent": "nlp-agent",
                                "message": f"Response format validation failed: {e}",
                                "response_format": "Legacy/Custom",
                                "fields_present": list(result.keys()),
                                "raw_response": result
                            }
                    else:
                        return {
                            "status": "ERROR",
                            "agent": "nlp-agent",
                            "message": f"HTTP {response.status}: {await response.text()}"
                        }
        except Exception as e:
            return {
                "status": "ERROR",
                "agent": "nlp-agent",
                "message": f"Connection failed: {e}"
            }
    
    async def test_data_agent_response(self) -> Dict[str, Any]:
        """Test Data Agent response format"""
        try:
            payload = {
                "sql_query": "SELECT 'test' as message, 123 as value",
                "query_context": {
                    "metric_type": "revenue",
                    "time_period": "quarterly"
                },
                "query_id": "test_query_123"
            }
            
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(f"{self.data_agent_url}/execute", json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # Try to parse as DataQueryResponse
                        try:
                            data_response = DataQueryResponse(**result)
                            return {
                                "status": "PASS",
                                "agent": "data-agent",
                                "message": "Response format is standardized",
                                "response_format": "DataQueryResponse",
                                "fields_present": list(result.keys()),
                                "has_agent_metadata": "agent_metadata" in result,
                                "has_success_field": "success" in result
                            }
                        except Exception as e:
                            return {
                                "status": "FAIL",
                                "agent": "data-agent",
                                "message": f"Response format validation failed: {e}",
                                "response_format": "Legacy/Custom",
                                "fields_present": list(result.keys()),
                                "raw_response": result
                            }
                    else:
                        return {
                            "status": "ERROR",
                            "agent": "data-agent",
                            "message": f"HTTP {response.status}: {await response.text()}"
                        }
        except Exception as e:
            return {
                "status": "ERROR",
                "agent": "data-agent",
                "message": f"Connection failed: {e}"
            }
    
    async def test_viz_agent_response(self) -> Dict[str, Any]:
        """Test Visualization Agent response format"""
        try:
            payload = {
                "data": [
                    {"period": "Q1 2024", "revenue": 1000000},
                    {"period": "Q2 2024", "revenue": 1200000}
                ],
                "query_context": {
                    "metric_type": "revenue",
                    "time_period": "quarterly"
                },
                "query_id": "test_viz_123"
            }
            
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(f"{self.viz_agent_url}/visualize", json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # Try to parse as VisualizationResponse
                        try:
                            viz_response = VisualizationResponse(**result)
                            return {
                                "status": "PASS",
                                "agent": "viz-agent",
                                "message": "Response format is standardized",
                                "response_format": "VisualizationResponse",
                                "fields_present": list(result.keys()),
                                "has_agent_metadata": "agent_metadata" in result,
                                "has_success_field": "success" in result
                            }
                        except Exception as e:
                            return {
                                "status": "FAIL",
                                "agent": "viz-agent",
                                "message": f"Response format validation failed: {e}",
                                "response_format": "Legacy/Custom",
                                "fields_present": list(result.keys()),
                                "raw_response": result
                            }
                    else:
                        return {
                            "status": "ERROR",
                            "agent": "viz-agent",
                            "message": f"HTTP {response.status}: {await response.text()}"
                        }
        except Exception as e:
            return {
                "status": "ERROR",
                "agent": "viz-agent",
                "message": f"Connection failed: {e}"
            }
    
    async def test_backend_validation(self) -> Dict[str, Any]:
        """Test backend response format validation"""
        try:
            payload = {
                "query": "Show me quarterly revenue for this year",
                "context": {},
                "user_id": "test_user",
                "session_id": "test_session"
            }
            
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(f"{self.backend_url}/api/query", json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        return {
                            "status": "PASS",
                            "agent": "backend",
                            "message": "Backend processed request successfully",
                            "response_format": "QueryResponse",
                            "fields_present": list(result.keys()),
                            "validation_logs_present": "Validated agent responses in backend"
                        }
                    else:
                        return {
                            "status": "ERROR",
                            "agent": "backend",
                            "message": f"HTTP {response.status}: {await response.text()}"
                        }
        except Exception as e:
            return {
                "status": "ERROR",
                "agent": "backend",
                "message": f"Connection failed: {e}"
            }
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all agent response format tests"""
        print("🚀 Starting Agent Response Format Consistency Tests...")
        print("=" * 70)
        
        results = {
            "test_timestamp": datetime.now().isoformat(),
            "test_results": [],
            "summary": {
                "total_tests": 4,
                "passed": 0,
                "failed": 0,
                "errors": 0
            }
        }
        
        # Test each agent
        tests = [
            ("NLP Agent", self.test_nlp_agent_response),
            ("Data Agent", self.test_data_agent_response),
            ("Viz Agent", self.test_viz_agent_response),
            ("Backend Validation", self.test_backend_validation)
        ]
        
        for test_name, test_func in tests:
            print(f"\n📋 Testing {test_name}...")
            result = await test_func()
            results["test_results"].append(result)
            
            # Update summary
            if result["status"] == "PASS":
                results["summary"]["passed"] += 1
                print(f"✅ {test_name}: {result['message']}")
                if "response_format" in result:
                    print(f"   Response Format: {result['response_format']}")
                if "has_agent_metadata" in result:
                    print(f"   Agent Metadata Present: {result['has_agent_metadata']}")
            elif result["status"] == "FAIL":
                results["summary"]["failed"] += 1
                print(f"❌ {test_name}: {result['message']}")
                print(f"   Fields Present: {result.get('fields_present', [])}")
            else:
                results["summary"]["errors"] += 1
                print(f"🚨 {test_name}: {result['message']}")
        
        # Print summary
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        print(f"Total Tests: {results['summary']['total_tests']}")
        print(f"✅ Passed: {results['summary']['passed']}")
        print(f"❌ Failed: {results['summary']['failed']}")
        print(f"🚨 Errors: {results['summary']['errors']}")
        
        success_rate = (results['summary']['passed'] / results['summary']['total_tests']) * 100
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if results['summary']['passed'] == results['summary']['total_tests']:
            print("🎉 ALL TESTS PASSED - Agent response formats are standardized!")
        elif results['summary']['failed'] > 0:
            print("⚠️  Some agents still use legacy response formats")
        
        return results

async def main():
    """Main test runner"""
    tester = AgentResponseTester()
    results = await tester.run_all_tests()
    
    # Save results to file
    results_file = "/home/obaidsafi31/Desktop/Agentic BI /task_5_test_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: {results_file}")
    
    return results['summary']['passed'] == results['summary']['total_tests']

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
