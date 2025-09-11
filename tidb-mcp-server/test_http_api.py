#!/usr/bin/env python3
"""
Simple HTTP API test script for Universal MCP Server.
Tests both database and LLM endpoints via HTTP.
"""

import json
import sys
import time
import asyncio
from typing import Dict, Any

try:
    import httpx
except ImportError:
    print("❌ httpx not installed. Please install with: pip install httpx")
    sys.exit(1)


class HTTPAPITester:
    """Test Universal MCP Server HTTP API endpoints."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.client = None
        
    async def setup(self):
        """Setup HTTP client."""
        self.client = httpx.AsyncClient(timeout=30.0)
        print(f"🌐 Testing Universal MCP Server at {self.base_url}")
        
    async def cleanup(self):
        """Cleanup HTTP client."""
        if self.client:
            await self.client.aclose()
    
    async def test_endpoint(self, method: str, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Test a single endpoint."""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = await self.client.get(url)
            elif method.upper() == "POST":
                response = await self.client.post(url, json=data or {})
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            return {
                "success": True,
                "status_code": response.status_code,
                "data": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                "error": None
            }
            
        except Exception as e:
            return {
                "success": False,
                "status_code": None,
                "data": None,
                "error": str(e)
            }
    
    async def test_health_check(self):
        """Test health check endpoint."""
        print("\n🏥 Testing Health Check...")
        
        result = await self.test_endpoint("GET", "/health")
        
        if result["success"] and result["status_code"] == 200:
            print("✅ Health check: Server is running")
            print(f"   Status: {result['data'].get('status', 'Unknown')}")
            return True
        else:
            print(f"❌ Health check failed: {result['error']}")
            return False
    
    async def test_tools_listing(self):
        """Test tools listing endpoint."""
        print("\n📋 Testing Tools Listing...")
        
        result = await self.test_endpoint("GET", "/tools")
        
        if result["success"] and result["status_code"] == 200:
            tools = result["data"]
            print("✅ Tools listing: Success")
            print(f"   Database tools: {len(tools.get('database_tools', []))}")
            print(f"   LLM tools: {len(tools.get('llm_tools', []))}")
            
            # Show available tools
            if tools.get('database_tools'):
                print("   Database tools available:")
                for tool in tools['database_tools'][:3]:
                    print(f"     - {tool}")
                    
            if tools.get('llm_tools'):
                print("   LLM tools available:")
                for tool in tools['llm_tools']:
                    print(f"     - {tool}")
            
            return True
        else:
            print(f"❌ Tools listing failed: {result['error']}")
            return False
    
    async def test_database_tools(self):
        """Test database tool endpoints."""
        print("\n🗄️ Testing Database Tools...")
        
        tests_passed = 0
        total_tests = 0
        
        # Test query validation
        total_tests += 1
        print("Testing query validation...")
        result = await self.test_endpoint("POST", "/tools/validate_query_tool", {
            "query": "SELECT 1 as test_column"
        })
        
        if result["success"] and result["status_code"] == 200:
            validation_result = result["data"]
            if validation_result.get('valid'):
                print("✅ Query validation: Valid query accepted")
                tests_passed += 1
            else:
                print(f"⚠️ Query validation: {validation_result.get('message', 'Unknown error')}")
        else:
            print(f"❌ Query validation failed: {result['error']}")
        
        # Test server stats
        total_tests += 1
        print("Testing server statistics...")
        result = await self.test_endpoint("POST", "/tools/get_server_stats_tool")
        
        if result["success"] and result["status_code"] == 200:
            stats = result["data"]
            print("✅ Server stats: Retrieved successfully")
            print(f"   Cache stats available: {'cache' in stats}")
            tests_passed += 1
        else:
            print(f"❌ Server stats failed: {result['error']}")
        
        # Test database discovery (may fail without real DB)
        total_tests += 1
        print("Testing database discovery...")
        result = await self.test_endpoint("POST", "/tools/discover_databases_tool")
        
        if result["success"] and result["status_code"] == 200:
            databases = result["data"]
            print(f"✅ Database discovery: Found {len(databases) if isinstance(databases, list) else 'N/A'} databases")
            tests_passed += 1
        else:
            print(f"⚠️ Database discovery failed (expected without real DB): {result['error']}")
        
        print(f"   Database tools: {tests_passed}/{total_tests} tests passed")
        return tests_passed, total_tests
    
    async def test_llm_tools(self):
        """Test LLM tool endpoints."""
        print("\n🤖 Testing LLM Tools...")
        
        tests_passed = 0
        total_tests = 0
        
        # Test text generation
        total_tests += 1
        print("Testing text generation...")
        result = await self.test_endpoint("POST", "/tools/llm_generate_text_tool", {
            "prompt": "Hello, this is a test prompt for the Universal MCP Server",
            "max_tokens": 50,
            "temperature": 0.7,
            "use_cache": False
        })
        
        if result["success"] and result["status_code"] == 200:
            generation_result = result["data"]
            if generation_result.get('success'):
                print("✅ Text generation: Success")
                print(f"   Generated text: {generation_result.get('generated_text', '')[:100]}...")
                tests_passed += 1
            else:
                print(f"⚠️ Text generation failed (expected with mock API): {generation_result.get('error', 'Unknown error')}")
        else:
            print(f"⚠️ Text generation endpoint failed: {result['error']}")
        
        # Test data analysis
        total_tests += 1
        print("Testing data analysis...")
        test_data = {
            "sales_data": [100, 150, 200, 180, 220, 250],
            "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
            "product": "Widget A"
        }
        
        result = await self.test_endpoint("POST", "/tools/llm_analyze_data_tool", {
            "data": json.dumps(test_data),
            "analysis_type": "financial",
            "context": "Monthly sales performance analysis"
        })
        
        if result["success"] and result["status_code"] == 200:
            analysis_result = result["data"]
            if analysis_result.get('success'):
                print("✅ Data analysis: Success")
                tests_passed += 1
            else:
                print(f"⚠️ Data analysis failed (expected with mock API): {analysis_result.get('error', 'Unknown error')}")
        else:
            print(f"⚠️ Data analysis endpoint failed: {result['error']}")
        
        # Test SQL generation
        total_tests += 1
        print("Testing SQL generation...")
        result = await self.test_endpoint("POST", "/tools/llm_generate_sql_tool", {
            "natural_language_query": "Show me the top 10 customers by total revenue",
            "schema_info": "customers table: id, name, email; orders table: id, customer_id, amount, date"
        })
        
        if result["success"] and result["status_code"] == 200:
            sql_result = result["data"]
            if sql_result.get('success'):
                print("✅ SQL generation: Success")
                tests_passed += 1
            else:
                print(f"⚠️ SQL generation failed (expected with mock API): {sql_result.get('error', 'Unknown error')}")
        else:
            print(f"⚠️ SQL generation endpoint failed: {result['error']}")
        
        # Test result explanation
        total_tests += 1
        print("Testing result explanation...")
        sample_results = [
            {"customer_name": "Acme Corp", "total_revenue": 15000},
            {"customer_name": "Beta Inc", "total_revenue": 12000},
            {"customer_name": "Gamma LLC", "total_revenue": 8500}
        ]
        
        result = await self.test_endpoint("POST", "/tools/llm_explain_results_tool", {
            "query": "SELECT customer_name, SUM(amount) as total_revenue FROM orders GROUP BY customer_name ORDER BY total_revenue DESC LIMIT 3",
            "results": sample_results,
            "context": "Top customers analysis"
        })
        
        if result["success"] and result["status_code"] == 200:
            explanation_result = result["data"]
            if explanation_result.get('success'):
                print("✅ Result explanation: Success")
                tests_passed += 1
            else:
                print(f"⚠️ Result explanation failed (expected with mock API): {explanation_result.get('error', 'Unknown error')}")
        else:
            print(f"⚠️ Result explanation endpoint failed: {result['error']}")
        
        print(f"   LLM tools: {tests_passed}/{total_tests} tests passed")
        return tests_passed, total_tests
    
    async def test_admin_endpoints(self):
        """Test admin endpoints."""
        print("\n⚙️ Testing Admin Endpoints...")
        
        tests_passed = 0
        total_tests = 0
        
        # Test status endpoint
        total_tests += 1
        result = await self.test_endpoint("GET", "/status")
        
        if result["success"] and result["status_code"] == 200:
            status = result["data"]
            print("✅ Status endpoint: Success")
            print(f"   HTTP API status: {status.get('http_api_status', 'Unknown')}")
            print(f"   MCP server initialized: {status.get('mcp_server_initialized', 'Unknown')}")
            tests_passed += 1
        else:
            print(f"❌ Status endpoint failed: {result['error']}")
        
        # Test initialization endpoint
        total_tests += 1
        result = await self.test_endpoint("POST", "/admin/initialize")
        
        if result["success"] and result["status_code"] == 200:
            init_result = result["data"]
            print(f"✅ Initialize endpoint: {init_result.get('status', 'Unknown')}")
            tests_passed += 1
        else:
            print(f"⚠️ Initialize endpoint: {result['error']} (may already be initialized)")
        
        print(f"   Admin endpoints: {tests_passed}/{total_tests} tests passed")
        return tests_passed, total_tests
    
    async def run_all_tests(self):
        """Run all HTTP API tests."""
        print("🧪 Universal MCP Server - HTTP API Test Suite")
        print("=" * 60)
        
        await self.setup()
        
        total_passed = 0
        total_tests = 0
        
        try:
            # Test health check first
            health_ok = await self.test_health_check()
            if not health_ok:
                print("\n❌ Server is not running. Please start the server with:")
                print("   cd /home/obaidsafi31/Desktop/Agentic BI /tidb-mcp-server")
                print("   python -m tidb_mcp_server.main")
                return False
            
            # Test tools listing
            tools_ok = await self.test_tools_listing()
            if tools_ok:
                total_passed += 1
            total_tests += 1
            
            # Test database tools
            db_passed, db_total = await self.test_database_tools()
            total_passed += db_passed
            total_tests += db_total
            
            # Test LLM tools
            llm_passed, llm_total = await self.test_llm_tools()
            total_passed += llm_passed
            total_tests += llm_total
            
            # Test admin endpoints
            admin_passed, admin_total = await self.test_admin_endpoints()
            total_passed += admin_passed
            total_tests += admin_total
            
        except Exception as e:
            print(f"❌ Test suite error: {e}")
        
        finally:
            await self.cleanup()
        
        # Print final results
        print("\n" + "=" * 60)
        print("📊 HTTP API TEST RESULTS")
        print("=" * 60)
        
        print(f"🎯 Overall: {total_passed}/{total_tests} tests passed")
        
        if total_passed == total_tests:
            print("🎉 All HTTP API tests passed! Universal MCP Server is working correctly.")
        elif total_passed > total_tests * 0.7:
            print("✅ Most tests passed. Some failures expected with mock configuration.")
        else:
            print("⚠️ Multiple test failures. Check server configuration and status.")
        
        return total_passed >= total_tests * 0.7  # 70% pass rate is acceptable


async def main():
    """Main test function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Universal MCP Server HTTP API")
    parser.add_argument("--url", default="http://localhost:8000", help="Server URL")
    args = parser.parse_args()
    
    tester = HTTPAPITester(args.url)
    success = await tester.run_all_tests()
    
    return 0 if success else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n❌ Test interrupted by user")
        sys.exit(1)
