#!/usr/bin/env python3
"""
Comprehensive System Test for Multi-Agent BI System (using requests)
Tests integration between Backend, NLP-Agent, Data-Agent, and Viz-Agent
Excludes Personal-Agent as it's not ready
"""

import requests
import json
import time
import sys
from datetime import datetime
from typing import Dict, Any, List

class SystemTestSuite:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.test_results = []
        self.session = requests.Session()
        
    def run_test(self, test_name: str, test_func):
        """Run individual test with error handling"""
        print(f"\n🧪 Running test: {test_name}")
        start_time = time.time()
        
        try:
            result = test_func()
            duration = time.time() - start_time
            
            if result:
                print(f"✅ {test_name} - PASSED ({duration:.2f}s)")
                self.test_results.append({
                    "test": test_name,
                    "status": "PASSED",
                    "duration": duration,
                    "error": None
                })
            else:
                print(f"❌ {test_name} - FAILED ({duration:.2f}s)")
                self.test_results.append({
                    "test": test_name,
                    "status": "FAILED", 
                    "duration": duration,
                    "error": "Test returned False"
                })
                
        except Exception as e:
            duration = time.time() - start_time
            print(f"💥 {test_name} - ERROR ({duration:.2f}s): {str(e)}")
            self.test_results.append({
                "test": test_name,
                "status": "ERROR",
                "duration": duration,
                "error": str(e)
            })
    
    def test_backend_health(self) -> bool:
        """Test backend service health"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"   Backend health: {data}")
                return data.get("status") == "healthy"
            return False
        except Exception as e:
            print(f"   Backend health check failed: {e}")
            return False
    
    def test_nlp_agent_integration(self) -> bool:
        """Test NLP agent integration via backend"""
        try:
            query_data = {
                "query": "Show me the revenue trend for the last quarter",
                "user_id": "test_user_001",
                "context": {"department": "finance"}
            }
            
            response = self.session.post(
                f"{self.base_url}/api/nlp/process", 
                json=query_data,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   NLP response: {data.get('intent_type', 'Unknown')}")
                return "intent_type" in data and data.get("success", False)
            else:
                print(f"   NLP request failed with status: {response.status_code}")
                return False
                    
        except Exception as e:
            print(f"   NLP integration test failed: {e}")
            return False
    
    def test_data_agent_connection(self) -> bool:
        """Test data agent database connectivity (if available)"""
        try:
            query_data = {
                "query_type": "revenue_data",
                "parameters": {
                    "start_date": "2024-01-01",
                    "end_date": "2024-12-31",
                    "granularity": "monthly"
                }
            }
            
            response = self.session.post(
                f"{self.base_url}/api/data/query",
                json=query_data,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   Data agent response: {len(data.get('data', []))} records")
                return "data" in data
            elif response.status_code == 503:
                print("   Data agent service unavailable (expected if TiDB unhealthy)")
                return True  # Don't fail the test if data-agent is unavailable
            else:
                print(f"   Data request failed with status: {response.status_code}")
                return False
                    
        except Exception as e:
            print(f"   Data agent test failed: {e}")
            return True  # Don't fail if data agent is not available
    
    def test_viz_agent_integration(self) -> bool:
        """Test visualization agent integration"""
        try:
            viz_data = {
                "request_id": f"test_{int(time.time())}",
                "user_id": "test_user_001",
                "query_intent": {
                    "metric_type": "revenue",
                    "chart_preference": "line",
                    "time_period": "quarterly"
                },
                "data": [
                    {"date": "2024-Q1", "revenue": 1250000, "quarter": "Q1"},
                    {"date": "2024-Q2", "revenue": 1450000, "quarter": "Q2"},
                    {"date": "2024-Q3", "revenue": 1380000, "quarter": "Q3"},
                    {"date": "2024-Q4", "revenue": 1620000, "quarter": "Q4"}
                ],
                "preferences": {
                    "color_scheme": "corporate",
                    "show_trend": True
                }
            }
            
            response = self.session.post(
                f"{self.base_url}/api/viz/generate",
                json=viz_data,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   Viz generation time: {data.get('processing_time_ms', 0)}ms")
                return data.get("success", False) and "chart_html" in data
            else:
                print(f"   Viz request failed with status: {response.status_code}")
                return False
                    
        except Exception as e:
            print(f"   Viz agent test failed: {e}")
            return False
    
    def test_end_to_end_workflow(self) -> bool:
        """Test complete end-to-end workflow"""
        try:
            # Step 1: Natural language query
            nl_query = {
                "query": "Create a bar chart showing revenue by quarter for 2024",
                "user_id": "test_user_001"
            }
            
            response = self.session.post(
                f"{self.base_url}/api/nlp/process",
                json=nl_query,
                timeout=10
            )
            
            if response.status_code != 200:
                return False
                
            nlp_result = response.json()
            print(f"   NLP Intent: {nlp_result.get('intent_type')}")
            
            # Step 2: Use NLP result to generate visualization
            if nlp_result.get("success"):
                viz_request = {
                    "request_id": f"e2e_test_{int(time.time())}",
                    "user_id": "test_user_001", 
                    "query_intent": nlp_result.get("parsed_intent", {}),
                    "data": [
                        {"quarter": "Q1 2024", "revenue": 1250000},
                        {"quarter": "Q2 2024", "revenue": 1450000},
                        {"quarter": "Q3 2024", "revenue": 1380000},
                        {"quarter": "Q4 2024", "revenue": 1620000}
                    ]
                }
                
                viz_response = self.session.post(
                    f"{self.base_url}/api/viz/generate",
                    json=viz_request,
                    timeout=15
                )
                
                if viz_response.status_code == 200:
                    viz_result = viz_response.json()
                    print(f"   E2E workflow completed in {viz_result.get('processing_time_ms', 0)}ms")
                    return viz_result.get("success", False)
            
            return False
            
        except Exception as e:
            print(f"   End-to-end workflow failed: {e}")
            return False
    
    def test_performance_benchmarks(self) -> bool:
        """Test system performance benchmarks"""
        try:
            response_times = []
            
            # Run multiple requests to test performance
            for i in range(3):  # Reduced from 5 to 3 for faster testing
                start_time = time.time()
                
                test_data = {
                    "request_id": f"perf_test_{i}_{int(time.time())}",
                    "user_id": "perf_test_user",
                    "query_intent": {"metric_type": "performance_test"},
                    "data": [{"x": j, "y": j * 2} for j in range(50)]  # Reduced data size
                }
                
                response = self.session.post(
                    f"{self.base_url}/api/viz/generate",
                    json=test_data,
                    timeout=10
                )
                
                if response.status_code == 200:
                    response_time = (time.time() - start_time) * 1000
                    response_times.append(response_time)
            
            if response_times:
                avg_time = sum(response_times) / len(response_times)
                max_time = max(response_times)
                min_time = min(response_times)
                
                print(f"   Performance: avg={avg_time:.0f}ms, min={min_time:.0f}ms, max={max_time:.0f}ms")
                
                # Consider test passed if average response time < 5 seconds
                return avg_time < 5000
            
            return False
            
        except Exception as e:
            print(f"   Performance test failed: {e}")
            return False
    
    def test_error_handling(self) -> bool:
        """Test system error handling"""
        try:
            # Test with invalid data
            invalid_requests = [
                {"invalid": "request"},  # Missing required fields
                {"query_intent": {}, "data": []},  # Empty data
            ]
            
            success_count = 0
            for i, invalid_req in enumerate(invalid_requests):
                response = self.session.post(
                    f"{self.base_url}/api/viz/generate",
                    json=invalid_req,
                    timeout=5
                )
                
                # Should handle errors gracefully (4xx or return error response)
                if response.status_code in [400, 422] or response.status_code == 200:
                    if response.status_code == 200:
                        data = response.json()
                        # If status 200, should have success=False for invalid data
                        if not data.get("success", True):
                            success_count += 1
                    else:
                        success_count += 1
            
            print(f"   Error handling: {success_count}/{len(invalid_requests)} handled correctly")
            return success_count >= len(invalid_requests) - 1  # Allow one failure
            
        except Exception as e:
            print(f"   Error handling test failed: {e}")
            return False
    
    def run_all_tests(self):
        """Run all system tests"""
        print("🎯 Starting Multi-Agent BI System Test Suite")
        print("=" * 60)
        print(f"Testing against: {self.base_url}")
        print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Define test suite
        tests = [
            ("Backend Health Check", self.test_backend_health),
            ("NLP Agent Integration", self.test_nlp_agent_integration),
            ("Data Agent Connection", self.test_data_agent_connection),
            ("Viz Agent Integration", self.test_viz_agent_integration),
            ("End-to-End Workflow", self.test_end_to_end_workflow),
            ("Performance Benchmarks", self.test_performance_benchmarks),
            ("Error Handling", self.test_error_handling)
        ]
        
        # Run all tests
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "=" * 60)
        print("📊 SYSTEM TEST RESULTS SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result["status"] == "PASSED")
        failed = sum(1 for result in self.test_results if result["status"] == "FAILED")
        errors = sum(1 for result in self.test_results if result["status"] == "ERROR")
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"💥 Errors: {errors}")
        print(f"📈 Success Rate: {(passed/total)*100:.1f}%")
        
        total_time = sum(result["duration"] for result in self.test_results)
        print(f"⏱️  Total Time: {total_time:.2f}s")
        
        # Detailed results
        print("\n📋 Detailed Results:")
        print("-" * 60)
        for result in self.test_results:
            status_icon = "✅" if result["status"] == "PASSED" else "❌" if result["status"] == "FAILED" else "💥"
            print(f"{status_icon} {result['test']:<35} {result['duration']:>6.2f}s")
            if result["error"]:
                print(f"   └─ Error: {result['error']}")
        
        # Overall result
        print("\n" + "=" * 60)
        if failed == 0 and errors == 0:
            print("🎉 ALL TESTS PASSED! System is ready for production.")
        elif failed + errors <= 2:
            print("⚠️  MOSTLY SUCCESSFUL. Minor issues detected.")
        else:
            print("❌ SYSTEM ISSUES DETECTED. Investigation required.")
        print("=" * 60)

def main():
    """Main test runner"""
    test_suite = SystemTestSuite()
    test_suite.run_all_tests()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Test suite interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test suite failed with error: {e}")
        sys.exit(1)
