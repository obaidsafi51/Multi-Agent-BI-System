#!/usr/bin/env python3
"""
Comprehensive test script to verify all components are working after communication fixes.
"""

import asyncio
import httpx
import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Test configuration
BACKEND_URL = "http://localhost:8000"
AGENT_URLS = {
    "nlp": "http://localhost:8011",
    "data": "http://localhost:8012", 
    "viz": "http://localhost:8013"
}

WEBSOCKET_URLS = {
    "nlp": "ws://localhost:8011",
    "data": "ws://localhost:8012",
    "viz": "ws://localhost:8013"
}

class ComponentTester:
    def __init__(self):
        self.results = {
            "backend": {"status": "unknown", "tests": [], "errors": []},
            "nlp_agent": {"status": "unknown", "tests": [], "errors": []},
            "data_agent": {"status": "unknown", "tests": [], "errors": []},
            "viz_agent": {"status": "unknown", "tests": [], "errors": []},
            "communication": {"status": "unknown", "tests": [], "errors": []}
        }
        
    def log(self, message, level="INFO"):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    async def test_agent_health(self, name, url):
        """Test agent health endpoint"""
        self.log(f"Testing {name} agent health at {url}")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{url}/health")
                if response.status_code == 200:
                    data = response.json()
                    self.results[f"{name}_agent"]["tests"].append("health_check: PASS")
                    self.log(f"{name.upper()} agent health: OK - {data}")
                    return True
                else:
                    self.results[f"{name}_agent"]["errors"].append(f"Health check failed: {response.status_code}")
                    return False
        except Exception as e:
            self.results[f"{name}_agent"]["errors"].append(f"Health check error: {str(e)}")
            self.log(f"{name.upper()} agent health check failed: {str(e)}", "ERROR")
            return False
            
    async def test_agent_functionality(self, name, url):
        """Test agent specific functionality"""
        self.log(f"Testing {name} agent functionality")
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                if name == "nlp":
                    # Test NLP agent query processing
                    payload = {"query": "Show me revenue by month", "user_id": "test_user"}
                    response = await client.post(f"{url}/process_query", json=payload)
                elif name == "data":
                    # Test data agent query execution
                    payload = {"query": "SELECT 1 as test_value", "user_id": "test_user"}
                    response = await client.post(f"{url}/execute_query", json=payload)
                elif name == "viz":
                    # Test viz agent chart creation
                    payload = {
                        "data": [{"month": "Jan", "revenue": 1000}],
                        "chart_type": "bar",
                        "title": "Test Chart",
                        "user_id": "test_user"
                    }
                    response = await client.post(f"{url}/create_visualization", json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    self.results[f"{name}_agent"]["tests"].append("functionality_test: PASS")
                    self.log(f"{name.upper()} agent functionality: OK")
                    return True
                else:
                    self.results[f"{name}_agent"]["errors"].append(f"Functionality test failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            self.results[f"{name}_agent"]["errors"].append(f"Functionality test error: {str(e)}")
            self.log(f"{name.upper()} agent functionality test failed: {str(e)}", "ERROR")
            return False
    
    async def test_backend_health(self):
        """Test backend health"""
        self.log("Testing backend health")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{BACKEND_URL}/health")
                if response.status_code == 200:
                    data = response.json()
                    self.results["backend"]["tests"].append("health_check: PASS")
                    self.log(f"Backend health: OK - {data}")
                    return True
                else:
                    self.results["backend"]["errors"].append(f"Health check failed: {response.status_code}")
                    return False
        except Exception as e:
            self.results["backend"]["errors"].append(f"Health check error: {str(e)}")
            self.log(f"Backend health check failed: {str(e)}", "ERROR")
            return False
    
    async def test_communication_flow(self):
        """Test end-to-end communication flow"""
        self.log("Testing end-to-end communication flow")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Test a complete query workflow
                payload = {
                    "query": "Show me sales data for the last month",
                    "user_id": "test_user"
                }
                response = await client.post(f"{BACKEND_URL}/api/query", json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    self.results["communication"]["tests"].append("e2e_query: PASS")
                    self.log("End-to-end communication: OK")
                    return True
                else:
                    self.results["communication"]["errors"].append(f"E2E test failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            self.results["communication"]["errors"].append(f"E2E test error: {str(e)}")
            self.log(f"End-to-end communication test failed: {str(e)}", "ERROR")
            return False
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("COMPONENT TEST SUMMARY")
        print("="*60)
        
        total_tests = 0
        total_passed = 0
        
        for component, results in self.results.items():
            print(f"\n{component.upper().replace('_', ' ')}:")
            print("-" * 40)
            
            tests = results.get("tests", [])
            errors = results.get("errors", [])
            
            if tests:
                for test in tests:
                    print(f"  ✓ {test}")
                    total_passed += 1
                    total_tests += 1
                    
            if errors:
                for error in errors:
                    print(f"  ✗ {error}")
                    total_tests += 1
            
            if not tests and not errors:
                print("  ⚠ No tests run")
        
        print("\n" + "="*60)
        print(f"OVERALL RESULT: {total_passed}/{total_tests} tests passed")
        
        if total_passed == total_tests and total_tests > 0:
            print("🎉 ALL COMPONENTS WORKING CORRECTLY!")
            return True
        else:
            print("❌ SOME COMPONENTS HAVE ISSUES")
            return False

async def main():
    """Main test function"""
    print("Multi-Agent BI System - Component Verification Test")
    print("=" * 60)
    
    tester = ComponentTester()
    
    # Test all agents
    agent_results = {}
    for agent_name, agent_url in AGENT_URLS.items():
        health_ok = await tester.test_agent_health(agent_name, agent_url)
        if health_ok:
            func_ok = await tester.test_agent_functionality(agent_name, agent_url)
            agent_results[agent_name] = health_ok and func_ok
            tester.results[f"{agent_name}_agent"]["status"] = "working" if (health_ok and func_ok) else "issues"
        else:
            agent_results[agent_name] = False
            tester.results[f"{agent_name}_agent"]["status"] = "not_responding"
    
    # Test backend
    backend_ok = await tester.test_backend_health()
    tester.results["backend"]["status"] = "working" if backend_ok else "not_responding"
    
    # Test communication if backend is working
    if backend_ok:
        comm_ok = await tester.test_communication_flow()
        tester.results["communication"]["status"] = "working" if comm_ok else "issues"
    
    # Print summary
    success = tester.print_summary()
    
    # Save results to file
    results_file = Path("component_test_results.json")
    with open(results_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "results": tester.results,
            "summary": {
                "all_working": success,
                "backend_status": tester.results["backend"]["status"],
                "agents_status": {k: tester.results[f"{k}_agent"]["status"] for k in AGENT_URLS.keys()}
            }
        }, f, indent=2)
    
    print(f"\nDetailed results saved to: {results_file}")
    
    return success

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Test failed with error: {e}")
        sys.exit(1)
